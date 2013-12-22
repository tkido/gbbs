#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import datetime
import logging
import time
import webapp2
from webapp2_extras import routes

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
    @deco.default()
    @deco.cache(3)
    def get(self, context):
        boards = m.Board.query_normal().fetch(conf.MAX_FETCH)
        context.update({
            'page_title' : 'トップページ',
            'boards': boards,
        })
        return te.render(':default/index', context, layout=':default/base')

class IndexHandler(webapp2.RequestHandler):
    @deco.default()
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
    @deco.default()
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
        query = m.Res.query_all(thread_id, first)
        reses = query.fetch(fetch_count) if fetch_count else []
        
        last_number = reses[-1].key.id() % c.TT if reses else 0
        thread._writable = (thread.status == c.NORMAL and last_number < board.max[c.RESES])
        
        context.update({
            'page_title': thread.title,
            'thread_id': thread_id,
            'thread': thread,
            'reses': reses,
            'NORMAL': c.NORMAL,
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
    @deco.default()
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
    @deco.default()
    @deco.board()
    @deco.cache()
    def get(self, context, year, slash, month, slash2):
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
        #threads = m.Thread.query_stored(update_from, update_to).fetch(conf.MAX_FETCH)
        threads = m.Thread.query_stored().fetch(conf.MAX_FETCH)
        context.update({
            'page_title' : '過去ログ',
            'threads': threads,
        })
        return te.render(':stored', context)

class WriteHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    def get(self, context, thread_id):
        raise ex.PostMethodRequired('スレッドに戻る', '/%s/' % thread_id)
        
    @deco.default()
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
        
        handle = self.request.get('handle') or self.request.get('char-name') or '名無しさん'
        char_id = self.request.get('character') or 'none'
        emotion = self.request.get('emotion') or 'normal'
        trip = '' #placeholder
        
        new_id = m.Res.latest_num_of(thread_id) + 1
        new_number = new_id % c.TT
        if new_number > board.max[c.RESES]: raise ex.ThreadNotWritable()
        
        res = m.Res(
            id = new_id,
            author_id = myuser.myuser_id,
            updater_id = myuser.myuser_id,
            author_auth = myuser.status,
            remote_host = self.request.remote_addr,

            status = c.NORMAL,
            updated = now,
            since = now,

            number = new_number,
            dt_str = dt_str,
            hashed_id = hashed_id,
            content = content,

            handle = handle,
            char_id = char_id,
            emotion = emotion,
            trip = trip,
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
            except Exception as err:
                raise err
        util.flush_page('/%d/' % thread_id)
        if conf.LOCAL_SDK: time.sleep(0.5)
        raise ex.Redirect('/%d/#%d' % (thread_id, new_number))

class WriteAnonymousHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    def get(self, context, thread_id):
        raise ex.PostMethodRequired('スレッドに戻る', '/%s/' % thread_id)
        
    @deco.default()
    @deco.board()
    def post(self, context, thread_id):
        board = context['board']
        if not board.allow_anonymous:
            raise ex.ThreadNotWritable()
        
        content = board.validate_content(self.request.get('content'))
        
        thread_id = int(thread_id)
        thread_key = ndb.Key('Thread', thread_id)
        thread = thread_key.get()
        
        now = board.now()
        dt_str = util.dt_to_str(now)
        hashed_id = board.hash(self.request.remote_addr)
        
        handle = self.request.get('handle') or self.request.get('char-name') or '名無しさん'
        char_id = self.request.get('character') or 'none'
        emotion = self.request.get('emotion') or 'normal'
        trip = '' #placeholder
        
        new_id = m.Res.latest_num_of(thread_id) + 1
        new_number = new_id % c.TT
        if new_number > board.max[c.RESES]: raise ex.ThreadNotWritable()
        
        res = m.Res(
            id = new_id,
            author_id = 0,
            updater_id = 0,
            author_auth = 3,
            remote_host = self.request.remote_addr,

            status = c.NORMAL,
            updated = now,
            since = now,

            number = new_number,
            dt_str = dt_str,
            hashed_id = hashed_id,
            content = content,

            handle = handle,
            char_id = char_id,
            emotion = emotion,
            trip = trip,
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
            except Exception as err:
                raise err
        util.flush_page('/%d/' % thread_id)
        if conf.LOCAL_SDK: time.sleep(0.5)
        raise ex.Redirect('/%d/#%d' % (thread_id, new_number))

class RelatedThreadHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    @deco.cache()
    def get(self, context, thread_id):
        thread_id = int(thread_id)
        thread = ndb.Key('Thread', thread_id).get()
        if not thread or not thread.readable(): raise ex.ThreadNotFound()
        threads = m.Thread.query_related(thread.template_id).fetch()
        context.update({
            'page_title': '関連スレ一覧',
            'thread': thread,
            'threads': threads,
            'DELETED': c.DELETED,
        })
        return te.render(':related', context)

class TemplateHandler(webapp2.RequestHandler):
    @deco.default()
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
            'page_title': '次スレのテンプレート（予定）',
            'thread': thread,
            'thread_id': thread_id,
            'template': template,
            'MARGIN_VOTE': conf.MARGIN_VOTE,
        })
        return te.render(':template', context)

class EditTemplateHandler(webapp2.RequestHandler):
    @deco.default()
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
            'page_title': '次スレのテンプレート変更案を作成する',
            'thread': thread,
            'template': template,
        })
        return te.render(':edit', context)

class UpdateTemplateHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    def get(self, context, thread_id):
        raise ex.PostMethodRequired('スレッドに戻る', '/%s/' % thread_id)
    
    @deco.default()
    @deco.board()
    @deco.myuser(c.WRITER)
    def post(self, context, thread_id):
        thread_id = int(thread_id)
        thread = m.Thread.get_by_id(thread_id)
        if not thread or not thread.readable(): raise ex.ThreadNotFound()
        if thread.status != c.NORMAL: raise ex.TemplateNotWritable()
        template_key = ndb.Key('Template', thread.template_id)
        template = template_key.get()
        if not template: raise ex.TemplateNotFound()
        
        if template.changed():
            raise ex.TemplateNotWritable()
        
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
            template.agree.append(myuser.myuser_id)
            template.put()
        update_template()
        raise ex.Redirect('/template/%d/' % thread_id)

class VoteHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    def get(self, context, thread_id):
        raise ex.PostMethodRequired('スレッドに戻る', '/%s/' % thread_id)
    
    @deco.default()
    @deco.board()
    @deco.myuser(c.WRITER)
    def post(self, context, thread_id):
        thread_id = int(thread_id)
        thread = m.Thread.get_by_id(thread_id)
        if not thread or not thread.readable(): raise ex.ThreadNotFound()
        if thread.status != c.NORMAL: raise ex.TemplateNotWritable()
        template_key = ndb.Key('Template', thread.template_id)
        template = template_key.get()
        if not template: raise ex.TemplateNotFound()
        
        id = context['user'].myuser_id
        operation = self.request.get('operation')

        @ndb.transactional()
        def update_template():
            template = template_key.get()
            if operation == 'agree':
                if id in template.agree: raise ex.InvalidVote()
                template.agree.append(id)
                if id in template.deny:
                    template.deny.remove(id)
            elif operation == 'deny':
                if id in template.deny: raise ex.InvalidVote()
                template.deny.append(id)
                if id in template.agree:
                    template.agree.remove(id)
                if len(template.deny) - len(template.agree) >= conf.MARGIN_VOTE:
                    template.title = template.title_keeped
                    template.content = template.content_keeped
                    template.agree = []
                    template.deny = []
            else:
                raise ex.InvalidOperation()
            template.put()
        update_template()
        
        raise ex.Redirect('/template/%d/' % thread_id)


class LoginHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    def get(self, context):
        board = context['board']
        user = users.get_current_user()
        if not user: raise ex.RedirectLogin()
        myuser = m.MyUser.get_by_id(user.user_id())
        if myuser:
            if myuser.status == c.READER:
                raise ex.RedirectAgreement()
            else:
                raise ex.RedirectContinue()
        myuser_id = m.Counter.incr('MyUser')
        now = board.now()
        myuser = m.MyUser(
            id = user.user_id(),
            user = user,
            myuser_id = myuser_id,
            ban_count = 0,

            status = c.READER,
            updated = now,
            since = now,
            )
        myuser.put()
        raise ex.RedirectAgreement()

class AgreementHandler(webapp2.RequestHandler):
    @deco.default()
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
    @deco.default()
    @deco.board()
    @deco.myuser(c.DELETED)
    def get(self, context):
        myuser = context['user']
        if myuser.status == c.READER:
            myuser_key = myuser.key
            @ndb.transactional()
            def rise_to_writer():
                myuser = myuser_key.get()
                myuser.status = c.WRITER
                myuser.flush()
                myuser.put()
            rise_to_writer()
        raise ex.RedirectContinue()

class MyPageHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    @deco.myuser(c.BANNED)
    def get(self, context):
        context.update({
            'page_title' : 'ユーザー情報',
            'status_str' : c.AUTHORITIES[context['user'].status],
        })
        return te.render(':mypage', context)

class NewThreadHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    @deco.myuser(c.WRITER)
    def get(self, context):
        context.update({'page_title' : '新しいスレッドの作成'})
        return te.render(':new', context)
        
class CreateNewThreadHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    def get(self, context):
        raise ex.PostMethodRequired('新スレッド作成画面へ戻る', '/new/')
    
    @deco.default()
    @deco.board()
    @deco.myuser(c.WRITER)
    def post(self, context):
        board = context['board']
        title = board.validate_title(self.request.get('title'))
        content = board.validate_template(self.request.get('content'))
        
        template_id = m.Counter.incr('Template')
        myuser = context['user']
        now = board.now()
        template = m.Template(
            id = template_id,
            author_id = myuser.myuser_id,
            updater_id = myuser.myuser_id,

            status = c.NORMAL,
            updated = now,
            since = now,

            title = title,
            content = content,
            title_keeped = title,
            content_keeped = content,

            agree = [],
            deny = [],
            )
        template_key = template.put()
        
        thread_id = m.Counter.incr('Thread')
        thread = m.Thread(
            id = thread_id,
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
        if conf.LOCAL_SDK: time.sleep(0.5)
        m.Thread.clean(board)
        raise ex.Redirect('/%d/' % thread_id)

class EditThreadHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    @deco.myuser(c.EDITOR)
    def get(self, context, thread_id):
        thread_id = int(thread_id)
        board = context['board']
        
        thread = m.Thread.get_by_id(thread_id)
        if not thread: raise ex.ThreadNotFound()
        
        reses = m.Res.query_all(thread_id).fetch(conf.MAX_FETCH)
        
        thread._can_reopen = (thread.status != c.NORMAL) and (thread.res_count < board.max[c.RESES])
        thread._can_store = (thread.status != c.STORED)
        thread._can_delete = (thread.status != c.DELETED)
        
        context.update({
            'page_title': thread.title,
            'thread_id': thread_id,
            'thread': thread,
            'reses': reses,
            'DELETED': c.DELETED,
        })
        return te.render(':admin/thread', context)

class UpdateThreadHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    @deco.myuser(c.EDITOR)
    def post(self, context, thread_id):
        thread_id = int(thread_id)
        thread = m.Thread.get_by_id(thread_id)
        if not thread: raise ex.ThreadNotFound()
        
        operation = self.request.get('operation')
        if operation == 'reopen' and \
           thread.status != c.NORMAL and \
           thread.res_count < board.max[c.RESES]:
            thread.reopen()
        elif operation == 'store' and \
             thread.status != c.STORED:
            thread.store()
        elif operation == 'delete' and \
             thread.status != c.DELETED:
            thread.delete()
        else:
            raise ex.InvalidOperation()
        
        util.flush_page('/%d/' % thread_id)
        raise ex.Redirect('/admin/%d/' % thread_id)

class UpdateResesHandler(webapp2.RequestHandler):
    @deco.default()
    @deco.board()
    @deco.myuser(c.EDITOR)
    def post(self, context, thread_id):
        thread_id = int(thread_id)
        thread = m.Thread.get_by_id(thread_id)
        if not thread: raise ex.ThreadNotFound()
        
        status_to = m.Res.validate_operation(self.request.get('operation'))
        
        myuser = context['user']
        board = context['board']
        now = board.now()
        list = self.request.POST.getall('check')
        list = [ndb.Key('Res', thread_id * c.TT + int(n)) for n in list]
        list = ndb.get_multi(list)
        def update(res):
            res.status = status_to
            res.updater_id = myuser.myuser_id
            res.updated = now
            return res
        list = [update(res) for res in list if res.status != status_to]
        ndb.put_multi(list)
        
        util.flush_page('/%d/' % thread_id)
        if conf.LOCAL_SDK: time.sleep(0.5)
        raise ex.Redirect('/admin/%d/' % thread_id)


app = webapp2.WSGIApplication([
    ('/', TopPageHandler),
    routes.PathPrefixRoute('/<:[0-9a-z_-]{2,16}>', [
        webapp2.Route('/', IndexHandler),
        webapp2.Route('/<:\d+>/<:\d*><:-?><:\d*>', ThreadHandler),
        webapp2.Route('/link', LinkHandler),
        webapp2.Route('/stored/<:(\d{4})?><:/?><:(\d{1,2})?><:/?>', StoredHandler),
        webapp2.Route('/related/<:\d+>/', RelatedThreadHandler),
        webapp2.Route('/_login', LoginHandler),
        webapp2.Route('/_write/<:\d+>', WriteHandler),
        webapp2.Route('/_write_a/<:\d+>', WriteAnonymousHandler),
        webapp2.Route('/mypage/', MyPageHandler),
        webapp2.Route('/agreement/', AgreementHandler),
        webapp2.Route('/_agree', AgreeHandler),
        webapp2.Route('/template/<:\d+>/', TemplateHandler),
        webapp2.Route('/edit/<:\d+>/', EditTemplateHandler),
        webapp2.Route('/_edit/<:\d+>', UpdateTemplateHandler),
        webapp2.Route('/_vote/<:\d+>', VoteHandler),
        webapp2.Route('/new/', NewThreadHandler),
        webapp2.Route('/_new', CreateNewThreadHandler),

        webapp2.Route('/admin/<:\d+>/', EditThreadHandler),
        webapp2.Route('/admin/_edit/thread/<:\d+>/', UpdateThreadHandler),
        webapp2.Route('/admin/_edit/<:\d+>/', UpdateResesHandler),
    ]),
    routes.PathPrefixRoute('/a/<:[0-9a-z_-]{2,16}>', [
        webapp2.Route('/<:\d+>/', EditThreadHandler),
        webapp2.Route('/_edit/thread/<:\d+>/', UpdateThreadHandler),
    ]),
    ],
    debug=conf.DEBUG
    )
