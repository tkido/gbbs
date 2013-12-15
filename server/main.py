#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import datetime
import logging
import time
import webapp2

from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import ndb

import conf
import c
import deco
import ex
import m
import te
import util

class TopPageHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.cache(3)
    def get(self, context):
        boards = m.Board.query_normal().fetch(conf.MAX_FETCH)
        context.update({
            'page_title' : 'トップページ',
            'boards': boards,
        })
        return te.render(':default/index', context, layout=':default/base')

class IndexHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    @deco.cache(5)
    def get(self, context):
        query = m.Thread.query_normal()
        threads = query.fetch(conf.MAX_FETCH)
        context.update({
            'page_title' : '',
            'threads': threads,
        })
        return te.render(':index', context)

class ThreadHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    @deco.cache()
    def get(self, context, thread_id, first, hyphen, last):
        board = context['board']
        
        thread_id = int(thread_id)
        thread_key = ndb.Key('Thread', thread_id)
        thread = thread_key.get()
        if not thread or not thread.readable(): raise ex.ThreadNotFound()
        
        if first:
            first = int(first)
            if 0 < first <= board.max[c.RESES]:
                fetch_count = 1
            else:
                raise ex.ThreadArgument('/%d/' % thread_id)
        else:
            first = 1
            fetch_count = board.max[c.RESES]
        if hyphen:
            fetch_count = board.max[c.RESES] - first + 1
            if last:
                last = int(last)
                if first <= last <= board.max[c.RESES]:
                    fetch_count = last - first + 1
            else:
                raise ex.ThreadArgument('/%d/' % thread_id)
        query = m.Res.query_normal(thread_id, first)
        reses = query.fetch(fetch_count) if fetch_count else []
        
        last_number = reses[-1].key.id() % c.TT if reses else 0
        thread.writable = (thread.status == c.NORMAL and last_number < board.max[c.RESES])
        
        context.update({
            'page_title': thread.title,
            'thread_id': thread_id,
            'thread': thread,
            'reses': reses,
        })
        
        now = board.now()
        if ((now - thread.resed) > datetime.timedelta(seconds = 10) and thread.res_count < last_number):
            thread.resed = now
            thread.res_count = last_number
            thread.put()
        
        html = te.render(':thread', context)
        
        flag = False
        if thread.next_id == 0 and last_number >= board.max[c.RESES]:
            thread.prepare_next()
            flag = True
        if thread.next_id > 0 and thread.next_title == '':
            thread.create_next(board)
            flag = True
        if thread.status == c.NORMAL and thread.next_title != '':
            thread.store()
            flag = True
        if flag: raise ex.RedirectOrg
        
        return html

class LinkHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    @deco.cache()
    def get(self, context):
        href = self.request.get('to')
        context.update({
            'page_title' : '外部ページへのリンク',
            'href': href,
        })
        return te.render(':link', context)

class StoredHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    @deco.cache()
    def get(self, context, year, month):
        board = context['board']
        if ((not year) and (not month)):
            update_to = board.now()
            update_from = update_to - datetime.timedelta(days = 31)
            page_title = '最近一ヶ月'
        else:
            year = int(year)
            if not month:
                update_from = datetime.datetime(year, 1, 1)
                update_to = datetime.datetime(year+1, 1, 1)
                page_title = '%d年' % year
            else:
                month = int(month)
                update_from = datetime.datetime(year, month, 1)
                update_to = datetime.datetime(year+1, 1, 1) if month == 12 else datetime.datetime(year, month+1, 1)
                page_title = '%d年%d月' % (year, month)
        threads = m.Thread.query_stored(update_from, update_to).fetch(conf.MAX_FETCH)
        context.update({
            'page_title' : '%sの過去ログ' % page_title,
            'threads': threads,
        })
        return te.render(':stored', context)

class WriteHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    def get(self, context, thread_id):
        raise ex.PostMethodRequired('スレッドに戻る', '/%s/' % thread_id)
        
    @deco.catch()
    @deco.board()
    @deco.myuser(c.WRITER)
    def post(self, context, thread_id):
        board = context['board']
        content = board.validate_content(self.request.get('content'))
        
        thread_id = int(thread_id)
        thread_key = ndb.Key('Thread', thread_id)
        thread = thread_key.get()
        
        now = board.now()
        dt_str = util.dt_to_str(now)
        myuser = context['user']
        hashed_id = board.hash(myuser.myuser_id)
        
        char_name = self.request.get('char_name') or '名無しの村人さん'
        char_id = self.request.get('character') or 'none'
        char_emotion = self.request.get('emotion') or 'normal'
        
        new_id = m.Res.latest_num_of(thread_id) + 1
        new_number = new_id % c.TT
        if new_number > board.max[c.RESES]: raise ex.ThreadNotWritable()
        
        res = m.Res(id = new_id,
                    author_id = myuser.myuser_id,
                    updater_id = myuser.myuser_id,
                    
                    status = c.NORMAL,
                    updated = now,
                    since = now,
                    
                    number = new_number,
                    dt_str = dt_str,
                    hashed_id = hashed_id,
                    content = content,
                    
                    char_name = char_name,
                    char_id = char_id,
                    char_emotion = char_emotion,
                   )
        @ndb.transactional()
        def write_unique():
            if m.Res.get_by_id(new_id):
                raise ex.SameId()
            else:
                return res.put()
        while True:
            try:
                if write_unique(): break
            except ex.SameId:
                new_id += 1
                new_number = new_id % c.TT
                if new_number > board.max[c.RESES]: raise ex.ThreadNotWritable()
                res.key = ndb.Key('Res', new_id)
                res.number = new_number
        util.flush_page('/%d/' % thread_id)
        if conf.LOCAL_SDK: time.sleep(0.5)
        raise ex.Redirect('/%d/#%d' % (thread_id, new_number))

class RelatedThreadHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    @deco.cache()
    def get(self, context, thread_id):
        thread_id = int(thread_id)
        thread = ndb.Key('Thread', thread_id).get()
        if not thread or not thread.readable(): raise ex.ThreadNotFound()
        threads = m.Thread.query_template(thread.template_id).fetch()
        context.update({
            'page_title': '関連スレ一覧',
            'thread': thread,
            'threads': threads,
        })
        return te.render(':related', context)

class EditTemplateHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    @deco.myuser(c.WRITER)
    def get(self, context, thread_id):
        thread_id = int(thread_id)
        thread = ndb.Key('Thread', thread_id).get()
        if not thread or not thread.readable(): raise ex.ThreadNotFound()
        if thread.status != c.NORMAL: raise ex.TemplateNotWritable()
        template = ndb.Key('Template', thread.template_id).get()
        if not template: raise ex.TemplateNotFound()
        context.update({
            'page_title': 'テンプレート編集',
            'thread': thread,
            'template': template,
        })
        return te.render(':edit', context)

class UpdateTemplateHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    def get(self, context, thread_id):
        raise ex.PostMethodRequired('スレッドに戻る', '/%s/' % thread_id)
    
    @deco.catch()
    @deco.board()
    @deco.myuser(c.WRITER)
    def post(self, context, thread_id):
        thread_id = int(thread_id)
        thread = ndb.Key('Thread', thread_id).get()
        if not thread or not thread.readable(): raise ex.ThreadNotFound()
        if thread.status != c.NORMAL: raise ex.TemplateNotWritable()
        template_key = ndb.Key('Template', thread.template_id)
        template = template_key.get()
        if not template: raise ex.TemplateNotFound()
        
        board = context['board']
        title = board.validate_title(self.request.get('title'))
        content = board.validate_template(self.request.get('content'))
        
        myuser = context['user']
        @ndb.transactional()
        def update_template():
            template = template_key.get()
            template.title = title
            template.content = content
            template.updated = board.now()
            template.updater_id = myuser.myuser_id
            template.put()
        if not update_template(): raise ex.TemplateNotWritable()
        raise ex.Redirect('/edit/%d/' % thread_id)

class LoginHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    def get(self, context):
        board = context['board']
        user = users.get_current_user()
        if not user: raise ex.RedirectLogin()
        myuser = m.MyUser.get_by_id(user.user_id())
        if myuser:
            if (myuser.status == c.READER) or (myuser.status == c.DELETED):
                raise ex.RedirectAgreement()
            else:
                raise ex.RedirectContinue()
        myuser_id = m.Counter.incr('MyUser')
        if not myuser_id: raise ex.NewUserIdCouldNotGet()
        now = board.now()
        myuser = m.MyUser(id = user.user_id(),
                          user = user,
                          myuser_id = myuser_id,
                          ban_count = 0,
                          
                          status = c.READER,
                          updated = now,
                          since = now,
                         )
        if not myuser.put(): raise ex.NewUserCouldNotPut()
        raise ex.RedirectAgreement()

class AgreementHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    def get(self, context):
        ns = context['ns']
        user = users.get_current_user()
        login_url = '/%s/_agree' % ns
        if self.request.get('continue'):
            login_url += '?continue=%s' % self.request.get('continue')
        context.update({
            'page_title': '利用規約',
            'user': user,
            'login_url': login_url,
            'logout_url': users.create_logout_url('/%s/' % ns),
        })
        return te.render(':agreement', context)

class AgreeHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    @deco.myuser(c.DELETED)
    def get(self, context):
        myuser = context['user']
        if (myuser.status == c.READER) or (myuser.status == c.DELETED):
            myuser_key = myuser.key
            @ndb.transactional()
            def rise_to_writer():
                myuser = myuser_key.get()
                myuser.status = c.WRITER
                myuser.flush()
                return myuser.put()
            if not rise_to_writer(): raise ex.UserCouldNotUpdate()
        raise ex.RedirectContinue()

class MyPageHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    @deco.myuser(c.BANNED)
    def get(self, context):
        context.update({
            'page_title' : 'ユーザー情報',
            'status_str' : c.AUTHORITIES[context['user'].status],
        })
        return te.render(':mypage', context)

class NewThreadHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    @deco.myuser(c.WRITER)
    def get(self, context):
        context.update({'page_title' : '新しいスレッドの作成'})
        return te.render(':new', context)
        
class CreateNewThreadHandler(webapp2.RequestHandler):
    @deco.catch()
    @deco.board()
    def get(self, context):
        raise ex.PostMethodRequired('新スレッド作成画面へ戻る', '/new/')
    
    @deco.catch()
    @deco.board()
    @deco.myuser(c.WRITER)
    def post(self, context):
        board = context['board']
        title = board.validate_title(self.request.get('title'))
        content = board.validate_template(self.request.get('content'))
        
        template_id = m.Counter.incr('Template')
        if not template_id: raise ex.NewTemplateIdCouldNotGet()
        
        myuser = context['user']
        now = board.now()
        template = m.Template(id = template_id,
                              author_id = myuser.myuser_id,
                              updater_id = myuser.myuser_id,
                              
                              status = c.NORMAL,
                              updated = now,
                              since = now,
                              
                              title = title,
                              content = content,
                              keeped_title = title,
                              keeped_content = content,
                             )
        template_key = template.put()
        if not template_key: raise ex.NewTemplateCouldNotCreate()
        
        thread_id = m.Counter.incr('Thread')
        if not thread_id: raise ex.NewThreadIdCouldNotGet()
        thread = m.Thread(id = thread_id,
                          template_id = template_id,
                          author_id = myuser.myuser_id,
                          updater_id = myuser.myuser_id,
                          
                          status = c.NORMAL,
                          updated = now,
                          since = now,
                          
                          title = title % 1,
                          dt_str = util.dt_to_str(now),
                          hashed_id = board.hash(myuser.myuser_id),
                          content = content,
                          
                          number = 1,
                          res_count = 0,
                          resed = now,
                          
                          prev_id = 0,
                          prev_title = '',
                          next_id = 0,
                          next_title = '',
                         )
        thread_key = thread.put()
        if not thread_key: raise ex.NewThreadCouldNotCreate()
        if conf.LOCAL_SDK: time.sleep(0.5)
        m.Thread.clean(board)
        raise ex.Redirect('/%d/' % thread_id)

app = webapp2.WSGIApplication([('/', TopPageHandler),
                               (r'/([0-9a-z_-]{2,16})/', IndexHandler),
                               (r'/([0-9a-z_-]{2,16})/(\d+)/(\d*)(-?)(\d*)', ThreadHandler),
                               (r'/([0-9a-z_-]{2,16})/link', LinkHandler),
                               (r'/([0-9a-z_-]{2,16})/related/(\d+)/', RelatedThreadHandler),
                               (r'/([0-9a-z_-]{2,16})/stored/(\d{4})?/?(\d{1,2})?/?', StoredHandler),
                               (r'/([0-9a-z_-]{2,16})/_login', LoginHandler),
                               (r'/([0-9a-z_-]{2,16})/_write/(\d+)', WriteHandler),
                               (r'/([0-9a-z_-]{2,16})/mypage/', MyPageHandler),
                               (r'/([0-9a-z_-]{2,16})/agreement/', AgreementHandler),
                               (r'/([0-9a-z_-]{2,16})/_agree', AgreeHandler),
                               (r'/([0-9a-z_-]{2,16})/edit/(\d+)/', EditTemplateHandler),
                               (r'/([0-9a-z_-]{2,16})/_edit/(\d+)', UpdateTemplateHandler),
                               (r'/([0-9a-z_-]{2,16})/new/', NewThreadHandler),
                               (r'/([0-9a-z_-]{2,16})/_new', CreateNewThreadHandler),
                              ],
                              debug=True
                             )