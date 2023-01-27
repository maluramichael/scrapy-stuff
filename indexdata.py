import re

from bs4 import BeautifulSoup
from opensearchpy import helpers
from scrapy.utils.project import get_project_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from opensearch import opensearch, create_index

from phpbbscrapy.models import Category, Thread, Post

engine = create_engine(get_project_settings().get("CONNECTION_STRING"))
Session = sessionmaker(bind=engine)

session = Session()
categories = session.query(Category).all()

create_index()


def cleanup_content(content):
    soup = BeautifulSoup(content, 'lxml')
    soup_get_text = soup.get_text()
    result_text = re.sub(r' +', r' ', soup_get_text).strip()
    return result_text


for category in categories:
    threads = session.query(Thread).filter_by(category_id=category.id).all()
    for thread in threads:
        print("Index thread: %s" % thread.title)
        posts = session.query(Post).filter_by(thread_id=thread.id).all()
        docs = []
        for post in posts:
            clean_content = cleanup_content(post.content)
            docs.append({
                "_index": "posts",
                "post_id": post.id,
                "thread_id": thread.id,
                "category_id": category.id,
                "title": thread.title,
                "url": thread.url,
                "content": clean_content,
                "category": category.title,
                "author": post.author,
                "date": post.date
            })


        helpers.bulk(opensearch, docs)

session.close()
