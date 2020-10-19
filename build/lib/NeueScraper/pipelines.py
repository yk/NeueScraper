# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import os
import logging
import re
import sys
import traceback
import hashlib
import json
import scrapy
import inspect
from scrapy.utils.python import to_bytes
from scrapy.utils.boto import is_botocore
from twisted.internet import defer, threads
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from io import BytesIO
from scrapy.utils.misc import md5sum
from lxml import etree

filenamechars=re.compile("[^-a-zA-Z0-9]")

from urllib.parse import urlparse

from scrapy.pipelines.files import FilesPipeline
from scrapy.pipelines.files import S3FilesStore
from scrapy.pipelines.files import FSFilesStore
from scrapy.pipelines.files import GCSFilesStore
from scrapy.pipelines.files import FTPFilesStore

class MyWriterPipeline:
	def open_spider(self,spider):
		logger.info("pipeline open")

	def close_spider(self,spider):
		logger.info("pipeline close")

	def process_item(self, item, spider):
		logger.info("pipeline item")
		if 'Num' in item:
			logger.info("Geschäftsnummer: "+item['Num'])

		if 'PDFFiles' in item and item['PDFFiles']:
			logger.info("Files: "+json.dumps(item['PDFFiles'][0]))
		else:
			logger.warning("kein PDF geholt")
			#Später wenn auch kein HTML ein DropItem

		root = etree.Element('Entscheid')
		meta = etree.Element('Meta')
		root.append(meta)
		PipelineHelper.xml_add_element(meta,'Signatur',item['Signatur'])
		PipelineHelper.xml_add_element(meta,'Spider',spider.name)
		PipelineHelper.xml_add_element(meta,'Job',spider.scrapy_job)
		PipelineHelper.xml_add_element(meta,'Kanton',item['Signatur'][:2])
		if spider.ebenen > 1 and 'Gericht' in item:
			PipelineHelper.xml_add_element(meta,'Gericht',item['Gericht'])
		if spider.ebenen > 2 and 'Kammer' in item:
			PipelineHelper.xml_add_element(meta,'Kammer',item['Kammer'])
		treffer = etree.Element('Treffer')
		root.append(treffer)
		quelle = etree.Element('Quelle')
		treffer.append(quelle)
		if 'Gerichtsbarkeit' in item:
			PipelineHelper.xml_add_element(quelle,'Gerichtsbarkeit',item['Gerichtsbarkeit'])
		if 'VGericht' in item:
			PipelineHelper.xml_add_element(quelle,'Gericht',item['VGericht'])
		elif 'Gericht' in item:
			PipelineHelper.xml_add_element(quelle,'Gericht',item['Gericht'])	
		if 'VKammer' in item:
			PipelineHelper.xml_add_element(quelle,'Kammer',item['VKammer'])
		elif 'Kammer' in item:
			PipelineHelper.xml_add_element(quelle,'Kammer',item['Kammer'])
		kurz = etree.Element('Kurz')
		treffer.append(kurz)
		if 'Titel' in item:
			PipelineHelper.xml_add_element(kurz,'Titel',item['Titel'])
		if 'Leitsatz' in item:
			PipelineHelper.xml_add_element(kurz,'Leitsatz',item['Leitsatz'])
		if 'Rechtsgebiet' in item:
			PipelineHelper.xml_add_element(kurz,'Rechtsgebiet',item['Rechtsgebiet'])
		if 'Entscheidart' in item:
			PipelineHelper.xml_add_element(kurz,'Entscheidart',item['Entscheidart'])
		sonst = etree.Element('Sonst')
		treffer.append(sonst)
		if 'PDatum' in item:
			PipelineHelper.xml_add_element(sonst,'PDatum',item['PDatum'])
		if 'Weiterzug' in item:
			PipelineHelper.xml_add_element(sonst,'Weiterzug',item['Weiterzug'])
		source = etree.Element('Source')
		treffer.append(source)
		if 'DocID' in item:
			PipelineHelper.xml_add_element(source,'DocID',item['DocID'])
		if 'PdfUrl' in item:
			PipelineHelper.xml_add_element(source,'PdfUrl',item['PdfUrl'][0])
		if 'HtmlUrl' in item:
			PipelineHelper.xml_add_element(source,'HtmlUrl',item['HtmlUrl'][0])
		if 'Raw' in item:
			PipelineHelper.xml_add_element(source,'Raw',etree.CDATA(item['Raw']))
		upload_file_content = etree.tostring(root, pretty_print=True)
			
		upload_file_key = MyS3FilesStore.shared_s3_prefix+PipelineHelper.file_path(self,item, spider)+".xml"
		upload_file_meta={}
		upload_file_meta['ScrapyJob']=spider.scrapy_job
		upload_file_meta['Spider']=spider.name
		upload_file_tags=PipelineHelper.get_tags(self, item, spider)

		MyS3FilesStore.shared_s3_client.put_object(Body=upload_file_content, Bucket=MyS3FilesStore.shared_s3_bucket, Key=upload_file_key, ACL=MyS3FilesStore.POLICY, Metadata={k: str(v) for k, v in upload_file_meta.items()}, Tagging=upload_file_tags)
		
		return item
		
