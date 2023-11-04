# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import datetime
import os
import shutil
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests
from sqlalchemy import func
# useful for handling different item types with a single interface
from sqlalchemy.orm import sessionmaker
import scrapy
import pytz
from urllib import parse

from phpbbscrapy.items import PostItem, ThreadItem, CategoryItem, BoardItem, PostAttachmentItem
from phpbbscrapy.models import create_table, db_connect, Category, Thread, Post, Board
from scrapy.exceptions import DropItem
from scrapy.pipelines.files import FilesPipeline
from scrapy.pipelines.images import ImagesPipeline


class DatabasePipeline:
    def __init__(self) -> None:
        """
        Initializes database connection and sessionmaker
        Creates tables
        """
        engine = db_connect()
        create_table(engine)


class BoardPipeline:
    def __init__(self) -> None:
        engine = db_connect()
        self.session = sessionmaker(bind=engine)

    def process_item(self, item, spider):
        if isinstance(item, BoardItem):
            self.store_db(item)

        return item

    def store_db(self, item):
        with self.session() as session:
            found = session.query(Board).filter_by(name=item['name']).first()

            if not found:
                session.add(Board(**item))
                print("Added board with name: " + item['name'])
                session.commit()
                session.close()
            else:
                session.close()
                raise DropItem("Duplicate item found: %s" % item)


class AttachmentPipeline:
    def process_item(self, item, spider):
        if isinstance(item, PostAttachmentItem):
            self.save_file(item)

    def save_file(self, item):
        url = item['url']
        post_id = int(item["post_id"])
        thread_id = int(item["thread_id"])
        category_id = int(item["category_id"])
        board_name = item["board_name"]

        attachment_local_path = f'attachments/{board_name}/{category_id}/{thread_id}/{post_id}/'
        # create directory if it doesn't exist
        os.makedirs(attachment_local_path, exist_ok=True)

        filename = item['filename']
        file_extension = filename.split('.')[-1]
        filename = filename.replace(f'.{file_extension}', '')

        # convert filename to something that can be used as a filename, replace all non-alphanumeric characters with _
        filename = ''.join([c if c.isalnum() else '_' for c in filename])
        filename += f'.{file_extension}'
        attachment_local_path += filename

        if not os.path.exists(attachment_local_path):
            response = requests.get(url)
            with open(attachment_local_path, 'wb') as f:
                f.write(response.content)
            del response


class PostPipeline:
    def __init__(self) -> None:
        engine = db_connect()
        self.session = sessionmaker(bind=engine)

    def process_item(self, item, spider):
        if isinstance(item, PostItem):
            return self.store_db(item)

        return item

    def store_db(self, item):
        post_id = int(item["post_id"])
        thread_id = int(item["thread_id"])
        category_id = int(item["category_id"])
        board_name = item["board_name"]

        category = get_category_from_db(self.session, board_name, category_id)
        thread = get_thread_from_db(self.session, category, thread_id)

        with self.session() as session:
            found = session.query(Post).filter_by(post_id=post_id, thread_id=thread.id).first()

            if not found:
                del item["board_name"]
                del item["category_id"]
                del item["file_urls"]
                del item["image_urls"]

                if "files" in item:
                    del item["files"]
                if "images" in item:
                    del item["images"]

                item['thread_id'] = thread.id

                session.add(Post(**item))
                session.commit()
                session.close()

                return item
            else:
                session.close()
                raise DropItem("Duplicate item found: %s" % item)


class MyFilesPipeline(FilesPipeline):
    def get_media_requests(self, item, info):
        if "file_urls" not in item:
            return

        for attachment in item["file_urls"]:
            url = attachment['url']
            yield scrapy.Request(url)
    def file_path(self, request, response=None, info=None, *, item=None):
        file_urls = item["file_urls"]
        found_item = next((x for x in file_urls if x['url'] == request.url), None)

        if not found_item:
            raise DropItem("Image not found: %s" % request.url)

        post_id = int(item["post_id"])
        thread_id = int(item["thread_id"])
        category_id = int(item["category_id"])
        board_name = item["board_name"]

        attachment_local_path = f'{board_name}/{category_id}/{thread_id}/{post_id}/'

        filename = found_item['filename']
        file_extension = filename.split('.')[-1]
        filename = filename.replace(f'.{file_extension}', '')

        # convert filename to something that can be used as a filename, replace all non-alphanumeric characters with _
        filename = ''.join([c if c.isalnum() else '_' for c in filename])
        filename += f'.{file_extension}'
        attachment_local_path += filename

        return attachment_local_path

class MyImagesPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        if "image_urls" not in item:
            return

        for attachment in item["image_urls"]:
            url = attachment['url']
            yield scrapy.Request(url)

    def file_path(self, request, response=None, info=None, *, item=None):
        image_urls = item["image_urls"]
        found_item = next((x for x in image_urls if x['url'] == request.url), None)

        if not found_item:
            raise DropItem("Image not found: %s" % request.url)

        post_id = int(item["post_id"])
        thread_id = int(item["thread_id"])
        category_id = int(item["category_id"])
        board_name = item["board_name"]

        attachment_local_path = f'{board_name}/{category_id}/{thread_id}/{post_id}/'

        filename = found_item['filename']
        file_extension = filename.split('.')[-1]
        filename = filename.replace(f'.{file_extension}', '')

        # convert filename to something that can be used as a filename, replace all non-alphanumeric characters with _
        filename = ''.join([c if c.isalnum() else '_' for c in filename])
        filename += f'.{file_extension}'
        attachment_local_path += filename

        return attachment_local_path


def get_category_from_db(sessionmaker, board_name, category_id):
    with sessionmaker() as session:
        found = session.query(Category).filter_by(category_id=category_id, board_name=board_name).first()

        if not found:
            return None

        return found

def remove_unwanted_query_parameters(url, unwanted_query_parameters):
    split = parse.urlsplit(url)
    query = split.query
    parsed = parse.parse_qs(query)
    parameters = dict(parsed)

    for unwanted_query_parameter in unwanted_query_parameters:
        if unwanted_query_parameter in parameters:
            del parameters[unwanted_query_parameter]

    query = parse.urlencode(parameters, doseq=True)
    return parse.urlunsplit((split.scheme, split.netloc, split.path, query, split.fragment))


class ThreadPipeline:
    def __init__(self) -> None:
        engine = db_connect()
        self.session = sessionmaker(bind=engine)
        session = self.session()
        self.threads = [(e[0], e[1].replace(tzinfo=pytz.UTC)) for e in
                        session.query(Thread.id, Thread.last_post_date).all()]
        session.close()

    def process_item(self, item, spider):
        if isinstance(item, ThreadItem):
            return self.store_db(item)

        return item

    def store_db(self, item):
        session = self.session()
        thread_id = int(item["thread_id"])
        category_id = int(item["category_id"])
        board_name = item["board_name"]

        category = get_category_from_db(self.session, board_name, category_id)
        found = get_thread_from_db(self.session, category, thread_id)
        session.close()

        if not found:
            with self.session() as session:
                del item["board_name"]

                item['category_id'] = category.id

                session.add(Thread(**item))
                session.commit()
                session.close()
                return item
        else:
            raise DropItem("Duplicate item found: %s" % item)

        # with self.session() as session:
        #     found_latest_post = session.query(Post).filter_by(thread_id=thread_id).order_by(Post.date.desc()).first()
        #     thread_last_post_date = item["last_post_date"].replace(tzinfo=pytz.UTC)
        #     database_thread_last_post_date = found_latest_post.date.replace(tzinfo=pytz.UTC)
        #
        #     if database_thread_last_post_date < thread_last_post_date:
        #         found.last_post_date = thread_last_post_date
        #         found.number_of_posts = item["number_of_posts"]
        #         session.commit()
        #         session.close()
        #         return item
        #     else:
        #         session.close()
        #         raise DropItem("Duplicate item found: %s" % item)


