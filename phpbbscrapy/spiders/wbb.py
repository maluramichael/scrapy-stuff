import random

import scrapy
import re
from bs4 import BeautifulSoup
import datetime
from phpbbscrapy.items import CategoryItem, PostItem, ThreadItem, BoardItem
from scrapy.exceptions import CloseSpider
from phpbbscrapy.models import db_connect, Category, Post
from sqlalchemy.orm import sessionmaker
import pytz

from phpbbscrapy.pipelines import get_post_count_in_category, get_post_count_in_thread, get_last_post_date_in_category, get_last_post_datein_thread


class WBBSpider(scrapy.Spider):
    name = 'wbb'
    base_url = ''
    post_body_xpath = '//div[@class="postbody"]'
    author_xpath = './/p[contains(@class, "author")]'
    post_count_xpath = 'dd[@class="profile-posts" or not(@class)]//a/text()'
    post_time_xpath = 'time/@datetime'
    post_text_xpath = 'div[@class="content"]'

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)

        engine = db_connect()
        self.session = sessionmaker(bind=engine)
        self.post_thread_ids = self.get_post_thread_ids()

    def parse(self, response, **kwargs):
        board = BoardItem()
        board['name'] = self.name
        yield board

        yield from self.parse_forums(response, None)

    def clean_url(self, url):
        # Remove the session id from the url
        cleaned = re.sub(r"\?s=[a-z0-9]+$", "", url)
        return cleaned

    def parse_forums(self, response, parent_category):
        forums = response.xpath('//li[contains(@class, "category")]//ul//li')
        random.shuffle(forums)

        for forum in forums:
            category = CategoryItem()
            category['title'] = forum.xpath('.//h4[@class="boardTitle"]//a//text()').get()
            category['url'] = self.clean_url(forum.xpath('.//h4[@class="boardTitle"]//a//@href').get())

            id_match = re.match(".+/([0-9]+)-.+$", category['url'])

            if not id_match:
                continue

            category['id'] = int(id_match.group(1))
            category['description'] = forum.xpath('.//p[@class="boardlistDescription"]//text()').get().strip()
            category['number_of_posts'] = 0
            last_post_date_string = forum.xpath('.//div[@class="boardlistLastPost"]//div[2]//p[2]//span//text()').get()
            last_post_date = self.parse_post_date(last_post_date_string)
            category['last_post_date'] = last_post_date

            if parent_category:
                category['parent_id'] = parent_category['id']
            else:
                category['parent_id'] = None

            category['board_name'] = self.name

            # database_last_post_date_in_category = get_last_post_date_in_category(self.session, category['id'])
            #
            # if database_last_post_date_in_category and database_last_post_date_in_category >= last_post_date:
            #     continue

            yield category
            yield scrapy.Request(category['url'], callback=self.parse_threads, meta={'category': category})

    def parse_post_date(self, post_date_string):
        if post_date_string is None:
            return None

        post_date_string = post_date_string.replace('(', '').replace(')', '').strip()

        if "Gestern" in post_date_string:
            yesterday_matches = re.match(r"Gestern, ([0-9]+):([0-9]+)", post_date_string)

            hour = yesterday_matches.group(1)
            minute = yesterday_matches.group(2)

            post_date = datetime.datetime.now() - datetime.timedelta(days=1)
            post_date = post_date.replace(hour=int(hour), minute=int(minute))
        elif "Von" in post_date_string:
            post_date = datetime.datetime.min
        else:
            post_date = datetime.datetime.strptime(post_date_string, '%d.%m.%Y, %H:%M')

        post_date = post_date.replace(second=0, microsecond=0, tzinfo=pytz.timezone('Europe/Berlin'))

        return post_date

    def parse_threads(self, response):
        category = response.meta['category']

        yield from self.parse_forums(response, category)
        topics = response.xpath('//tr[starts-with(@id,"threadRow")]')
        random.shuffle(topics)
        print("")
        for topic in topics:
            thread = ThreadItem()
            thread['title'] = topic.xpath('./td[2]/div[1]/p/a/text()').get()
            thread['url'] = topic.xpath('./td[2]/div[1]/p/a/@href').get()
            thread['author'] = topic.xpath('./td[2]/p/a/text()').get()

            if thread['author'] is None:
                thread['author'] = topic.xpath('./td[2]/p/text()').get()

                if thread['author'] is None:
                    raise Exception(f"Could not find author in thread")

                if 'Anonym' in thread['author']:
                    thread['author'] = 'Anonymous'

            thread['category_id'] = category['id']

            created_at_string = topic.xpath('./td[2]/p[1]/text()[2]').get()

            if created_at_string is None:
                created_at_string = topic.xpath('./td[2]/p/text()').get()
                created_at_string = created_at_string.replace('\n', ' ').replace('\t', '').replace('Von Anonymous', '').replace('(', '').replace(')', '').strip()

                if created_at_string is None:
                    raise Exception(f"Could not find created at string in thread")

            created_at = self.parse_post_date(created_at_string)

            if created_at is None:
                raise Exception(f"Could not parse created at date for thread {thread['title']}")

            thread['created_at'] = created_at

            try:
                number_of_posts_string = topic.xpath('./td[3]/text()').get()
                number_of_posts_string = number_of_posts_string.replace(' ', '').strip()
                if u'\xa0' in number_of_posts_string:
                    number_of_posts_string = number_of_posts_string.replace(u'\xa0', '')
                thread['number_of_posts'] = int(number_of_posts_string.strip()) + 1
            except ValueError:
                print("Could not parse number of posts for thread: " + thread['title'])
            last_post_date_string = topic.xpath('./td[5]/div[2]/p[2]/text()').get()
            last_post_date = self.parse_post_date(last_post_date_string)

            if last_post_date is None:
                last_post_date = created_at

            thread['last_post_date'] = last_post_date

            id_match = re.match(".+/([0-9]+)-.+$", thread['url'])

            if not id_match:
                continue

            thread['id'] = int(id_match.group(1))

            database_last_post_datein_thread = get_last_post_datein_thread(self.session, thread['id'])

            board_name =self.name
            category_id = category['id']
            thread_id = thread['id']
            number_of_posts_in_thread = get_post_count_in_thread(self.session, board_name, category_id, thread_id)
            # if database_last_post_datein_thread and database_last_post_datein_thread >= last_post_date:
            #     continue

            if number_of_posts_in_thread == thread['number_of_posts']:
                print("s", end="")
                continue

            # print(f"Processing new posts in thread {category['title']} > {thread['title']} ({thread['url']})")

            print("T", end="")

            yield thread
            yield scrapy.Request(thread['url'], callback=self.parse_posts, meta={'category': category, 'thread': thread})

        next_link = response.xpath('//div[@class="pageNavigation"]/ul/li[@class="active"]/following-sibling::li[1]/a/@href').extract_first()

        if next_link:
            full_next_link = response.urljoin(next_link)
            yield scrapy.Request(full_next_link, callback=self.parse_threads, meta={'category': category})

    def parse_posts(self, response):
        category = response.meta['category']
        thread = response.meta['thread']
        print("")
        for post in response.xpath('//div[starts-with(@id,"postRow")]'):
            post_item = PostItem()
            post_text = post.xpath('./div/div[2]/div/div[2]/div').get()
            post_item['content'] = self.clean_text(post_text)
            author_string = post.xpath('.//p[@class="userName"]//span/strong/text()').get()

            if author_string is None:
                author_string = post.xpath('.//p[@class="userName"]//span/text()').get()
            if author_string is None:
                author_string = post.xpath('.//p[@class="userName"]/text()').get()
            if 'Anonymous' in author_string:
                author_string = 'Anonymous'

            if author_string is None:
                print("Z", end="")
                raise Exception(f"Could not find author in post")

            post_item['author'] = author_string
            date_string = post.xpath('./div/div[2]/div/div[1]/div[2]/p/text()').get()
            post_date = self.parse_post_date(date_string)
            post_item['date'] = post_date
            post_item['url'] = post.xpath('./div/div[2]/div/div[1]/p/a/@href').get()
            id_match = re.match(".+/([0-9]+)#post[0-9]+$", post_item['url'])
            if not id_match:
                print("X", end="")
                continue

            post_item['id'] = int(id_match.group(1))
            post_item['thread_id'] = thread['id']

            if not post_item.valid():
                print("V", end="")
                raise CloseSpider('Post not valid')

            post_id = post_item['id']
            thread_id = post_item['thread_id']

            if thread_id in self.post_thread_ids and post_id in self.post_thread_ids[thread_id]:
                print("D", end="")
                continue

            print(".", end="")
            # post_profile = post.xpath('./preceding-sibling::dl')
            # author_post_count = post_profile.xpath(self.post_count_xpath).get()
            # post_quotes = self.clean_quote(post_text)

            yield post_item

        next_link = response.xpath('//div[@class="pageNavigation"]/ul/li[@class="active"]/following-sibling::li[1]/a/@href').extract_first()

        if next_link:
            full_next_link = response.urljoin(next_link)
            yield scrapy.Request(full_next_link, callback=self.parse_posts, meta={'category': category, 'thread': thread})

    def clean_quote(self, string):
        # CLEAN HTML TAGS FROM POST TEXT, MARK QUOTES
        soup = BeautifulSoup(string, 'lxml')
        block_quotes = soup.find_all('blockquote')
        for i, quote in enumerate(block_quotes):
            block_quotes[i] = '<quote-%s>=%s' % (str(i + 1), quote.get_text())
        return ''.join(block_quotes).strip()

    def clean_text(self, string):
        # CLEAN HTML TAGS FROM POST TEXT, MARK REPLIES TO QUOTES
        tags = ['blockquote']
        soup = BeautifulSoup(string, 'lxml')
        for tag in tags:
            for i, item in enumerate(soup.find_all(tag)):
                item.replaceWith('<reply-%s>=' % str(i + 1))

        soup_get_text = soup.get_text()
        result_text = re.sub(r' +', r' ', soup_get_text).strip()

        return str(list(soup.html.body.children)).strip()

    def get_post_thread_ids(self):
        with self.session() as session:
            result = {}
            for t in session.query(Post.thread_id, Post.id).all():
                thread_id = t[0]
                post_id = t[1]

                if thread_id is None or post_id is None:
                    continue

                if thread_id not in result:
                    result[thread_id] = []

                result[thread_id].append(post_id)

            return result
