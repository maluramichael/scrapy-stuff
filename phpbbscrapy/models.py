from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from scrapy.utils.project import get_project_settings

Base = declarative_base()

def db_connect():
    return create_engine(get_project_settings().get("CONNECTION_STRING"))


def create_table(engine):
    Base.metadata.create_all(engine)

class Category(Base):
    __tablename__ = 'category'
    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False)
    description = Column(Text(), nullable=False, default='')
    url = Column(String(250), nullable=False)
    parent_id = Column(Integer, ForeignKey('category.id'))
    parent = relationship('Category', remote_side=[id])
    number_of_posts = Column(Integer, nullable=False, default=0)
    last_post_date = Column(DateTime(timezone=True), nullable=False)

class Thread(Base):
    __tablename__ = 'thread'
    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    author = Column(String(250), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    number_of_posts = Column(Integer, nullable=False)
    last_post_date = Column(DateTime(timezone=True), nullable=False)
    url = Column(String(250), nullable=False)

class Post(Base):
    __tablename__ = 'post'
    id = Column(Integer, primary_key=True)
    content = Column(Text(), nullable=False, default='')
    author = Column(String(250), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    url = Column(String(250), nullable=False)
    thread_id = Column(Integer, ForeignKey('thread.id'))
    thread = relationship(Thread)
