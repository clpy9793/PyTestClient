#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-06-12 10:52:31
# @Author  : Your Name (you@example.org)
# @Link    : http://example.org
# @Version : $Id$

import os
import time
import uuid
import random
import struct
import hashlib
import asyncio
import aiohttp
import binascii
import websockets
from aiohttp import ClientSession
from config import *
try:
    import ujson as json
except ImportError:
    import json


ST_INIT = 0
ST_LOGIN = 1

HEART_COIN = "IT0003"


class HttpSession(object):
    '''ClientSession'''

    def __init__(self, cookies=None, headers=None):
        if cookies is None:
            cookies = {}
        if headers is None:
            headers = {}
        self._session = None

    @property
    def session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def make_sign(self, key=None):
        '''时间戳签名'''
        if key is None:
            key = PACKAGE_KEY
        res = {}
        now = int(time.time())
        res['check_time_stamp'] = now
        res['check_sign'] = hashlib.md5("{0}{1}".format(now, key).encode('utf8')).hexdigest()
        return res

    async def post(self, url, data=None):
        if data is None:
            data = {}
        data.update(self.make_sign())
        async with self.session.post(url, data=data) as resp:
            ret = await resp.text(encoding='utf8')
            try:
                ret = json.loads(ret)
                if not ret.get('result'):
                    # pass
                    print('[ERROR]:\n{}\t{}'.format(ret.get('msg_id'), ret.get('error_code')))
            except Exception:
                pass
            finally:
                return ret

    async def get(self):
        pass

    def close(self):
        self._session.close()


class WebSocketSession(object):
    '''WebSocketSession'''

    def __init__(self, host, port, cookies=None, headers=None):
        if cookies is None:
            cookies = {}
        if headers is None:
            headers = {}
        self._session = None
        self.host = host
        self.port = port

    @property
    async def session(self):
        if self._session is None or self._session.state != 1:
            self._session = await websockets.connect('ws://{}:{}'.format(self.host, self.port))
        return self._session

    def make_sign(self, key=None):
        '''时间戳签名'''
        if key is None:
            key = PACKAGE_KEY
        res = {}
        now = int(time.time())
        res['check_time_stamp'] = now
        res['check_sign'] = hashlib.md5("{0}{1}".format(now, key).encode('utf8')).hexdigest()
        return res

    def dumps(self, param):
        '''ws封包'''
        EVENT_FLAG = 21586
        stream = []
        msg_id = param['msg_id']
        del param['msg_id']
        param.pop('msg_id', 0)
        param.pop('url', 0)
        data = json.dumps(param)
        # data = param
        data_stream = list(map(lambda x: ord(x), data))
        # key_start = random.randint(0, len(PACKAGE_KEY) - 1)
        # data_stream = list(msgpack.packb(data))
        # data_stream = list(map(lambda x: ord(x), list(msgpack.packb(data))))
        # data_stream = encrypt_data(data_stream, key_start, len(data_stream))
        length = len(data_stream) + 8
        stream.append(EVENT_FLAG & 0xff)
        stream.append(EVENT_FLAG >> 8)
        stream.append(length & 0xff)
        stream.append(length >> 8)
        stream.append(msg_id & 0xff)
        stream.append((msg_id >> 8) & 0xff)
        stream.append((msg_id >> 16) & 0xff)
        stream.append(msg_id >> 24)
        # stream.append(key_start & 0xff)
        # stream.append(key_start >> 8)
        stream.extend(data_stream)
        stream = list(map(lambda x: "{:02x}".format(ord(x) if isinstance(x, str) else x), stream))
        stream = "".join(stream)
        return stream

    def loads(self, data):
        data = binascii.unhexlify(data)
        ret = json.loads(data[8:].decode())
        return ret

    async def post(self, data=None):
        if data is None:
            return
        data = self.dumps(data)
        session = await self.session
        await session.send(data)
        # ret = await session.recv()
        # self.loads(ret)

    async def get(self):
        pass

    def close(self):
        self._session.close()


