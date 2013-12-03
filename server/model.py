#!/usr/local/bin/python
# -*- coding:utf-8 -*-
import datetime
import logging
import re

from google.appengine.ext import ndb

import const
import config

class Counter(ndb.Model):
    #id = "MyUser" or "Thread" or "Theme"
    count = ndb.IntegerProperty(required=True, indexed=False)

class Board(ndb.Model):
    #id = namespace string
    author_id = ndb.IntegerProperty(required=True, indexed=False)
    updater_id = ndb.IntegerProperty(required=True, indexed=False)
    
    status = ndb.IntegerProperty(required=True)
    updated_at = ndb.DateTimeProperty(required=True)
    since = ndb.DateTimeProperty(required=True, indexed=False)
    
    title = ndb.StringProperty(required=True, indexed=False)
    description = ndb.StringProperty(required=True, indexed=False)
    keywords = ndb.StringProperty(required=True, indexed=False)
    template = ndb.TextProperty(required=True)

class MyUser(ndb.Model):
    #id = user.user_id()
    user = ndb.UserProperty(required=True)
    
    myuser_id = ndb.IntegerProperty(required=True)
    ban_count = ndb.IntegerProperty(required=True, indexed=False)
    
    status = ndb.IntegerProperty(required=True)
    updated_at = ndb.DateTimeProperty(required=True)
    since = ndb.DateTimeProperty(required=True, indexed=False)

class Theme(ndb.Model):
    #id = from model.Counter("Theme").count
    author_id = ndb.IntegerProperty(required=True, indexed=False)
    updater_id = ndb.IntegerProperty(required=True, indexed=False)
    
    status = ndb.IntegerProperty(required=True)
    updated_at = ndb.DateTimeProperty(required=True)
    since = ndb.DateTimeProperty(required=True, indexed=False)
    
    title_template = ndb.StringProperty(required=True, indexed=False)
    template = ndb.TextProperty(required=True)
    keeped_title_template = ndb.StringProperty(required=True, indexed=False)
    keeped_template = ndb.TextProperty(required=True)
    
    def readable(self):
        return self.status != const.DELETED
    def writable(self):
        return self.status == const.NORMAL
    
    @classmethod
    def validate_title_template(cls, title_template):
        d_count = len(re.findall('%d', title_template))
        if not title_template or \
           len(title_template) > config.MAX_CHARS_IN_TITLE or \
           d_count >= 2:
            return None
        if d_count == 0:
            title_template += u' その%d'
        return title_template
    
    @classmethod
    def validate_template(cls, template):
        if not template or \
           len(template) > config.MAX_CHARS_IN_CONTENT or \
           len(re.findall('\n', template)) >= config.MAX_ROWS_IN_CONTENT:
            return None
        return template

class Thread(ndb.Model):
    #id = from model.Counter("Thread").count
    theme_id = ndb.IntegerProperty(required=True)
    author_id = ndb.IntegerProperty(required=True, indexed=False)
    updater_id = ndb.IntegerProperty(required=True, indexed=False)
    
    status = ndb.IntegerProperty(required=True)
    updated_at = ndb.DateTimeProperty(required=True)
    since = ndb.DateTimeProperty(required=True, indexed=False)
    
    title = ndb.StringProperty(required=True, indexed=False)
    datetime_str = ndb.StringProperty(required=True, indexed=False)
    hashed_id = ndb.StringProperty(required=True, indexed=False)
    content = ndb.TextProperty(required=True)
    
    thread_number = ndb.IntegerProperty(required=True, indexed=False)
    response_count = ndb.IntegerProperty(required=True, indexed=False)
    responsed_at = ndb.DateTimeProperty(required=True, indexed=False)
    
    prev_thread_id = ndb.IntegerProperty(indexed=False)
    prev_thread_title = ndb.StringProperty(indexed=False)
    next_thread_id = ndb.IntegerProperty(indexed=False)
    next_thread_title = ndb.StringProperty(indexed=False)
    
    def readable(self):
        return self.status != const.DELETED
    def writable(self):
        return self.status == const.NORMAL and \
               self.response_count < config.MAX_RESES_IN_THREAD
    def need_to_update_response_count(self, now, last_number):
        return last_number >= config.MAX_RESES_IN_THREAD or \
               ((now - self.responsed_at) > datetime.timedelta(seconds = 10) and \
                self.response_count < last_number)
    def need_to_prepare_next_thread(self):
        return self.next_thread_id == 0 and \
               self.response_count >= config.MAX_RESES_IN_THREAD
    def need_to_create_next_thread(self):
        return self.next_thread_id > 0 and \
               self.next_thread_title == ''
    def need_to_store(self):
        return self.status == const.NORMAL and \
               self.next_thread_title != ''
    
    @classmethod
    def query_normal(cls):
        return cls.query(cls.status == const.NORMAL).order(-cls.updated_at)
    @classmethod
    def query_stored(cls, update_from, update_to):
        return cls.query(cls.status == const.STORED).filter(cls.updated_at >= update_from).filter(cls.updated_at < update_to).order(-cls.updated_at)

class Response(ndb.Model):
    #id = thread.id * 10000 + id
    author_id = ndb.IntegerProperty(required=True, indexed=False)
    updater_id = ndb.IntegerProperty(required=True, indexed=False)
    
    status = ndb.IntegerProperty(required=True)
    updated_at = ndb.DateTimeProperty(required=True)
    since = ndb.DateTimeProperty(required=True, indexed=False)
    
    number = ndb.IntegerProperty(required=True, indexed=False)
    datetime_str = ndb.StringProperty(required=True, indexed=False)
    hashed_id = ndb.StringProperty(required=True, indexed=False)
    content = ndb.TextProperty(required=True)
    
    char_name = ndb.StringProperty(indexed=False)
    char_id = ndb.StringProperty(indexed=False)
    char_emotion = ndb.StringProperty(indexed=False)
    
    @classmethod
    def validate_content(cls, content):
        if not content or \
           len(content) > config.MAX_CHARS_IN_CONTENT or \
           len(re.findall('\n', content)) >= config.MAX_ROWS_IN_CONTENT:
            return None
        return content
    
    @classmethod
    def query_normal(cls, thread_id, first):
        first_key = ndb.Key('Response', thread_id * 10000 + first)
        last_key = ndb.Key('Response', thread_id * 10000 + 1000)
        return cls.query(first_key <= cls._key).filter(cls._key <= last_key)
    
    @classmethod
    def latest_num_of(cls, thread_id):
        first_id = thread_id * 10000
        first_key = ndb.Key('Response', first_id)
        last_key = ndb.Key('Response', first_id + 1000)
        keys = cls.query(first_key <= cls._key).filter(cls._key <= last_key).fetch(1000, keys_only=True)
        if not keys:
            return first_id
        id = keys[-1].id()
        return first_id if id < first_id else id

