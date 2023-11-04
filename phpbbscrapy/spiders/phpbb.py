import random
import scrapy
import re
from bs4 import BeautifulSoup
import datetime
from phpbbscrapy.items import CategoryItem, PostItem, ThreadItem, BoardItem, PostAttachmentItem
from scrapy.exceptions import CloseSpider
from phpbbscrapy.models import db_connect
from sqlalchemy.orm import sessionmaker
import pytz
from scrapy.utils.project import get_project_settings
from tabulate import tabulate
from phpbbscrapy.pipelines import get_post_count_in_category, get_post_count_in_thread, get_category_from_db, remove_unwanted_query_parameters

DEBUG_CATEGORY_ID = None
DEBUG_THREAD_ID = None
DEBUG_CHECK_POST_COUNT = False


def get_filename_from_title(title):
    if 'betrachtet' in title:
        return re.sub(r' \([\d\.]+ [KiBGM]+\) .+betrachtet$', '', title)
    elif 'Viewed' in title:
        return re.sub(r' \([\d\.]+ [KiBGM]+\) Viewed \d+ times$', '', title) #
    else:
        title_chunks = title.split(' ')
        first_chunk = title_chunks[0]
        return first_chunk
class PHPBBSpider(scrapy.Spider):
    name = 'phpBB'
    post_body_xpath = '//div[@class="postbody"]'
    author_xpath = './/p[contains(@class, "author")]'
    post_count_xpath = 'dd[@class="profile-posts" or not(@class)]//a/text()'
    post_time_xpath = 'time/@datetime'
    post_text_xpath = 'div[@class="content"]'
    start_urls = []
    cookies = {}
    login_url = None
    login_required = False
    username = None
    password = None

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)

        engine = db_connect()
        self.session = sessionmaker(bind=engine)

        self.images_found = 0
        self.files_found = 0

    def after_login(self, response):
        text = response.text

        if 'was invalid' in text:
            raise CloseSpider('Login failed')

        yield from self.parse_forums(response, None)

    def parse(self, response, **kwargs):
        board = BoardItem()
        board['name'] = self.name
        yield board

        if self.login_required:
            formxpath = '//form'
            formdata = {'username': self.username, 'password': self.password, 'autologin': 'on'}
            form_request = scrapy.FormRequest.from_response(
                response,
                formxpath=formxpath,
                formdata=formdata,
                callback=self.after_login,
                dont_click=False,

            )
            yield form_request
        else:
            yield from self.parse_forums(response, None)

    def parse_forums(self, response, parent_category):
        topic_lists = response.xpath('//ul[@class="topiclist forums"]')
        for forum_list in topic_lists:
            topics = forum_list.xpath('li')
            for forum in topics:
                category = CategoryItem()
                category['title'] = forum.xpath('.//div[@class="list-inner"]//a//text()').get()
                category['url'] = response.urljoin(forum.xpath('.//div[@class="list-inner"]//a//@href').get())

                id_match = re.match(".+f=(\d+)", category['url'])

                if not id_match:
                    continue

                category['category_id'] = int(id_match.group(1))
                category['description'] = forum.xpath(
                    './/dt//div[@class="list-inner"]//br//following-sibling::text()').get().strip()
                category['number_of_posts'] = int(forum.xpath('dl//dd[@class="posts"]//text()').get().strip())
                last_post_date_string = forum.xpath('dl//dd[@class="lastpost"]//time/@datetime').get()
                category['last_post_date'] = datetime.datetime.fromisoformat(last_post_date_string).replace(
                    tzinfo=pytz.UTC)

                if parent_category:
                    parent_category_in_db = get_category_from_db(self.session, self.name, parent_category['category_id'])
                    if parent_category_in_db:
                        category['parent_id'] = parent_category_in_db.id
                else:
                    category['parent_id'] = None

                category['board_name'] = self.name

                database_post_count_in_category = get_post_count_in_category(self.session, self.name,
                                                                             category['category_id'])

                if DEBUG_CHECK_POST_COUNT and database_post_count_in_category == category['number_of_posts']:
                    continue

                if DEBUG_CATEGORY_ID and category['category_id'] != DEBUG_CATEGORY_ID:
                    continue

                yield category
                yield scrapy.Request(category['url'], callback=self.parse_threads,
                                     meta={'category': category, 'board_name': self.name})

    def parse_threads(self, response):
        category = response.meta['category']

        yield from self.parse_forums(response, category)

        for topic_list in response.xpath('//ul[@class="topiclist topics"]'):
            topics = topic_list.xpath('li[not(contains(@class, "global-announce"))]')
            topics = random.sample(topics, len(topics))

            for topic in topics:
                thread = ThreadItem()
                thread['title'] = topic.xpath('.//a[@class="topictitle"]//text()').get()
                thread['author'] = topic.xpath('dl//dt//div//div[contains(@class, "topic-post")]//a//text()').get()

                if not thread['author']:
                    thread['author'] = topic.xpath(
                        'dl//dt//div//div[contains(@class, "topic-poster")]//span//text()').get()

                thread['category_id'] = category['category_id']
                thread['board_name'] = self.name
                created_at_string = topic.xpath(
                    'dl//dt//div//div[contains(@class, "topic-post")]//time//@datetime').get()
                thread['created_at'] = datetime.datetime.fromisoformat(created_at_string)
                thread['number_of_posts'] = int(
                    topic.xpath('dl//dd[contains(@class, "posts")]//text()').get().strip()) + 1
                last_post_date_string = topic.xpath('dl//dd[contains(@class, "lastpost")]//time//@datetime').get()
                thread['last_post_date'] = datetime.datetime.fromisoformat(last_post_date_string)
                url = topic.xpath('dl//dt//div//a[@class="topictitle"]//@href').get()
                thread['url'] = response.urljoin(url)
                thread['thread_id'] = int(re.match(".+t=(\d+)", thread['url']).group(1))

                board_name = self.name
                category_id = category['category_id']
                category_from_db = get_category_from_db(self.session, board_name, category_id)

                thread_id = thread['thread_id']
                database_post_count_in_thread = get_post_count_in_thread(self.session, category_from_db, thread_id)

                if DEBUG_CHECK_POST_COUNT and database_post_count_in_thread == thread['number_of_posts']:
                    continue

                if DEBUG_THREAD_ID and thread['thread_id'] != DEBUG_THREAD_ID:
                    continue

                # print(f"Processing new posts in thread {category['title']} > {thread['title']} ({thread['url']})")
                yield thread
                yield scrapy.Request(thread['url'], callback=self.parse_posts,
                                     meta={'category': category, 'thread': thread})

        next_link = response.xpath('//li[@class="arrow next"]//a/@href').extract_first()

        if next_link:
            full_next_link = response.urljoin(next_link)
            yield scrapy.Request(full_next_link, callback=self.parse_threads, meta={'category': category})

    def parse_posts(self, response):
        category = response.meta['category']
        thread = response.meta['thread']
        posts = response.xpath(self.post_body_xpath)

        pretty_table_data = []

        images_in_thread = 0
        files_in_thread = 0

        for post in posts:
            post_item = PostItem()
            post_text = post.xpath('.//div[@class="content"]').get()
            post_attachbox = post.xpath('.//dl[@class="attachbox"]').get() or ''
            post_text = '\n'.join([post_text, post_attachbox])
            post_item['content'] = self.clean_text(post_text)
            author = post.xpath(self.author_xpath)
            post_item['author'] = author.xpath(
                './/a[contains(@class, "username")]//text()|.//span[contains(@class,"username")]//text()').get()
            date_string = author.xpath(self.post_time_xpath).get()
            post_item['date'] = datetime.datetime.fromisoformat(date_string)
            post_item['url'] = response.urljoin(post.xpath('div//h3//a//@href').get())
            id_match = re.match(".+p=(\d+)", post_item['url'])

            if not id_match:
                continue

            post_item['category_id'] = category['category_id']
            post_item['board_name'] = self.name
            post_item['post_id'] = id_match.group(1)
            post_item['thread_id'] = thread['thread_id']

            if not post_item.valid():
                print('Post not valid')
                continue

            # post_profile = post.xpath('./preceding-sibling::dl')
            # author_post_count = post_profile.xpath(self.post_count_xpath).get()
            # post_quotes = self.clean_quote(post_text)

            file_urls = []
            image_urls = []

            # find a.postlink in post via xpath where href starts with ./download/file.php
            # if found, yield scrapy.Request(response.urljoin(href), callback=self.parse_file)
            post_links = post.xpath('.//a[contains(@class, "postlink")]')
            post_images = post.xpath('.//img[contains(@class, "postimage")]')

            for post_link in post_links:
                post_href = post_link.xpath('./@href').get()

                if post_href and './download/file.php' in post_href:
                    post_attachment = PostAttachmentItem()
                    post_attachment['board_name'] = self.name
                    post_attachment['post_id'] = post_item['post_id']
                    post_attachment['thread_id'] = thread['thread_id']
                    post_attachment['category_id'] = category['category_id']
                    post_attachment['url'] = response.urljoin(
                        post_href)  # https://forum.xentax.com/download/file.php?id=19118

                    download_id = re.match(".+id=(\d+)", post_attachment['url']).group(1)
                    text = post_link.xpath('./text()').get()

                    if text and re.match(r'.*\.\w{1,10}$', text):
                        text = text.strip()
                        post_attachment['filename'] = f"{download_id}_{text}"
                    else:
                        print(f"Could not find filename for {post_attachment['url']} in post {post_item['url']}")
                        continue

                    # yield post_attachment
                    # print(f"Found file {post_attachment['filename']} in post {post_item['url']}")
                    file_urls.append(post_attachment)

            for post_image in post_images:
                image_src = post_image.xpath('./@src').get()

                if image_src and 'download/file.php' in image_src:
                    image_title = post_image.xpath('./@title').get()
                    url = response.urljoin(image_src)
                    alt = post_image.xpath('./@alt').get()

                    post_attachment = PostAttachmentItem()
                    post_attachment['board_name'] = self.name
                    post_attachment['post_id'] = post_item['post_id']
                    post_attachment['thread_id'] = thread['thread_id']
                    post_attachment['category_id'] = category['category_id']
                    post_attachment['url'] = url
                    post_attachment['filename'] = alt
                    download_id = re.match(".+id=(\d+)", post_attachment['url']).group(1)

                    # WhatsApp Image 2023-01-08 at 20.30.39.jpeg (343.11 KiB) 353 mal betrachtet
                    if image_title:
                        image_title = get_filename_from_title(image_title)
                        post_attachment['filename'] = f"{download_id}_{image_title}"
                    elif alt and re.match(r'.+\.\w{1,10}$', alt):
                        post_attachment['filename'] = f"{download_id}_{alt}"
                    else:
                        # if parent is dt
                        parent = post_image.xpath('..')

                        if parent and parent.xpath('name()').get() == 'dt' or parent.xpath('name()').get() == 'dd':
                            last_dd = parent.xpath('../dd[last()]')
                            if last_dd:
                                text = last_dd.xpath('./text()').get()
                                image_title = get_filename_from_title(text)
                                post_attachment['filename'] = f"{download_id}_{image_title}"
                            else:
                                print(f"Could not find filename for {post_attachment['url']} in post {post_item['url']}")
                                continue
                        else:
                            post_attachment['filename'] = f"{download_id}_no_extension_found"

                    post_attachment['url'] = remove_unwanted_query_parameters(post_attachment['url'], ['t'])

                    image_urls.append(post_attachment)

            post_item['file_urls'] = file_urls
            post_item['image_urls'] = image_urls

            if len(file_urls) > 0:
                self.files_found += len(file_urls)
                files_in_thread += len(file_urls)
            if len(image_urls) > 0:
                self.images_found += len(image_urls)
                images_in_thread += len(image_urls)

            pretty_table_data.append([
                post_item['author'],
                post_item['category_id'],
                post_item['thread_id'],
                post_item['post_id'],
                len(file_urls),
                len(image_urls)
            ])

            yield post_item

        print(f"Found {images_in_thread} images and {files_in_thread} files in {thread['title']} ({thread['url']}). Total images: {self.images_found}, total files: {self.files_found}")

        # print(tabulate(pretty_table_data, headers=['Author', 'Category', 'Thread', 'Post', 'Files', 'Images']))
        next_link = response.xpath('//li[@class="arrow next"]//a/@href').extract_first()

        if next_link:
            full_next_link = response.urljoin(next_link)
            yield scrapy.Request(full_next_link, callback=self.parse_posts,
                                 meta={'category': category, 'thread': thread})

    def clean_quote(self, string):
        # CLEAN HTML TAGS FROM POST TEXT, MARK QUOTES
        soup = BeautifulSoup(string, 'lxml')
        block_quotes = soup.find_all('blockquote')
        for i, quote in enumerate(block_quotes):
            block_quotes[i] = '<quote-%s>=%s' % (str(i + 1), quote.get_text())
        return ''.join(block_quotes).strip()

    def clean_text(self, string):
        # CLEAN HTML TAGS FROM POST TEXT, MARK REPLIES TO QUOTES
        # tags = ['blockquote']
        soup = BeautifulSoup(string, 'lxml')
        # for tag in tags:
        #     for i, item in enumerate(soup.find_all(tag)):
        #         item.replaceWith('<reply-%s>=' % str(i + 1))

        children = list(soup.html.body.children)
        children_string = str(children).strip()

        # remove first and last characters (square brackets)
        children_string = children_string[1:-1]

        return children_string
