#!/usr/local/bin/python
# -*- coding:utf-8 -*-

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

#for status of Board, Thread, Res
NORMAL        = 0
STORED        =-1
BANNED        =-2
DELETED       =-3

#for boards
BOARD_NAMESPACE = 'b'

# m.Board.max[_]
THREADS        = 0
RESES          = 1
CHARS          = 2
CHARS_TITLE    = 3
CHARS_TEMPLATE = 4
ROWS           = 5
ROWS_TEMPLATE  = 6

#const
K  =  1000
TT = 10000 # ten thousand
