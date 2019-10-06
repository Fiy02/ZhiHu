# -*- coding: utf-8 -*-
import json

from scrapy import Spider, Request

from zhihuuser.items import UserItem


# 获取知乎所有账户的信息；
class ZhihuSpider(Spider):
    name = 'zhihu'
    allowed_domains = ['www.zhihu.com']
    start_urls = ['http://www.zhihu.com/']

    start_user = 'excited-vczh'

    # 用户链接信息；
    user_url = 'https://www.zhihu.com/api/v4/members/{user}?include={include}'
    user_query = 'allow_message,is_followed,is_following,is_org,is_blocking,employments,answer_count,follower_count,articles_count,gender,badge[?(type=best_answerer)].topics'

    # 单页所有用户的链接信息；
    follows_url = 'https://www.zhihu.com/api/v4/members/{user}/followees?include={include}&offset={' \
                  'offset}&limit={limit}'
    follows_query = 'data[*].answer_count,articles_count,gender,follower_count,is_followed,is_following,badge[?(type=best_answerer)].topics'

    # 粉丝列表；
    followers_url = 'https://www.zhihu.com/api/v4/members/{user}/followers?include={include}&offset={offset}&limit={' \
                    'limit}'
    followers_query = 'data[*].answer_count,articles_count,gender,follower_count,is_followed,is_following,badge[?(type=best_answerer)].topics'

    def start_requests(self):
        yield Request(self.user_url.format(user=self.start_user, include=self.user_query), self.parse_user)
        yield Request(self.follows_url.format(user=self.start_user, include=self.follows_query, offset=0, limit=20),
                      callback=self.parse_follows)
        yield Request(self.followers_url.format(user=self.start_user, include=self.followers_query, offset=0, limit=20),
                      callback=self.parse_followers)

    # 返回用户数据及其链接信息；
    def parse_user(self, response):
        result = json.loads(response.text)
        item = UserItem()
        for field in item.fields:
            if field in result.keys():
                item[field] = result.get(field)
        yield item
        # 再进行对每个人的关注列表进行请求，层层递进；
        yield Request(self.follows_url.format(user=result.get('url_token'), include=self.follows_query, limit=20,
                                              offset=0), self.parse_follows)
        # 对每个人的粉丝列表进行请求；
        yield Request(self.followers_url.format(user=result.get('url_token'), include=self.followers_query, limit=20,
                                              offset=0), self.parse_followers)

    # 获取关注列表的请求；
    def parse_follows(self, response):
        results = json.loads(response.text)
        # 获取关注列表的 data 数据，再从中获取 url_token 的值来构造新的请求得到该用户的信息；
        if 'data' in results.keys():
            for result in results.get('data'):
                yield Request(self.user_url.format(user=result.get('url_token'), include=self.user_query),
                              self.parse_user)
        # 判断是否还有下一页并获取下一页的链接，最后回调函数本身再次获取关注列表的 data 数据，直到最后一页；
        if 'paging' in results.keys() and results.get('paging').get('is_end') == False:
            next_page = results.get('paging').get('next')
            yield Request(next_page, self.parse_follows)

    # 获取粉丝列表的请求；（与关注列表类似）
    def parse_followers(self, response):
        results = json.loads(response.text)
        if 'data' in results.keys():
            for result in results.get('data'):
                yield Request(self.user_url.format(user=result.get('url_token'), include=self.user_query),
                              self.parse_user)

        if 'paging' in results.keys() and results.get('paging').get('is_end') == False:
            next_page = results.get('paging').get('next')
            yield Request(next_page, self.parse_followers)