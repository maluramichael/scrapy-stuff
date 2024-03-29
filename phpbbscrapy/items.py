# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class BoardItem(scrapy.Item):
    name = scrapy.Field()


class PostAttachmentItem(scrapy.Item):
    board_name = scrapy.Field()
    post_id = scrapy.Field()
    thread_id = scrapy.Field()
    category_id = scrapy.Field()
    url = scrapy.Field()
    filename = scrapy.Field()


class CategoryItem(scrapy.Item):
    category_id = scrapy.Field()
    title = scrapy.Field()
    description = scrapy.Field()
    parent_id = scrapy.Field()
    number_of_posts = scrapy.Field()
    last_post_date = scrapy.Field()
    url = scrapy.Field()
    board_name = scrapy.Field()


class ThreadItem(scrapy.Item):
    thread_id = scrapy.Field()
    title = scrapy.Field()
    category_id = scrapy.Field()
    author = scrapy.Field()
    created_at = scrapy.Field()
    number_of_posts = scrapy.Field()
    last_post_date = scrapy.Field()
    url = scrapy.Field()
    board_name = scrapy.Field()


class PostItem(scrapy.Item):
    post_id = scrapy.Field()
    thread_id = scrapy.Field()
    category_id = scrapy.Field()
    content = scrapy.Field()
    author = scrapy.Field()
    date = scrapy.Field()
    url = scrapy.Field()
    board_name = scrapy.Field()
    files = scrapy.Field()
    images = scrapy.Field()
    file_urls = scrapy.Field()
    image_urls = scrapy.Field()

    def valid(self):
        if not self.get('thread_id'):
            return False
        if not self.get('content'):
            return False
        if not self.get('author'):
            return False
        if not self.get('date'):
            return False
        if not self.get('url'):
            return False
        return True
