import scrapy
import re
from bs4 import BeautifulSoup
import datetime
from phpbbscrapy.items import CategoryItem, PostItem, ThreadItem, BoardItem
from scrapy.exceptions import CloseSpider
from phpbbscrapy.models import db_connect
from sqlalchemy.orm import sessionmaker
import pytz

from phpbbscrapy.pipelines import get_post_count_in_category, get_post_count_in_thread


class PHPBBSpider(scrapy.Spider):
    name = 'phpBB'
    post_body_xpath = '//div[@class="postbody"]'
    author_xpath = './/p[contains(@class, "author")]'
    post_count_xpath = 'dd[@class="profile-posts" or not(@class)]//a/text()'
    post_time_xpath = 'time/@datetime'
    post_text_xpath = 'div[@class="content"]'

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)

        engine = db_connect()
        self.session = sessionmaker(bind=engine)

    def parse(self, response, **kwargs):
        board = BoardItem()
        board['name'] = self.name
        yield board

        yield from self.parse_forums(response, None)

    def parse_forums(self, response, parent_category):
        for forum_list in response.xpath('//ul[@class="topiclist forums"]'):
            for forum in forum_list.xpath('li'):
                category = CategoryItem()
                category['title'] = forum.xpath('.//div[@class="list-inner"]//a//text()').get()
                category['url'] = response.urljoin(forum.xpath('.//div[@class="list-inner"]//a//@href').get())

                id_match = re.match(".+f=(\d+)", category['url'])

                if not id_match:
                    continue

                category['id'] = int(id_match.group(1))
                category['description'] = forum.xpath('.//dt//div[@class="list-inner"]//br//following-sibling::text()').get().strip()
                category['number_of_posts'] = int(forum.xpath('dl//dd[@class="posts"]//text()').get().strip())
                last_post_date_string = forum.xpath('dl//dd[@class="lastpost"]//time/@datetime').get()
                category['last_post_date'] = datetime.datetime.fromisoformat(last_post_date_string).replace(tzinfo=pytz.UTC)

                if parent_category:
                    category['parent_id'] = parent_category['id']
                else:
                    category['parent_id'] = None

                category['board_name'] = self.name

                database_post_count_in_category = get_post_count_in_category(self.session, category['id'])

                if database_post_count_in_category == category['number_of_posts']:
                    continue

                yield category
                yield scrapy.Request(category['url'], callback=self.parse_threads, meta={'category': category})

    def parse_threads(self, response):
        category = response.meta['category']

        yield from self.parse_forums(response, category)

        for topic_list in response.xpath('//ul[@class="topiclist topics"]'):
            for topic in topic_list.xpath('li'):
                thread = ThreadItem()
                thread['title'] = topic.xpath('.//a//text()').get()
                thread['author'] = topic.xpath('dl//dt//div//div[contains(@class, "topic-post")]//a//text()').get()

                if not thread['author']:
                    thread['author'] = topic.xpath('dl//dt//div//div[contains(@class, "topic-poster")]//span//text()').get()

                thread['category_id'] = category['id']
                created_at_string = topic.xpath('dl//dt//div//div[contains(@class, "topic-post")]//time//@datetime').get()
                thread['created_at'] = datetime.datetime.fromisoformat(created_at_string)
                thread['number_of_posts'] = int(topic.xpath('dl//dd[contains(@class, "posts")]//text()').get().strip()) + 1
                last_post_date_string = topic.xpath('dl//dd[contains(@class, "lastpost")]//time//@datetime').get()
                thread['last_post_date'] = datetime.datetime.fromisoformat(last_post_date_string)
                thread['url'] = response.urljoin(topic.xpath('dl//dt//div//a//@href').get())
                thread['id'] = int(re.match(".+t=(\d+)", thread['url']).group(1))

                database_post_count_in_thread = get_post_count_in_thread(self.session, thread)

                if database_post_count_in_thread == thread['number_of_posts']:
                    continue

                print(f"Processing new posts in thread {category['title']} > {thread['title']} ({thread['url']})")
                yield thread
                yield scrapy.Request(thread['url'], callback=self.parse_posts, meta={'category': category, 'thread': thread})

        next_link = response.xpath('//li[@class="arrow next"]//a/@href').extract_first()

        if next_link:
            full_next_link = response.urljoin(next_link)
            yield scrapy.Request(full_next_link, callback=self.parse_threads, meta={'category': category})

    def parse_posts(self, response):
        category = response.meta['category']
        thread = response.meta['thread']

        for post in response.xpath(self.post_body_xpath):
            post_item = PostItem()
            post_text = post.xpath('.//div[@class="content"]').get()
            post_item['content'] = self.clean_text(post_text)
            author = post.xpath(self.author_xpath)
            post_item['author'] = author.xpath('.//a[contains(@class, "username")]//text()|.//span[contains(@class,"username")]//text()').get()
            date_string = author.xpath(self.post_time_xpath).get()
            post_item['date'] = datetime.datetime.fromisoformat(date_string)
            post_item['url'] = response.urljoin(post.xpath('div//h3//a//@href').get())
            id_match = re.match(".+p=(\d+)", post_item['url'])
            if not id_match:
                continue

            post_item['id'] = id_match.group(1)
            post_item['thread_id'] = thread['id']

            if not post_item.valid():
                raise CloseSpider('Post not valid')

            # post_profile = post.xpath('./preceding-sibling::dl')
            # author_post_count = post_profile.xpath(self.post_count_xpath).get()
            # post_quotes = self.clean_quote(post_text)

            yield post_item

        next_link = response.xpath('//li[@class="arrow next"]//a/@href').extract_first()

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
