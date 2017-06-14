#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-06-12 13:41:54
# @Author  : Your Name (you@example.org)
# @Link    : http://example.org
# @Version : $Id$

import os
import asyncio
import unittest
import pandas as pd
from client import *


class GA(unittest.TestCase):

    client = None

    @classmethod
    def setUpClass(cls):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(cls.start())

    @classmethod
    def tearDownClass(cls):
        cls.client.session.close()
        loop = asyncio.get_event_loop()
        loop.close()

    @classmethod
    async def start(cls, *args, **kwargs):
        cls.client = await GatewayClient.run()

    def setUp(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_set_up())

    def tearDown(self):
        pass

    def test_player(self):
        '''玩家信息'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_player())

    async def async_set_up(self):
        await self.client.login_again()

    async def async_player(self):
        ''''''
        # 点赞数
        ret = await self.client.get_player()
        self.assertEqual(self.client.player_info['like'], ret['like'])

        # 修改名字
        name = await self.client.get_random_name()
        name = name['name']
        self.assertNotEqual(name, self.client.player_info['name'])
        await self.client.update_player({'name': name})
        await self.client.login_again()
        self.assertEqual(name, self.client.player_info['name'])

    def test_store(self):
        '''商店'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_store())

    async def async_store(self):

        # 测试购买
        ignore_item = {"ST0021"}
        item = ['currency', 'IT0011', 'count', 100000000]
        await self.client.test_add_item(item)
        item = ['currency', 'IT0001', 'count', 100000000]
        await self.client.test_add_item(item)
        await self.client.login_again()
        df = pd.read_csv('../static/store.csv')
        for item_id in df.Id:
            if item_id in ignore_item:
                continue
            ret = await self.client.buy_store_item(item_id)
            self.assertTrue(ret['result'], item_id)

        # 测试抽奖
        df = pd.read_csv('../static/lottery.csv')
        for i in df.Id:
            for _ in range(5):
                ret = await self.client.get_lottery_reward(i, 1)
                self.assertTrue(ret['result'], (i, 1))
                ret = await self.client.get_lottery_reward(i, 2)
                self.assertTrue(ret['result'], (i, 2))

    def atest_level(self):
        '''关卡'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_level())

    async def async_level(self):

        # 测试正常游戏关卡流程
        # 添加能量
        item = ['item', 'IT0020', 'count', 10000]
        ret = await self.client.test_add_item(item)
        self.assertTrue(ret['result'])

        # 开启任务
        ret = await self.client.test_add_task()
        self.assertTrue(ret['result'])

        df = pd.read_csv('../static/level.csv')
        for i, v in enumerate(df.MapId):
            ret = await self.client.enter_level(v)
            self.assertTrue(ret['result'], v)

            ret = await self.client.complete_level(v, 10000, 100)
            self.assertTrue(ret['result'], v)
            print('[INFO]:  完成', v)
        self.client = await GatewayClient.run()

    def test_avatar(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_avatar())

    async def async_avatar(self):
        df = pd.read_csv('../static/avatar.csv')
        # 添加货币
        item = ['currency', 'IT0011', 'count', 100000000]
        await self.client.test_add_item(item)
        item = ['currency', 'IT0001', 'count', 100000000]
        await self.client.test_add_item(item)
        ret = await self.client.test_add_all_avatar()
        self.assertTrue(ret['result'])

        for i, v in enumerate(df.ID):

            # 组合
            blue = json.loads(df.Blueprint[i])
            if blue:
                ret = await self.client.avatar_compound(v)
                self.assertTrue(ret['result'], v)

            # 进化                
            evolution = json.loads(df.EvolutionForm[i])
            if evolution:
                ret = await self.client.avatar_evolution(v)
                self.assertTrue(ret['result'], v)

            # 附魔
            # EnchantItem
            enchant = json.loads(df.EnchantForm[i])
            if enchant:
                for index, av_id in enchant.items():
                    if av_id != v:
                        ret = await self.client.avatar_enchant(v, index)
                        self.assertTrue(ret['result'], v)            

                # 分解
            ret = await self.client.avatar_resolve(v)
            self.assertTrue(ret['result'], v)                   

if __name__ == '__main__':
    unittest.main()
