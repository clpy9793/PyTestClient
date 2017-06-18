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
NUMS = 1


async def start():
    await asyncio.sleep(1, 3)
    c = await GatewayClient().run()
    try:
        await run(c)
    except Exception:
        traceback.print_exc()


async def run(client):
    loop = asyncio.get_event_loop()
    loop.create_task(client.event_listen())
    await client.open_test_switch()
    while True:
        
        n = random.randint(1, 100)
        await client.game_flow()
        await asyncio.sleep(random.randint(1, 2))
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
        


def main():
    loop = asyncio.get_event_loop()
    tasks = [start() for _ in range(NUMS)]
    loop.run_until_complete(asyncio.gather(*tasks))

if __name__ == '__main__':
    main()