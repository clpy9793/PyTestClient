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
from contextlib import contextmanager
KV = {}


class GA(unittest.TestCase):

    client = None

    @classmethod
    def setUpClass(cls):
        pass
        # loop = asyncio.get_event_loop()
        # loop.run_until_complete(cls.start())

    @classmethod
    def tearDownClass(cls):
        pass
        # cls.client.session.close()
        # for i in cls.client.task_list:
        #     i.cancel()

    @classmethod
    async def start(cls, *args, **kwargs):
        cls.client = await GatewayClient.run()

    def setUp(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_set_up())
        print()

    def tearDown(self):
        self.client.session.close()
        for i in self.client.task_list:
            i.cancel()
        print()

    async def wait_for(self, msg_id, timeout=200):
        for i in range(timeout):
            await asyncio.sleep(0.01)
            ret = self.client.kv.get(msg_id)
            if ret:
                return ret
        return None

    def pop(self, msg_id):
        self.client.kv.pop(msg_id, 0)

    async def async_set_up(self):
        # await self.client.login_again()
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.client.event_listen())
        self.client.task_list.append(task)
        # await asyncio.sleep(0.1)

    # @unittest.skip('skip')
    def test_player(self):
        '''玩家信息'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_player())

    # @unittest.skip('skip')
    def test_store(self):
        '''商店'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_store())

    # @unittest.skip('skip')
    def test_level(self):
        '''关卡'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_level())

    # @unittest.skip('skip')
    def test_daily_task(self):
        '''每日任务'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_daily_task())

    # @unittest.skip('skip')
    def test_task(self):
        '''任务'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_task())

    # @unittest.skip("skip")
    def test_mail(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_mail())        

    # @unittest.skip("skip")
    def test_friend(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_friend())        

    async def async_player(self):
        ''''''
        # 点赞数
        self.pop(20001)
        await self.client.get_player()
        ret = await self.wait_for(20001)
        self.assertTrue(ret)
        self.assertEqual(self.client.player_info.get('like', 0), ret['like'])

        # 修改名字
        await self.client.get_random_name()
        self.pop(20009)
        ret = await self.wait_for(20009)
        name = ret['name']
        self.assertNotEqual(name, self.client.player_info['name'])
        self.pop(20003)
        await self.client.update_player({'name': name})
        ret = await self.wait_for(20003)
        self.pop(10003)
        await self.client.player_login()
        ret = await self.wait_for(10003)
        self.assertEqual(name, self.client.player_info['name'])

    async def async_store(self):

        # 测试购买
        ignore_item = {"ST0021"}
        item = ['currency', 'IT0011', 'count', 100000000]

        await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret)

        item = ['currency', 'IT0001', 'count', 100000000]
        ret = await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret)

        item = ['currency', 'IT0002', 'count', 100000000]
        ret = await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret)

        item = ['currency', 'IT0003', 'count', 100000000]
        ret = await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret)

        ret = await self.client.player_login()
        ret = await self.wait_for(10003)
        self.assertTrue(ret)

        df = pd.read_csv('../static/store.csv')
        for item_id in df.Id:
            if item_id in ignore_item:
                continue
            self.pop(21002)
            ret = await self.client.buy_store_item(item_id)
            ret = await self.wait_for(21002)
            self.assertTrue(ret, item_id)
            print('[INFO]:\tstore\titem_id\t', item_id)

        # 测试抽奖
        df = pd.read_csv('../static/lottery.csv')
        for i in df.Id:
            for _ in range(5):
                self.pop(21006)
                ret = await self.client.get_lottery_reward(i, 1)
                ret = await self.wait_for(21006)
                self.assertTrue(ret, (i, 1))

                # 验证抽奖获得
                drop = ret['data']
                items = {x[1]: x[-1] for x in drop}
                for item in drop:
                    self.pop(20011)
                    await self.client.query_package_data(item[:3])
                    ret = await self.client.wait_for(20011)
                    self.assertTrue(ret)
                    val = self.client.get_item(*item[:3]) + items[item[1]]
                    self.assertEqual(val, ret['item'][-1], items)
                    self.client.set_item(*ret['item'])

                self.pop(21006)
                ret = await self.client.get_lottery_reward(i, 2)
                ret = await self.wait_for(21006)
                self.assertTrue(ret, (i, 2))

                drop = ret['data']
                items = {x[1]: x[-1] for x in drop}
                for item in drop:
                    self.pop(20011)
                    await self.client.query_package_data(item[:3])
                    ret = await self.client.wait_for(20011)
                    self.assertTrue(ret)
                    val = self.client.get_item(*item[:3]) + items[item[1]]
                    self.assertEqual(val, ret['item'][-1], items)
                    self.client.set_item(*ret['item'])                

    async def async_level(self):

        # 测试正常游戏关卡流程
        # 添加能量
        item = ['item', 'IT0020', 'count', 10000]
        self.pop(3003)
        ret = await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret)

        # 开启任务
        self.pop(3004)
        ret = await self.client.test_add_task()
        ret = await self.wait_for(3004)
        self.assertTrue(ret)

        df = pd.read_csv('../static/level.csv')
        for i, v in enumerate(df.MapId):
            self.pop(30001)
            ret = await self.client.enter_level(v)
            ret = await self.wait_for(30001)
            self.assertTrue(ret, v)

            # 查询过关前获得数量
            drop = ret['drop']
            query = []
            for item in ret['drop']:
                self.pop(20011)
                await self.client.query_package_data(item[:3])
                ret = await self.client.wait_for(20011)
                self.assertTrue(ret)
                tmp = ret['item']
                tmp[-1] += item[-1]
                query.append(tmp)


            query = {i[1]: i[-1] for i in query}

            self.pop(30002)
            ret = await self.client.complete_level(v, 10000, 100)
            ret = await self.wait_for(30002)
            self.assertTrue(ret, v)

            # 检验过关后获得道具数量
            for item in drop:
                self.pop(20011)
                await self.client.query_package_data(item[:3])
                ret = await self.client.wait_for(20011)
                self.assertTrue(ret['item'][-1], query[item[1]])
                print('[INFO]:\t', query[item[1]], '', ret['item'][-1])

            print('[INFO]:  完成', v)
        # self.client = await GatewayClient.run()

    async def async_avatar(self):
        df = pd.read_csv('../static/avatar.csv')
        # 添加货币
        item = ['currency', 'IT0011', 'count', 100000000]
        self.pop(3003)
        await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret)

        item = ['currency', 'IT0001', 'count', 100000000]
        self.pop(3003)
        await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret)

        self.pop(3002)
        ret = await self.client.test_add_all_avatar()
        ret = await self.wait_for(3002)
        self.assertTrue(ret)

        compond_list = []
        enchant_list = []
        evolution_list = []
        for i, v in enumerate(df.ID):

            # 组合
            blue = json.loads(df.Blueprint[i])
            if blue:
                self.pop(40006)
                ret = await self.client.avatar_compound(v)
                ret = await self.wait_for(40006)
                self.assertTrue(ret['result'], v)
                print('[INFO]: 组合 ', v)

            # 进化
            evolution = json.loads(df.EvolutionForm[i])
            if evolution:
                self.pop(40007)
                ret = await self.client.avatar_evolution(v)
                ret = await self.wait_for(40007)
                self.assertTrue(ret['result'], v)
                print('[INFO]: 进化 ', v)

            # 附魔
            # EnchantItem
            enchant = json.loads(df.EnchantForm[i])
            if enchant:
                for index, av_id in enchant.items():
                    if av_id != v:
                        self.pop(40009)
                        ret = await self.client.avatar_enchant(v, index)
                        ret = await self.wait_for(40009)
                        self.assertTrue(ret['result'], v)
                        print('[INFO]: 附魔 ', v)
                # 分解
            self.pop(40008)
            ret = await self.client.avatar_resolve(v)
            ret = await self.wait_for(40008)
            self.assertTrue(ret['result'], v)
            print('[INFO]: 分解 ', v)

    async def async_daily_task(self):
        self.client.pop(60001)
        await self.client.get_daily_task()
        ret = await self.client.wait_for(60001)
        self.assertTrue(ret)

    async def async_task(self):
        while True:
            self.pop(60008)
            ret = await self.client.get_task_progress()
            ret = await self.wait_for(60008)
            self.assertTrue(ret)

            if ret['progress']:
                for task_id in ret['progress'].keys():
                    print("[INFO]:\ttask_id\t", task_id)
                    self.pop(60005)
                    ret = await self.client.complete_task(task_id)
                    ret = await self.wait_for(60005)
                    self.assertTrue(ret)
            else:
                print(ret)
                break
        pass

    async def async_friend(self):

        # 测试推荐好友
        self.pop(70004)
        await self.client.recommend_friend()
        ret = await self.wait_for(70004)
        self.assertTrue(ret)
        li = ret['data']
        for i in li:
            if i[-1]:
                self.pop(70003)
                await self.client.add_friend(i[0])
                ret = await self.wait_for(70003)
                self.assertTrue(ret)

        # 测试推荐好友的申请状态
        self.pop(70004)
        await self.client.recommend_friend()
        ret = await self.wait_for(70004)
        self.assertTrue(ret)
        li = ret['data']
        for i in li:
            self.assertFalse(i[-1])

        # 添加好友
        c = await GatewayClient.run()
        loop = asyncio.get_event_loop()
        task = loop.create_task(c.event_listen())
        c.task_list.append(task)
        friend_id = c.player_id
        self.pop(70003)
        await self.client.add_friend(friend_id)
        ret = await self.wait_for(70003)
        self.assertTrue(ret)

        # 同意申请
        c.pop(70013)
        await c.get_apply_list()
        ret = await c.wait_for(70013)
        self.assertTrue(ret)

        li = ret['data']
        for i in li:
            c.pop(70014)
            await c.agree_friend_apply(i[0])
            ret = await c.wait_for(70014)
            self.assertTrue(ret)

        # 好友列表
        self.client.pop(70001)
        await self.client.get_friend_list()
        ret = await self.client.wait_for(70001)
        self.assertTrue(ret)
        li = {i[0] for i in ret['friend_list']}
        self.assertIn(c.player_id, li)

        # 点赞
        self.client.pop(73001)
        await self.client.set_like(c.player_id)
        ret = await self.client.wait_for(73001)
        self.assertTrue(ret)

        # 给予体力
        self.client.pop(75001)
        await self.client.give_energy(c.player_id)
        ret = await self.client.wait_for(75001)
        self.assertTrue(ret)

        # 领取体力
        c.pop(75003)
        await c.get_energy()
        ret = await c.wait_for(75003)
        self.assertEqual(ret['count'], 1)

        # 索要
        self.client.pop(75002)
        await self.client.ask_energy(c.player_id)
        ret = await self.client.wait_for(75002)
        self.assertTrue(ret)

        # 回赠
        self.client.pop(75003)
        await self.client.get_energy()
        ret = await self.client.wait_for(75003)
        self.assertTrue(ret)

        c.pop(75001)
        await c.give_energy(self.client.player_id)
        ret = await c.wait_for(75001)
        self.assertTrue(ret)

        self.client.pop(75003)
        await self.client.get_energy()
        ret = await self.client.wait_for(75003)
        self.assertEqual(ret['count'], 1)

        # 删除好友

        c.pop(70001)
        await c.get_friend_list()
        ret = await c.wait_for(70001)
        li = ret['friend_list']
        for i in li:
            c.pop(70002)
            await c.del_friend(i[0])
            ret = await c.wait_for(70002)
            self.assertTrue(ret)

        self.client.pop(70001)
        await self.client.get_friend_list()
        ret = await self.client.wait_for(70001)
        self.assertFalse(ret['friend_list'])

        # 拒绝申请
        self.client.pop(70003)
        await self.client.add_friend(c.player_id)
        ret = await self.client.wait_for(70003)
        self.assertTrue(ret)

        c.pop(70013)
        await c.get_apply_list()
        ret = await c.wait_for(70013)
        self.assertTrue(ret)
        li = ret['data']
        self.assertIn(self.client.player_id, [i[0] for i in li])

        c.pop(70015)
        ret = await c.refuse_friend_apply(self.client.player_id)
        ret = await c.wait_for(70015)
        self.assertTrue(ret)

        c.pop(70013)
        await c.get_apply_list()
        ret = await c.wait_for(70013)
        self.assertTrue(ret)
        li = ret['data']
        self.assertNotIn(self.client.player_id, [i[0] for i in li])


        # 关闭消息处理
        for i in c.task_list:
            i.cancel()

    async def async_mail(self):
        # 邮件阅读
        self.client.pop(90001)
        await self.client.get_mail_list()
        ret = await self.client.wait_for(90001)
        self.assertTrue(ret)

        for k, v in ret['data'].items():
            if not v['isRead']:
                # print(k)
                self.client.pop(90004)
                await self.client.read_mail(int(k))
                ret = await self.client.wait_for(90004)
                self.assertTrue(ret)

        self.client.pop(90001)
        await self.client.get_mail_list()
        ret = await self.client.wait_for(90001)
        self.assertTrue(ret)
        for k, v in ret['data'].items():
            if v['isRead']:
                self.assertTrue(v['items'])

                self.client.pop(90005)
                await self.client.get_mail_reward(int(k))
                ret = await self.client.wait_for(90005)
                self.assertTrue(ret)


if __name__ == '__main__':
    unittest.main()
