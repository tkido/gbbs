#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import datetime
import logging
import time
import webapp2

from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import ndb

import config
import const
import deco
import error
import model
import tengine
import util

def prepare_next_thread(thread_key, board):
    tc_key = ndb.Key('Counter', 'Thread')
    @ndb.transactional()
    def increment_tc():
        tc = tc_key.get()
        tc.count += 1
        tc.put()
        return tc.count
    next_thread_id = increment_tc()
    
    @ndb.transactional()
    def set_next_thread_id():
        thread = thread_key.get()
        if thread.next_thread_id == 0:
            thread.next_thread_id = next_thread_id
            thread.put()
            return thread
    return set_next_thread_id()
    
def create_next_thread(thread_key, board):
    thread = thread_key.get()
    now = board.now()
    datetime_str = util.datetime_to_str(now)
    myuser_id = 0
    hashed_id = board.hash(myuser_id)
    
    theme = ndb.Key('Theme', thread.theme_id).get()
    next_thread_number = thread.thread_number + 1
    new_title = theme.title_template % next_thread_number
    
    next_key = ndb.Key('Thread', thread.next_thread_id)
    @ndb.transactional()
    def get_or_insert():
        next_thread = next_key.get()
        if next_thread:
            return next_thread
        else:
            next_thread = model.Thread(id = thread.next_thread_id,
                                       theme_id = thread.theme_id,
                                       author_id = myuser_id,
                                       updater_id = myuser_id,

                                       status = const.NORMAL,
                                       updated_at = now,
                                       since = now,

                                       title = new_title,
                                       datetime_str = datetime_str,
                                       hashed_id = hashed_id,
                                       content = theme.template,

                                       thread_number = next_thread_number,
                                       response_count = 0,
                                       responsed_at = now,

                                       prev_thread_id = thread.key.id(),
                                       prev_thread_title = thread.title,
                                       next_thread_id = 0,
                                       next_thread_title = '',
                                      )
            if next_thread.put():
                return next_thread
            else:
                return None

    next_thread = get_or_insert()
    if next_thread:
        util.flush_page('/related/%d/' % thread.theme_id)
        @ndb.transactional()
        def set_next_thread_title():
            thread = thread_key.get()
            if thread.next_thread_title == '':
                thread.next_thread_title = next_thread.title
                if thread.put():
                    return thread
                else:
                    return None
        return set_next_thread_title()
    else:
        return None

def store(thread_key):
    @ndb.transactional()
    def store_thread():
        thread = thread_key.get()
        thread.status = const.STORED
        thread.put()
    store_thread()

def clean_old_threads(board):
    query = model.Thread.query_normal()
    keys = query.fetch(board.max_threads+3, keys_only=True)
    needs = len(keys) - board.max_threads
    for i in range(needs):
        store(keys[-i-1])

class IndexHandler(webapp2.RequestHandler):
    @deco.board()
    @deco.cache(5)
    def get(self, context):
        query = model.Thread.query_normal()
        threads = query.fetch(config.MAX_FETCH)
        context.update({
            'page_title' : '',
            'threads': threads,
        })
        html = tengine.render(':index', context)
        self.response.out.write(html)
        return html

class ThreadHandler(webapp2.RequestHandler):
    @deco.board()
    @deco.cache()
    def get(self, context, thread_id, first, hyphen, last):
        board = context['board']
        
        thread_id = int(thread_id)
        thread_key = ndb.Key('Thread', thread_id)
        thread = thread_key.get()
        if not thread or not thread.readable():
            error.page(self, context, error.ThreadNotFound()); return;
        
        if first:
            first = int(first)
            if 0 < first <= board.max_reses:
                fetch_count = 1
            else:
                error.page(self, context, error.ThreadArgument('/%d/' % thread_id)); return;
        else:
            first = 1
            fetch_count = board.max_reses
        if hyphen:
            fetch_count = board.max_reses - first + 1
            if last:
                last = int(last)
                if first <= last <= board.max_reses:
                    fetch_count = last - first + 1
            else:
                error.page(self, context, error.ThreadArgument('/%d/' % thread_id)); return;
        query = model.Response.query_normal(thread_id, first)
        reses = query.fetch(fetch_count) if fetch_count else []
        
        last_number = reses[-1].key.id() % const.TT if reses else 0
        thread.writable = (thread.status == const.NORMAL and last_number < board.max_reses)
        
        context.update({
            'page_title': thread.title,
            'thread_id': thread_id,
            'thread': thread,
            'reses': reses,
        })
        
        now = board.now()
        if ((now - thread.responsed_at) > datetime.timedelta(seconds = 10) and thread.response_count < last_number):
            thread.responsed_at = now
            thread.response_count = last_number
            thread.put()
        
        html = tengine.render(':thread', context)
        self.response.out.write(html)
        
        if thread.next_thread_id == 0 and last_number >= board.max_reses:
            thread = prepare_next_thread(thread_key, board)
            html = None
        if thread.next_thread_id > 0 and thread.next_thread_title == '':
            thread = create_next_thread(thread_key, board)
            html = None
        if thread.status == const.NORMAL and thread.next_thread_title != '':
            thread = store(thread_key)
            html = None
        return html

