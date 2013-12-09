#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import datetime
import logging
import re

from google.appengine.api import memcache
from google.appengine.api import namespace_manager
from google.appengine.api import users
from google.appengine.ext import ndb

import config
import const
import error
import model

def now():
  return datetime.datetime.now() + datetime.timedelta(hours = config.TIMEZONE)

def datetime_to_str(dt):
  return '%04d/%02d/%02d(%s) %02d:%02d:%02d' % (dt.year,
                                                dt.month,
                                                dt.day,
                                                const.WEEKDAYS[dt.weekday()],
                                                dt.hour,
                                                dt.minute,
                                                dt.second
                                               )

def flush_user(myuser):
    memcache.delete(myuser.user.user_id())

def flush_page(path):
    path = namespaced(path)
    memcache.delete_multi([path + '!login', path])

def namespaced(path):
    return str('/%s%s' % (namespace_manager.get_namespace(), path))

def board_required():
    def wrapper_func(original_func):
        def decorated_func(org, namespace, *args, **kwargs):
            context = {}
            namespace_manager.set_namespace(const.BOARD_NAMESPACE)
            board = memcache.get(namespace)
            if not board:
                board = ndb.Key('Board', namespace).get()
                memcache.add(namespace, board, 3600)
            if not board or not board.readable():
                error.page(org, context, error.BoardNotFound()); return;
            namespace_manager.set_namespace(namespace)
            context.update({
                'namespace' : namespace,
                'board': board,
                'login_url': '/%s/_login?continue=%s' % (namespace, org.request.uri),
                'logout_url': users.create_logout_url(org.request.uri),
            })
            original_func(org, context, *args, **kwargs)
        return decorated_func
    return wrapper_func

def memcached_with(second = const.MEMCACHE_DEFAULT_KEEP_SECONDS):
    def wrapper_func(original_func):
        def decorated_func(org, context, *args, **kwargs):
            user = users.get_current_user()
            key = org.request.path + ('!login' if user else '')
            html = memcache.get(key)
            if html:
                org.response.out.write(html)
                return
            else:
                context.update({ 'user': user })
                html = original_func(org, context, *args, **kwargs)
                if html:
                    html += """<!-- memcached with "%s" at "%s" -->""" % (key, now())
                    memcache.add(key, html, second)
        return decorated_func
    return wrapper_func

def myuser_required(required_auth = const.BANNED):
    def wrapper_func(original_func):
        def decorated_func(org, context, *args, **kwargs):
            user = users.get_current_user()
            if not user:
                org.redirect(str(users.create_login_url(context['login_url']))); return;
            myuser = memcache.get(user.user_id())
            if not myuser:
                myuser = model.MyUser.get_by_id(user.user_id())
                memcache.add(user.user_id(), myuser, 600)
            if not myuser or not myuser.readable():
                org.redirect(str(context['login_url'])); return;
            context.update({
                'user': myuser,
                'logout_url': users.create_logout_url(namespaced('/')),
            })
            if myuser.status < required_auth:
                error.page(org, context, error.AuthorityRequiredError(required_auth, myuser.status)); return;
            original_func(org, context, *args, **kwargs)
        return decorated_func
    return wrapper_func

