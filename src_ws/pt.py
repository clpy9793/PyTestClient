#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-06-12 13:41:54
# @Author  : Your Name (you@example.org)
# @Link    : http://example.org
# @Version : $Id$

import os
import random
import asyncio
import traceback
from client import *
from contextlib import contextmanager

KV = {}
NUMS = 500
COUNT = 0

print(500)

async def start():
    while True:
        try:
            await asyncio.sleep(1)
            c = await GatewayClient.run()
            await run(c)
        except Exception:
            exit()




async def run(client):
    global COUNT
    await asyncio.sleep(1)
    loop = asyncio.get_event_loop()
    loop.create_task(client.event_listen())

    while True:
        if random.randint(1, 10) == 1:
            item = ['item', 'IT0020', 'count', 1000000000000]
            await client.test_add_item(item)
            ret = await client.wait_for(3003)
            if not ret or not ret['result']:
                continue
                # return 
        n = random.randint(1, 100)
        await client.game_flow()
        COUNT += 1
        print('[COUNT]:\t', COUNT)
        await asyncio.sleep(random.randint(3, 8))

        # await asyncio.sleep(random.randint(1, 2))
        # if 1 <= n <= 10:
        #     await client.game_flow()
        # if 11 <= n <= 20:
        #     await client.store_flow()
        # if 20 <= n <= 30:
        #     await client.friend_flow()
        # if 31 <= n <= 40:
        #     await client.chat_flow()
        # if 41 <= n <= 50:
        #     await client.avatar_flow()

def task():
    loop = asyncio.get_event_loop()
    tasks = [start() for _ in range(NUMS)]
    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))


def main():
    pass

if __name__ == '__main__':
    main()
