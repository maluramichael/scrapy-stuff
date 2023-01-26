# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import datetime

from sqlalchemy import func
# useful for handling different item types with a single interface
from sqlalchemy.orm import sessionmaker
import pytz

from phpbbscrapy.items import PostItem, ThreadItem, CategoryItem, BoardItem
from phpbbscrapy.models import create_table, db_connect, Category, Thread, Post, Board
from scrapy.exceptions import DropItem


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


class PostPipeline:
    def __init__(self) -> None:
        engine = db_connect()
        self.session = sessionmaker(bind=engine)

    def process_item(self, item, spider):
        if isinstance(item, PostItem):
            self.store_db(item)

        return item

    def store_db(self, item):
        id = int(item["id"])

        with self.session() as session:
            found = session.query(Post).filter_by(id=id).first()

            if not found:
                session.add(Post(**item))
                print("Added post with id: " + str(id))
                session.commit()
                session.close()
            else:
                session.close()
                raise DropItem("Duplicate item found: %s" % item)


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
            self.store_db(item)

        return item

    def store_db(self, item):
        session = self.session()
        thread_id = int(item["id"])
        found = session.query(Thread).filter_by(id=thread_id).first()
        session.close()

        if not found:
            with self.session() as session:
                session.add(Thread(**item))
                session.commit()
                session.close()
                return item
        else:
            raise DropItem("Duplicate item found: %s" % item)

        with self.session() as session:
            found_latest_post = session.query(Post).filter_by(thread_id=thread_id).order_by(Post.date.desc()).first()
            thread_last_post_date = item["last_post_date"].replace(tzinfo=pytz.UTC)
            database_thread_last_post_date = found_latest_post.date.replace(tzinfo=pytz.UTC)

            if database_thread_last_post_date < thread_last_post_date:
                found.last_post_date = thread_last_post_date
                found.number_of_posts = item["number_of_posts"]
                session.commit()
                session.close()
                return item
            else:
                session.close()
                raise DropItem("Duplicate item found: %s" % item)


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
        category_id = int(item["id"])
        found = session.query(Category).filter_by(id=category_id).first()
        session.close()

        if not found:
            with self.session() as session:
                session.add(Category(**item))
                session.commit()
                session.close()
                return item
        else:
            raise DropItem("Duplicate item found: %s" % item)

        with self.session() as session:
            found_latest_thread = session.query(Thread).filter_by(category_id=category_id).order_by(
                Thread.last_post_date.desc()).first()
            thread_id = found_latest_thread.id
            found_latest_post = session.query(Post).filter_by(thread_id=thread_id).order_by(Post.date.desc()).first()
            category_last_post_date = item["last_post_date"].replace(tzinfo=pytz.UTC)
            database_category_last_post_date = found_latest_post.date.replace(tzinfo=pytz.UTC)

            if database_category_last_post_date < category_last_post_date:
                found.last_post_date = category_last_post_date
                found.number_of_posts = item["number_of_posts"]
                session.commit()
                session.close()
                return item
            else:
                session.close()
                raise DropItem("Duplicate item found: %s" % item)


def get_post_count_in_category(sessionmaker, category_id):
    with sessionmaker() as session:
        child_categories = session.query(Category).filter_by(parent_id=category_id)
        post_count_in_child_categories = 0
        for child_category in child_categories:
            post_count_in_child_categories += get_post_count_in_category(sessionmaker, child_category.id)

        thread_post_groups = session.query(Post.id, func.count(Post.id)).join(Thread).filter_by(
            category_id=category_id).group_by(Post.thread_id).all()
        post_count_in_threads = sum([e[1] for e in thread_post_groups])

        return post_count_in_child_categories + post_count_in_threads


def get_last_post_date_in_category(sessionmaker, category_id):
    with sessionmaker() as session:
        child_categories = session.query(Category).filter_by(parent_id=category_id)
        last_post_date = datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=pytz.UTC)

        for child_category in child_categories:
            child_category_post_date = get_last_post_date_in_category(sessionmaker, child_category.id)

            if child_category_post_date > last_post_date:
                last_post_date = child_category_post_date

        category_post = session.query(Post.date).join(Thread).filter_by(category_id=category_id).order_by(Post.date.desc()).first()

        if category_post:
            category_post_date = category_post[0].replace(tzinfo=pytz.UTC)

            if category_post_date > last_post_date:
                last_post_date = category_post_date

        return last_post_date


def get_last_post_datein_thread(sessionmaker, thread_id):
    with sessionmaker() as session:
        last_post_date = datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=pytz.UTC)
        post = session.query(Post.date).filter_by(thread_id=thread_id).order_by(Post.date.desc()).first()

        if post:
            post_date = post[0].replace(tzinfo=pytz.UTC)

            if post_date > last_post_date:
                last_post_date = post_date

        return last_post_date


def get_post_count_in_thread(sessionmaker, thread):
    with sessionmaker() as session:
        thread_id = int(thread["id"])
        return session.query(Post).filter_by(thread_id=thread_id).count()
