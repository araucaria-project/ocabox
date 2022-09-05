#!/usr/bin/env python
import asyncio
import logging
import sys

from ob.data_colection.base_components.tree_base_broker import TreeBaseBroker
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.comunication.request_solver import RequestSolver
from ob.comunication.router import Router
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_blocker_access_grantor import TreeBlockerAccessGrantor
from ob.data_colection.specialistic_components.tree_request_alpaca_blocker import TreeRequestAlpacaBlocker


async def stop_router_timeout(vrr):
    await asyncio.sleep(10)
    logging.warning('close router from stop_router_timeout()')
    vrr.stop()


def main(argv):
    logging.basicConfig(level=logging.INFO)
    alpaca_module = TreeAlpacaObservatory('dibi_sample', observatory_name='dibi-camk')
    alpaca_blocker = TreeRequestAlpacaBlocker('dibi_blocker', alpaca_module)
    vc = TreeProvider('sample_provider_1', 'sample_telescope', alpaca_blocker)
    blocker_grantor = TreeBlockerAccessGrantor('sample_grantor', 'alpaca_grantor',alpaca_blocker)
    vb = TreeBaseBroker('sample_broker_1', [vc, blocker_grantor])
    rs = RequestSolver(vb)
    vr = Router(rs)
    coro = vr.main_coroutine()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(rs.run_tree())
        loop.run_until_complete(coro)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            # cancel router tasks
            vr.stop()
            vr_stop = asyncio.gather(vr.get_stop_task(), rs.stop_tree(), return_exceptions=True)
            loop.run_until_complete(vr_stop)

            # make sure if all task is finished (router task and every other in this loop)
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
