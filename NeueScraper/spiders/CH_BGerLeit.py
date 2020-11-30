# -*- coding: utf-8 -*-
import scrapy
import logging
import bs4
import datetime
from NeueScraper.spiders.basis import BasisSpider

logger = logging.getLogger(__name__)
CUR_YEAR = datetime.datetime.now().year

class BGerLeitSpider(BasisSpider):
    name = 'CH_BGerLeit'

    SUCH_URL='https://www.bger.ch/ext/eurospider/live/de/php/clir/http/index.php?lang=de&type=simple_query&query_words=&lang=de&top_subcollection_clir=bge&from_year={year}&to_year={year}'
    
    def request_generator(self, start_jahr=1954, end_jahr=CUR_YEAR):
        """ Generates scrapy frist request
        """

        return [scrapy.Request(url=self.SUCH_URL.format(year=year), callback=self.parse_suchergebnis, errback=self.errback_httpbin) for year in range(1954, CUR_YEAR+1)]

    def __init__(self):
        super().__init__()
        self.request_gen = self.request_generator()

    def parse_suchergebnis(self, response):
        soup = bs4.BeautifulSoup(response.body_as_unicode(), 'html.parser')
        last_footer_a = next(reversed(soup.select('.ranklist_footer a')))
        try:
            int(last_footer_a.text)
            # Wenn dies eine nummer ist, sind wir auf der letzten Seite.
        except ValueError:
            # Wenn wir nicht auf der letzten Seite sind, eine Seite weiter gehen.
            yield response.follow(last_footer_a['href'], callback=self.parse_suchergebnis)

        for li in soup.select('.ranklist_content ol li'):
            rank_title = li.select_one('.rank_title')
            rank_data = li.select_one('.rank_data')
            yield response.follow(rank_title.select_one('a')['href'], cb_kwargs={'rank_title': rank_title.text.strip(), 'rank_data_html': str(rank_data)}, callback=self.parse_entscheid)

    def parse_entscheid(self, response, rank_title=None, rank_data_html=None):
        soup = bs4.BeautifulSoup(response.body_as_unicode(), 'html.parser')
        rank_data = bs4.BeautifulSoup(rank_data_html, 'html.parser')
        content = soup.select_one('#highlight_content .content')
        # TODO: aus rank_data und content ein item erstellen


    def errback_httpbin(self, failure):
        # log all errback failures,
        # in case you want to do something special for some errors,
        # you may need the failure's type
        logger.error(repr(failure))
