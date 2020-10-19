# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class NeuescraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    Signatur = scrapy.Field()
    Spider = scrapy.Field()
    Job = scrapy.Field()
    Kanton = scrapy.Field()
    Gericht = scrapy.Field()
    Kammer = scrapy.Field()
    Num = scrapy.Field()
    EDatum = scrapy.Field()
    Titel = scrapy.Field()
    Leitsatz = scrapy.Field()
    PDatum = scrapy.Field()
    Rechtsgebiet = scrapy.Field()
    DocID = scrapy.Field()
    PDFUrls = scrapy.Field()
    HTMLUrls = scrapy.Field()
    PDFFiles = scrapy.Field()
    HTMLFiles = scrapy.Field()
    Raw = scrapy.Field()
    Gerichtsbarkeit = scrapy.Field()
    Weiterzug = scrapy.Field()
    Entscheidart = scrapy.Field()

    # pass


"""
<Entscheid>
	<Meta>
		<Signatur>...</Signatur>!
		<Spider>...</Spider>!
		<Job>...</Job>!
		<Kanton>...</Kanton>!
		<Gericht>...</Gericht>!
		<Kammer>...</Kammer>?
	</Meta>
	<Treffer>
		<Quelle>
			<Gerichtsbarkeit>...</Gerichtsbarkeit>?
			<Gericht>...</Gericht>!
			<Kammer>...</Kammer>?
		</Quelle>
		<Kurz>
			<Titel>...</Titel>?
			<Leitsatz>...</Leitsatz>?
			<Rechtsgebiet>...</Rechtsgebiet>?
			<Entscheidart>...</Entscheidart>?
		</Kurz>
		<Sonst>
			<PDatum>...</PDatum>?
			<Weiterzug>...</Weiterzug>?
		</Sonst>
		<Source>
			<DocID>...</DocID>?
			<PdfUrl>...</PdfUrl>*
			<PdfFile>...</PdfFile>*
			<HtmlUrl>...</HtmlUrl>*
			<HtmlFile>...</HtmlFile>*
			<Raw>...</Raw>?
		</Source>
	</Treffer>
</Entscheid>"""
			
			
			
