import base64
import datetime
import os
from datetime import time
import PIL
import magic
from PIL import Image
from flask import (
    Flask,
    render_template, request, Response
)
import ffmpeg
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


@app.route('/images/<path:path>')
def images(path):
    decode_base64_string = lambda s: base64.b64decode(s.encode('utf-8')).decode('utf-8')
    decoded_path = decode_base64_string(path)
    thumbnail_path = f"thumbnails/{path}.jpg"
    local_path = f"/Volumes{decoded_path}"

    if not os.path.exists(local_path):
        return {}

    try:
        if not os.path.exists(thumbnail_path):
            mime = magic.from_file(local_path, mime=True)
            thumbnail_size = 200

            if mime.startswith('image'):
                with Image.open(local_path) as pillow_image:
                    pillow_image.thumbnail((thumbnail_size, thumbnail_size))
                    pillow_image.save(thumbnail_path)
            elif mime.startswith('video'):
                probe = ffmpeg.probe(local_path)
                streams = probe['streams']
                first_video_stream = next((stream for stream in streams if stream['codec_type'] == 'video'), None)

                if not first_video_stream:
                    return {}

                if 'duration' not in first_video_stream:
                    return {}

                duration = first_video_stream['duration']
                time = int(float(duration) / 2)
                width = first_video_stream['width']

                if width > thumbnail_size:
                    width = thumbnail_size

                ffmpeg.input(local_path, ss=time).filter('scale', width, -1).output(thumbnail_path, vframes=1, update=True).run()
            else:
                return {}

        return Response(open(thumbnail_path, 'rb').read(), mimetype="image/jpeg")
    except Exception as e:
        # return erro 500
        return {}


@app.route('/search', methods=['GET'])
@cross_origin()
def search_posts():
    query = request.args.get('q')
    page = int(request.args.get('page')) or 0
    size = int(request.args.get('size')) or 10

    if not query:
        return []

    ranges = []

    for i in range(1, 15, 3):
        now = datetime.datetime.now()
        ranges.append({
            "range": {
                "date": {
                    "gte": (now - datetime.timedelta(days=i * 30)).isoformat(),
                    "boost": 15 - i
                }
            }
        })

    data = opensearch.search(
        index=["posts", "fs"],
        body={
            "from": page * size,
            "size": size,
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": ["content", "title", "filename", "path", "meta_data"],
                            "operator": "AND"
                        },
                    },
                    "should": [
                        {
                            "match": {
                                "mime": {
                                    "query": "image",
                                    "boost": 10
                                }
                            },
                        },
                        {
                            "match": {
                                "mime": {
                                    "query": "video",
                                    "boost": 5
                                }
                            }
                        }
                    ]
                    # "should": ranges
                }
            },
            "highlight": {
                "fields": {
                    "content": {},
                    "title": {},
                    "filename": {},
                    "path": {},
                }
            },
        }
    )
    data['page'] = page

    return data
