#!/usr/local/bin/python
# -*- coding:utf-8 -*-

TIMEZONE = 9

# memcached n seconds
CACHED_DEFAULT = 60
CACHED_BOARD = 3600
CACHED_MYUSER = 600

# for ndb
MAX_FETCH = 1000


import os
LOCAL_SDK = os.environ.get("SERVER_SOFTWARE").startswith("Development")
HTTP_HOST = os.environ.get("HTTP_HOST")

if not LOCAL_SDK:
    from google.appengine.ext import ereporter
    ereporter.register_logger()
