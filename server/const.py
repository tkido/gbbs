#!/usr/local/bin/python
# -*- coding:utf-8 -*-

MEMCACHE_DEFAULT_KEEP_SECONDS = 60

#day of the week in Japanese
WEEKDAYS = ['月', '火', '水', '木', '金', '土', '日']

#auth names in Japanese
AUTHORITIES = ['訪問者',
               '読者',
               '投稿者',
               '協力者',
               '編集者',
               '監督者',
               '副管理人',
               '管理人',
               'システム協力者',
               'システム管理者',
               
               '削除済み',
               '投稿禁止',
               '一時停止',
              ]

#auth table
SYSTEM_ADMIN  = 9
SYSTEM_HELPER = 8
ADMINISTRATOR = 7
SUB_ADMIN     = 6
SUPERVISOR    = 5
EDITOR        = 4
SUPPORTER     = 3
WRITER        = 2
READER        = 1
VISITOR       = 0

DINIED        =-1
BANNED        =-2
DELETED       =-3

#for status of Board, Thread, Response
NORMAL        = 0
STORED        =-1
BANNED        =-2
DELETED       =-3

MAX_FETCH_COUNT = 1000

#for boards
BOARD_NAMESPACE = 'default'