class LinkHandler(webapp2.RequestHandler):
    @deco.board()
    @deco.cache()
    def get(self, context):
        href = self.request.get('to')
        context.update({
            'page_title' : '外部ページへのリンク',
            'href': href,
        })
        html = tengine.render(':link', context)
        self.response.out.write(html)
        return html

class WriteHandler(webapp2.RequestHandler):
    @deco.board()
    def get(self, context, thread_id):
        error.page(self, context, error.PostMethodRequired('スレッドに戻る', '/%s/' % thread_id)); return;
        
    @deco.board()
    @deco.myuser(const.WRITER)
    def post(self, context, thread_id):
        board = context['board']
        content = board.validate_content(self.request.get('content'))
        if not content:
            error.page(self, context, error.ContentValidation(board)); return;
        
        thread_id = int(thread_id)
        thread_key = ndb.Key('Thread', thread_id)
        thread = thread_key.get()
        
        now = board.now()
        datetime_str = util.datetime_to_str(now)
        myuser = context['user']
        hashed_id = board.hash(myuser.myuser_id)
        
        char_name = self.request.get('char_name') or '名無しの村人さん'
        char_id = self.request.get('character') or 'none'
        char_emotion = self.request.get('emotion') or 'normal'
        
        new_id = model.Response.latest_num_of(thread_id) + 1
        new_number = new_id % const.TT
        response = model.Response(id = new_id,
                                  author_id = myuser.myuser_id,
                                  updater_id = myuser.myuser_id,
                                  
                                  status = const.NORMAL,
                                  updated_at = now,
                                  since = now,
                                  
                                  number = new_number,
                                  datetime_str = datetime_str,
                                  hashed_id = hashed_id,
                                  content = content,
                                  
                                  char_name = char_name,
                                  char_id = char_id,
                                  char_emotion = char_emotion,
                                 )
        @ndb.transactional()
        def write_unique():
            other = model.Response.get_by_id(new_id)
            if other:
                raise error.SameId()
            else:
                return response.put()
        while True:
            try:
                if write_unique():
                    break
            except error.SameId, err:
                new_id += 1
                new_number = new_id % const.TT
                if new_number > const.K:
                    error.page(self, context, error.ThreadNotWritable()); return;
                response.key = ndb.Key('Response', new_id)
                response.number = new_number
        util.flush_page('/%d/' % thread_id)
        if config.LOCAL_SDK:
            time.sleep(0.5)
        self.redirect(util.namespaced('/%d/#%d' % (thread_id, new_number)))

class RelatedThreadHandler(webapp2.RequestHandler):
    @deco.board()
    @deco.cache()
    def get(self, context, thread_id):
        thread_id = int(thread_id)
        thread = ndb.Key('Thread', thread_id).get()
        if not thread or not thread.readable():
            error.page(self, context, error.ThreadNotFound()); return;
        threads = model.Thread.query_theme(thread.theme_id).fetch()
        context.update({
            'page_title': '関連スレ一覧',
            'thread': thread,
            'threads': threads,
        })
        html = tengine.render(':related', context)
        self.response.out.write(html)
        return html

