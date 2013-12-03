#!/usr/local/bin/python
# -*- coding:utf-8 -*-

TIMEZONE = +9

SALT = 'foobar'

#0:ever(no change)
#1:year
#2:month
#3:day
ID_CHANGE_CYCLE = 3

MAX_RESES_IN_THREAD = 3

MAX_THREADS_IN_BOARD = 3

MAX_CHARS_IN_TITLE = 32
MAX_ROWS_IN_CONTENT = 80
MAX_CHARS_IN_CONTENT = 4096


import os
LOCAL_SDK = (os.environ.get("SERVER_SOFTWARE") == "Development/2.0")
