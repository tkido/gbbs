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
import util

class Counter(ndb.Model):
    #id = "Board", "MyUser", "Thread", "Template", "Log"
    count = ndb.IntegerProperty(required=True, indexed=False)

    @classmethod
    @ndb.transactional()
    def incr(cls, id):
        counter = cls.get_by_id(id)
        counter.count += 1
        if counter.put():
            return counter.count

class Log(ndb.Model):
    #id = Counter("Log").count
    log = ndb.TextProperty(required=True, indexed=False)

class Board(ndb.Model):
    #id = ns, or 'b'(default)
    author_id          = ndb.IntegerProperty( required=True, indexed=False)
    updater_id         = ndb.IntegerProperty( required=True, indexed=False)
    
    status             = ndb.IntegerProperty( required=True               )
    updated            = ndb.DateTimeProperty(required=True, indexed=False)
    since              = ndb.DateTimeProperty(required=True, indexed=False)
    
    title              = ndb.StringProperty(  required=True, indexed=False)
    description        = ndb.StringProperty(                 indexed=False)
    keywords           = ndb.StringProperty(                 indexed=False)
    template           = ndb.TextProperty(                   indexed=False)
    
    hash_cycle         = ndb.IntegerProperty( required=True, indexed=False)  #0:ever(no change) 1:year 2:month 3:day
    salt               = ndb.StringProperty(  required=True, indexed=False)
    timezone           = ndb.IntegerProperty( required=True, indexed=False)
    
    allow_index        = ndb.BooleanProperty( required=True, indexed=False)
    allow_robots       = ndb.BooleanProperty( required=True, indexed=False)
    
    max                = ndb.IntegerProperty(                indexed=False, repeated=True)
    ad                 = ndb.TextProperty(                   indexed=False, repeated=True)
    
    @classmethod
    def query_normal(cls):
        return cls.query(cls.status == c.NORMAL, namespace = c.BOARD_NAMESPACE)

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
      
    def validate_title(self, title):
        d_count = len(re.findall('%d', title))
        if not title or \
           len(title) > self.max[c.CHARS_TITLE] or \
           d_count >= 2:
            raise ex.InvalidTitle(self)
        if d_count == 0:
            title += u' その%d'
        return title
    
    def validate_content(self, content):
        if not content or \
           len(content) > self.max[c.CHARS] or \
           len(re.findall('\n', content)) >= self.max[c.ROWS]:
            raise ex.InvalidContent(self)
        return content
    
    def validate_template(self, template):
        if not template or \
           len(template) > self.max[c.CHARS_TEMPLATE] or \
           len(re.findall('\n', template)) >= self.max[c.ROWS_TEMPLATE]:
            raise ex.InvalidTemplate(self)
        return template
    
class MyUser(ndb.Model):
    #id = user.user_id()
    user      = ndb.UserProperty(    required=True               )
    
    myuser_id = ndb.IntegerProperty (required=True               )
    ban_count = ndb.IntegerProperty (required=True, indexed=False)
    
    status    = ndb.IntegerProperty (required=True               )
    updated   = ndb.DateTimeProperty(required=True, indexed=False)
    since     = ndb.DateTimeProperty(required=True, indexed=False)
    
    def readable(self):
        return self.status != c.DELETED
    def flush(self):
        memcache.delete(self.key.id())
    
class Template(ndb.Model):
    #id = Counter("Template").count
    author_id       = ndb.IntegerProperty( required=True, indexed=False)
    updater_id      = ndb.IntegerProperty( required=True, indexed=False)
    
    status          = ndb.IntegerProperty( required=True, indexed=False)
    updated         = ndb.DateTimeProperty(required=True, indexed=False)
    since           = ndb.DateTimeProperty(required=True, indexed=False)
    
    title           = ndb.StringProperty(  required=True, indexed=False)
    content         = ndb.TextProperty(    required=True               )
    keeped_title    = ndb.StringProperty(  required=True, indexed=False)
    keeped_content  = ndb.TextProperty(    required=True               )
    
    def readable(self):
        return self.status != c.DELETED
    def writable(self):
        return self.status == c.NORMAL
    
