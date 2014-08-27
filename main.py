# -*- coding: utf-8 -*-
from flask import Flask, request, render_template
from libs import wechat


wx = wechat.WechatCallbackApi('wechat')
app = Flask(__name__)
app.config['DEBUG'] = False


@app.route('/wx', methods=['GET', 'POST'])
def wechat():
    if request.method == 'GET':
        return wx.auth(request)
    elif request.method == 'POST':
        return wx.respond(request)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/help')
def help():
    return render_template('help.html')

@app.errorhandler(403)
def page_not_found(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def permission_forbidden(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500