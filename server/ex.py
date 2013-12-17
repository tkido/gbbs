#!/usr/local/bin/python
# -*- coding:utf-8 -*-

import conf
import c

from google.appengine.api import namespace_manager
from google.appengine.api import users

import te

def page(org, context, error):
    org.error(500)
    context.update({
        'page_title': 'エラー',
        'error' : error,
        'org' : org,
    })
    if isinstance(error, BoardNotFound):
        org.response.out.write(te.render(':error', context, layout=':default/base'))
    else:
        ns = context['ns']
        context.update({
            'user' : users.get_current_user(),
            'login_url': users.create_login_url('/%s/' % ns),
            'logout_url': users.create_logout_url('/%s/' % ns),
        })
        org.response.out.write(te.render(':error', context))

class Throwable(Exception):
    pass

class Redirect(Throwable):
    def __init__(self, to = ''):
        self.to = to
class RedirectAgreement(Redirect):
    pass
class RedirectContinue(Redirect):
    pass
class RedirectLogin(Redirect):
    pass
class RedirectOrg(Redirect):
    pass
    
class SameId(Throwable):
    pass


class Error(Exception):
    pass
class AppError(Error):
    pass
class SysError(Error):
    pass

class BoardNotFound(AppError):
  def __init__(self):
    self.title = '掲示板が見つかりません'
    self.message = '存在しないか、すでに削除されています。'

class ThreadNotFound(AppError):
  def __init__(self):
    self.title = 'スレッドが見つかりません'
    self.message = '存在しないか、すでに削除されています。'

class ThreadArgument(AppError):
  def __init__(self, continue_uri):
    self.title = 'レス番号の範囲指定が間違っています'
    self.message = '指定できる範囲は1-%dです。' % conf.MAX_RESES_IN_THREAD
    self.continue_label = 'スレッド全体を見る'
    self.continue_uri = continue_uri

class PostMethodRequired(AppError):
  def __init__(self, continue_label = None, continue_uri = None):
    self.title = 'POSTメソッドでのアクセスが必要です'
    self.message = 'GETメソッドでアクセスしています。入力中にGoogleアカウントの期限が切れ、ログインし直した場合に、この状態になることがあるようです。フォームの内容はブラウザで戻ることによって取り戻せる可能性があります。'
    self.continue_label = continue_label
    self.continue_uri = continue_uri

class AuthorityRequired(AppError):
  def __init__(self, required_auth, your_auth):
    self.title = '権限が足りません'
    self.message = '指定された動作には『%s』以上の権限が必要ですが、現在の権限は『%s』です。権限についてはヘルプをご覧下さい。' % (c.AUTHORITIES[required_auth], c.AUTHORITIES[your_auth])
    self.report = ''
    self.help = '/authority'

class TemplateNotWritable(AppError):
  def __init__(self):
    self.title = 'テンプレートの編集はできません'
    self.message = 'スレがすでに倉庫に送りになっているか、書き込み禁止されています。'

class ThreadNotWritable(AppError):
  def __init__(self):
    self.title = 'このスレッドにはもう書き込めません'
    self.message = 'レス数がすでに%dに達している、すでに過去ログになっている、書き込み禁止されている、などの理由により、もう書けません。' % conf.MAX_RESES_IN_THREAD

class InvalidTitle(AppError):
  def __init__(self, board):
    self.title = 'タイトルが不正です'
    self.message = '空ではなく、%d字以内である必要があります。' % board.max[c.CHARS_TITLE]
    self.message += '2つ以上の『%d』を含むことはできません。'
        
class InvalidContent(AppError):
  def __init__(self, board):
    self.title = '内容が不正です'
    self.message = '空ではなく、%d行以内かつ%d字以内である必要があります。' % (board.max[c.ROWS], board.max[c.CHARS])

class InvalidTemplate(AppError):
  def __init__(self, board):
    self.title = '内容が不正です'
    self.message = '空ではなく、%d行以内かつ%d字以内である必要があります。' % (board.max[c.ROWS_TEMPLATE], board.max[c.CHARS_TEMPLATE])

class InvalidOperation(AppError):
  def __init__(self):
    self.title = '実行する内容を選択して下さい'
    self.message = '誤った操作を防止するため必ず選択する必要があります。'


# ndb error
class UserNotFound(SysError):
  def __init__(self):
    self.title = 'ユーザーデータの取得に失敗しました'
    self.message = '再度アクセスすれば成功するかもしれません。うまくいかない場合は報告して下さい。'

class UserCouldNotUpdate(SysError):
  def __init__(self):
    self.title = 'ユーザーデータの更新に失敗しました'
    self.message = '再度アクセスすれば成功する可能性が高いです。それでもうまくいかない場合は報告して下さい。'
    
class NewUserIdCouldNotGet(SysError):
  def __init__(self):
    self.title = '新しいユーザーIDの取得に失敗しました'
    self.message = 'もう一度試せば成功する可能性が高いです。それでもうまくいかない場合はバグかもしれません。報告して下さい。'

class NewThreadIdCouldNotGet(SysError):
  def __init__(self):
    self.title = '新しいスレッドIDの取得に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。時間を置いて試してもうまくいかない場合は、バグかもしれませんので報告して下さい。'

class NewThreadCouldNotPut(SysError):
  def __init__(self):
    self.title = '新スレッドの作成に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。時間を置いて試してもうまくいかない場合は、バグかもしれませんので報告して下さい。'

class NewUserCouldNotPut(SysError):
  def __init__(self):
    self.title = '新規ユーザーの作成に失敗しました'
    self.message = 'もう一度試せば成功する可能性が高いです。それでもうまくいかない場合はバグかもしれません。報告して下さい。'

class ThreadCouldNotPut(SysError):
  def __init__(self):
    self.title = 'スレッドの保存に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。'

class ResCouldNotPut(SysError):
  def __init__(self):
    self.title = 'レスの保存に失敗しました'
    self.message = '再送信を行うと今度は成功する可能性がありますが、続いて失敗した場合はそれ以上繰り返さずに、あとでもう一度書き込んで下さい。フォームの入力内容はブラウザの戻るボタンで戻ることによって取り戻せる可能性があります。'
