#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import logging
import re

from google.appengine.api import namespace_manager

import tenjin
import tenjin.gae
from tenjin.helpers import escape, to_str
from tenjin.helpers.html import text2html

import conf

tenjin.gae.init()
#logging.basicConfig(level=logging.DEBUG)
#tenjin.logger = logging
te = tenjin.Engine(path=['view'], postfix='.pyhtml', layout=':base')

GBBS_URL_HEAD = 'http://%s/' % conf.HTTP_HOST
ANCHOR_PAT = re.compile('&gt;&gt;(1000|0|[1-9][0-9]{0,2})(-?)((1000|0|[1-9][0-9]{0,2})?)')
# John Gruber's regex to find URLs in plain text, converted to Python/Unicode https://gist.github.com/uogbuji/705383
GRUBER_URLINTEXT_PAT = re.compile(ur'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))')


def decorate(source):
    ns = namespace_manager.get_namespace()
    def anchor(source):
        def replaced(match):
            g = match.groups()
            if g[1]:
                return '<a href=\"#%s\">&gt;&gt;</a><a href=\"%s%s%s\">%s%s%s</a>' % \
                       (g[0], g[0], g[1], g[2], g[0], g[1], g[2])
            elif g[2] and not g[1]:
                return match.group(0)
            else:
                return '<a href=\"#%s\">&gt;&gt;</a><a href=\"%s\">%s</a>%s%s' % \
                       (g[0], g[0], g[0], g[1], g[2])
        return re.sub(ANCHOR_PAT, replaced, source)
    def link(match):
        def replaced(match):
            g = match.group()
            if g.startswith(GBBS_URL_HEAD):
                return '<a href=\"%s\">%s</a>' % (g, g)
            else:
                return '<a href=\"/%s/link?to=%s\">%s</a>' % (ns, g, g)
        return re.sub(GRUBER_URLINTEXT_PAT, replaced, source)
    return anchor(link(source))

def render(tempalte, context, **kwargs):
    return te.render(tempalte, context, **kwargs)
