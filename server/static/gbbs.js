/**
 * Cookie plugin
 *
 * Copyright (c) 2006 Klaus Hartl (stilbuero.de)
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
 *
 */

/**
 * Create a cookie with the given name and value and other optional parameters.
 *
 * @example $.cookie('the_cookie', 'the_value');
 * @desc Set the value of a cookie.
 * @example $.cookie('the_cookie', 'the_value', { expires: 7, path: '/', domain: 'jquery.com', secure: true });
 * @desc Create a cookie with all available options.
 * @example $.cookie('the_cookie', 'the_value');
 * @desc Create a session cookie.
 * @example $.cookie('the_cookie', null);
 * @desc Delete a cookie by passing null as value. Keep in mind that you have to use the same path and domain
 *       used when the cookie was set.
 *
 * @param String name The name of the cookie.
 * @param String value The value of the cookie.
 * @param Object options An object literal containing key/value pairs to provide optional cookie attributes.
 * @option Number|Date expires Either an integer specifying the expiration date from now on in days or a Date object.
 *                             If a negative value is specified (e.g. a date in the past), the cookie will be deleted.
 *                             If set to null or omitted, the cookie will be a session cookie and will not be retained
 *                             when the the browser exits.
 * @option String path The value of the path atribute of the cookie (default: path of page that created the cookie).
 * @option String domain The value of the domain attribute of the cookie (default: domain of page that created the cookie).
 * @option Boolean secure If true, the secure attribute of the cookie will be set and the cookie transmission will
 *                        require a secure protocol (like HTTPS).
 * @type undefined
 *
 * @name $.cookie
 * @cat Plugins/Cookie
 * @author Klaus Hartl/klaus.hartl@stilbuero.de
 */

/**
 * Get the value of a cookie with the given name.
 *
 * @example $.cookie('the_cookie');
 * @desc Get the value of a cookie.
 *
 * @param String name The name of the cookie.
 * @return The value of the cookie.
 * @type String
 *
 * @name $.cookie
 * @cat Plugins/Cookie
 * @author Klaus Hartl/klaus.hartl@stilbuero.de
 */
jQuery.cookie = function(name, value, options) {
    if (typeof value != 'undefined') { // name and value given, set cookie
        options = options || {};
        if (value === null) {
            value = '';
            options.expires = -1;
        }
        var expires = '';
        if (options.expires && (typeof options.expires == 'number' || options.expires.toUTCString)) {
            var date;
            if (typeof options.expires == 'number') {
                date = new Date();
                date.setTime(date.getTime() + (options.expires * 24 * 60 * 60 * 1000));
            } else {
                date = options.expires;
            }
            expires = '; expires=' + date.toUTCString(); // use expires attribute, max-age is not supported by IE
        }
        // CAUTION: Needed to parenthesize options.path and options.domain
        // in the following expressions, otherwise they evaluate to undefined
        // in the packed version for some reason...
        var path = options.path ? '; path=' + (options.path) : '';
        var domain = options.domain ? '; domain=' + (options.domain) : '';
        var secure = options.secure ? '; secure' : '';
        document.cookie = [name, '=', encodeURIComponent(value), expires, path, domain, secure].join('');
    } else { // only name given, get cookie
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
};

/*
 * jQuery Disable On Submit Plugin
 * http://www.evanbot.com/article/jquery-disable-on-submit-plugin/13
 *
 * Copyright (c) 2009 Evan Byrne (http://www.evanbot.com)     
 */
$.fn.disableOnSubmit = function(disableList){
	
	if(disableList == null){var $list = 'input[type=submit],input[type=button],input[type=reset],button';}
	else{var $list = disableList;}
	
	// Makes sure button is enabled at start
	$(this).find($list).removeAttr('disabled');
	
	$(this).submit(function(){$(this).find($list).attr('disabled','disabled');});
	return this;
};


/* gbbs */
$(document).ready(function(){
    //二重投稿防止
    $('form').disableOnSubmit();
    
    /* クッキー設定 */
    var cookie_options = { path: '/', expires: 14 };
    
    /* 共通関数 */
    //character変更時、characterとemotion欄更新、emotionリセット。
    function character_changed(){
        var character_to = $('#form select.character').children("option:selected").val();
        var emotions = $.characters[character_to]['emotions'];
        var select = $('#form select.emotion');
        select.empty();
        $.each(emotions, function(val, text) {
            select.append(
                $('<option></option>').val(val).html(text)
            );
        });
        var icon = $('#char-icon');
        icon.attr('class', 'char-icon');
        icon.addClass(character_to);
        var fullname = $('#form input[type=hidden][name=char_name]');
        fullname.val($.characters[character_to]['fullname']);
        $.cookie('character', character_to, cookie_options);
    }
    //emotion変更時、emotion更新。
    function emotion_changed(){
        var character_to = $('#form select.character').children("option:selected").val();
        var emotion_to = $('#form select.emotion').children("option:selected").val();
        var icon = $('#char-icon');
        icon.attr('class', 'char-icon');
        icon.addClass(character_to);
        icon.addClass(emotion_to);
        $.cookie('emotion', emotion_to, cookie_options);
    }

    /* 起動時の処理 */
    $('#form select.character').empty();
    $.each($.characters, function(id, character) {
        $('#form select.character').append(
            $('<option></option>').val(id).html(character['name'])
        );
    });
    
    if ($.cookie('character')){
        var selecter = '#form select.character option[value="' + $.cookie('character') + '"]'
        $(selecter).attr("selected","selected");
    }
    character_changed();
    if ($.cookie('emotion')){
        var selecter = '#form select.emotion option[value="' + $.cookie('emotion') + '"]'
        $(selecter).attr("selected","selected");
    }
    emotion_changed();
    
    if ($.cookie('sage') == 'true'){
        $('#form input[name=sage]').attr('checked', 'checked');
    }

    //初期化終了
    $('#form').toggle();
    
    /* 起動時以外の処理 */
    $('#form select.character').change(character_changed);
    
    $('#form select.emotion').change(emotion_changed);
    
    $('#form input[name=sage]').click(function(){
        $.cookie('sage', $(this).attr('checked'), cookie_options);
    });



















//末尾
});