class EditTemplateHandler(webapp2.RequestHandler):
    @deco.board()
    @deco.myuser(const.WRITER)
    def get(self, context, thread_id):
        thread_id = int(thread_id)
        thread = ndb.Key('Thread', thread_id).get()
        if not thread or not thread.readable():
            error.page(self, context, error.ThreadNotFound()); return;
        if thread.status != const.NORMAL:
            error.page(self, context, error.ThemeNotWritable()); return;
        theme = ndb.Key('Theme', thread.theme_id).get()
        if not theme:
            error.page(self, context, error.ThemeNotFound()); return;
        context.update({
            'page_title': 'テンプレート編集',
            'thread': thread,
            'theme': theme,
        })
        self.response.out.write(tengine.render(':edit', context))

class UpdateTemplateHandler(webapp2.RequestHandler):
    @deco.board()
    def get(self, context, thread_id):
        error.page(self, context, error.PostMethodRequired('スレッドに戻る', '/%s/' % thread_id)); return;
    
    @deco.board()
    @deco.myuser(const.WRITER)
    def post(self, context, thread_id):
        thread_id = int(thread_id)
        thread = ndb.Key('Thread', thread_id).get()
        if not thread or not thread.readable():
            error.page(self, context, error.ThreadNotFound()); return;
        if thread.status != const.NORMAL:
            error.page(self, context, error.ThemeNotWritable()); return;
        theme_key = ndb.Key('Theme', thread.theme_id)
        theme = theme_key.get()
        if not theme:
            error.page(self, context, error.ThemeNotFound()); return;
        
        board = context['board']
        title_template = board.validate_title(self.request.get('title_template'))
        if not title_template:
            error.page(self, context, error.TitleValidation(board)); return;
        template = board.validate_template(self.request.get('template'))
        if not template:
            error.page(self, context, error.ContentValidation(board)); return;
        
        myuser = context['user']
        @ndb.transactional()
        def update_template():
            theme = theme_key.get()
            theme.title_template = title_template
            theme.template = template
            theme.updated_at = board.now()
            theme.updater_id = myuser.myuser_id
            theme.put()
        try:
            update_template()
        except error.ThemeNotWritable, err:
            error.page(self, context, err); return;
        else:
            self.redirect(util.namespaced('/edit/%d/' % thread_id))

class LoginHandler(webapp2.RequestHandler):
    @deco.board()
    def get(self, context):
        namespace = context['namespace']
        board = context['board']
        user = users.get_current_user()
        if not user:
            self.redirect(str(users.create_login_url(self.request.uri)))
            return
        myuser = model.MyUser.get_by_id(user.user_id())
        if myuser:
            if (myuser.status == const.READER) or (myuser.status == const.DELETED):
                redirect_to = '/%s/agreement/' % namespace
                if self.request.get('continue'):
                    redirect_to += '?continue=%s' % self.request.get('continue')
                self.redirect(str(redirect_to)); return;
            else:
                redirect_to = self.request.get('continue') or '/%s/' % namespace
                self.redirect(str(redirect_to)); return;
        uc_key = ndb.Key('Counter', 'MyUser')
        @ndb.transactional()
        def increment_uc():
            uc = uc_key.get()
            uc.count += 1
            uc.put()
            return uc.count
        myuser_id = increment_uc()
        if not myuser_id:
            error.page(self, context, error.NewUserIdCouldNotGet()); return;
        now = board.now()
        myuser = model.MyUser(id = user.user_id(),
                              user = user,
                              myuser_id = myuser_id,
                              ban_count = 0,
                              
                              status = const.READER,
                              updated_at = now,
                              since = now,
                             )
        if not myuser.put():
            error.page(self, context, error.NewUserCouldNotPut()); return;
        redirect_to = '/%s/agreement/' % namespace
        if self.request.get('continue'):
            redirect_to += '?continue=%s' % self.request.get('continue')
        self.redirect(str(redirect_to))

class AgreeHandler(webapp2.RequestHandler):
    @deco.board()
    @deco.myuser(const.DELETED)
    def get(self, context):
        namespace = context['namespace']
        myuser = context['user']
        if (myuser.status == const.READER) or (myuser.status == const.DELETED):
            myuser_key = myuser.key
            @ndb.transactional()
            def rise_to_writer():
                myuser = myuser_key.get()
                myuser.status = const.WRITER
                myuser.flush()
                return myuser.put()
            if not rise_to_writer():
                error.page(self, context, error.UserCouldNotUpdate()); return;
        redirect_to = self.request.get('continue') or '/%s/' % namespace
        self.redirect(str(redirect_to))

