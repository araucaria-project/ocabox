import asyncio
import logging
import time
import unittest
from typing import List
from ob.comunication.client import Client
from ob.comunication.comunication_error import CommunicationRuntimeError, CommunicationTimeoutError
from ob.comunication.cycle_query import CycleQuery
from ob.comunication.message_serializer import MessageSerializer
from ob.comunication.multipart_structure import MultipartStructure
from ob.comunication.request_solver import RequestSolver
from ob.data_colection.address import AddressError, Address
from ob.comunication.router import Router
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.specialistic_components.tree_cache_observatory import TreeCache
from ob.data_colection.specialistic_components.tree_conditional_freezer import TreeConditionalFreezer
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest, ValueResponse
from test.comunication.sample_test_resolver import SampleTestResolver
from test.data_colection.sample_test_value_provider import SampleTestValueProvider

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class TestCycleQuery(unittest.TestCase):

    def setUp(self):
        super().setUp()
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # tree
        self.tree_provider2 = SampleTestValueProvider('sample_name2', 'provider2', [])
        self.tree_cache = TreeCache('sample_name_cache', self.tree_provider2)
        self.tree_freezer = TreeConditionalFreezer('sample_freezer', self.tree_cache)
        self.tree_provider1 = TreeProvider('sample_name1', 'provider1', self.tree_freezer)
        self.max_refreshes = 3
        self.tree_freezer.set_max_refreshes(self.max_refreshes)
        self.time_interval = 0.2  # number of seconds to test the temporal aspects of the module
        # router
        name = 'SampleTestRouter'
        self.vr = Router(RequestSolver(self.tree_provider1), name=name)
        self.vr.start(self.loop)
        self.client = Client(name='SampleTestClient')

    def tearDown(self) -> None:
        self.vr.stop()
        vr_stop = asyncio.gather(self.vr.get_stop_task(), return_exceptions=True)
        self.loop.run_until_complete(vr_stop)
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
        self.vr.__del__()
        super().tearDown()

    @staticmethod
    def multipart_to_V_response(resp):
        try:
            vr = ValueResponse.from_byte(resp)
        except TypeError:
            vr = ValueResponse('', None, False, None)
        except AddressError:
            vr = ValueResponse('', None, False, None)
        except ValueError:
            vr = ValueResponse('', None, False, None)
        return vr

    def test_get_no_cachable_value(self):
        address = Address('.'.join([self.tree_provider1.get_source_name(),
                                    self.tree_provider2.get_source_name(),
                                    'value_error']))
        time_of_data_tolerance = self.time_interval

        request = ValueRequest(address, time.time(),
                               time_of_data_tolerance=time_of_data_tolerance,
                               request_type='PUT',
                               request_data={'time_of_known_change': None},
                               cycle_query=True)
        delay = 0.5

        async def coro():
            cq = CycleQuery(client=self.client, list_request=[request], delay=delay, only_new_data=True)
            try:
                cq.start()
                with self.assertRaises(CommunicationRuntimeError):
                    result = await cq.get_response()
                self.assertTrue(cq.is_stopped())
            finally:
                cq.stop()

        self.loop.run_until_complete(coro())


if __name__ == '__main__':
    unittest.main()
