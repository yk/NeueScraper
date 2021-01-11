# -*- coding: utf-8 -*-
import scrapy
import logging
import bs4
import datetime
import re
from NeueScraper.spiders.basis import BasisSpider

logger = logging.getLogger(__name__)
CUR_YEAR = datetime.datetime.now().year

months_de = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
months_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
raw_date_re = re.compile(r'(\d+)\.?\s+({})\s+((1|2)\d\d\d)'.format('|'.join(months_de + months_fr)))
date_re = re.compile(r'(du|vom)\s+{}'.format(raw_date_re.pattern))
kammer_re = re.compile(r"\d+\.?\s+(Auszug aus dem Urteil|Urteil|Extrait de l'arrêt|Arrêt)\s+(des|der|du|de la)(.+?)\s+(vom|du|i\.S\.|dans|{})".format(date_re.pattern))

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
        head = rank_data.select('.urt')[0].text.strip()
        date_match = date_re.search(head)
        if date_match is None:
            raise ValueError('Could not find date in {}:{}'.format(rank_title, head))
        day, month, year = date_match.groups()[1:4]
        month = (months_de.index(month) if month in months_de else months_fr.index(month)) + 1
        kammer_match = kammer_re.search(head)
        if kammer_match is None:
            raise ValueError('Could not find kammer in {}:{}'.format(rank_title, head))
        kammer = kammer_match.group(3)
        if raw_date_re.search(kammer) is not None:
            raise ValueError('Could not find kammer in {}:{}'.format(rank_title, head))
        regeste = content.select('#regeste')
        if not regeste:
            raise ValueError('Could not find regeste in {}'.format(rank_title))
        regeste = regeste[0].select('.paraatf')[0].text.strip()
        # TODO: item erstellen


    def errback_httpbin(self, failure):
        # log all errback failures,
        # in case you want to do something special for some errors,
        # you may need the failure's type
        logger.error(repr(failure))
