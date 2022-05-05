#!/usr/bin/env python
import asyncio
import logging

from ob.value_router import ValueRouter


async def cc(vrr):
    await asyncio.sleep(5)
    logging.warning('close router from cc()')
    vrr.stop()



async def wmain(c, c2):
    task2 = asyncio.create_task(c2)
    await c
    await task2


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    vr = ValueRouter()
    coro = vr.main_coroutine()
    cor2 = cc(vr)

    asyncio.run(wmain(coro, cor2))

    # @DATACLAS zrobic klase do danych,
    # jak najszybciej przesywac przez 0mq dane nie JSON nie sownik
    # router ma si dorzucac do istniejacej petli
