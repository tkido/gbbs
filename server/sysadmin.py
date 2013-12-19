#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import os
import uuid

from google.appengine.api import memcache
from google.appengine.api import namespace_manager
from google.appengine.api import users
from google.appengine.ext import ndb
import webapp2

import conf
import c
import ex
import m
import te
import util

class IndexHandler(webapp2.RequestHandler):
    def get(self):
        namespace_manager.set_namespace(c.BOARD_NAMESPACE)
        user = users.get_current_user()
        myuser = m.MyUser.get_by_id(user.user_id())
        myuser_counter = m.Counter.get_by_id('MyUser')
        board_counter = m.Counter.get_by_id('Board')
        
        context = {
            'page_title' : 'システム管理者専用ページ',
            'ns' : c.BOARD_NAMESPACE,
            'user' : myuser,
            
            'total_user': myuser_counter.count,
            'total_board': board_counter.count,
        }
        html = te.render(':sysadmin/index', context, layout=':sysadmin/base')
        self.response.out.write(html)

class EnvironmentHandler(webapp2.RequestHandler):
    def get(self):
        for name in os.environ.keys():
            self.response.out.write("%s = %s<br>\n" % (name, os.environ[name]))

class MemcacheHandler(webapp2.RequestHandler):
    def get(self, ns):
        namespace_manager.set_namespace(ns)
        dic = memcache.get_stats()
        for name in dic.keys():
            self.response.out.write("%s = %s<br>\n" % (name, dic[name]))

class CreateBoardHandler(webapp2.RequestHandler):
    def post(self):
        namespace_manager.set_namespace(c.BOARD_NAMESPACE)
        user = users.get_current_user()
        myuser = m.MyUser.get_by_id(user.user_id())
        if not myuser:
            return
        ns = self.request.get('bbs_id')
        board = m.Board.get_by_id(ns)
        if board:
            raise ex.SameId()
        m.Counter.incr('Board')
        
        now = util.now()
        board = m.Board(id = ns,
                        author_id = myuser.myuser_id,
                        updater_id = myuser.myuser_id,
                        
                        status = c.NORMAL,
                        updated = now,
                        since = now,
                        
                        title = '%s BBS' % ns,
                        description = '',
                        keywords = '',
                        template = '',
                        
                        hash_cycle = 3, #0:ever(no change) 1:year 2:month 3:day
                        salt = str(uuid.uuid4()),
                        timezone = 9,
                        
                        allow_index = True,
                        allow_robots = True,
                        allow_anonymous = True,
                        
                        max = [3, 3, 4096, 32, 8192, 80, 160],
                        ad = []
                       )
        namespace_manager.set_namespace(ns)
        myuser_counter = m.Counter(id = 'MyUser', count = 0)
        template_counter = m.Counter(id = 'Template', count = 0)
        thread_counter = m.Counter(id = 'Thread', count = 0)
        ndb.put_multi([board, myuser_counter, thread_counter, template_counter])
        
        self.redirect('/s/')

class InitHandler(webapp2.RequestHandler):
    def get(self):
        namespace_manager.set_namespace(c.BOARD_NAMESPACE)
        user = users.get_current_user()
        myuser = m.MyUser.get_by_id(user.user_id())
        context = {
            'page_title' : '管理者ユーザとカウンタの作成',
            'ns' : c.BOARD_NAMESPACE,
            'user' : myuser,
        }
        html = te.render(':sysadmin/init', context, layout=':sysadmin/base')
        self.response.out.write(html)
        
class InitializeHandler(webapp2.RequestHandler):
    def post(self):
        namespace_manager.set_namespace(c.BOARD_NAMESPACE)
        user = users.get_current_user()
        myuser = m.MyUser.get_by_id(user.user_id())
        myuser_counter = m.Counter.get_by_id('MyUser')
        board_counter = m.Counter.get_by_id('Board')
        if myuser:
            self.redirect('/s/'); return;
        if myuser_counter:
            self.redirect('/s/'); return;
        if board_counter:
            self.redirect('/s/'); return;
        now = util.now()
        myuser = m.MyUser(id = user.user_id(),
                          user = user,
                          myuser_id = 1,
                          ban_count = 0,
                          
                          status = c.SYSTEM_ADMIN,
                          updated = now,
                          since = now,
                         )
        
        myuser_counter = m.Counter(id = 'MyUser', count = 1)
        board_counter = m.Counter(id = 'Board', count = 0)
        
        ndb.put_multi([myuser, myuser_counter, board_counter])
        self.redirect('/s/')

app = webapp2.WSGIApplication([('/s/', IndexHandler),
                               ('/s/env', EnvironmentHandler),
                               (r'/s/memcache/([0-9a-z_-]{2,16})', MemcacheHandler),
                               (r'/s/_create/', CreateBoardHandler),
                               ('/s/init/', InitHandler),
                               ('/s/_init/', InitializeHandler),
                              ],
                              debug=conf.DEBUG
                             )