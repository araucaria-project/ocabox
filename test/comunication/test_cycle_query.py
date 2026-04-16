"""Unit tests for the extended cycle_query classes in ob.comunication.cycle_query.

These tests verify the error-callback registration and invocation behaviour added by
the ocabox package on top of the upstream obcom classes, using mocks and asyncio helpers
so that no live server connection is required.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from obcom.comunication.comunication_error import CommunicationRuntimeError

from ob.comunication.cycle_query import BaseCycleQuery, ConditionalCycleQuery, PeriodicCycleQuery


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_crs():
    """Return a minimal mock for BaseClientRequestSolver."""
    crs = MagicMock()
    crs.send_request = AsyncMock()
    return crs


def _make_request():
    """Return a minimal mock for ValueRequest."""
    req = MagicMock()
    req.address = 'test.address'
    req.request_data = {}
    req.copy = MagicMock(return_value=MagicMock(address='test.address', request_data={}))
    return req


# ---------------------------------------------------------------------------
# BaseCycleQuery (via a concrete subclass that has a trivial _send_message)
# ---------------------------------------------------------------------------

class _StubCycleQuery(BaseCycleQuery):
    """Minimal concrete subclass used to test BaseCycleQuery infrastructure."""

    def __init__(self, *args, loop=None, **kwargs):
        super().__init__(*args, loop=loop, **kwargs)
        self._stop_after: int = 0  # number of responses before raising error
        self._terminal_error: CommunicationRuntimeError | None = None

    async def _send_message(self):
        """Emit `_stop_after` events then set an error and stop."""
        for _ in range(self._stop_after):
            self._last_response = [MagicMock()]
            self._event.set()
            await asyncio.sleep(0)
            self._event.clear()

        # Simulate terminal stop
        if self._terminal_error:
            self._errors = self._terminal_error
        else:
            self._errors = CommunicationRuntimeError(message='Test terminal error')
        self._event.set()


class TestBaseCycleQueryErrorCallbacks(unittest.IsolatedAsyncioTestCase):
    """Test error-callback registration and invocation on terminal stop."""

    async def asyncSetUp(self):
        self.loop = asyncio.get_running_loop()
        self.crs = _make_crs()
        self.request = _make_request()

    def _make_cq(self, stop_after=0):
        cq = _StubCycleQuery(
            crs=self.crs,
            list_request=[self.request],
            loop=self.loop,
            query_name='test-query',
        )
        cq._stop_after = stop_after
        return cq

    # ------------------------------------------------------------------

    # ------------------------------------------------------------------

    async def test_add_error_callback_method_registers(self):
        """add_error_callback_method must append to _error_callback_methods."""
        cq = self._make_cq()
        handler = MagicMock()
        cq.add_error_callback_method(handler)
        self.assertIn(handler, cq._error_callback_methods)

    async def test_add_async_error_callback_method_registers(self):
        """add_async_error_callback_method must append to _error_callback_methods_a."""
        cq = self._make_cq()
        handler = AsyncMock()
        cq.add_async_error_callback_method(handler)
        self.assertIn(handler, cq._error_callback_methods_a)

    async def test_sync_error_callback_called_on_terminal_stop(self):
        """Sync error callback must be called exactly once with the error on terminal stop."""
        cq = self._make_cq()
        error_handler = MagicMock()
        cq.add_error_callback_method(error_handler)

        cq.start()
        await cq.stop_and_wait()

        error_handler.assert_called_once()
        called_with = error_handler.call_args[0][0]
        self.assertIsInstance(called_with, CommunicationRuntimeError)

    async def test_async_error_callback_called_on_terminal_stop(self):
        """Async error callback must be awaited exactly once with the error on terminal stop."""
        cq = self._make_cq()
        async_error_handler = AsyncMock()
        cq.add_async_error_callback_method(async_error_handler)

        cq.start()
        await cq.stop_and_wait()

        async_error_handler.assert_called_once()
        called_with = async_error_handler.call_args[0][0]
        self.assertIsInstance(called_with, CommunicationRuntimeError)

    async def test_error_callback_not_called_on_normal_stop(self):
        """Error callbacks must NOT be called when stop() is called externally."""
        cq = self._make_cq(stop_after=100)
        error_handler = MagicMock()
        cq.add_error_callback_method(error_handler)

        cq.start()
        cq.stop()
        await cq.stop_and_wait()

        error_handler.assert_not_called()

    async def test_regular_callback_still_called_after_terminal_stop_with_last_response(self):
        """Regular callbacks must still fire once with the last response on terminal stop."""
        cq = self._make_cq(stop_after=1)  # one real response then stop
        regular_callback = MagicMock()
        cq.add_callback_method(regular_callback)

        cq.start()
        await cq.stop_and_wait()

        # Regular callback called at least once (for the real response + possibly once more
        # for the terminal last-response fallback)
        self.assertGreater(regular_callback.call_count, 0)

    async def test_multiple_error_callbacks_all_called(self):
        """All registered error callbacks (sync and async) must be invoked."""
        cq = self._make_cq()
        handler1 = MagicMock()
        handler2 = MagicMock()
        async_handler = AsyncMock()
        cq.add_error_callback_method(handler1)
        cq.add_error_callback_method(handler2)
        cq.add_async_error_callback_method(async_handler)

        cq.start()
        await cq.stop_and_wait()

        handler1.assert_called_once()
        handler2.assert_called_once()
        async_handler.assert_called_once()

    async def test_error_log_emitted_on_terminal_stop(self):
        """An ERROR-level log must be emitted when the subscription terminates permanently."""
        cq = self._make_cq()

        with patch('ob.comunication.cycle_query.logger') as mock_logger:
            cq.start()
            await cq.stop_and_wait()

        # At least one error() call whose first argument contains the expected phrase
        error_messages = [call.args[0] for call in mock_logger.error.call_args_list if call.args]
        self.assertTrue(
            any('No further callbacks will fire' in msg for msg in error_messages),
            msg=f"Expected terminal-stop log not found; error messages were: {error_messages}",
        )


# ---------------------------------------------------------------------------
# ConditionalCycleQuery – verify it is an instance of both parents
# ---------------------------------------------------------------------------

class TestConditionalCycleQueryInheritance(unittest.TestCase):
    """Smoke-tests for ConditionalCycleQuery MRO / instance checks."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(None)

    def test_is_instance_of_extended_base(self):
        """ConditionalCycleQuery must be a BaseCycleQuery (extended)."""
        from obcom.comunication.cycle_query import BaseCycleQuery as _ObcomBase
        crs = _make_crs()
        req = _make_request()
        cq = ConditionalCycleQuery(crs=crs, list_request=[req], loop=self.loop)
        self.assertIsInstance(cq, BaseCycleQuery)
        self.assertIsInstance(cq, _ObcomBase)

    def test_has_error_callback_attributes(self):
        """ConditionalCycleQuery instances must expose error-callback lists."""
        crs = _make_crs()
        req = _make_request()
        cq = ConditionalCycleQuery(crs=crs, list_request=[req], loop=self.loop)
        self.assertTrue(hasattr(cq, '_error_callback_methods'))
        self.assertTrue(hasattr(cq, '_error_callback_methods_a'))
        self.assertEqual(cq._error_callback_methods, [])
        self.assertEqual(cq._error_callback_methods_a, [])

    def test_add_error_callback_method(self):
        """ConditionalCycleQuery must support add_error_callback_method."""
        crs = _make_crs()
        req = _make_request()
        cq = ConditionalCycleQuery(crs=crs, list_request=[req], loop=self.loop)
        handler = MagicMock()
        cq.add_error_callback_method(handler)
        self.assertIn(handler, cq._error_callback_methods)


# ---------------------------------------------------------------------------
# PeriodicCycleQuery – verify it is an instance of both parents
# ---------------------------------------------------------------------------

class TestPeriodicCycleQueryInheritance(unittest.TestCase):
    """Smoke-tests for PeriodicCycleQuery MRO / instance checks."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(None)

    def test_is_instance_of_extended_base(self):
        """PeriodicCycleQuery must be a BaseCycleQuery (extended)."""
        crs = _make_crs()
        req = _make_request()
        cq = PeriodicCycleQuery(crs=crs, list_request=[req], loop=self.loop)
        self.assertIsInstance(cq, BaseCycleQuery)

    def test_has_error_callback_attributes(self):
        """PeriodicCycleQuery instances must expose error-callback lists."""
        crs = _make_crs()
        req = _make_request()
        cq = PeriodicCycleQuery(crs=crs, list_request=[req], loop=self.loop)
        self.assertTrue(hasattr(cq, '_error_callback_methods'))
        self.assertTrue(hasattr(cq, '_error_callback_methods_a'))


if __name__ == '__main__':
    unittest.main()
