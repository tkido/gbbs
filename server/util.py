#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import base64
import datetime
import hashlib
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

def hash(source):
  string_source = str(source)
  sha1 = hashlib.sha1()
  sha1.update(string_source + config.SALT)

  local_now = now()
  if config.ID_CHANGE_CYCLE >= 1:
    sha1.update(str(local_now.year))
  if config.ID_CHANGE_CYCLE >= 2:
    sha1.update(str(local_now.month))
  if config.ID_CHANGE_CYCLE >= 3:
    sha1.update(str(local_now.day))

  rst = sha1.digest()
  rst = base64.urlsafe_b64encode(rst)
  rst = rst[:8]
  return rst

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

def delete_memcache(path):
    path = namespaced(path)
    memcache.delete_multi([path + '!login', path + '!logout'])

def namespaced(path):
    return str('/%s%s' % (namespace_manager.get_namespace(), path))

def get_board(board_id):
    namespace_manager.set_namespace(const.BOARD_NAMESPACE)
    board = memcache.get(board_id)
    if not board:
        board = ndb.Key('Board', board_id).get()
    if not board:
        raise error.BoardNotFoundError()
    else:
        memcache.add(board_id, board, 3600)
    namespace_manager.set_namespace(board_id)
    return board

def myuser_required(required_auth = const.BANNED):
    def wrapper_func(original_func):
        def decorated_func(org, namespace, *args, **kwargs):
            board = get_board(namespace)
            user = users.get_current_user()
            if not user:
                org.redirect(str(users.create_login_url('/%s/login?continue=%s' % (namespace, org.request.uri))))
                return
            myuser = model.MyUser.get_by_id(user.user_id())
            if not myuser:
                org.redirect(str('/%s/login?continue=%s' % (namespace, org.request.uri)))
                return
            context = {'namespace' : namespace,
                       'board': board,
                       'user': myuser,
                       'login_url': '/%s/login?continue=%s' % (namespace, org.request.uri),
                       'logout_url': users.create_logout_url(org.request.uri) }
            if myuser.status < required_auth:
                error.page(org, context, error.AuthorityRequiredError(required_auth, myuser.status)); return;
            original_func(org, context, *args, **kwargs)
        return decorated_func
    return wrapper_func

def memcached_with(second = const.MEMCACHE_DEFAULT_KEEP_SECONDS):
    def wrapper_func(original_func):
        def decorated_func(org, namespace, *args, **kwargs):
            board = get_board(namespace)
            user = users.get_current_user()
            key = org.request.path + ('!login' if user else '!logout')
            html = memcache.get(key)
            if html:
                org.response.out.write(html)
                return
            else:
                context = {'namespace' : namespace,
                           'board': board,
                           'user': user,
                           'login_url': '/%s/login?continue=%s' % (namespace, org.request.uri),
                           'logout_url': users.create_logout_url(org.request.uri) }
                html = original_func(org, context, *args, **kwargs)
                if html:
                    html += """<!-- memcached with "%s" at "%s" -->""" % (key, now())
                    memcache.add(key, html, second)
        return decorated_func
    return wrapper_func

def namespace_required():
    def wrapper_func(original_func):
        def decorated_func(org, namespace, *args, **kwargs):
            board = get_board(namespace)
            context = {'namespace' : namespace,
                       'board': board,
                       'login_url': '/%s/login?continue=%s' % (namespace, org.request.uri),
                       'logout_url': users.create_logout_url(org.request.uri) }
            original_func(org, context, *args, **kwargs)
        return decorated_func
    return wrapper_func
