#!/usr/local/bin/python
# -*- coding:utf-8 -*-

TIMEZONE = 9

# memcached n seconds
CACHED_DEFAULT = 60
CACHED_BOARD = 3600
CACHED_MYUSER = 600

# for ndb
MAX_FETCH = 1000

# for setting
MARGIN_VOTE = 3
MARGIN_CLEAN = 3

import os
LOCAL_SDK = os.environ.get("SERVER_SOFTWARE").startswith("Development")
HTTP_HOST = os.environ.get("HTTP_HOST")
DEBUG = LOCAL_SDK or (HTTP_HOST == "www.tohobbs.net")
PRO = (HTTP_HOST == "www.gbbs.jp")

if not LOCAL_SDK:
    from google.appengine.ext import ereporter
    ereporter.register_logger()
