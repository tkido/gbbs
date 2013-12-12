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

def catch():
    def wrapper_func(original_func):
        def decorated_func(org, ns = '', *args, **kwargs):
            try:
                context = { 'ns' : ns }
                original_func(org, context, *args, **kwargs)
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
            namespace_manager.set_namespace(c.BOARD_NAMESPACE)
            ns = context['ns']
            board = memcache.get(ns)
            if not board:
                board = ndb.Key('Board', ns).get()
                memcache.add(ns, board, conf.CACHED_BOARD)
            if not board or not board.readable(): raise ex.BoardNotFound()
            namespace_manager.set_namespace(ns)
            context.update({
                'ns' : ns,
                'board': board,
                'login_url': '/%s/_login?continue=%s' % (ns, org.request.uri),
                'logout_url': users.create_logout_url(org.request.uri),
            })
            original_func(org, context, *args, **kwargs)
        return decorated_func
    return wrapper_func

def cache(second = conf.CACHED_DEFAULT):
    def wrapper_func(original_func):
        def decorated_func(org, context = {}, *args, **kwargs):
            user = users.get_current_user()
            key = org.request.uri + ('!login' if user else '')
            html = memcache.get(key)
            if html:
                org.response.out.write(html)
                return
            else:
                context.update({ 'user': user })
                html = original_func(org, context, *args, **kwargs)
                if html:
                    html += """<!-- memcached with "%s" at "%s" -->""" % (key, util.now())
                    memcache.add(key, html, second)
        return decorated_func
    return wrapper_func

def myuser(required_auth = c.BANNED):
    def wrapper_func(original_func):
        def decorated_func(org, context, *args, **kwargs):
            user = users.get_current_user()
            if not user: raise ex.RedirectLogin(context['login_url'])
            myuser = memcache.get(user.user_id())
            if not myuser:
                myuser = m.MyUser.get_by_id(user.user_id())
                memcache.add(user.user_id(), myuser, conf.CACHED_MYUSER)
            if not myuser or not myuser.readable(): raise ex.Redirect(context['login_url'])
            context.update({
                'user': myuser,
                'logout_url': users.create_logout_url('/%s/' % context['ns']),
            })
            if myuser.status < required_auth: raise ex.AuthorityRequired(required_auth, myuser.status)
            original_func(org, context, *args, **kwargs)
        return decorated_func
    return wrapper_func

