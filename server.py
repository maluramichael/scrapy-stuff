from flask import (
    Flask,
    render_template
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from scrapy.utils.project import get_project_settings

from phpbbscrapy.models import Category, Thread, Post

engine = create_engine(get_project_settings().get("CONNECTION_STRING"))
Session = sessionmaker(bind=engine)

# Create the application instance
app = Flask(__name__, template_folder="templates")
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/')
def home():
    session = Session()
    categories = session.query(Category).all()
    session.close()
    return render_template('home.html', categories=categories)

@app.route('/category/<int:category_id>')
def categories(category_id):
    session = Session()
    categories = session.query(Category).all()
    threads = session.query(Thread).filter_by(category_id=category_id).all()
    session.close()
    return render_template('threads.html', categories=categories, threads=threads)

@app.route('/category/<int:category_id>/<int:thread_id>')
def posts(category_id, thread_id):
    session = Session()
    categories = session.query(Category).all()
    posts = session.query(Post).filter_by(thread_id=thread_id).all()
    thread = session.query(Thread).filter_by(id=thread_id).first()
    session.close()
    return render_template('posts.html', categories=categories, posts=posts, thread=thread)
