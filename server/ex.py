#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import config
import const

from google.appengine.api import namespace_manager
from google.appengine.api import users

import tengine

def page(org, context, error):
    org.error(500)
    context.update({
        'page_title': 'エラー',
        'error' : error,
        'org' : org,
    })
    if isinstance(error, BoardNotFound):
        org.response.out.write(tengine.render(':error', context, layout=':default/base'))
    else:
        namespace = context['namespace']
        context.update({
            'user' : users.get_current_user(),
            'login_url': users.create_login_url('/%s/' % namespace),
            'logout_url': users.create_logout_url('/%s/' % namespace),
        })
        org.response.out.write(tengine.render(':error', context))

class Redirect(Exception):
    """Base class for Redirect in this application."""
    def __init__(self, to = '/'):
        self.to = to or '/'

class RedirectAgreement(Redirect):
    pass
class RedirectContinue(Redirect):
    pass
class RedirectLogin(Redirect):
    pass

class Error(Exception):
    """Base class for errors in this application."""
    pass

class SameId(Error):
  pass

class BoardNotFound(Error):
  def __init__(self):
    self.title = '板が見つかりません'
    self.message = '板が存在しないか、すでに削除されています。'

class ThreadNotFound(Error):
  def __init__(self):
    self.title = 'スレッドが見つかりません'
    self.message = 'スレッドが存在しないか、すでに削除されています。'

class ThreadArgument(Error):
  def __init__(self, continue_uri):
    self.title = 'レス番号の範囲指定が間違っています'
    self.message = '指定できる範囲は1-%dです。' % config.MAX_RESES_IN_THREAD
    self.continue_label = 'スレッド全体を見る'
    self.continue_uri = continue_uri

class UserNotFound(Error):
  def __init__(self):
    self.title = 'ユーザーデータの取得に失敗しました'
    self.message = '再度アクセスすれば成功するかもしれません。うまくいかない場合は報告して下さい。'

class UserCouldNotUpdate(Error):
  def __init__(self):
    self.title = 'ユーザーデータの更新に失敗しました'
    self.message = '再度アクセスすれば成功する可能性が高いです。それでもうまくいかない場合は報告して下さい。'
    
class PostMethodRequired(Error):
  def __init__(self, continue_label = None, continue_uri = None):
    self.title = 'POSTメソッドでのアクセスが必要です'
    self.message = 'GETメソッドでアクセスしています。入力中にGoogleアカウントの期限が切れ、ログインし直した場合に、この状態になることがあるようです。フォームの内容はブラウザで戻ることによって取り戻せる可能性があります。'
    self.continue_label = continue_label
    self.continue_uri = continue_uri

class AuthorityRequired(Error):
  def __init__(self, required_auth, your_auth):
    self.title = '権限が足りません'
    self.message = '指定された動作には『%s』以上の権限が必要ですが、現在の権限は『%s』です。権限についてはヘルプをご覧下さい。' % (const.AUTHORITIES[required_auth], const.AUTHORITIES[your_auth])
    self.report = ''
    self.help = '/authority'

class ThemeNotWritable(Error):
  def __init__(self):
    self.title = 'テンプレートの編集はできません'
    self.message = 'スレがすでに倉庫に送りになっているか、書き込み禁止されています。'

class ThreadNotWritable(Error):
  def __init__(self):
    self.title = 'このスレッドにはもう書き込めません'
    self.message = 'レス数がすでに%dに達している、すでに過去ログになっている、書き込み禁止されている、など。' % config.MAX_RESES_IN_THREAD

class NewUserIdCouldNotGet(Error):
  def __init__(self):
    self.title = '新しいユーザーIDの取得に失敗しました'
    self.message = 'もう一度試せば成功する可能性が高いです。それでもうまくいかない場合はバグかもしれません。報告して下さい。'

class NewThreadIdCouldNotGet(Error):
  def __init__(self):
    self.title = '新しいスレッドIDの取得に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。時間を置いて試してもうまくいかない場合は、バグかもしれませんので報告して下さい。'

class NewThreadCouldNotPut(Error):
  def __init__(self):
    self.title = '新スレッドの作成に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。時間を置いて試してもうまくいかない場合は、バグかもしれませんので報告して下さい。'

class TitleValidation(Error):
  def __init__(self, board):
    self.title = 'タイトルが不正です'
    self.message = '空ではなく、%d字以内である必要があります。' % board.max_chars_title
    self.message += '2つ以上の『%d』が含むことはできません。'
        
class ContentValidation(Error):
  def __init__(self, board):
    self.title = '内容が不正です'
    self.message = '空ではなく、%d行以内かつ%d字以内である必要があります。' % (board.max_rows, board.max_chars)

class TemplateValidation(Error):
  def __init__(self, board):
    self.title = '内容が不正です'
    self.message = '空ではなく、%d行以内かつ%d字以内である必要があります。' % (board.max_rows_template, board.max_chars_template)

class NewUserCouldNotPut(Error):
  def __init__(self):
    self.title = '新規ユーザーの作成に失敗しました'
    self.message = 'もう一度試せば成功する可能性が高いです。それでもうまくいかない場合はバグかもしれません。報告して下さい。'

class ThreadCouldNotPut(Error):
  def __init__(self):
    self.title = 'スレッドの保存に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。'

class ResponseCouldNotPut(Error):
  def __init__(self):
    self.title = 'レスの保存に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。'
