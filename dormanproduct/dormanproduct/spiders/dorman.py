# -*- coding: utf-8 -*-
import scrapy
import json
import re
import logging
from urllib.parse import urljoin
from scrapy.http import HtmlResponse
from scrapy.selector import Selector


class DormanSpider(scrapy.Spider):
    name = 'dorman'
    allowed_domains = ['dormanproducts.com']
    start_urls = ['http://dormanproducts.com/']
    url_template = 'https://www.dormanproducts.com/gsearch.aspx?type=oesearch&origin=oesearch&q={}'

    def __init__(self, p=None, fn=None, *args, **kwargs):
        super(DormanSpider, self).__init__(*args, **kwargs)
        if not p and not fn:
            raise ValueError(
                'You have to input either product code via the command line (-o) or use a filename (-fn)!')
        if p:
            self.productcodes = [x.strip().lower() for x in p.split(',')]
        else:
            with open(fn, 'r') as fp:
                self.productcodes = [x.replace('\n', '') for x in fp.readlines()]
            logging.debug('outcodes loaded...{}'.format(self.productcodes))

    def start_requests(self):
        for code in self.productcodes:
            url = self.url_template.format(code)
            print(url)
            yield scrapy.Request(url, callback=self.parse_listing)

    def parse_listing(self, response):
        logging.debug('parsing listings...{}'.format(response.url))
        sel = Selector(response)
        links = sel.xpath('//div[@class="row searchResults"]').extract()
        for i in links:
            parse = Selector(text=i)
            itemname = parse.xpath('//span[@class="item-name"]/text()').get()
            iteminfo = parse.xpath('//h4/text()').get()
            itemsum = parse.xpath('string(//p)').get()
            tablehead = parse.xpath('//table//thead//th/text()').get()
            tablebody = parse.xpath('//table//tbody//th/text()').get()
            tabledata = parse.xpath('//table//td/text()').get()
            product_details = {
                'ProductName': itemname,
                'ProductInfo': iteminfo,
                'ProductSummary': itemsum,
                'Cross': tablehead,
                'OE': tablebody,
                'Mfr Name': tabledata
            }
            next_page = parse.xpath(
                '//a[@class="btn btn-darkgrey centered detail-btn"]/@href').extract()
            if next_page:
                url = urljoin('https://www.dormanproducts.com/', next_page[0])
                yield scrapy.Request(url, callback=self.detailparse, meta={'details':product_details,'dont_merge_cookies': True})

    def detailparse(self, response):
        sel = Selector(response)
        tabledetails = sel.xpath('//section[@id="productOE"]').extract()
        parse1 = Selector(text=tabledetails[0])
        oehead = parse1.xpath('//table//tbody//th//text()').get()
        oedata = parse1.xpath('//table//tbody//td//text()').get()
        oe_details = {
            'OE details': (oehead + ':' + oedata)
        }
        finalresult = response.meta['details']
        finalresult.update(oe_details)
        results = json.dumps(finalresult)
        item = json.loads(results)
        yield item

