import datetime
from datetime import time

from flask import (
    Flask,
    render_template, request, Response
)
from flask_cors import CORS, cross_origin
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from scrapy.utils.project import get_project_settings

from opensearch import opensearch
from phpbbscrapy.models import Category, Thread, Post

engine = create_engine(get_project_settings().get("CONNECTION_STRING"))
Session = sessionmaker(bind=engine)

# Create the application instance
app = Flask(__name__, template_folder="templates")
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
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
    page = int(request.args.get('page') or 1)
    page_size = 20
    with Session() as session:
        posts_query = session.query(Post).filter_by(thread_id=thread_id)
        number_of_posts = posts_query.count()
        thread = session.query(Thread).filter_by(id=thread_id).first()
        session.close()
        return render_template(
            'posts.html',
            categories=session.query(Category).all(),
            posts=posts_query.order_by(Post.date.asc()).limit(page_size).offset((page - 1) * page_size).all(),
            number_of_posts=number_of_posts,
            pages=list(range(1, number_of_posts // page_size + 1)),
            thread=thread
        )


@app.route('/search', methods=['GET'])
@cross_origin()
def search_posts():
    query = request.args.get('q')
    if not query:
        return []

    ranges = []

    for i in range(1, 15, 3):
        now = datetime.datetime.now()
        ranges.append({
            "range": {
                "date": {
                    "gte": (now - datetime.timedelta(days=i*30)).isoformat(),
                    "boost": 15 - i
                }
            }
        })

    data = opensearch.search(
        index="posts",
        body={
            "query": {
                "bool": {
                    "must": {
                        "match": {
                            "content": {
                                "query": query,
                                "operator": "AND"
                            }
                        }
                    },
                    "should": ranges
                }
            },
            "highlight": {
                "fields": {
                    "content": {}
                }
            },
            "size": 30
        }
    )
    return data