class AccountClient(object):
    '''获取账号, Token'''

    def __init__(self, host, port):
        '''初始化'''
        self.host = host
        self.port = port
        self.session = HttpSession()

    async def auth(self):
        '''msg_id:6001'''
        data = {}
        data['msg_id'] = 6001
        data['auth_type'] = 1
        data['user_name'] = str(uuid.uuid4().hex)
        url = 'http://{}:{}/auth'.format(ACCOUNT_HOST, ACCOUNT_PORT)
        ret = await self.session.post(url, data)
        if ret.get('result'):
            self.token = ret['token']
            self.refresh_token = ret['refresh_token']
            self.user_id = ret['user_id']
        else:
            print(ret)
        return ret


class GatewayClient(object):
    ''''''

    def __init__(self, data, session=None):
        ''''''
        if session is None:
            self.session = WebSocketSession(GATEWAY_HOST, GATEWAY_PORT)
        else:
            self.session = session
        self.token = data['token']
        self.refresh_token = data['refresh_token']
        self.user_id = data['user_id']
        self.session_key = None
        self.player_id = None
        self.player_info = None
        self.package = None
        self.state = 0
        self.is_listen = True
        self.kv = {}
        self.task_list = []
        self.wait_time = 0
        self.wait_count = 0

    @staticmethod
    async def run():

        ''''''
        c = AccountClient(ACCOUNT_HOST, ACCOUNT_PORT)
        ret = await c.auth()
        c.session.close()
        c = GatewayClient(ret)
        await c.login()
        session = await c.session.session
        ret = await session.recv()
        ret = c.session.loads(ret)
        c.token = ret['token']
        c.refresh_token = ret['refresh_token']
        c.session_key = ret['session_key']
        await c.player_login()
        ret = await session.recv()
        ret = c.session.loads(ret)
        # if ret.get('result'):
        c.player_id = ret['player_id']
        c.player_info = ret['data']['player_info']
        c.package = ret['data']['package']
        c.cd_pool = ret['data']['player_cd_pool']
        # await session.close()
        return c

    async def event_listen(self):
        '''处理服务端消息'''
        session = await self.session.session
        while True:
            try:    
                ret = await asyncio.wait_for(session.recv(), 5)
                # ret = await session.recv()
                ret = self.session.loads(ret)

                if ret.get('result'):
                    msg_id = ret['msg_id']
                    self.kv[msg_id] = ret
                    if msg_id == 10003:
                        self.player_id = ret['player_id']
                        self.player_info = ret['data']['player_info']
                        self.package = ret['data']['package']
                        self.cd_pool = ret['data']['player_cd_pool']                        
                else:
                    print('\n[ERROR]:\t', ret.get('msg_id'), ret.get('error_code'))
                    msg_id = ret.get('msg_id')                    
                    err_cd = ret.get("error_code")
                    if err_cd and err_cd != 500:
                        self.kv[msg_id] = ret
            except asyncio.TimeoutError:
                pass

    def pop(self, msg_id):
        self.kv.pop(msg_id, 0)

    def get_item(self, package, item_id, attr):
        '''查询背包'''
        try:
            if attr == 'count':
                return self.package[package][item_id][0]
            return 0
        except Exception:
            # import traceback
            # traceback.print_exc()
            return 0

    def set_item(self, package, item_id, attr, val):
        '''查询背包'''
        try:
            if attr == 'count':
                # self.package.setdefault(package, {}).setdefault(item_id, [])[0] = val
                self.package.setdefault(package, {})
                if item_id not in self.package[package]:
                    self.package[package][item_id] = [0]

                self.package[package][item_id][0] = val
            return True
        except Exception:
            import traceback
            print(self.package[package])
            traceback.print_exc()
            return False         

    async def wait_for(self, msg_id, timeout=200):
        t1 = time.time()
        for i in range(timeout):
            await asyncio.sleep(0.01)
            ret = self.kv.get(msg_id)
            if ret:
                self.kv.pop(msg_id, 0)
                t2 = time.time()
                self.wait_count += 1
                self.wait_time += int(t2 * 1000 - t1 * 1000)                
                # print('[RES]\n', 'msg_id:\t', msg_id, '\t', int(t2 * 1000 - t1 * 1000))
                # print('[AVG]\n', self.wait_time / float(self.wait_count))                
                return ret
        print('[INFO]:\t超时')
        # await asyncio.sleep(2)
        self.kv.pop(msg_id, 0)
        return None

    async def test_add_all_avatar(self):
        '''msg_id: 3002'''
        data = {}
        data['msg_id'] = 3002
        data['user_id'] = self.user_id
        data['session_key'] = self.session_key
        ret = await self.session.post(data)
        return ret

    async def test_add_item(self, item=None):
        '''msg_id: 3003'''
        if item is None:
            item = []
        data = {}
        data['msg_id'] = 3003
        data['user_id'] = self.user_id
        data['session_key'] = self.session_key
        data['item'] = item
        ret = await self.session.post(data)
        return ret

    async def test_add_task(self):
        '''msg_id: 3004'''
        data = {}
        data['msg_id'] = 3004
        data['user_id'] = self.user_id
        data['session_key'] = self.session_key
        ret = await self.session.post(data)
        return ret

    async def test_add_level(self):
        '''msg_id: 3006'''
        data = {}
        data['msg_id'] = 3006
        data['user_id'] = self.user_id
        data['session_key'] = self.session_key
        ret = await self.session.post(data)
        return ret        

    async def login(self):
        '''msg_id: 10001'''
        data = {}
        data['msg_id'] = 10001
        data['user_id'] = self.user_id
        data['token'] = self.token
        data['refresh_token'] = self.refresh_token
        ret = await self.session.post(data)
        return ret

    async def player_login(self):
        '''msg_id: 10003'''
        data = {}
        data['msg_id'] = 10003
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        return ret

    async def login_again(self):
        pass
        # await self.login()
        # await self.player_login()

    async def get_player(self):
        '''msg_id: 20001'''
        data = {}
        data['msg_id'] = 20001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     self.player_info['like'] = ret['like']
        return ret

    async def update_player(self, info=None):
        '''msg_id: 20003'''
        if info is None:
            info = {}
        data = {}
        data['msg_id'] = 20003
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['player_info'] = info
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     if ret.get('name'):
        #         self.player_info['name'] = ret['name']
        return ret

    async def get_gam(self):
        '''msg_id: 20008'''
        data = {}
        data['msg_id'] = 20008
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def get_random_name(self):
        '''msg_id: 20009'''
        data = {}
        data['msg_id'] = 20009
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def query_package_data(self, item):
        '''msg_id: 20011'''
        data = {}
        data['msg_id'] = 20011
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['item'] = item
        ret = await self.session.post(data)
        return ret

    async def buy_store_item(self, item_id, count=1):
        '''msg_id: 21002'''
        data = {}
        data['msg_id'] = 21002
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['count'] = count
        data['store_item_id'] = item_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def get_lottery_reward(self, lottery_id, ltype):
        '''msg_id: 21006'''
        data = {}
        data['msg_id'] = 21006
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['lottery_id'] = lottery_id
        data['type'] = ltype
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def enter_level(self, map_id="MA00101"):
        '''msg_id: 30001'''
        data = {}
        data['msg_id'] = 30001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['map_id'] = map_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def complete_level(self, map_id, score, coin):
        '''msg_id: 30002'''
        data = {}
        data['msg_id'] = 30002
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['map_id'] = map_id
        data['score'] = score
        data['coin'] = coin
        ret = await self.session.post(data)
        return ret

    async def use_avatar(self, avatar_id):
        '''
        msg_id: 40002
        使用装扮
        '''
        data = {}
        data['msg_id'] = 40002
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['id'] = avatar_id
        ret = await self.session.post(data)
        return ret

    async def avatar_compound(self, avatar_id):
        '''msg_id: 40006'''
        data = {}
        data['msg_id'] = 40006
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['avatar_id'] = avatar_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def avatar_evolution(self, avatar_id):
        '''msg_id: 40007'''
        data = {}
        data['msg_id'] = 40007
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['avatar_id'] = avatar_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def avatar_resolve(self, avatar_id, count=1):
        '''msg_id: 40008'''
        data = {}
        data['msg_id'] = 40008
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['avatar_id'] = {avatar_id: count}
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def avatar_enchant(self, avatar_id, index, count=1):
        '''msg_id: 40009'''
        data = {}
        data['msg_id'] = 40009
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['avatar_id'] = avatar_id
        data['index'] = index
        data['count'] = count
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def get_daily_task(self):
        '''msg_id: 60001'''
        data = {}
        data['msg_id'] = 60001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        return ret        

    async def get_daily_task_reward(self, task_id):
        '''msg_id: 60002'''
        data = {}
        data['msg_id'] = 60002
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['task_id'] = task_id
        ret = await self.session.post(data)
        return ret          

    async def get_daily_task_activity_reward(self, active):
        '''msg_id: 60003'''
        data = {}
        data['msg_id'] = 60003
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['active'] = active
        ret = await self.session.post(data)
        return ret   

    async def complete_task(self, task_id, debug=True):
        '''msg_id: 60005'''
        data = {}
        data['msg_id'] = 60005
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['id'] = task_id
        data['debug'] = debug
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def get_task_progress(self):
        '''msg_id: 60008'''
        data = {}
        data['msg_id'] = 60008
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        return ret

    async def start_guide(self, guide=None):
        '''msg_id: 60009'''
        if guide is None:
            guide = 'GU0001'
        data = {}
        data['msg_id'] = 60009
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['guide_id'] = guide
        ret = await self.session.post(data)
        return ret

    async def finish_guide(self, guide=None):
        '''msg_id: 60010'''
        if guide is None:
            guide = 'GU0001'
        data = {}
        data['msg_id'] = 60010
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['guide_id'] = guide
        ret = await self.session.post(data)
        return ret        

    async def get_friend_list(self):
        '''msg_id: 70001'''
        data = {}
        data['msg_id'] = 70001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def del_friend(self, friend_id):
        '''msg_id: 70002'''
        data = {}
        data['msg_id'] = 70002
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['friend_id'] = friend_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def add_friend(self, friend_id, channel=1):
        '''msg_id: 70003'''
        data = {}
        data['msg_id'] = 70003
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['player_id'] = friend_id
        data['type'] = channel
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def recommend_friend(self):
        '''msg_id: 70004'''
        data = {}
        data['msg_id'] = 70004
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def get_friend_highest_level(self):
        '''msg_id: 70007'''
        data = {}
        data['msg_id'] = 70007
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def friend_search_by_id(self, friend_id):
        '''msg_id: 70010'''
        data = {}
        data['msg_id'] = 70010
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['player_id'] = friend_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def get_apply_list(self):
        '''msg_id: 70013'''
        data = {}
        data['msg_id'] = 70013
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def agree_friend_apply(self, friend_id):
        '''msg_id: 70014'''
        data = {}
        data['msg_id'] = 70014
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['friend_id'] = friend_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def refuse_friend_apply(self, friend_id):
        '''msg_id: 70015'''
        data = {}
        data['msg_id'] = 70015
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['friend_id'] = friend_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret             

    async def get_friend_map_rank(self, map_id):
        '''msg_id: 71001'''
        data = {}
        data['msg_id'] = 71001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['map_id'] = map_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def get_map_rank(self, map_id):
        '''msg_id: 71002'''
        data = {}
        data['msg_id'] = 71002
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['map_id'] = map_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def set_like(self, friend_id):
        '''msg_id: 73001'''
        data = {}
        data['msg_id'] = 73001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['friend_id'] = friend_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def give_energy(self, friend_id):
        '''msg_id: 75001'''
        data = {}
        data['msg_id'] = 75001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['friend_id'] = friend_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def ask_energy(self, friend_id):
        '''msg_id: 75002'''
        data = {}
        data['msg_id'] = 75002
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['friend_id'] = friend_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret        

    async def get_energy(self):
        '''msg_id: 75003'''
        data = {}
        data['msg_id'] = 75003
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def get_mail_list(self):
        '''msg_id: 90001'''
        data = {}
        data['msg_id'] = 90001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def read_mail(self, mail_id):
        '''msg_id: 90004'''
        data = {}
        data['msg_id'] = 90004
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['mail_id'] = mail_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def get_mail_reward(self, mail_id):
        '''msg_id: 90005'''
        data = {}
        data['msg_id'] = 90005
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['mail_id'] = mail_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     pass
        return ret

    async def enter_chat_room(self, room_type, room_id):
        '''
        进入聊天室, 开始接收对应聊天室的消息推送
        msg_id: 100001
        '''
        data = {}
        data['msg_id'] = 100001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['type'] = room_type
        data['room_id'] = room_id
        ret = await self.session.post(data)
        return ret

    async def exit_chat_room(self, room_type, room_id):
        '''
        退出对应聊天室, 取消对应聊天室的消息推送
        msg_id: 100002
        '''
        data = {}
        data['msg_id'] = 100002
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['type'] = room_type
        data['room_id'] = room_id
        ret = await self.session.post(data)
        return ret

    async def send_message(self, room_type, room_id, msg, *, friend_id=None):
        '''
        发送消息
        msg_id: 100003
        '''
        data = {}
        data['msg_id'] = 100003
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['type'] = room_type
        data['room_id'] = room_id
        data['msg'] = msg
        if friend_id is not None:
            data['friend_id'] = friend_id
            data['type'] = 2
            data['room_id'] = 0
        if data['type'] == 0:
            data['room_id'] = 0
        ret = await self.session.post(data)
        return ret

    async def get_message(self, room_type, room_id, *, count=30, ts=None, friend_id=None):
        '''
        拉取聊天消息
        msg_id: 100004
        '''        
        data = {}
        data['msg_id'] = 100004
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['type'] = room_type
        data['room_id'] = room_id
        data['ts'] = ts
        data['count'] = count
        if friend_id is not None:
            data['friend_id'] = friend_id
            data['room_id'] = 0
            data['type'] = 2
        ret = await self.session.post(data)
        return ret

    async def push_message(self):
        '''
        服务端推送聊天消息
        msg_id: 100007
        '''        
        pass     

    async def open_test_switch(self):
        '''
        测试开关
        增加金币, 钻石, 能量
        '''
        pass
        # 添加能量
        item = ['currency', 'IT0020', 'count', 10000]
        self.pop(3003)
        ret = await self.test_add_item(item)
        ret = await self.wait_for(3003)

        # 金币
        item = ['currency', 'IT0011', 'count', 100000000]
        await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret['result'])

        # 钻石
        item = ['currency', 'IT0001', 'count', 100000000]
        ret = await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret['result']) 

        # PK币
        item = ['currency', 'IT0002', 'count', 100000000]
        ret = await self.test_add_item(item)
        ret = await self.wait_for(3003)

        # 爱心币
        item = ['currency', 'IT0003', 'count', 100000000]
        ret = await self.test_add_item(item)
        ret = await self.wait_for(3003)


    async def game_flow(self):
        '''模拟单线游戏'''
        # 增加体力

        # 进入游戏
        map_id = 'MA00101'
        self.pop(30001)
        await self.enter_level(map_id)
        ret = await self.wait_for(30001)
        if not ret or not ret['result']:
            return
        await asyncio.sleep(random.randint(2, 3))


        # 完成游戏
        self.pop(30002)
        await self.complete_level(map_id, 10000, 100)
        ret = await self.wait_for(30002)
        if not ret or not ret['result']:
            return 
        await asyncio.sleep(random.randint(2, 3))

    async def friend_flow(self):
        '''模拟好友社交'''
        pass

    async def store_flow(self):
        '''模拟商店行为'''
        # 随机一件物品购买
        pass

    async def chat_flow(self):
        '''模拟聊天行为'''
        # 世界聊天
        # 进入聊天室
        room_type = 0
        room_id = 0
        self.pop(100001)
        await self.enter_chat_room(room_type, room_id)
        ret = await self.wait_for(100001)
        if not ret['result']:
            return
        await asyncio.sleep(3)

        # 模拟聊天
        s = pd.Series(range(0, 15))
        count = int(s.sample(1, weights=list(range(15, 0, -1))))
        for i in range(count):
            self.pop(100003)
            await self.send_message(room_type, room_id, 'xxxxx')
            await asyncio.sleep(random.randint(1, 3))

        # 退出聊天室
        self.pop(100002)
        await self.exit_chat_room(room_type, room_id)

    async def daily_task_flow(self):
        '''
        模拟
        '''
        pass

    async def avatar_flow(self):
        '''模拟 Avatar 行为'''
        # 分解
        if 'avatar' not in self.package:
            return
        for k, v in self.package['avatar'].items():
            if v[0] == 0:
                continue
            self.pop(40008)
            await self.avatar_resolve(k)
            await asyncio.sleep(random.randint(1, 5))

        await asyncio.sleep(random.randint(3, 5))


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(GatewayClient.run())
    loop.close()


if __name__ == '__main__':
    main()
    # s = HttpSession()
    # print(s.session)
