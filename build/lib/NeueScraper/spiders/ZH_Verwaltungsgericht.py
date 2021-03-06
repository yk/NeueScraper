# -*- coding: utf-8 -*-
import scrapy
import re
import logging
from scrapy.http.cookies import CookieJar
import datetime
from NeueScraper.spiders.basis import BasisSpider
from NeueScraper.pipelines import MyFilesPipeline
from NeueScraper.pipelines import PipelineHelper


logger = logging.getLogger(__name__)

class ZurichVerwgerSpider(BasisSpider):
	name = 'ZH_Verwaltungsgericht'
	MINIMUM_PAGE_LEN = 148
	MAX_PAGES = 10000
	TREFFERLISTE_URL='https://vgrzh.djiktzh.ch/cgi-bin/nph-omniscgi.exe?OmnisPlatform=WINDOWS&WebServerUrl=https://vgrzh.djiktzh.ch&WebServerScript=/cgi-bin/nph-omniscgi.exe&OmnisLibrary=JURISWEB&OmnisClass=rtFindinfoWebHtmlService&OmnisServer=JURISWEB,127.0.0.1:7000&Parametername=WWW&Schema=ZH_VG_WEB&Source=&Aufruf=search&cTemplate=standard/results/resultpage.fiw&cTemplateSuchkriterien=standard/results/searchcriteriarow.fiw&cSprache=GER&W10_KEY=4004259&nSeite={page}'
	ab=None
	reDatum=re.compile('[0-9]{2}\\.[0-9]{2}\\.[0-9]{4}')
	reTyp=re.compile('.+(?= vom [0-9]{2}\\.[0-9]{2}\\.[0-9]{4})')
	
	def request_generator(self, ab, page):
		""" Generates scrapy frist request
		"""
		# return [scrapy.Request(url=self.RESULT_PAGE_URL, method="POST", body= self.RESULT_PAGE_PAYLOAD.format(Jahr=self.START_JAHR), headers=self.HEADERS, callback=self.parse_trefferliste_unsortiert, errback=self.errback_httpbin)]
		# Erst einmal den Basisrequest machen, um Cookie zu setzen
		
		if(ab==None):
			request=scrapy.Request(url=self.TREFFERLISTE_URL.format(page=page), callback=self.parse_trefferliste, errback=self.errback_httpbin, meta={'page': page})
		else:
			request=scrapy.Request(url=self.TREFFERLISTE_URL.format(page=page), callback=self.parse_trefferliste, errback=self.errback_httpbin, meta={'page': page})	
		return [request]

	def __init__(self, ab=None):
		super().__init__()
		self.ab=ab
		self.request_gen = self.request_generator(self.ab, 1)

	def parse_trefferliste(self, response):
		logging.info("parse_trefferliste response.status "+str(response.status))
		logging.info("parse_trefferliste Rohergebnis "+str(len(response.body))+" Zeichen")
		logging.info("parse_trefferliste Rohergebnis: "+response.body_as_unicode())
		
		treffer=response.xpath("(//table[@width='98%']//table[@width='100%']/tr/td/b/text())[2]").get()
		trefferZahl=int(treffer)
		
		entscheide=response.xpath("//table[@width='100%']/tr/td[@valign='top']/table")
		for entscheid in entscheide:
			logging.info("Verarbeite Entscheid: "+entscheid.get())
			url=entscheid.xpath(".//a/@href").get()
			logging.info("url: "+url)
			num=entscheid.xpath(".//a/font/text()").get()
			logging.info("num: "+num)
			vkammer=entscheid.xpath(".//tr[1]/td[4]/font/text()").get()
			if vkammer==None:
				vkammer=""
				logging.info("keine Kammer")
			else:
				logging.info("Kammer: "+vkammer)
			titel=entscheid.xpath(".//tr[2]/td[2]/b/text()").get()
			logging.info("Titel: "+titel)
			regesten=entscheid.xpath(".//tr[2]/td[2]/text()").getall()
			regeste=""
			for s in regesten:
				if not(s.isspace() or s==""):
					if len(regeste)>0:
						regeste=regeste+" "
					regeste=regeste+s
			datum=entscheid.xpath(".//td[@colspan='2']/i/text()").get()
			logging.info("Typ+Datum: "+datum)
			edatum=self.reDatum.search(datum).group(0)
			if self.reTyp.search(datum):
				typ= self.reTyp.search(datum).group(0)
			else:
				typ=""
			id=entscheid.xpath(".//td[a]/text()").get()
			logging.info("ID?: "+id)
			vgericht=''
			signatur, gericht, kammer=self.detect(vgericht,vkammer,num)
		
			item = {
				'Kanton': self.kanton_kurz,
				'Gericht' : gericht,
				'VGericht' : vgericht,
				'EDatum': edatum,
				'Titel': titel,
				'Leitsatz': regeste.strip(),
				'Num': num,
				'HTMLUrls': [url],
				'PDFUrls': [],
				'Kammer': kammer,
				'VKammer': vkammer,
				'Entscheidart': typ,
				'Signatur': signatur
			}
			request=scrapy.Request(url=url, callback=self.parse_page, errback=self.errback_httpbin, meta = {'item':item})
			yield(request)
		
		page=response.meta['page']+1

		if page*10<trefferZahl:
			logging.info("Hole Seite "+ str(page) +" von "+treffer+" Treffern.")
			request=self.request_generator(self.ab,page)[0]
			yield(request)
		

	def parse_page(self, response):	
		""" Parses the current search result page, downloads documents and yields the request for the next search
		result page
		"""
		logging.info("parse_page response.status "+str(response.status))
		logging.info("parse_page Rohergebnis "+str(len(response.body))+" Zeichen")
		logging.info("parse_page Rohergebnis: "+response.body_as_unicode())
		item=response.meta['item']
		item['html']=response.body_as_unicode()
		item['HTMLFiles']=[{'url': item['HTMLUrls'][0]}]
		yield(item)								


	def errback_httpbin(self, failure):
		# log all errback failures,
		# in case you want to do something special for some errors,
		# you may need the failure's type
		logging.error(repr(failure))
