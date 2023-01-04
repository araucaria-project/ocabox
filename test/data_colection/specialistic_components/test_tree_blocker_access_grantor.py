import logging
import time
import unittest

from ob.data_colection.base_components.tree_base_broker import TreeBaseBroker
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.specialistic_components.tree_blocker_access_grantor import TreeBlockerAccessGrantor
from ob.data_colection.specialistic_components.tree_request_alpaca_blocker import TreeRequestAlpacaBlocker
from ob.data_colection.tree_user import TreeServiceUser
from ob.data_colection.value_call import ValueRequest
from test.data_colection.base_async_test import BaseAsyncTest
from test.data_colection.sample_test_value_provider import SampleTestValueProvider

logger = logging.getLogger(__name__)


class TreeRequestAlpacaBlockerTest(unittest.TestCase, BaseAsyncTest):

    def setUp(self):
        super().setUp()
        self.sample_provider_name = 'sample_name'
        self.sample_provider_source_name = 'source_sample_name'
        self.sample_provider = SampleTestValueProvider(self.sample_provider_name, self.sample_provider_source_name, [])
        self.blocker_name = 'test_sample_blocker'  # this name is used in config file
        self.blocker = TreeRequestAlpacaBlocker(component_name=self.blocker_name, subcontractor=self.sample_provider)
        self.provider_name = 'provider_sample_name'
        self.provider_source_name = 'provider_source_sample_name'
        self.provider = TreeProvider(self.provider_name, self.provider_source_name, self.blocker)

        self.grantor_name = 'sample_grantor'
        self.grantor_source_name = 'sample_grantor_source_name'
        self.grantor = TreeBlockerAccessGrantor(self.grantor_name, self.grantor_source_name, self.blocker)

        self.sample_broker_name = 'sample_broker'
        self.broker = TreeBaseBroker(self.sample_broker_name, [self.provider, self.grantor])
        self._setUpLoop()

    def tearDown(self) -> None:
        self._tearDownLoop()
        super().tearDown()

    def test_take_control(self):
        """ test command: take_control"""
        async def coro():
            user = TreeServiceUser(name='some_user')
            req = ValueRequest('.'.join([self.provider_source_name, self.sample_provider_source_name, 'new_val']),
                               request_type='PUT',
                               user=user)
            result = await self.broker.get_response(request=req)
            self.assertIsNone(result.value)
            self.assertTrue(result.error.code == 1004)
            # take control
            req = ValueRequest('.'.join([self.grantor_source_name, 'take_control']),
                               request_type='GET',
                               user=user)
            result = await self.broker.get_response(request=req)
            self.assertTrue(result.value.v)
            self.assertTrue(self.blocker.get_current_user is not None)
            # make request again, now can go ahead
            req = ValueRequest('.'.join([self.provider_source_name, self.sample_provider_source_name, 'new_val']),
                               request_type='PUT',
                               user=user)
            result = await self.broker.get_response(request=req)
            self.assertIsNotNone(result.value)
            self.assertIsNone(result.error)

        self.loop.run_until_complete(coro())

    def test_return_control(self):
        """ test command: return_control"""
        async def coro():
            user = TreeServiceUser(name='some_user')
            self.blocker.make_reservation(user=user)
            self.assertIsNotNone(self.blocker.get_current_user)

            req = ValueRequest('.'.join([self.grantor_source_name, 'return_control']),
                               request_type='GET', user=user)
            result = await self.broker.get_response(request=req)
            self.assertTrue(result.value.v)
            self.assertIsNone(self.blocker.get_current_user())

        self.loop.run_until_complete(coro())

    def test_current_user(self):
        """ test command: current_user"""
        async def coro():
            user = TreeServiceUser(name='some_user')
            self.blocker.make_reservation(user=user)
            self.assertIsNotNone(self.blocker.get_current_user)
            req = ValueRequest('.'.join([self.grantor_source_name, 'current_user']),
                               request_type='GET',
                               user=user)
            result = await self.broker.get_response(request=req)
            self.assertIsNotNone(result.value.v)
            self.assertTrue(isinstance(result.value.v, dict))
            self.assertTrue(result.value.v.get('name') == user.name)

        self.loop.run_until_complete(coro())

    def test_timeout_current_control(self):
        """ test command: timeout_current_control"""
        async def coro():
            user = TreeServiceUser(name='some_user')
            self.blocker.make_reservation(user=user)
            self.assertIsNotNone(self.blocker.get_current_user)
            req = ValueRequest('.'.join([self.grantor_source_name, 'timeout_current_control']),
                               request_type='GET',
                               user=user)
            result = await self.broker.get_response(request=req)
            self.assertIsNotNone(result.value.v)
            self.assertTrue(isinstance(result.value.v, float))

        self.loop.run_until_complete(coro())

    def test_take_control_with_specific_timeout(self):
        """ test command 'take_control' witch custom timeout"""
        async def coro():
            user = TreeServiceUser(name='some_user')
            self.blocker.make_reservation(user=user)
            self.assertIsNotNone(self.blocker.get_current_user)
            sample_timeout = 120
            req = ValueRequest('.'.join([self.grantor_source_name, 'take_control']),
                               request_type='GET',
                               user=user,
                               request_data={'timeout_reservation': sample_timeout + time.time()})
            result = await self.broker.get_response(request=req)
            self.assertIsNotNone(result.value.v)
            rest_time = self.blocker.get_timeout_current_reservation() - time.time()
            self.assertTrue(0 < rest_time < sample_timeout and rest_time > sample_timeout - 10)

        self.loop.run_until_complete(coro())

    def test_break_control(self):
        """test command: break_control"""
        async def coro():
            user = TreeServiceUser(name='some_user')
            self.blocker.make_reservation(user=user)
            self.assertIsNotNone(self.blocker.get_current_user)

            other_user = TreeServiceUser(name='some_other_user')
            req = ValueRequest('.'.join([self.grantor_source_name, 'break_control']),
                               request_type='GET', user=other_user)
            result = await self.broker.get_response(request=req)
            self.assertIsNone(self.blocker.get_current_user())
            self.assertTrue(result.value.v)

        self.loop.run_until_complete(coro())


if __name__ == '__main__':
    unittest.main()
