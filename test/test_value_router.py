import asyncio
import logging
import unittest
from ob.value_router import ValueRouter

logger = logging.getLogger(__name__)


class ValueRouterTest(unittest.TestCase):

    def setUp(self):
        super().setUp()
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()

    def tearDown(self) -> None:
        try:
            all_tasks = asyncio.all_tasks(self.loop)
            for t in all_tasks:
                t.cancel()
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            all_tasks = asyncio.all_tasks(self.loop)
            if not all_tasks:
                logger.info('All task in loop is finished')
            else:
                logger.error('Some of the tasks in current loop is still running')
                raise RuntimeError
        finally:
            asyncio.set_event_loop(None)
            self.loop.close()
        super().tearDown()

    def test_routers_name_conflict(self):
        """
        the test checks if it is not possible to loop two routers with the same name
        :return:
        """
        name1 = 'router1'
        name2 = 'router1'
        vr = ValueRouter(name=name1, port=5559)
        vr2 = ValueRouter(name=name2, port=5558)

        async def coro():
            vr.start()
            await asyncio.sleep(0)
            vr2.start()
            # don't care about stop router because in unit test tearDown() method close all task and safety end loop

        with self.assertRaises(ValueError):
            self.loop.run_until_complete(coro())

    def test_stop_router(self):
        """
        This test check, if method stop() correctly close all router task
        :return:
        """
        name1 = 'router1'
        vr = ValueRouter(name=name1)

        async def coro():
            vr.start()
            await asyncio.sleep(0)
            vr.stop()
            await asyncio.sleep(0)

        self.loop.run_until_complete(coro())
        self.assertTrue(vr.is_stopped())
        all_tasks = asyncio.all_tasks(self.loop)
        self.assertTrue(len(all_tasks) == 0)

    def test_router_is_stopped(self):
        """
        This test check if .is_stopped() method work good
        :return:
        """
        name1 = 'router1'
        vr = ValueRouter(name=name1, port=5559)

        async def coro():
            vr.start()
            await asyncio.sleep(0)
            return vr.is_stopped()

        out = self.loop.run_until_complete(coro())
        self.assertFalse(out)
        self.assertFalse(self.loop.is_running())
        # the loop is stop but don't close so the router should be not stop just freeze
        self.assertFalse(vr.is_stopped())
        # force close router
        all_tasks = asyncio.all_tasks(self.loop)
        for t in all_tasks:
            t.cancel()
        self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        # now router should be stopped
        self.assertTrue(vr.is_stopped())

    def test_router_stop_task(self):
        """
        This test check if stop task for router work correct
        :return:
        """
        name1 = 'router1'
        vr = ValueRouter(name=name1, port=5559)

        async def coro():
            vr.start()
            await asyncio.sleep(0)

        self.loop.run_until_complete(coro())
        vr.stop()
        stop_task = vr.get_stop_task()
        self.assertIsNotNone(stop_task)  # here stop task was create but not run so it must exist and can't finished

        # here should be exist some task in loop because stop task don't finished yet
        all_tasks = asyncio.all_tasks(self.loop)
        self.assertFalse(len(all_tasks) == 0)

        async def foo2():
            # it should be finished immediately if it waiting that mean is something wrong
            await asyncio.wait_for(stop_task, timeout=1.0)
        self.loop.run_until_complete(foo2())
        stop_task = vr.get_stop_task()
        self.assertIsNone(stop_task)  # here stop task finished so it can't exist in router

        #  now shouldn't be any task in loop
        all_tasks = asyncio.all_tasks(self.loop)
        self.assertTrue(len(all_tasks) == 0)


if __name__ == '__main__':
    unittest.main()
