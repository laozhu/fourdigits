# -*- coding: utf-8 -*-
from time import time
from hashlib import sha1
from flask import make_response
from lxml import etree
from . import kvdb, digits


# 微信消息文字模板
TEXT_TPL = """<xml>
<ToUserName><![CDATA[%s]]></ToUserName>
<FromUserName><![CDATA[%s]]></FromUserName>
<CreateTime>%s</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[%s]]></Content>
</xml>"""

# 创建KVDB对象
kv = kvdb.KVClient()


# 微信回调类
class WechatCallbackApi(object):

    # 初始化
    def __init__(self, token):
        self.token = token

    # 应用认证
    def auth(self, request):
        data = request.args
        echostr = data.get('echostr', '')
        signature = data.get('signature', '')
        timestamp = data.get('timestamp', '')
        nonce = data.get('nonce', '')
        token_list = [self.token, timestamp, nonce]
        token_list.sort()
        token_str = ''.join(token_list)
        token_str = sha1(token_str).hexdigest()
        if token_str == signature:
            return echostr
        return "auth fail"

    # 是否订阅事件
    def is_subscribe(self, msg):
        return msg['MsgType'] == 'event' and msg['Event'] == 'subscribe'

    # 是否取消订阅事件
    def is_unsubscribe(self, msg):
        return msg['MsgType'] == 'event' and msg['Event'] == 'unsubscribe'

    # 是否点击事件
    def is_click(self, msg):
        return msg['MsgType'] == 'event' and msg['Event'] == 'CLICK'

    # 是否特定命令
    def is_command(self, msg, command=None):
        if not command:
            return msg['MsgType'] == 'text'
        else:
            return msg['MsgType'] == 'text' and msg['Content'].strip().lower() == command

    # 是否合法请求
    def is_legal(self, request):
        try:
            child = etree.fromstring(request.data)
        except etree.ParseError:
            return False
        key_list = []
        need_list = ['ToUserName', 'FromUserName', 'CreateTime', 'MsgType']
        for item in child:
            key_list.append(item.tag)
        for key in need_list:
            if key not in key_list:
                return False
        return True

    # 初始化数据库
    def init_db(self, from_user_name):
        password = digits.choice()
        kv.set_multi(kvdb.KVDB_KEYS, [from_user_name, 0, 0, 0, 0.0, 0.0, password, '',], from_user_name)

    # 清理数据库
    def clean_db(self, from_user_name):
        for key in kv.getkeys_by_prefix(from_user_name):
            kv.delete(key)

    # 更新数据库（兼容老版本）
    def update_db(self, from_user_name):
        if kv.get(from_user_name):
            kv.delete(from_user_name)
            kv.delete(from_user_name + 'list')
            self.init_db(from_user_name)

    # 格式化猜数字提示信息
    def format_tips(self, tips):
        format_tips = ""
        n = 1
        for item in tips.split('-'):
            format_tips += u"第{n}次: {digit} -> {tip}\n".format(n=n, digit=item[0:4], tip=item[4:8])
            n = n + 1

        if n <= 5:
            emoji = '/::D'
        elif n == 6:
            emoji = '/::)'
        elif n == 7:
            emoji = '/:dig'
        elif n == 8:
            emoji = '/:@x'
        elif n == 9:
            emoji = '/:,@!'
        else:
            emoji = '/:!!!'

        format_tips += u"\n您已经猜过{n}次了... {emoji}".format(n=n-1, emoji=emoji)
        return format_tips

    # 获取猜数字次数
    def get_times(self, tips):
        return len(tips.split('-')) + 1

    def respond(self, request):

        # 字典化请求消息
        msg = respond_msg = {}
        for item in etree.fromstring(request.data):
            msg[item.tag] = item.text

        # 判断请求是否合法
        if self.is_legal(request):

            # 发送者和接收者
            from_user_name = msg['FromUserName']
            to_user_name = msg['ToUserName']

            # 处理关注请求
            if self.is_subscribe(msg):
                self.init_db(from_user_name)
                respond_msg = make_response(TEXT_TPL % (
                    from_user_name,
                    to_user_name,
                    str(int(time())),
                    u"欢迎关注微信猜数字游戏，直接回复数字开始游戏！",
                ))

            # 处理取消关注请求
            elif self.is_unsubscribe(msg):
                self.clean_db(from_user_name)

            # 是否为命令请求
            elif self.is_command(msg):

                # 老用户数据库清理
                self.update_db(from_user_name)

                # 如果命令请求是数字 - 2345
                if digits.check(msg['Content'].strip()):

                    content = digits.tips(
                        kv.get(from_user_name + '_digits'),
                        msg['Content'].strip(),
                    )

                    # 如果猜对了 - 2345
                    if content == '4A0B':
                        average_times = kv.get(from_user_name + '_average_times')
                        success = kv.get(from_user_name + '_success')
                        tips = kv.get(from_user_name + '_tips')
                        average_times = (average_times * success + self.get_times(tips)) / (success + 1)
                        times = kv.get(from_user_name + '_times') + 1
                        success = kv.get(from_user_name + '_success') + 1
                        success_rate = float(success) / times
                        password = digits.choice()
                        kv.set_multi(
                            ['times', 'success', 'success_rate', 'average_times', 'digits', 'tips'],
                            [times, success, success_rate, average_times, password, ''],
                            from_user_name,
                        )
                        content = u"恭喜您猜对了/:strong，新的数字已生成，继续挑战吧！"

                    # 如果没猜对 - 2345
                    else:
                        tip = msg['Content'].strip() + content
                        if not kv.get(from_user_name + '_tips'):
                            tips = tip
                        else:
                            tips = kv.get(from_user_name + '_tips') + '-' + tip
                        kv.set(from_user_name + '_tips', tips)

                # 命令 - 提示
                elif self.is_command(msg, command=u'提示') or self.is_command(msg, command='t'):
                    content = kv.get(from_user_name + '_tips')
                    if not content:
                        content = u"您尚未开始游戏 ..."
                    else:
                        content = self.format_tips(content)

                # 命令 - 重来
                elif self.is_command(msg, command=u'重来') or self.is_command(msg, command='r'):

                    # 中途放弃
                    if kv.get(from_user_name + '_tips'):
                        times = kv.get(from_user_name + '_times') + 1
                        success = kv.get(from_user_name + '_success')
                        failure = kv.get(from_user_name + '_failure') + 1
                        success_rate = float(success) / times
                        password = digits.choice()
                        kv.set_multi(
                            ['times', 'failure', 'success_rate', 'digits', 'tips'],
                            [times, failure, success_rate, password, ''],
                            from_user_name,
                        )
                        content = u"坚持是一种习惯，放弃也是，新的数字已生成，继续挑战吧！"

                    # 直接放弃
                    else:
                        content = u"还未尝试，怎能轻言放弃！"

                # 命令 - 数据
                elif self.is_command(msg, command=u'数据') or self.is_command(msg, command='d'):
                    success_rate = "%.2f%%" % (kv.get(from_user_name + '_success_rate') * 100)
                    average_times = "%.2f" % (kv.get(from_user_name + '_average_times'))
                    content = u"总次数: {times}\n胜场数: {success}\n败场数: {failure}\n成功率: {success_rate}\n场均值: {average_times}".format(
                        times = kv.get(from_user_name + '_times'),
                        success = kv.get(from_user_name + '_success'),
                        failure = kv.get(from_user_name + '_failure'),
                        success_rate = success_rate,
                        average_times = average_times,
                    )

                # 命令 - 帮助
                elif self.is_command(msg, command=u'帮助') or self.is_command(msg, command='h'):
                    content = u"帮助(h) -> 查看游戏帮助\n重来(r) -> 放弃本局，重新开始\n提示(t) -> 查看本局提示信息\n数据(d) -> 查看个人数据\n"
                    content += u'\n查看完整的 <a href="http://fourdigits.sinaapp.com/help">游戏帮助</a>'

                # 命令 - 格式不正确
                else:
                    content = u'您的命令格式不正确，遇到问题请查看完整的 <a href="http://fourdigits.sinaapp.com/help">游戏帮助</a>'

                respond_msg = make_response(TEXT_TPL % (
                    from_user_name,
                    to_user_name,
                    str(int(time())),
                    content,
                ))
            respond_msg.content_type = "application/xml"
            return respond_msg
        else:
            return "illegal request"