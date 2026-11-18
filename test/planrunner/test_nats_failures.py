"""A failing NATS must not interrupt the plan runner: every serverish failure is handled where it is reported."""
import asyncio
import unittest
from unittest import mock

from serverish.base import (MessengerConnectionClosed, MessengerNotConnected, MessengerPublishAckTimeout,
                            MessengerRequestNoResponders, MessengerRequestTimeout, MessengerTransportError)

import ocaboxapi.telescope  # noqa: F401  first: ob.planrunner cannot be imported on its own (import cycle)
from ob.comunication import nats_bus
from ob.planrunner import base_subcommand
from ob.planrunner.base_subcommand import BaseSubCommand
from ob.planrunner.status import PlanStatus

PUBLISH_FAILURES = (MessengerNotConnected('not connected'),
                    MessengerPublishAckTimeout('no ack'),
                    MessengerConnectionClosed('connection closed'),
                    MessengerTransportError('transport'))


class StatusErrorPublishTest(unittest.IsolatedAsyncioTestCase):
    """The error report of a subcommand (e.g. on the way to close the dome)"""

    def setUp(self):
        self.sub = mock.Mock(spec=BaseSubCommand)
        self.sub.id, self.sub.uobi, self.sub.name = '1.2', 22, 'dome_slew'
        self.sub.telescope = mock.Mock(id='dev')
        self.sub.status_error_pub = mock.AsyncMock()
        self.sub.STATUS_ERROR_PUBLISH_TIMEOUT = BaseSubCommand.STATUS_ERROR_PUBLISH_TIMEOUT
        self.sub.STATUS_ERROR_PUBLISH_DEADLINE = BaseSubCommand.STATUS_ERROR_PUBLISH_DEADLINE

    async def _report(self) -> None:
        await BaseSubCommand.status_error_publish(self.sub, level='critical', description='x',
                                                  plan_runner_quits=True)

    async def test_published(self):
        await self._report()
        _, kwargs = self.sub.status_error_pub.publish.await_args
        self.assertEqual(kwargs['data']['error_level'], 'critical')
        self.assertEqual(kwargs['timeout'], BaseSubCommand.STATUS_ERROR_PUBLISH_TIMEOUT)

    async def test_no_publish_failure_interrupts_the_caller(self):
        for failure in PUBLISH_FAILURES:
            with self.subTest(failure=type(failure).__name__):
                self.sub.status_error_pub.publish.side_effect = failure
                with self.assertLogs(base_subcommand.logger, level='ERROR') as logs:
                    await self._report()
                self.assertIn(type(failure).__name__, logs.output[-1])

    async def test_a_hanging_publish_is_cut_at_the_deadline(self):
        async def hang(**_):
            await asyncio.sleep(60)

        self.sub.status_error_pub.publish.side_effect = hang
        self.sub.STATUS_ERROR_PUBLISH_DEADLINE = 0.05
        with self.assertLogs(base_subcommand.logger, level='ERROR'):
            await asyncio.wait_for(self._report(), timeout=2)

    async def test_programming_errors_are_not_swallowed(self):
        self.sub.status_error_pub.publish.side_effect = AttributeError('a bug')
        with self.assertRaises(AttributeError):
            await self._report()


class PlanStatusPublishTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_publish_failure_escapes(self):
        publisher = mock.AsyncMock()
        for failure in PUBLISH_FAILURES:
            with self.subTest(failure=type(failure).__name__):
                publisher.publish.side_effect = failure
                await PlanStatus.send_to_nats(mock.Mock(spec=PlanStatus), publisher=publisher, data={})


class RpcRequestTest(unittest.IsolatedAsyncioTestCase):
    async def test_every_serverish_failure_is_no_answer(self):
        failures = (MessengerRequestNoResponders('nobody'), MessengerRequestTimeout('late'),
                    MessengerNotConnected('not connected'), MessengerConnectionClosed('connection closed'))
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                journal = mock.AsyncMock()
                with mock.patch.object(nats_bus, 'request', side_effect=failure):
                    self.assertEqual(await nats_bus.rpc_request('rpc.x', {}, journal=journal), (None, None))
                journal.error.assert_awaited_once()
                self.assertIn(type(failure).__name__, journal.error.await_args.args[0])


if __name__ == '__main__':
    unittest.main()
