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
from collections import defaultdict
from contextlib import contextmanager
try:
    import ujson as json
except ImportError:
    import json

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

    # @unittest.skip("skip")
    def test_avatar(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_avatar())

    # @unittest.skip("skip")
    def test_chat_room(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_chat_room())

    @unittest.skip("skip")
    def test_drop(self):
        '''drop掉落概率测试'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_drop())        

    # @unittest.skip('skip')
    def test_guide(self):
        '''引导'''
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_guide())

    async def async_guide(self):
        self.client.pop(60009)
        await self.client.start_guide()
        ret = await self.client.wait_for(60009)
        self.assertTrue(ret['result'])

        self.client.pop(60010)
        await self.client.finish_guide()
        ret = await self.client.wait_for(60010)
        self.assertTrue(ret['result'])

        self.client.pop(60009)
        await self.client.start_guide()
        ret = await self.client.wait_for(60009)
        self.assertEqual(ret['error_code'], 60015)

        self.client.pop(60009)
        await self.client.start_guide('GGGGG')
        ret = await self.client.wait_for(60009)
        self.assertEqual(ret['error_code'], 60014)



    async def async_player(self):
        ''''''
        # 点赞数
        self.pop(20001)
        await self.client.get_player()
        ret = await self.wait_for(20001)
        self.assertTrue(ret['result'])
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
        self.assertTrue(ret['result'])

        item = ['currency', 'IT0001', 'count', 100000000]
        ret = await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret['result'])

        item = ['currency', 'IT0002', 'count', 100000000]
        ret = await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret['result'])

        item = ['currency', 'IT0003', 'count', 100000000]
        ret = await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret['result'])

        ret = await self.client.player_login()
        ret = await self.wait_for(10003)
        self.assertTrue(ret['result'])

        # # 测试商品购买
        df = pd.read_csv('../static/store.csv')
        for i, item_id in enumerate(df.Id):
            if item_id in ignore_item:
                continue
            lock = json.loads(df.Lock[i])
            if lock:
                # 解锁条件
                for item in lock:
                    self.client.pop(3003)
                    await self.client.test_add_item(item)
                    ret = await self.wait_for(3003)
                    self.assertTrue(ret['result'])

            self.pop(21002)
            ret = await self.client.buy_store_item(item_id)
            ret = await self.wait_for(21002)
            self.assertTrue(ret['result'], item_id)
            print('[INFO]:\tstore\titem_id\t', item_id)

        # 重新登录
        self.client.pop(10003)
        await self.client.player_login()
        ret = await self.client.wait_for(10003)
        self.assertTrue(ret)

        # 测试抽奖
        df = pd.read_csv('../static/lottery.csv')
        for i in df.Id:
            for _ in range(5):
                # 单抽
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
                    self.assertTrue(ret['result'])
                    val = self.client.get_item(*item[:3]) + items[item[1]]                    
                    self.assertEqual(val, ret['item'][-1], items)
                    r = self.client.set_item(*ret['item'])
                    self.assertTrue(r)

                # 十连
                self.pop(21006)
                ret = await self.client.get_lottery_reward(i, 2)
                ret = await self.wait_for(21006)
                self.assertTrue(ret['result'], (i, 2))
                drop = ret['data']
                items = {x[1]: x[-1] for x in drop}
                for item in drop:
                    self.pop(20011)
                    await self.client.query_package_data(item[:3])
                    ret = await self.client.wait_for(20011)
                    self.assertTrue(ret['result'])
                    val = self.client.get_item(*item[:3]) + items[item[1]]
                    self.assertEqual(val, ret['item'][-1], (item))
                    r = self.client.set_item(*ret['item'])
                    self.assertTrue(r)

    async def async_level(self):

        # 测试正常游戏关卡流程
        # 添加能量
        item = ['currency', 'IT0020', 'count', 10000]
        self.pop(3003)
        ret = await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret['result'])

        # 开启任务
        self.pop(3004)
        ret = await self.client.test_add_task()
        ret = await self.wait_for(3004)
        self.assertTrue(ret['result'])

        df = pd.read_csv('../static/level.csv')
        for i, v in enumerate(df.MapId):
            TargetCount = sum(json.loads(df.TargetCount[i]))
            goal_score = int(TargetCount * 1000)
            self.pop(30001)
            ret = await self.client.enter_level(v)
            ret = await self.wait_for(30001)
            self.assertTrue(ret['result'], v)

            # 查询过关前获得数量
            drop = ret['drop']
            query = []
            for item in ret['drop']:
                self.pop(20011)
                await self.client.query_package_data(item[:3])
                ret = await self.client.wait_for(20011)
                self.assertTrue(ret['result'])
                tmp = ret['item']
                tmp[-1] += item[-1]
                query.append(tmp)

            query = {i[1]: i[-1] for i in query}

            self.pop(30002)
            ret = await self.client.complete_level(v, goal_score, 100)
            ret = await self.wait_for(30002)
            self.assertTrue(ret['result'], v)
            self.assertIn('new_record', ret, v)

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
        self.assertTrue(ret['result'])

        item = ['currency', 'IT0001', 'count', 100000000]
        self.pop(3003)
        await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret['result'])

        self.pop(3002)
        ret = await self.client.test_add_all_avatar()
        ret = await self.wait_for(3002)
        self.assertTrue(ret['result'])

        compond_list = []
        enchant_list = []
        evolution_list = []
        for i, v in enumerate(df.ID):

            # 制作
            blue = json.loads(df.Blueprint[i])
            if blue:
                self.pop(40006)
                ret = await self.client.avatar_compound(v)
                ret = await self.wait_for(40006)
                self.assertTrue(ret['result'], v)
                print('[INFO]: 组合 ', v)

            # 进阶
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

            # 使用装扮
            self.client.pop(40002)
            await self.client.use_avatar(v)
            ret = await self.wait_for(40002)
            self.assertTrue(ret['result'])

    async def async_daily_task(self):
        # 初始化
        df = pd.read_csv('../static/daily.csv')
        kv = pd.read_csv('../static/kv.csv')
        active_gift = None
        for i, v in enumerate(kv.key):
            if v == 'active_gift':
                active_gift = eval(kv.loc[i, 'value'])
                break
        self.assertTrue(active_gift)
        active_gift = {int(i): v for i, v in active_gift}

        dr = {v: i for i, v in enumerate(df.ID)}
        actives = 0
        await self.add_coin()

        # 每日任务列表
        self.client.pop(60001)
        await self.client.get_daily_task()
        ret = await self.client.wait_for(60001)
        self.assertTrue(ret['result'])
        for k, v in ret['List'].items():
            self.assertEqual(v['plan'], 0, k)
            self.assertFalse(v['isFinish'], k)
            self.assertIn(k, dr)
            # print(k, v)

        # 完成每日任务
        for k, v in dr.items():
            count = await self.run_task(k, dr, df)
            actives += count

        for i in active_gift.keys():
            active = int(i)
            if active <= actives:
                # 领取活跃度宝箱
                self.pop(60003)
                await self.client.get_daily_task_activity_reward(active)
                ret = await self.client.wait_for(60003)
                self.assertTrue(ret['result'])

                # 不可重复领奖
                self.pop(60003)
                await self.client.get_daily_task_activity_reward(active)
                ret = await self.client.wait_for(60003)
                self.assertEqual(ret['error_code'], 60004)
        # print(actives)

    async def run_task(self, task_id, dr, df):
        '''进行每日任务'''
        index = dr[task_id]
        cond = json.loads(df.loc[index, 'Cond'])
        if not cond:
            return 0
        dtype = cond[0][1]
        count = cond[0][-1]
        active = int(df.loc[index, 'Active'])
        if dtype == 'dr_wish':
            # 完成
            for _ in range(count):
                self.client.pop(21006)
                await self.client.get_lottery_reward('LY0001', 1)
                ret = await self.client.wait_for(21006)
                self.assertTrue(ret['result'])
        elif dtype == 'dr_level_win':
            for _ in range(count):
                self.client.pop(30001)
                await self.client.enter_level('MA00101')
                ret = await self.client.wait_for(30001)
                self.assertTrue(ret['result'])

                self.client.pop(30002)
                await self.client.complete_level('MA00101', 9000, 100)
                ret = await self.client.wait_for(30002)
                self.assertTrue(ret['result'])

        elif dtype == 'dr_level_times':
            for _ in range(count):
                self.client.pop(30001)
                await self.client.enter_level('MA00101')
                ret = await self.client.wait_for(30001)
                self.assertTrue(ret['result'])

                self.client.pop(30002)
                await self.client.complete_level('MA00101', 5000, 100)
                ret = await self.client.wait_for(30002)
                self.assertTrue(ret['result'])
        elif dtype == 'dr_shop':
            for _ in range(1):
                self.client.pop(21002)
                await self.client.buy_store_item('ST10301', count)
                ret = await self.client.wait_for(21002)
                self.assertTrue(ret['result'])
                # AV010001
        elif dtype == 'dr_enc':
            for _ in range(1):
                self.client.pop(40009)
                await self.client.avatar_enchant('AV010001', '0', count)
                ret = await self.client.wait_for(40009)
                self.assertTrue(ret['result'])
        elif dtype == 'dr_com':
            for _ in range(count):
                self.client.pop(40006)
                await self.client.avatar_compound('AV010006')
                ret = await self.client.wait_for(40006)
                self.assertTrue(ret['result'])
        elif dtype == 'dr_res':
            for _ in range(count):
                self.client.pop(40008)
                await self.client.avatar_resolve('AV010006')
                ret = await self.client.wait_for(40008)
                self.assertTrue(ret['result'])
        elif dtype == 'dr_pk_win':
            return 0
        elif dtype == 'dr_pk_times':
            return 0
        elif dtype == 'dr_share':
            return 0
        elif dtype == 'dr_friend':
            await self.async_add_friend(count)
        elif dtype == 'dr_friend_like':
            await self.async_add_friend(count)
            # return 0
        elif dtype == 'dr_mouth':
            return 0
        # 领取任务奖励
        self.pop(60002)
        await self.client.get_daily_task_reward(task_id)
        ret = await self.client.wait_for(60002)
        self.assertTrue(ret['result'])

        # 不可重复领奖
        self.pop(60002)
        await self.client.get_daily_task_reward(task_id)
        ret = await self.client.wait_for(60002)
        self.assertEqual(ret['error_code'], 60003)
        return active

    async def async_add_friend(self, count):
        '''增加好友'''
        self.client.pop(70001)
        await self.client.get_friend_list()
        ret = await self.client.wait_for(70001)
        fcount = len(ret['friend_list'])
        clients = []
        tl = []
        for i in range(count):
            c = await GatewayClient.run()
            clients.append(c)
            loop = asyncio.get_event_loop()
            tl.append(loop.create_task(c.event_listen()))
        # clients = [await GatewayClient.run() for _ in range(count)]
        for c in clients:
            self.pop(70003)
            await self.client.add_friend(c.player_id)
            ret = await self.client.wait_for(70003)
            self.assertTrue(ret['result'])

            c.pop(70014)
            await c.agree_friend_apply(self.client.player_id)
            ret = await c.wait_for(70014)
            self.assertTrue(ret['result'])

            # 点赞
            self.client.pop(73001)
            await self.client.set_like(c.player_id)
            ret = await self.client.wait_for(73001)
            self.assertTrue(ret['result'])

            # 给予能量
            self.client.pop(75001)
            await self.client.give_energy(c.player_id)
            ret = await self.client.wait_for(75001)
            self.assertTrue(ret['result'])

        # 取消任务
        for i in tl:
            i.cancel()

        self.pop(70001)
        await self.client.get_friend_list()
        ret = await self.client.wait_for(70001)
        self.assertEqual(len(ret['friend_list']), fcount + count)

    async def add_coin(self):
        '''添加货币'''
        self.pop(3002)
        await self.client.test_add_all_avatar()
        ret = await self.wait_for(3002)
        self.assertTrue(ret['result'])

        item = ['currency', 'IT0011', 'count', 100000000]
        self.pop(3003)
        await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret['result'])

        item = ['currency', 'IT0001', 'count', 100000000]
        self.pop(3003)
        await self.client.test_add_item(item)
        ret = await self.wait_for(3003)
        self.assertTrue(ret['result'])

    async def async_task(self):
        while True:
            self.pop(60008)
            ret = await self.client.get_task_progress()
            ret = await self.wait_for(60008)
            self.assertTrue(ret['result'])
            df = pd.read_csv('../static/task.csv')
            task_list = {v: i for i, v in enumerate(df.ID)}
            if ret['progress']:
                for task_id in ret['progress'].keys():
                    print("[INFO]:\ttask_id\t", task_id)
                    # 收集物品
                    gather_list = json.loads(df.GatherList[task_list[task_id]])
                    for item in gather_list:
                        count = item[-2] + 1000
                        self.client.pop(3003)
                        args = item[:3]
                        args.extend([count])
                        await self.client.test_add_item(args)
                        ret = await self.client.wait_for(3003)
                        self.assertTrue(ret['result'])
                    
                    self.pop(60005)
                    ret = await self.client.complete_task(task_id)
                    ret = await self.wait_for(60005)
                    self.assertTrue(ret['result'])
            else:
                print(ret)
                break
        pass

    async def async_friend(self):

        # 测试推荐好友
        self.pop(70004)
        await self.client.recommend_friend()
        ret = await self.wait_for(70004)
        self.assertTrue(ret['result'])
        li = ret['data']
        for i in li:
            if i[-1]:
                self.pop(70003)
                await self.client.add_friend(i[0])
                ret = await self.wait_for(70003)
                self.assertTrue(ret['result'])

        # 测试推荐好友的申请状态
        self.pop(70004)
        await self.client.recommend_friend()
        ret = await self.wait_for(70004)
        self.assertTrue(ret['result'])
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
        self.assertTrue(ret['result'])

        # 同意申请
        c.pop(70013)
        await c.get_apply_list()
        ret = await c.wait_for(70013)
        self.assertTrue(ret['result'])

        li = ret['data']
        for i in li:
            c.pop(70014)
            await c.agree_friend_apply(i[0])
            ret = await c.wait_for(70014)
            self.assertTrue(ret['result'])

        # 好友列表
        self.client.pop(70001)
        await self.client.get_friend_list()
        ret = await self.client.wait_for(70001)
        self.assertTrue(ret['result'])
        li = {i[0] for i in ret['friend_list']}
        self.assertIn(c.player_id, li)

        # 点赞
        self.client.pop(73001)
        await self.client.set_like(c.player_id)
        ret = await self.client.wait_for(73001)
        self.assertTrue(ret['result'])

        # 给予体力
        self.client.pop(75001)
        await self.client.give_energy(c.player_id)
        ret = await self.client.wait_for(75001)
        self.assertTrue(ret['result'])

        # 领取体力
        c.pop(75003)
        await c.get_energy()
        ret = await c.wait_for(75003)
        self.assertEqual(ret['count'], 1)

        # 索要
        self.client.pop(75002)
        await self.client.ask_energy(c.player_id)
        ret = await self.client.wait_for(75002)
        self.assertTrue(ret['result'])

        # 回赠
        self.client.pop(75003)
        await self.client.get_energy()
        ret = await self.client.wait_for(75003)
        self.assertTrue(ret['result'])

        c.pop(75001)
        await c.give_energy(self.client.player_id)
        ret = await c.wait_for(75001)
        self.assertTrue(ret['result'])

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
            self.assertTrue(ret['result'])

        self.client.pop(70001)
        await self.client.get_friend_list()
        ret = await self.client.wait_for(70001)
        self.assertFalse(ret['friend_list'])

        # 拒绝申请
        self.client.pop(70003)
        await self.client.add_friend(c.player_id)
        ret = await self.client.wait_for(70003)
        self.assertTrue(ret['result'])

        c.pop(70013)
        await c.get_apply_list()
        ret = await c.wait_for(70013)
        self.assertTrue(ret['result'])
        li = ret['data']
        self.assertIn(self.client.player_id, [i[0] for i in li])

        c.pop(70015)
        ret = await c.refuse_friend_apply(self.client.player_id)
        ret = await c.wait_for(70015)
        self.assertTrue(ret['result'])

        c.pop(70013)
        await c.get_apply_list()
        ret = await c.wait_for(70013)
        self.assertTrue(ret['result'])
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
        self.assertTrue(ret['result'])

        for k, v in ret['data'].items():
            if not v['isRead']:
                # print(k)
                self.client.pop(90004)
                await self.client.read_mail(int(k))
                ret = await self.client.wait_for(90004)
                self.assertTrue(ret['result'])

        self.client.pop(90001)
        await self.client.get_mail_list()
        ret = await self.client.wait_for(90001)
        self.assertTrue(ret['result'])
        for k, v in ret['data'].items():
            if v['isRead']:
                self.assertTrue(v['items'])

                self.client.pop(90005)
                await self.client.get_mail_reward(int(k))
                ret = await self.client.wait_for(90005)
                self.assertTrue(ret['result'])

    async def async_drop(self):
        '''测试概率'''
        return
        item = ['item', 'IT0020', 'count', 1000000]
        self.client.pop(3003)
        await self.client.test_add_item(item)
        ret = await self.client.wait_for(3003)
        self.assertTrue(ret['result'])

        self.client.pop(3004)
        await self.client.test_add_task()
        ret = await self.client.wait_for(3004)
        self.assertTrue(ret['result'])

        self.client.pop(3006)
        await self.client.test_add_level()
        ret = await self.client.wait_for(3006)
        self.assertTrue(ret['result'])

        maps = ['MA01208', 'MA01211', 'MA01215']

        for map_id in maps:
            drops = defaultdict(int)
            for _ in range(1000):
                self.client.pop(30001)
                await self.client.enter_level(map_id)
                ret = await self.client.wait_for(30001)
                self.assertTrue(ret['result'])
                for item in ret['drop']:
                    drops[item[1]] += item[-1]
            print('\n\n')
            print(map_id, '\n')
            for k, v in drops.items():
                print('\t', k, '\t', v)

    async def async_chat_room(self):
        '''
        测试聊天室
        '''
        ts = time.time()
        # 临时玩家
        c = await GatewayClient.run()
        loop = asyncio.get_event_loop()
        task = loop.create_task(c.event_listen())
        c.task_list.append(task)

        # 世界聊天
        room_type, room_id = 0, 0

        # 进入聊天室之前, 不可发送消息
        self.client.pop(100003)
        await self.client.send_message(room_type, room_id, '1')
        ret = await self.client.wait_for(100003)
        self.assertFalse(ret['result'])
        self.assertEqual(ret['error_code'], 100001)

        # 进入聊天室
        self.client.pop(100001)

        await self.client.enter_chat_room(room_type, room_id)
        ret = await self.client.wait_for(100001)
        self.assertTrue(ret['result'])

        c.pop(100001)
        await c.enter_chat_room(room_type, room_id)
        ret = await c.wait_for(100001)
        self.assertTrue(ret['result'])

        # 发送消息, 其他人可接收到推送
        self.client.pop(100003)
        c.pop(100007)
        await self.client.send_message(room_type, room_id, '1')
        ret = await self.client.wait_for(100003)
        self.assertTrue(ret['result'])

        ret = await c.wait_for(100007)
        self.assertTrue(ret, c.player_id)
        self.assertEqual(ret['msg'], '1')

        # 发送消息, 其他人可接收到推送
        c.pop(100003)
        self.client.pop(100007)
        await c.send_message(room_type, room_id, '2')
        ret = await c.wait_for(100003)
        self.assertTrue(ret['result'])

        ret = await self.client.wait_for(100007)
        self.assertTrue(ret, self.client.player_id)
        self.assertEqual(ret['msg'], '2')

        # 退出世界聊天室, 不再接收到推送
        c.pop(100002)
        await c.exit_chat_room(room_type, room_id)
        ret = await c.wait_for(100002)
        self.assertTrue(ret['result'])
        c.pop(100007)

        # 发送消息, 其他人可接收到推送
        self.client.pop(100003)
        c.pop(100007)
        await self.client.send_message(room_type, room_id, '3')
        ret = await self.client.wait_for(100003)
        self.assertTrue(ret['result'])

        ret = await c.wait_for(100007, 50)
        self.assertFalse(ret, c.player_id)

        # 拉取聊天数据
        self.client.pop(100004)
        await self.client.get_message(room_type, room_id, count=10)
        ret = await self.client.wait_for(100004)
        self.assertTrue(ret['result'])
        self.assertTrue(ret['result'])
        count = len(ret['msg_list'])
        self.assertTrue(count <= 10)
        for i in ret['msg_list']:
            if isinstance(i, str):
                i = json.loads(i)

        # 退出聊天室
        self.client.pop(100002)
        await self.client.exit_chat_room(room_type, room_id)
        ret = await self.client.wait_for(100002)
        self.assertTrue(ret['result'])

        # 好友私聊
        self.client.pop(100003)
        await self.client.send_message(0, 0, '11', friend_id=c.player_id)
        ret = await self.client.wait_for(100003)
        self.assertEqual(ret['error_code'], 70016)

        # 先添加好友, 再发送私聊
        self.client.pop(70003)
        await self.client.add_friend(c.player_id)
        ret = await self.client.wait_for(70003)
        self.assertTrue(ret['result'])

        c.pop(70014)
        await c.agree_friend_apply(self.client.player_id)
        ret = await c.wait_for(70014)
        self.assertTrue(ret['result'])

        self.client.pop(100003)
        c.pop(100007)
        await self.client.send_message(0, 0, '11', friend_id=c.player_id)
        ret = await self.client.wait_for(100003)
        self.assertTrue(ret['result'])

        ret = await c.wait_for(100007)
        self.assertTrue(ret['result'])

        # 拉取好友私聊消息
        self.client.pop(100004)
        await self.client.get_message(0, 0, friend_id=c.player_id)
        ret = await self.client.wait_for(100004)
        self.assertTrue(ret['result'])
        for i in ret['msg_list']:
            print(i)

        c.pop(100004)
        await c.get_message(0, 0, friend_id=self.client.player_id)
        ret = await c.wait_for(100004)
        self.assertTrue(ret['result'])
        for i in ret['msg_list']:
            print(i)

        # 清除
        for i in c.task_list:
            # i.cancel()
            pass

if __name__ == '__main__':
    unittest.main()
