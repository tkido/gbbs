#!/usr/local/bin/python
# -*- coding:utf-8 -*-

TIMEZONE = 9

import os
LOCAL_SDK = (os.environ.get("SERVER_SOFTWARE") == "Development/2.0")
HTTP_HOST = os.environ.get("HTTP_HOST")
