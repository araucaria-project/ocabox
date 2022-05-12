#!/usr/bin/env python
import asyncio
import logging
import sys

from router.value_router import ValueRouter


async def stop_router_timeout(vrr):
    await asyncio.sleep(10)
    logging.warning('close router from stop_router_timeout()')
    vrr.stop()


async def gather_coro(c, c2):
    task2 = asyncio.create_task(c2)
    await c
    await task2


def main(argv):
    logging.basicConfig(level=logging.INFO)

    vr = ValueRouter(None)
    coro = vr.main_coroutine()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            # cancel router tasks
            vr.stop()
            vr_stop = asyncio.gather(vr.get_stop_task(), return_exceptions=True)
            loop.run_until_complete(vr_stop)

            # make sure if all task is finished (router task and every others in this loop)
            all_tasks = asyncio.all_tasks(loop)
            if not all_tasks:
                logging.info('All task in loop is finished')
            else:
                logging.error('Some of the tasks in current loop is still running')
                raise RuntimeError

            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()

    # try:
    #     asyncio.run(coro)
    # except KeyboardInterrupt as e:
    #     logging.info('Caught keyboard interrupt. Canceling tasks...')

    return 0


if __name__ == '__main__':
    retcode = main(sys.argv)
    sys.exit(retcode)

    # @DATACLAS zrobic klase do danych,
    # jak najszybciej przesywac przez 0mq dane nie JSON nie sownik
    # router ma si dorzucac do istniejacej petli
