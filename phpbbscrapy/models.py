from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from scrapy.utils.project import get_project_settings

Base = declarative_base()


def db_connect():
    connection_string = get_project_settings().get("CONNECTION_STRING")
    engine = create_engine(connection_string)
    return engine


def create_table(engine):
    Base.metadata.create_all(engine)


class Board(Base):
    __tablename__ = 'board'
    name = Column(String(50), primary_key=True, nullable=False)


class Category(Base):
    __tablename__ = 'category'
    id = Column(Integer, primary_key=True, autoincrement=False)
    title = Column(String(250), nullable=False)
    description = Column(Text(), nullable=False, default='')
    url = Column(Text(4294000000), nullable=False)
    parent_id = Column(Integer, ForeignKey('category.id'))
    parent = relationship('Category', remote_side=[id])
    board_name = Column(String(50), ForeignKey('board.name'), primary_key=True)
    board = relationship(Board)
    number_of_posts = Column(Integer, nullable=False, default=0)
    last_post_date = Column(DateTime(timezone=True), nullable=False)


class Thread(Base):
    __tablename__ = 'thread'
    id = Column(Integer, primary_key=True, autoincrement=False)
    title = Column(String(250), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'), primary_key=True )
    category = relationship(Category)
    author = Column(String(250), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    number_of_posts = Column(Integer, nullable=False)
    last_post_date = Column(DateTime(timezone=True), nullable=False)
    url = Column(Text(4294000000), nullable=False)


class Post(Base):
    __tablename__ = 'post'
    id = Column(Integer, primary_key=True, autoincrement=False)
    content = Column(Text(4294000000), nullable=False, default='')
    author = Column(String(250), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    url = Column(Text(4294000000), nullable=False)
    thread_id = Column(Integer, ForeignKey('thread.id'), primary_key=True)
    thread = relationship(Thread)
