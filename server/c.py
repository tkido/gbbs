#!/usr/local/bin/python
# -*- coding:utf-8 -*-

#day of the week in Japanese
WEEKDAYS_JP = ['月', '火', '水', '木', '金', '土', '日']

#auth names in Japanese
AUTHORITIES = [
               '削除済み',
               '投稿禁止',
               '一時停止',
               '訪問者',
               '読者',
               '投稿者',
               '協力者',
               '編集者',
               '監督者',
               '副管理人',
               '管理人',
               'システム協力者',
               'システム管理者',
              ]

#for status of MyUser
SYSTEM_ADMIN  = 12
SYSTEM_HELPER = 11
ADMINISTRATOR = 10
SUB_ADMIN     = 9
SUPERVISOR    = 8
EDITOR        = 7
SUPPORTER     = 6
WRITER        = 5
READER        = 4

#for status of MyUser, Board, Thread, Res
NORMAL        = 3
STORED        = 2
BANNED        = 1
DELETED       = 0

#for boards
BOARD_NAMESPACE = 'b'

#for m.Board.max[n]
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
