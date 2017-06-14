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
        print(url, data)
        async with self.session.post(url, data=data) as resp:
            ret = await resp.text(encoding='utf8')
            try:
                ret = json.loads(ret)
                if not ret.get('result'):
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
            print(self.host, self.port)
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
        print(ret)
        c.token = ret['token']
        c.refresh_token = ret['refresh_token']
        c.session_key = ret['session_key']
        await c.player_login()
        ret = await session.recv()
        ret = c.session.loads(ret)
        # c.session.close() 
        return c

    async def test_add_all_avatar(self):
        '''msg_id: 3002'''
        data = {}
        data['msg_id'] = 3002
        data['user_id'] = self.user_id
        data['session_key'] = self.session_key
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def test_add_item(self, item=None):
        '''msg_id: 3003'''
        if item is None:
            item = []
        data = {}
        data['msg_id'] = 3003
        data['user_id'] = self.user_id
        data['session_key'] = self.session_key
        data['item'] = json.dumps(item)
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def test_add_task(self):
        '''msg_id: 3004'''
        data = {}
        data['msg_id'] = 3004
        data['user_id'] = self.user_id
        data['session_key'] = self.session_key
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def login(self):
        '''msg_id: 10001'''
        data = {}
        data['msg_id'] = 10001
        data['user_id'] = self.user_id
        data['token'] = self.token
        data['refresh_token'] = self.refresh_token
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     self.token = ret['token']
        #     self.refresh_token = ret['refresh_token']
        #     self.session_key = ret['session_key']
        return ret

    async def player_login(self):
        '''msg_id: 10003'''
        data = {}
        data['msg_id'] = 10003
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(data)
        # if ret.get('result'):
        #     self.player_id = ret['player_id']
        #     self.player_info = ret['data']['player_info']
        #     self.package = ret['data']['package']
        #     self.cd_pool = ret['data']['player_cd_pool']

        return ret

    async def login_again(self):
        await self.login()
        await self.player_login()

    async def get_player(self):
        '''msg_id: 20001'''
        data = {}
        data['msg_id'] = 20001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            self.player_info['like'] = ret['like']
        return ret

    async def update_player(self, info=None):
        '''msg_id: 20003'''
        if info is None:
            info = {}
        data = {}
        data['msg_id'] = 20003
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['player_info'] = json.dumps(info)
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            if ret.get('name'):
                self.player_info['name'] = ret['name']
        return ret

    async def get_gam(self):
        '''msg_id: 20008'''
        data = {}
        data['msg_id'] = 20008
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def get_random_name(self):
        '''msg_id: 20009'''
        data = {}
        data['msg_id'] = 20009
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def buy_store_item(self, item_id, count=1):
        '''msg_id: 21002'''
        data = {}
        data['msg_id'] = 21002
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['count'] = count
        data['store_item_id'] = item_id
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def get_lottery_reward(self, lottery_id, ltype):
        '''msg_id: 21006'''
        data = {}
        data['msg_id'] = 21006
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['lottery_id'] = lottery_id
        data['ltype'] = ltype
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def enter_level(self, map_id):
        '''msg_id: 30001'''
        data = {}
        data['msg_id'] = 30001
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['map_id'] = map_id
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
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
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def avatar_compound(self, avatar_id):
        '''msg_id: 40006'''
        data = {}
        data['msg_id'] = 40006
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['avatar_id'] = avatar_id
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def avatar_evolution(self, avatar_id):
        '''msg_id: 40007'''
        data = {}
        data['msg_id'] = 40007
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['avatar_id'] = avatar_id
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def avatar_resolve(self, avatar_id):
        '''msg_id: 40008'''
        data = {}
        data['msg_id'] = 40008
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['avatar_id'] = json.dumps({avatar_id: 1})
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret

    async def avatar_enchant(self, avatar_id, index, count=1):
        '''msg_id: 40009'''
        data = {}
        data['msg_id'] = 40009
        data['session_key'] = self.session_key
        data['user_id'] = self.user_id
        data['avatar_id'] = avatar_id
        data['index'] = index
        ret = await self.session.post(self.url, data)
        if ret.get('result'):
            pass
        return ret




def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(GatewayClient.run())
    loop.close()


if __name__ == '__main__':
    main()
    # s = HttpSession()
    # print(s.session)