class AgreementHandler(webapp2.RequestHandler):
    @deco.board()
    def get(self, context):
        namespace = context['namespace']
        user = users.get_current_user()
        if self.request.get('continue'):
            login_url = '/%s/_agree?continue=%s' % (namespace, self.request.get('continue'))
        else:
            login_url = '/%s/_agree' % namespace
        context.update({
            'page_title': '利用規約',
            'user': user,
            'login_url': login_url,
            'logout_url': users.create_logout_url('/%s/' % namespace),
        })
        self.response.out.write(tengine.render(':agreement', context))
        

class StoredHandler(webapp2.RequestHandler):
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
        threads = model.Thread.query_stored(update_from, update_to).fetch(config.MAX_FETCH)
        context.update({
            'page_title' : '%sの過去ログ' % page_title,
            'threads': threads,
        })
        html = tengine.render(':stored', context)
        self.response.out.write(html)
        return html
        
class MyPageHandler(webapp2.RequestHandler):
    @deco.board()
    @deco.myuser(const.BANNED)
    def get(self, context):
        context.update({
            'page_title' : 'ユーザー情報',
            'status_str' : const.AUTHORITIES[context['user'].status],
        })
        self.response.out.write(tengine.render(':mypage', context))

class NewThreadHandler(webapp2.RequestHandler):
    @deco.board()
    @deco.myuser(const.WRITER)
    def get(self, context):
        context.update({'page_title' : '新しいスレッドの作成'})
        self.response.out.write(tengine.render(':new', context))
        
class CreateNewThreadHandler(webapp2.RequestHandler):
    @deco.board()
    def get(self, context):
        error.page(self, context, error.PostMethodRequired('新スレッド作成画面へ戻る', '/new/')); return;
    
    @deco.board()
    @deco.myuser(const.WRITER)
    def post(self, context):
        board = context['board']
        title_template = board.validate_title(self.request.get('title_template'))
        if not title_template:
            error.page(self, context, error.TitleValidation(board)); return;
        template = board.validate_template(self.request.get('template'))
        if not template:
            error.page(self, context, error.ContentValidation(board)); return;
        
        @ndb.transactional()
        def increment_tc():
            tc = tc_key.get()
            tc.count += 1
            tc.put()
            return tc.count
        tc_key = ndb.Key('Counter', 'Theme')
        theme_id = increment_tc()
        if not theme_id:
            error.page(self, context, error.NewThemeIdCouldNotGet()); return;
        
        myuser = context['user']
        now = board.now()
        theme = model.Theme(id = theme_id,
                            author_id = myuser.myuser_id,
                            updater_id = myuser.myuser_id,
                            
                            status = const.NORMAL,
                            updated_at = now,
                            since = now,
                            
                            title_template = title_template,
                            template = template,
                            keeped_title_template = title_template,
                            keeped_template = template,
                           )
        theme_key = theme.put()
        if not theme_key:
            error.page(self, context, error.NewThemeCouldNotCreate()); return;
        
        tc_key = ndb.Key('Counter', 'Thread')
        thread_id = increment_tc()
        if not thread_id:
            error.page(self, context, error.NewThreadIdCouldNotGet()); return;
        thread = model.Thread(id = thread_id,
                              theme_id = theme_id,
                              author_id = myuser.myuser_id,
                              updater_id = myuser.myuser_id,
                              
                              status = const.NORMAL,
                              updated_at = now,
                              since = now,
                              
                              title = title_template % 1,
                              datetime_str = util.datetime_to_str(now),
                              hashed_id = board.hash(myuser.myuser_id),
                              content = template,
                              
                              thread_number = 1,
                              response_count = 0,
                              responsed_at = now,
                              
                              prev_thread_id = 0,
                              prev_thread_title = '',
                              next_thread_id = 0,
                              next_thread_title = '',
                             )
        thread_key = thread.put()
        if not thread_key:
            error.page(self, context, error.NewThreadCouldNotCreate()); return;
        
        self.redirect(util.namespaced('/%d/' % thread_id))
        
        if config.LOCAL_SDK:
            time.sleep(0.5)
        clean_old_threads(board)

app = webapp2.WSGIApplication([(r'/([0-9a-z_-]{2,16})/', IndexHandler),
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