from phpbbscrapy.spiders.phpbb import PHPBBSpider
from scrapy.http import FormRequest


class XentaxSpider(PHPBBSpider):
    name = 'xentax'
    allowed_domains = ['forum.xentax.com']
    base_url = 'https://forum.xentax.com'
    start_urls = ['https://forum.xentax.com/index.php']
    login_required = True
    username = 'YOUR_USERNAME'
    password = 'YOUR_PASSWORD'
