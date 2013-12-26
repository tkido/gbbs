#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import logging

from google.appengine.api import memcache
from google.appengine.api import namespace_manager
from google.appengine.api import users
from google.appengine.ext import ndb

import conf
import c
import ex
import m
import util

def default():
    def wrapper_func(original_func):
        def decorated_func(org, ns = '', *args, **kwargs):
            try:
                context = {
                    'ns' : ns,
                    'PRO' : conf.PRO,
                }
                html = original_func(org, context, *args, **kwargs)
                if html:
                    org.response.out.write(html)
            # Catch Redirect
            except ex.RedirectAgreement:
                to = '/%s/agreement/' % ns
                if org.request.get('continue'):
                    to += '?continue=%s' % org.request.get('continue')
                org.redirect(str(to))
            except ex.RedirectLogin as red:
                to = red.to if red.to else org.request.uri
                org.redirect(str(users.create_login_url(to)))
            except ex.RedirectContinue:
                org.redirect(str(org.request.get('continue') or '/%s/' % ns))
            except ex.RedirectOrg:
                org.redirect(str(org.request.uri))
            except ex.Redirect as red:
                org.redirect(str('/%s%s' % (ns, red.to)))
            # Catch Error
            except ex.AppError as err:
                ex.page(org, context, err)
            except ex.SysError as err:
                logging.exception(err)
            except Exception as e:
                logging.exception(e)
        return decorated_func
    return wrapper_func

def board():
    def wrapper_func(original_func):
        def decorated_func(org, context, *args, **kwargs):
            namespace_manager.set_namespace(c.NAMESPACE_BOARD)
            ns = context['ns']
            gbbs = memcache.get(c.NAMESPACE_BOARD)
            if not gbbs:
                gbbs = m.Board.get_by_id(c.NAMESPACE_BOARD)
                memcache.add(c.NAMESPACE_BOARD, gbbs, conf.CACHED_GBBS)
            if not gbbs: raise ex.NotFoundGbbs()
            board = memcache.get(ns)
            if not board:
                board = m.Board.get_by_id(ns)
                memcache.add(ns, board, conf.CACHED_BOARD)
            if not board or not board.readable(): raise ex.BoardNotFound()
            namespace_manager.set_namespace(ns)
            context.update({
                'board': board,
                'gbbs': gbbs,
                'login_url': '/%s/_login?continue=%s' % (ns, org.request.uri),
                'logout_url': users.create_logout_url(org.request.uri),
            })
            return original_func(org, context, *args, **kwargs)
        return decorated_func
    return wrapper_func

def cache(second = conf.CACHED_DEFAULT):
    def wrapper_func(original_func):
        def decorated_func(org, context = {}, *args, **kwargs):
            user = users.get_current_user()
            key = org.request.uri + ('!login' if user else '')
            html = memcache.get(key)
            if not html:
                context.update({ 'user': user })
                html = original_func(org, context, *args, **kwargs)
                if html:
                    html += """<!-- memcached with "%s" at "%s" -->""" % (key, util.now())
                    memcache.add(key, html, second)
            return html
        return decorated_func
    return wrapper_func

def myuser(required_auth = c.DELETED):
    def wrapper_func(original_func):
        def decorated_func(org, context, *args, **kwargs):
            user = users.get_current_user()
            if not user: raise ex.RedirectLogin(context['login_url'])
            myuser = memcache.get(user.user_id())
            if not myuser:
                myuser = m.MyUser.get_by_id(user.user_id())
                memcache.add(user.user_id(), myuser, conf.CACHED_MYUSER)
            if not myuser or not myuser.readable(): raise ex.Redirect('/_login?continue=%s' % org.request.uri)
            context.update({
                'user': myuser,
                'logout_url': users.create_logout_url('/%s/' % context['ns']),
            })
            if myuser.status < required_auth: raise ex.AuthorityRequired(required_auth, myuser.status)
            return original_func(org, context, *args, **kwargs)
        return decorated_func
    return wrapper_func

