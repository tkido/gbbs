#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import base64
import datetime
import hashlib
import logging
import re

from google.appengine.api import memcache
from google.appengine.ext import ndb

import c
import conf
import ex

class Counter(ndb.Model):
    #id = "Board", "MyUser", "Thread", "Theme"
    count = ndb.IntegerProperty(required=True, indexed=False)

class Board(ndb.Model):
    #id = namespace string
    author_id = ndb.IntegerProperty(required=True, indexed=False)
    updater_id = ndb.IntegerProperty(required=True, indexed=False)
    
    status = ndb.IntegerProperty(required=True)
    updated_at = ndb.DateTimeProperty(required=True, indexed=False)
    since = ndb.DateTimeProperty(required=True, indexed=False)
    
    title = ndb.StringProperty(required=True, indexed=False)
    description = ndb.StringProperty(indexed=False)
    keywords = ndb.StringProperty(indexed=False)
    template = ndb.TextProperty(indexed=False)
    
    hash_cycle = ndb.IntegerProperty(required=True, indexed=False)  #0:ever(no change) 1:year 2:month 3:day
    salt = ndb.StringProperty(required=True, indexed=False)
    timezone = ndb.IntegerProperty(required=True, indexed=False)
    
    allow_index = ndb.BooleanProperty(required=True, indexed=False)
    allow_robots = ndb.BooleanProperty(required=True, indexed=False)
    
    max_reses = ndb.IntegerProperty(required=True, indexed=False)
    max_threads = ndb.IntegerProperty(required=True, indexed=False)
    max_chars = ndb.IntegerProperty(required=True, indexed=False)
    max_chars_title = ndb.IntegerProperty(required=True, indexed=False)
    max_chars_template = ndb.IntegerProperty(required=True, indexed=False)
    max_rows = ndb.IntegerProperty(required=True, indexed=False)
    max_rows_template = ndb.IntegerProperty(required=True, indexed=False)

    def readable(self):
        return self.status != c.DELETED
    def writable(self):
        return self.status == c.NORMAL

    def now(self):
      return datetime.datetime.now() + datetime.timedelta(hours = self.timezone)
    
    def hash(self, source):
      sha1 = hashlib.sha1()
      sha1.update(str(source))
      sha1.update(self.salt)
      
      local_now = self.now()
      if self.hash_cycle >= 1:
        sha1.update(str(local_now.year))
      if self.hash_cycle >= 2:
        sha1.update(str(local_now.month))
      if self.hash_cycle >= 3:
        sha1.update(str(local_now.day))
      
      rst = sha1.digest()
      rst = base64.urlsafe_b64encode(rst)
      rst = rst[:8]
      return rst
      
    def validate_content(self, content):
        if not content or \
           len(content) > self.max_chars or \
           len(re.findall('\n', content)) >= self.max_chars:
            raise ex.InvalidContent(self)
        return content
    
    def validate_title(self, title):
        d_count = len(re.findall('%d', title))
        if not title or \
           len(title) > self.max_chars_title or \
           d_count >= 2:
            raise ex.InvalidTitle(self)
        if d_count == 0:
            title += u' その%d'
        return title
    
    def validate_template(self, template):
        if not template or \
           len(template) > self.max_chars_template or \
           len(re.findall('\n', template)) >= self.max_rows_template:
            raise ex.InvalidTemplate(self)
        return template
    
class MyUser(ndb.Model):
    #id = user.user_id()
    user = ndb.UserProperty(required=True)
    
    myuser_id = ndb.IntegerProperty(required=True)
    ban_count = ndb.IntegerProperty(required=True, indexed=False)
    
    status = ndb.IntegerProperty(required=True)
    updated_at = ndb.DateTimeProperty(required=True, indexed=False)
    since = ndb.DateTimeProperty(required=True, indexed=False)
    
    def readable(self):
        return self.status != c.DELETED
    def flush(self):
        memcache.delete(self.key.id())
    
class Theme(ndb.Model):
    #id = Counter("Theme").count
    author_id = ndb.IntegerProperty(required=True, indexed=False)
    updater_id = ndb.IntegerProperty(required=True, indexed=False)
    
    status = ndb.IntegerProperty(required=True, indexed=False)
    updated_at = ndb.DateTimeProperty(required=True, indexed=False)
    since = ndb.DateTimeProperty(required=True, indexed=False)
    
    title_template = ndb.StringProperty(required=True, indexed=False)
    template = ndb.TextProperty(required=True)
    keeped_title_template = ndb.StringProperty(required=True, indexed=False)
    keeped_template = ndb.TextProperty(required=True)
    
    def readable(self):
        return self.status != c.DELETED
    def writable(self):
        return self.status == c.NORMAL
    
class Thread(ndb.Model):
    #id = Counter("Thread").count
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
        return self.status != c.DELETED
    
    @classmethod
    def query_normal(cls):
        return cls.query(cls.status == c.NORMAL).order(-cls.updated_at)
    @classmethod
    def query_stored(cls, update_from, update_to):
        return cls.query(cls.status == c.STORED).filter(cls.updated_at >= update_from).filter(cls.updated_at < update_to).order(-cls.updated_at)
    @classmethod
    def query_theme(cls, theme_id):
        return cls.query(cls.theme_id == theme_id)

class Response(ndb.Model):
    #id = thread.id * c.TT + number
    author_id = ndb.IntegerProperty(required=True, indexed=False)
    updater_id = ndb.IntegerProperty(required=True, indexed=False)
    
    status = ndb.IntegerProperty(required=True, indexed=False)
    updated_at = ndb.DateTimeProperty(required=True, indexed=False)
    since = ndb.DateTimeProperty(required=True, indexed=False)
    
    number = ndb.IntegerProperty(required=True, indexed=False)
    datetime_str = ndb.StringProperty(required=True, indexed=False)
    hashed_id = ndb.StringProperty(required=True, indexed=False)
    content = ndb.TextProperty(required=True)
    
    char_name = ndb.StringProperty(indexed=False)
    char_id = ndb.StringProperty(indexed=False)
    char_emotion = ndb.StringProperty(indexed=False)
    
    @classmethod
    def query_normal(cls, thread_id, first):
        first_key = ndb.Key('Response', thread_id * c.TT + first)
        last_key = ndb.Key('Response', thread_id * c.TT + c.K)
        return cls.query(first_key <= cls._key).filter(cls._key <= last_key)
    
    @classmethod
    def latest_num_of(cls, thread_id):
        first_id = thread_id * c.TT
        first_key = ndb.Key('Response', first_id)
        last_key = ndb.Key('Response', first_id + c.K)
        keys = cls.query(first_key <= cls._key).filter(cls._key <= last_key).fetch(conf.MAX_FETCH, keys_only=True)
        if not keys:
            return first_id
        id = keys[-1].id()
        return first_id if id < first_id else id
