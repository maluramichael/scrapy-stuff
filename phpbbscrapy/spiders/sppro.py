from phpbbscrapy.spiders.wbb import WBBSpider


class SPPropider(WBBSpider):
    name = 'sppro'
    allowed_domains = ['www.spieleprogrammierer.de']
    base_url = 'https://www.spieleprogrammierer.de'
    start_urls = ['https://www.spieleprogrammierer.de']