logger = logging.getLogger(__name__)

class MyS3FilesStore(S3FilesStore):
	AWS_ACCESS_KEY_ID = "AKIAXYG6RX7BKEZXJFZT"
	AWS_SECRET_ACCESS_KEY = "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"
	AWS_ENDPOINT_URL = "s3://entscheidsuche.ch"
	AWS_REGION_NAME = "eu-west-3"
	AWS_USE_SSL = None
	AWS_VERIFY = None
	shared_s3_client = None
	shared_s3_bucket = None
	shared_s3_prefix = None

	POLICY = 'private'  # Overriden from settings.FILES_STORE_S3_ACL in FilesPipeline.from_settings
	HEADERS = {
		'Cache-Control': 'max-age=172800',
	}

	def __init__(self,uri=None):
		if uri is None:
			logger.info("__init__ ohne uri aufgerufen")
			uri='s3://entscheidsuche.ch/scraper'
		else:
			logger.info("__init__ mit uri '"+uri+"' aufgerufen")		

		self.is_botocore = is_botocore()
		if self.is_botocore:
			import botocore.session
			session = botocore.session.get_session()
			logger.info("init: AWS_ACCESS_KEY_ID: "+self.AWS_ACCESS_KEY_ID)
			logger.info("init: AWS_SECRET_ACCESS_KEY: "+self.AWS_SECRET_ACCESS_KEY)
			logger.info("init: AWS_ENDPOINT_URL: "+self.AWS_ENDPOINT_URL)
			logger.info("init: AWS_REGION_NAME: "+self.AWS_REGION_NAME)
			self.s3_client = session.create_client(
				's3',
				aws_access_key_id=self.AWS_ACCESS_KEY_ID,
				aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
				endpoint_url=self.AWS_ENDPOINT_URL,
				region_name=self.AWS_REGION_NAME,
				use_ssl=self.AWS_USE_SSL,
				verify=self.AWS_VERIFY
			)
			MyS3FilesStore.shared_s3_client=self.s3_client #Damit auch die anderen Schreiboperationen diesen Client mit nutzen können
		else:
			from boto.s3.connection import S3Connection
			self.S3Connection = S3Connection(self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY)
		if not uri.startswith("s3://"):
			raise ValueError(f"Incorrect URI scheme in {uri}, expected 's3'")
		self.bucket, self.prefix = uri[5:].split('/', 1)
		MyS3FilesStore.shared_s3_bucket=self.bucket
		MyS3FilesStore.shared_s3_prefix=self.prefix
		
	def stat_file(self, path, info):
		logger.info("stat_file called")
		def _onsuccess(boto_key):
			logger.info("stat_file_onsuccess called")
			if self.is_botocore:
				checksum = boto_key['ETag'].strip('"')
				last_modified = boto_key['LastModified']
				modified_stamp = time.mktime(last_modified.timetuple())
			else:
				checksum = boto_key.etag.strip('"')
				last_modified = boto_key.last_modified
				modified_tuple = parsedate_tz(last_modified)
				modified_stamp = int(mktime_tz(modified_tuple))
			return {'checksum': checksum, 'last_modified': modified_stamp}
		return self._get_boto_key(path).addCallback(_onsuccess)

	def persist_file(self, path, buf, info, meta=None, headers=None, item=None):
		logger.info("persist_file called")
		if meta==None:
			meta={}
		meta['scrapy_job']=info.spider.scrapy_job
		meta['spider']=info.spider.name
		upload_file_tags=PipelineHelper.get_tags(self, item, info.spider)

		# Upload file to S3 storage
		key_name = f'{self.prefix}{path}'
		logger.info("pf key_name: "+key_name)
		buf.seek(0)
		if self.is_botocore:
			logger.info("pf is_botocore")
			extra = self._headers_to_botocore_kwargs(self.HEADERS)
			if headers:
				extra.update(self._headers_to_botocore_kwargs(headers))
			logger.info("pf schreibe nun")
			return threads.deferToThread(
				self.s3_client.put_object,
				Bucket=self.bucket,
				Key=key_name,
				Body=buf,
				Metadata={k: str(v) for k, v in (meta or {}).items()},
				ACL=self.POLICY,
				Tagging=upload_file_tags,
				**extra)
		else: #ohne botocore noch keine Metadaten und Tags
			logger.info("pf not is_botocore")
			b = self._get_boto_bucket()
			k = b.new_key(key_name)
			if meta:
				for metakey, metavalue in meta.items():
					k.set_metadata(metakey, str(metavalue))
			h = self.HEADERS.copy()
			if headers:
				h.update(headers)
			return threads.deferToThread(
				k.set_contents_from_string, buf.getvalue(),
				headers=h, policy=self.POLICY)
		
	def _get_boto_bucket(self):
		logger.info("_get_boto_bucket called")
		logger.info("AWS_ACCESS_KEY_ID: "+self.AWS_ACCESS_KEY_ID+"AWS_SECRET_ACCESS_KEY"+self.AWS_SECRET_ACCESS_KEY)
		# disable ssl (is_secure=False) because of this python bug:
		# https://bugs.python.org/issue5103
		c = self.S3Connection(self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY, is_secure=False)
		return c.get_bucket(self.bucket, validate=False)

	def _get_boto_key(self, path):
		logger.info("_get_boto_key called")
		key_name = f'{self.prefix}{path}'
		logger.info("gbk key_name: "+key_name)
		if self.is_botocore:
			logger.info("gbk is_botocore")
			return threads.deferToThread(
				self.s3_client.head_object,
				Bucket=self.bucket,
				Key=key_name)
		else:
			logger.info("gkb not is_botocore")
			b = self._get_boto_bucket()
			return threads.deferToThread(b.get_key, key_name)