class CategoryPipeline:
    def __init__(self) -> None:
        engine = db_connect()
        self.session = sessionmaker(bind=engine)

    def process_item(self, item, spider):
        if isinstance(item, CategoryItem):
            return self.store_db(item)

        return item

    def store_db(self, item):
        session = self.session()
        category_id = int(item["category_id"])
        board_name = item["board_name"]
        found = session.query(Category).filter_by(category_id=category_id, board_name=board_name).first()
        session.close()

        if not found:
            with self.session() as session:

                # remove sid from url and keep everything elese
                item["url"] = remove_unwanted_query_parameters(item["url"], ["sid"])


                session.add(Category(**item))
                session.commit()
                session.close()
                return item
        else:
            raise DropItem("Duplicate item found: %s" % item)

        # with self.session() as session:
        #     found_latest_thread = session.query(Thread).filter_by(category_id=category_id).order_by(
        #         Thread.last_post_date.desc()).first()
        #     thread_id = found_latest_thread.id
        #     found_latest_post = session.query(Post).filter_by(thread_id=thread_id).order_by(Post.date.desc()).first()
        #     category_last_post_date = item["last_post_date"].replace(tzinfo=pytz.UTC)
        #     database_category_last_post_date = found_latest_post.date.replace(tzinfo=pytz.UTC)
        #
        #     if database_category_last_post_date < category_last_post_date:
        #         found.last_post_date = category_last_post_date
        #         found.number_of_posts = item["number_of_posts"]
        #         session.commit()
        #         session.close()
        #         return item
        #     else:
        #         session.close()
        #         raise DropItem("Duplicate item found: %s" % item)


def get_post_count_in_category(sessionmaker, board_name, category_id):
    with sessionmaker() as session:
        category_in_db = session.query(Category).filter_by(category_id=category_id, board_name=board_name).first()

        if not category_in_db:
            return 0

        child_categories = session.query(Category).filter_by(parent_id=category_in_db.id, board_name=board_name)
        post_count_in_child_categories = 0
        for child_category in child_categories:
            post_count_in_child_categories += get_post_count_in_category(sessionmaker, board_name, child_category.category_id)

        thread_post_groups = session.query(Post.id, func.count(Post.id)).join(Thread).filter_by(
            category_id=category_in_db.id).group_by(Post.thread_id).all()
        post_count_in_threads = sum([e[1] for e in thread_post_groups])

        return post_count_in_child_categories + post_count_in_threads


def get_thread_from_db(sessionmaker, category, thread_id):
    with sessionmaker() as session:
        if not category:
            return None

        thread_in_db = session.query(Thread).filter_by(thread_id=thread_id, category_id=category.id).first()

        if not thread_in_db:
            return None

        return thread_in_db


def get_last_post_date_in_category(sessionmaker, board_name, category_id):
    with sessionmaker() as session:
        category_in_db = session.query(Category).filter_by(category_id=category_id, board_name=board_name).first()
        child_categories = session.query(Category).filter_by(parent_id=category_in_db.id, board_name=board_name)
        last_post_date = datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=pytz.UTC)

        for child_category in child_categories:
            child_category_post_date = get_last_post_date_in_category(sessionmaker, board_name, child_category.category_id)

            if child_category_post_date > last_post_date:
                last_post_date = child_category_post_date

        category_post = session.query(Post.date).join(Thread).filter_by(category_id=category_in_db.id).order_by(
            Post.date.desc()).first()

        if category_post:
            category_post_date = category_post[0].replace(tzinfo=pytz.UTC)

            if category_post_date > last_post_date:
                last_post_date = category_post_date

        return last_post_date


def get_last_post_datein_thread(sessionmaker, thread_id):
    with sessionmaker() as session:
        last_post_date = datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=pytz.UTC)
        thread_in_db = session.query(Thread).filter_by(thread_id=thread_id).first()
        post = session.query(Post.date).filter_by(thread_id=thread_in_db.id).order_by(Post.date.desc()).first()

        if post:
            post_date = post[0].replace(tzinfo=pytz.UTC)

            if post_date > last_post_date:
                last_post_date = post_date

        return last_post_date


def get_post_count_in_thread(sessionmaker, category, thread_id):
    with sessionmaker() as session:
        thread_in_db = get_thread_from_db(sessionmaker, category, thread_id)

        if not thread_in_db:
            return 0

        count_in_db = session.query(Post).filter_by(thread_id=thread_in_db.id).count()

        return count_in_db