class Thread(ndb.Model):
    #id = Counter("Thread").count
    template_id = ndb.IntegerProperty( required=True               )
    author_id   = ndb.IntegerProperty( required=True, indexed=False)
    updater_id  = ndb.IntegerProperty( required=True, indexed=False)
    
    status      = ndb.IntegerProperty( required=True               )
    updated     = ndb.DateTimeProperty(required=True               )
    since       = ndb.DateTimeProperty(required=True, indexed=False)
    
    title       = ndb.StringProperty(  required=True, indexed=False)
    dt_str      = ndb.StringProperty(  required=True, indexed=False)
    hashed_id   = ndb.StringProperty(  required=True, indexed=False)
    content     = ndb.TextProperty(    required=True               )
    
    number      = ndb.IntegerProperty( required=True, indexed=False)
    res_count   = ndb.IntegerProperty( required=True, indexed=False)
    resed       = ndb.DateTimeProperty(required=True, indexed=False)
    
    prev_id     = ndb.IntegerProperty(                indexed=False)
    prev_title  = ndb.StringProperty(                 indexed=False)
    next_id     = ndb.IntegerProperty(                indexed=False)
    next_title  = ndb.StringProperty(                 indexed=False)
    
    def readable(self):
        return self.status != c.DELETED
    
    @ndb.transactional()
    def reopen(self):
        thread = self.key.get()
        thread.status = c.NORMAL
        thread.put()
    
    @ndb.transactional()
    def store(self):
        thread = self.key.get()
        thread.status = c.STORED
        thread.put()
    
    @ndb.transactional()
    def delete(self):
        thread = self.key.get()
        thread.status = c.DELETED
        thread.put()
    
    def prepare_next(self):
        next_id = Counter.incr('Thread')
        thread_key = self.key
        @ndb.transactional()
        def set_next_id():
            thread = thread_key.get()
            if thread.next_id == 0:
                thread.next_id = next_id
                if thread.put():
                    return thread
        self = set_next_id()

    def create_next(self, board):
        thread = self.key.get()
        now = board.now()
        dt_str = util.dt_to_str(now)
        myuser_id = 0
        hashed_id = board.hash(myuser_id)
        
        template = Template.get_by_id(thread.template_id)
        next_number = thread.number + 1
        new_title = template.title % next_number
        
        next_key = ndb.Key('Thread', thread.next_id)
        @ndb.transactional()
        def get_or_insert():
            next = next_key.get()
            if next:
                return next
            else:
                next = Thread(id = thread.next_id,
                              template_id = thread.template_id,
                              author_id = myuser_id,
                              updater_id = myuser_id,

                              status = c.NORMAL,
                              updated = now,
                              since = now,

                              title = new_title,
                              dt_str = dt_str,
                              hashed_id = hashed_id,
                              content = template.content,

                              number = next_number,
                              res_count = 0,
                              resed = now,

                              prev_id = thread.key.id(),
                              prev_title = thread.title,
                              next_id = 0,
                              next_title = '',
                             )
                if next.put():
                    return next
        next = get_or_insert()
        if next:
            util.flush_page('/related/%d/' % thread.template_id)
            @ndb.transactional()
            def set_next_title():
                thread = self.key.get()
                if thread.next_title == '':
                    thread.next_title = next.title
                    if thread.put():
                        return thread
            self = set_next_title()
    
    @classmethod
    def query_normal(cls):
        return cls.query(cls.status == c.NORMAL).order(-cls.updated)
    @classmethod
    def query_stored(cls):
        return cls.query(cls.status == c.STORED).order(-cls.updated)
    @classmethod
    def query_related(cls, template_id):
        return cls.query(cls.template_id == template_id)
    @classmethod
    def clean(cls, board):
        query = cls.query_normal()
        keys = query.fetch(board.max[c.THREADS]+3, keys_only=True)
        needs = len(keys) - board.max[c.THREADS]
        @ndb.transactional()
        def store(key):
            thread = key.get()
            thread.status = c.STORED
            thread.put()
        for i in range(needs):
            store(keys[-i-1])


class Res(ndb.Model):
    #id = thread.id * c.TT + number
    author_id    = ndb.IntegerProperty( required=True, indexed=False)
    updater_id   = ndb.IntegerProperty( required=True, indexed=False)
    
    status       = ndb.IntegerProperty( required=True, indexed=False)
    updated      = ndb.DateTimeProperty(required=True, indexed=False)
    since        = ndb.DateTimeProperty(required=True, indexed=False)
    
    number       = ndb.IntegerProperty( required=True, indexed=False)
    dt_str       = ndb.StringProperty(  required=True, indexed=False)
    hashed_id    = ndb.StringProperty(  required=True, indexed=False)
    content      = ndb.TextProperty(    required=True               )
    
    char_name    = ndb.StringProperty(                 indexed=False)
    char_id      = ndb.StringProperty(                 indexed=False)
    char_emotion = ndb.StringProperty(                 indexed=False)
    
    @classmethod
    def query_all(cls, thread_id, first = 1):
        first_key = ndb.Key('Res', thread_id * c.TT + first)
        last_key = ndb.Key('Res', thread_id * c.TT + c.K)
        return cls.query(first_key <= cls._key).filter(cls._key <= last_key)
    
    @classmethod
    def latest_num_of(cls, thread_id):
        first_id = thread_id * c.TT
        first_key = ndb.Key('Res', first_id)
        last_key = ndb.Key('Res', first_id + c.K)
        keys = cls.query(first_key <= cls._key).filter(cls._key <= last_key).fetch(conf.MAX_FETCH, keys_only=True)
        if not keys:
            return first_id
        id = keys[-1].id()
        return first_id if id < first_id else id
