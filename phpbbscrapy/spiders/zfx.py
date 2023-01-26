from phpbbscrapy.spiders.phpbb import PHPBBSpider


class ZFXSpider(PHPBBSpider):
    name = 'zfx'
    allowed_domains = ['zfx.info']
    base_url = 'https://zfx.info'
    start_urls = ['https://zfx.info']
