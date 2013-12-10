#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import logging
import re

import tenjin
import tenjin.gae
from tenjin.helpers import escape, to_str
from tenjin.helpers.html import text2html

tenjin.gae.init()
#logging.basicConfig(level=logging.DEBUG)
#tenjin.logger = logging
tengine = tenjin.Engine(path=['template'], postfix='.pyhtml', layout=':base')

ANCHOR_PAT = re.compile('&gt;&gt;(1000|0|[1-9][0-9]{0,2})(-?)((1000|0|[1-9][0-9]{0,2})?)')
# John Gruber's regex to find URLs in plain text, converted to Python/Unicode
# https://gist.github.com/uogbuji/705383
GRUBER_URLINTEXT_PAT = re.compile(ur'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))')
 
def decorate(source):
    def replace_anchor(match):
        g = match.groups()
        if g[1]:
            return '<a href=\"#%s\">&gt;&gt;</a><a href=\"%s%s%s\">%s%s%s</a>' % \
                   (g[0], g[0], g[1], g[2], g[0], g[1], g[2])
        elif g[2] and not g[1]:
            return match.group(0)
        else:
            return '<a href=\"#%s\">&gt;&gt;</a><a href=\"%s\">%s</a>%s%s' % \
                   (g[0], g[0], g[0], g[1], g[2])
    def replace_uri(match):
        g = match.group()
        return '<a href=\"%s\">%s</a>' % (g, g)
    source = re.sub(GRUBER_URLINTEXT_PAT, replace_uri, source)
    return re.sub(ANCHOR_PAT, replace_anchor, source)

def render(tempalte, context, **kwargs):
    return tengine.render(tempalte, context, **kwargs)
