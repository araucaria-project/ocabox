#!/usr/bin/env python
import asyncio
import logging
import sys

from ob.data_colection.base_components.tree_base_broker import TreeBaseBroker
from ob.data_colection.base_components.tree_base_broker_default_target import TreeBaseBrokerDefaultTarget
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.comunication.request_solver import RequestSolver
from ob.comunication.router import Router
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.specialistic_components.tree_blocker_access_grantor import TreeBlockerAccessGrantor
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_request_alpaca_blocker import TreeRequestAlpacaBlocker
from ob.ob_config import SingletonConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def stop_router_timeout(vrr):
    await asyncio.sleep(10)
    logger.warning('close router from stop_router_timeout()')
    vrr.stop()


def main(argv):
    SingletonConfig.add_config_file_from_config_dir('sample_config.yaml')
    alpaca_module = TreeAlpacaObservatory('zibi_sample', observatory_name='zibi-ocabox-800')
    alpaca_blocker = TreeRequestAlpacaBlocker('zibi_blocker', alpaca_module)
    cache_800 = TreeCache('sample_cache', alpaca_blocker)

    blocker_grantor = TreeBlockerAccessGrantor('grantor_800', 'access_grantor', alpaca_blocker)
    broker_800 = TreeBaseBrokerDefaultTarget('broker_800', [blocker_grantor], default_provider=cache_800)
    tp_800 = TreeProvider('module_800', '800', broker_800)

    vb = TreeBaseBroker('front_broker', [tp_800])
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
                logger.info('All task in loop is finished')
            else:
                logger.error('Some of the tasks in current loop is still running')
                raise RuntimeError

            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()

    # try:
    #     asyncio.run(coro)
    # except KeyboardInterrupt as e:
    #     logger.info('Caught keyboard interrupt. Canceling tasks...')

    return 0


if __name__ == '__main__':
    retcode = main(sys.argv)
    sys.exit(retcode)
