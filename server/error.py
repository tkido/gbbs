#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import config
import const

from google.appengine.api import namespace_manager
from google.appengine.api import users

import tengine


def default_page(org, error):
    org.error(500)
    context = {
        'page_title': 'エラー',
        'error' : error,
        'org' : org,
    }
    org.response.out.write(tengine.render(':error', context, layout=':default/base'))

def page(org, context, error):
    org.error(500)
    namespace = context['namespace']
    context.update({
        'user' : users.get_current_user(),
        'login_url': users.create_login_url('/%s/' % namespace),
        'logout_url': users.create_logout_url('/%s/' % namespace),
        
        'page_title': 'エラー',
        'error' : error,
        'org' : org,
    })
    org.response.out.write(tengine.render(':error', context))

class Error(Exception):
  """Base class for exceptions in this application."""
  pass

class SameIdError(Error):
  pass

class BoardNotFoundError(Error):
  def __init__(self):
    self.title = '板が見つかりません'
    self.message = '板が存在しないか、削除されています。'

class UserNotFoundError(Error):
  def __init__(self):
    self.title = 'ユーザーデータの取得に失敗しました'
    self.message = '再度アクセスすれば成功する可能性が高いです。それでもうまくいかない場合は報告して下さい。'

class UserCouldNotUpdateError(Error):
  def __init__(self):
    self.title = 'ユーザーデータの更新に失敗しました'
    self.message = '再度アクセスすれば成功する可能性が高いです。それでもうまくいかない場合は報告して下さい。'

class ThreadNotFoundError(Error):
  def __init__(self):
    self.title = 'スレッドが見つかりません'
    self.message = 'もう一度試せば成功する可能性があります。2回以上試して同じであれば、それ以上繰り返すのは無意味と思われます。'
    self.continue_label = ''
    self.continue_uri = None
    self.retry = True

class ThreadArgumentError(Error):
  def __init__(self, continue_uri = None):
    self.title = 'レス番号の範囲指定が間違っています'
    self.message = '指定できる範囲は1-%dで、先頭の数字が末尾の数字以下であることが必要です。' % config.MAX_RESES_IN_THREAD
    self.continue_label = 'スレッド全体を見る'
    self.continue_uri = continue_uri
    
class PostMethodRequiredError(Error):
  def __init__(self, continue_label = None, continue_uri = None):
    self.title = 'GETメソッドではアクセスすることができません'
    self.message = 'GETメソッドでアクセスしていますが、このURIにはPOSTメソッドでしかアクセスすることができません。フォームに入力中にGoogleアカウントのセッションが切れ、ログインし直した場合にこの状態になることがあります。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。'
    self.continue_label = continue_label
    self.continue_uri = continue_uri

class AuthorityRequiredError(Error):
  def __init__(self, required_auth, your_auth):
    self.title = '権限が足りません'
    self.message = '指定された動作には『%s』以上の権限が必要ですが、現在の権限は『%s』です。権限についてはヘルプをご覧下さい。' % (const.AUTHORITIES[required_auth], const.AUTHORITIES[your_auth])
    self.report = ''
    self.help = '/authority'

class ThemeNotWritableError(Error):
  def __init__(self):
    self.title = 'テンプレートの編集はできません'
    self.message = 'スレがすでに倉庫に送りになっているか、書き込み禁止されています。'

class ThreadNotWritableError(Error):
  def __init__(self):
    self.title = 'このスレッドにはもう書き込めません'
    self.message = '理由はレス数がすでに%dに達しているか、すでに倉庫に入ったスレであるか、書き込み禁止されたスレであるかのいずれかです。' % config.MAX_RESES_IN_THREAD

class NewUserIdCouldNotGetError(Error):
  def __init__(self):
    self.title = '新しいユーザーIDの取得に失敗しました'
    self.message = 'もう一度試せば成功する可能性が高いです。それでもうまくいかない場合はバグかもしれません。報告して下さい。'

class NewThreadIdCouldNotGetError(Error):
  def __init__(self):
    self.title = '新しいスレッドIDの取得に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。時間を置いて試してもうまくいかない場合は、バグかもしれませんので報告して下さい。'

class NewThreadCouldNotPutError(Error):
  def __init__(self):
    self.title = '新スレッドの作成に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。時間を置いて試してもうまくいかない場合は、バグかもしれませんので報告して下さい。'

class TitleValidationError(Error):
  def __init__(self):
    self.title = 'タイトルが不正です'
    self.message = '内容が空であったり、長すぎたり、2つ以上の『%d』' + 'が含まれていたりするという問題があります。タイトルの長さの限界は%d字です。' % config.MAX_CHARS_IN_TITLE
        
class ContentValidationError(Error):
  def __init__(self):
    self.title = '内容が不正です'
    self.message = '内容は空ではなく、%d行以内、%d字以内でなければなりません。' % (config.MAX_ROWS_IN_CONTENT, config.MAX_CHARS_IN_CONTENT)

class NewUserCouldNotPutError(Error):
  def __init__(self):
    self.title = '新規ユーザーの作成に失敗しました'
    self.message = 'もう一度試せば成功する可能性が高いです。それでもうまくいかない場合はバグかもしれません。報告して下さい。'

class ThreadCouldNotPutError(Error):
  def __init__(self):
    self.title = 'スレッドの保存に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。'

class ResponseCouldNotPutError(Error):
  def __init__(self):
    self.title = 'レスの保存に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。'

class ThreadResponsedError(Error):
  """cron専用。倉庫入り処理を始めてから書き込みされたスレを倉庫送りにしないためのもの。"""
  def __init__(self):
    self.title = ''
    self.message = ''
