import logging
import time
import unittest
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.specialistic_components.tree_request_alpaca_blocker import TreeRequestAlpacaBlocker, \
    ReservationError
from ob.data_colection.tree_user import TreeServiceUser
from ob.data_colection.value import TreeValueError, Value
from ob.data_colection.value_call import ValueRequest
from test.data_colection.base_async_test import BaseAsyncTest

logger = logging.getLogger(__name__)


class TreeRequestAlpacaBlockerTest(unittest.TestCase, BaseAsyncTest):
    class SampleTestValueProvider(TreeProvider):
        async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
            if request.index < len(request.address) and request.address[request.index] == 'some_val':
                return Value(5, time.time())
            else:
                raise TreeValueError

    def setUp(self):
        super().setUp()
        self.sample_provider_name = 'sample_name'
        self.sample_provider_source_name = 'source_sample_name'
        self.sample_provider = self.SampleTestValueProvider(self.sample_provider_name, self.sample_provider_source_name,
                                                            None)
        self.blocker_name = 'sample_blocker'
        self.blocker = TreeRequestAlpacaBlocker(self.blocker_name, self.sample_provider)
        self.provider_name = 'provider_sample_name'
        self.provider_source_name = 'provider_source_sample_name'
        self.provider = TreeProvider(self.provider_name, self.provider_source_name, self.blocker)
        self._setUpLoop()

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_access_granted_get_request(self):
        """Test access granted for GET request"""
        async def coro():
            # GET request always go through
            req = ValueRequest('.'.join([self.provider_source_name, self.sample_provider_source_name, 'some_val']))
            result = await self.provider.get_response(request=req)
            self.assertIsNotNone(result.value.v)
        self.loop.run_until_complete(coro())

    def test_access_denied_put_request(self):
        """Test when access denied"""
        async def coro():
            # PUT request stop
            req = ValueRequest('.'.join([self.provider_source_name, self.sample_provider_source_name, 'some_val']),
                               request_type='PUT')
            result = await self.provider.get_response(request=req)
            self.assertIsNone(result.value)
            self.assertTrue(result.error.code == 1004)
        self.loop.run_until_complete(coro())

    def test_access_granted_put_request(self):
        """Test when access granted for user"""
        async def coro():
            # PUT request when access granted
            user = TreeServiceUser(name='some_user')
            self.blocker.make_reservation(user=user, timeout_reservation=time.time() + 60)
            req = ValueRequest('.'.join([self.provider_source_name, self.sample_provider_source_name, 'some_val']),
                               request_type='PUT', user=user)
            result = await self.provider.get_response(request=req)
            self.assertIsNotNone(result.value)
            self.assertIsNone(result.error)
        self.loop.run_until_complete(coro())

    def test_wrong_type_request(self):
        async def coro():
            # wrong type request
            req = ValueRequest('.'.join([self.provider_source_name, self.sample_provider_source_name, 'some_val']),
                               request_type='EXECUTE')
            result = await self.provider.get_response(request=req)
            self.assertIsNone(result.value)
            self.assertTrue(result.error.code == 4001)
        self.loop.run_until_complete(coro())

    def test_access_timeout_put_request(self):
        """Test when user lost access by timeout"""
        async def coro():
            # PUT request when access denied by timeout
            user = TreeServiceUser(name='some_user')
            self.blocker.make_reservation(user=user, timeout_reservation=time.time() - 2)
            req = ValueRequest('.'.join([self.provider_source_name, self.sample_provider_source_name, 'some_val']),
                               request_type='PUT', user=user)
            result = await self.provider.get_response(request=req)
            self.assertIsNone(result.value)
            self.assertTrue(result.error.code == 1004)
        self.loop.run_until_complete(coro())

    def test_double_reservation(self):
        """test whether the reservation will not be overwritten before the end of the previous one. """
        user = TreeServiceUser(name='some_user')
        self.blocker.make_reservation(user=user, timeout_reservation=time.time() + 60)
        user2 = TreeServiceUser(name='some_user2')
        with self.assertRaises(ReservationError):
            self.blocker.make_reservation(user=user2, timeout_reservation=time.time() + 60)
        self.assertEqual(user, self.blocker.get_current_user())
        self.assertNotEqual(user2, self.blocker.get_current_user())


if __name__ == '__main__':
    unittest.main()
