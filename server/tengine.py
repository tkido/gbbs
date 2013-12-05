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
tenjin.logger = logging
tengine = tenjin.Engine(path=['template'], postfix='.html', layout=':base')

pattern = re.compile('&gt;&gt;(1000|0|[1-9][0-9]{0,2})(-?)((1000|0|[1-9][0-9]{0,2})?)')

def res_anchor(source):
    def replace(match):
        g = match.groups()
        if g[1]:
            return '<a href=\"#%s\">&gt;&gt;</a><a href=\"%s%s%s\">%s%s%s</a>' % \
                   (g[0], g[0], g[1], g[2], g[0], g[1], g[2])
        elif g[2] and not g[1]:
            return match.group(0)
        else:
            return '<a href=\"#%s\">&gt;&gt;</a><a href=\"%s\">%s</a>%s%s' % \
                   (g[0], g[0], g[0], g[1], g[2])
    return re.sub(pattern, replace, source)

def render(tempalte, context, **kwargs):
    return tengine.render(tempalte, context, **kwargs)