class NeuescraperPipeline:
    def process_item(self, item, spider):
        return item

class PipelineHelper:
	def file_path(self, item, spider=None):
		try:
			num=item['Num']
			logger.info('Geschäftsnummer: '+num)
			edatum=item['EDatum']
			if edatum is None:
				edatum='nodate'
			filename=filenamechars.sub('-',num)+"_"+filenamechars.sub('-',edatum)
			dir = "undefined"
			if spider:
				dir=spider.name
				logger.info('Spider-Name: '+spider.name)
				prefix=item['Signatur']
			pfad=dir+"/"+prefix+"_"+filename
			logger.info('Pfad: '+pfad)
			return pfad
		except Exception as e:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			logger.error("Unexpected error: " + repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
			raise
			
	def get_tags(self, item, spider):
		tags='Spider='+spider.name+'&ScrapyJob='+spider.scrapy_job+'&Signatur='+item['Signatur']+'&Kanton='+item['Signatur'][:2]
		if 'EDatum' in item:
			tags=tags+'&Entscheiddatum='+item['EDatum']
		if 'Num' in item:
			tags=tags+'&Geschaeftsnummer='+item['Num']
		if 'PDFFiles' in item:
			tags=tags+'&Filetyp=PDF'
		logger.info("Tags: "+tags)
		return tags

	def xml_add_element(parent, key, value):
		element = etree.Element(key)
		element.text=value
		parent.append(element)




class MyFilesPipeline(FilesPipeline):
	STORE_SCHEMES = {
		'': FSFilesStore,
		'file': FSFilesStore,
		's3': MyS3FilesStore,
		'gs': GCSFilesStore,
		'ftp': FTPFilesStore
	}

	def file_path(self, request, response=None, info=None, item=None):
		if item is None:
			item=request.meta['item']	
		return PipelineHelper.file_path(self,item, info.spider if info is not None else None)+".pdf"

	def get_media_requests(self, item, info):
		urls = item[self.files_urls_field] if self.files_urls_field in item else []
		return [scrapy.Request(url=u, meta={"item":item}) for u in urls]

	def file_downloaded(self, response, request, info=None, item=None):
		if item is None:
			item=request.meta['item']
			logger.info('item in file_downloaded gesetzt')
		else:
			logger.info('item war in file_downloaded bereits gesetzt')		
		path = self.file_path(request, response, info, item=item)
		buf = BytesIO(response.body)
		checksum = md5sum(buf)
		buf.seek(0)
		self.store.persist_file(path, buf, info, item=item) # Parameter item wurde hinzugefügt. store muss dazu angepasst werden (wurde hier für S3 getan)
		return checksum

	
