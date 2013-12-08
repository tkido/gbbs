#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import os
import uuid

from google.appengine.api import memcache
from google.appengine.api import namespace_manager
from google.appengine.api import users
from google.appengine.ext import ndb
import webapp2

import config
import const
import model
import tengine
import util

def initialize(org):
    namespace_manager.set_namespace(const.BOARD_NAMESPACE)
    user = users.get_current_user()
    myuser = model.MyUser.get_by_id(user.user_id())
    if myuser:
        org.redirect('/s/')
        return
    now = util.now()
    myuser = model.MyUser(id = user.user_id(),
                          user = user,
                          myuser_id = 1,
                          status = const.SYSTEM_ADMIN,
                          
                          ban_count = 0,
                          updated_at = now,
                          since = now )
    myuser_counter = model.Counter(id = 'MyUser', count = 1)
    board_counter = model.Counter(id = 'Board', count = 0)
    
    ndb.put_multi([myuser, myuser_counter, board_counter])
    org.redirect('/s/')

class IndexHandler(webapp2.RequestHandler):
    def get(self):
        namespace_manager.set_namespace(const.BOARD_NAMESPACE)
        user = users.get_current_user()
        myuser = model.MyUser.get_by_id(user.user_id())
        if not myuser:
            initialize(self)
            return
        myuser_counter = model.Counter.get_by_id('MyUser')
        board_counter = model.Counter.get_by_id('Board')
        
        context = {
            'page_title' : 'システム管理者専用ページ',
            'namespace' : const.BOARD_NAMESPACE,
            'user' : myuser,
            'login_url' : '/login?continue=' + self.request.uri,
            'logout_url' : users.create_logout_url(self.request.uri),
            
            'total_user': myuser_counter.count,
            'total_board': board_counter.count,
        }
        html = tengine.render(':sysadmin/index', context, layout=':sysadmin/base')
        self.response.out.write(html)

class EnvironmentHandler(webapp2.RequestHandler):
    def get(self):
        for name in os.environ.keys():
            self.response.out.write("%s = %s<br>\n" % (name, os.environ[name]))

class MemcacheHandler(webapp2.RequestHandler):
    def get(self, namespace):
        namespace_manager.set_namespace(namespace)
        dic = memcache.get_stats()
        for name in dic.keys():
            self.response.out.write("%s = %s<br>\n" % (name, dic[name]))

class CreateBoardHandler(webapp2.RequestHandler):
    def get(self, namespace):
        namespace_manager.set_namespace(const.BOARD_NAMESPACE)
        user = users.get_current_user()
        myuser = model.MyUser.get_by_id(user.user_id())
        if not myuser:
            return
        now = util.now()
        board = model.Board(id = namespace,
                            author_id = myuser.myuser_id,
                            updater_id = myuser.myuser_id,
                            
                            status = const.NORMAL,
                            updated_at = now,
                            since = now,
                            
                            title = '%s BBS' % namespace,
                            description = '',
                            keywords = '',
                            template = '',
                            
                            hash_cycle = 3, #0:ever(no change) 1:year 2:month 3:day
                            timezone = 9,
                            salt = str(uuid.uuid4()),
                            allow_index = True,
                            allow_robots = True,
                            
                            max_reses = 3,
                            max_threads = 3,
                            max_chars = 4096,
                            max_chars_title = 32,
                            max_chars_template = 4096 * 2,
                            max_rows = 80,
                            max_rows_template = 80,
                           )
        
        namespace_manager.set_namespace(namespace)
        myuser_counter = model.Counter(id = 'MyUser', count = 0)
        theme_counter = model.Counter(id = 'Theme', count = 0)
        thread_counter = model.Counter(id = 'Thread', count = 0)
        
        ndb.put_multi([myuser_counter, thread_counter, theme_counter, myuser, board])

app = webapp2.WSGIApplication([('/s/', IndexHandler),
                               ('/s/env', EnvironmentHandler),
                               (r'/s/memcache/([0-9a-z_-]{2,16})', MemcacheHandler),
                               (r'/s/create/board/([0-9a-z_-]{2,16})', CreateBoardHandler),
                               ],
                               debug=True
                              )