#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import datetime

from google.appengine.api import memcache
from google.appengine.api import namespace_manager

import conf
import c

def now():
  return datetime.datetime.now() + datetime.timedelta(hours = conf.TIMEZONE)

def dt_to_str(dt):
  return '%04d/%02d/%02d(%s) %02d:%02d:%02d' % (dt.year,
                                                dt.month,
                                                dt.day,
                                                c.WEEKDAYS[dt.weekday()],
                                                dt.hour,
                                                dt.minute,
                                                dt.second,
                                               )

def flush_page(path):
    path = 'http://%s/%s%s' % (conf.HTTP_HOST, namespace_manager.get_namespace(), path)
    memcache.delete_multi([path + '!login', path])
