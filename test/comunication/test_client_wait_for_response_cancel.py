import asyncio
import types
import unittest

from ob.comunication.client import Client


class _CancelThenRuntimeErrorCondition:
    def __init__(self, message: str):
        self._message = message

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def wait(self):
        task = asyncio.current_task()
        if task is not None:
            task.cancel()
        raise RuntimeError(self._message)


class _RuntimeErrorCondition:
    def __init__(self, message: str):
        self._message = message

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def wait(self):
        raise RuntimeError(self._message)


class TestClientWaitForResponseCancel(unittest.IsolatedAsyncioTestCase):
    async def _new_client_for_wait(self, condition):
        client = Client.__new__(Client)
        client._loop = asyncio.get_running_loop()
        client._msg_con = condition
        client._receive_task = types.SimpleNamespace(done=lambda: False)
        client._is_working_receive_task = True
        client._new_msgs = []
        client._front_socket = types.SimpleNamespace(close=lambda: None)
        client.context = types.SimpleNamespace(destroy=lambda: None)
        client._name = "test-client"
        return client

    async def test_wait_for_response_maps_lock_not_acquired_runtimeerror_to_cancelled_error(self):
        client = await self._new_client_for_wait(_CancelThenRuntimeErrorCondition("Lock is not acquired"))
        waiting_task = asyncio.create_task(client._wait_for_response(b"1", b"2"))

        with self.assertRaises(asyncio.CancelledError):
            await waiting_task

    async def test_wait_for_response_maps_loop_bound_runtimeerror_to_cancelled_error(self):
        client = await self._new_client_for_wait(
            _CancelThenRuntimeErrorCondition(
                "<asyncio.locks.Condition object at 0x0 [locked, waiters:3]> is bound to a different event loop"
            )
        )
        waiting_task = asyncio.create_task(client._wait_for_response(b"1", b"2"))

        with self.assertRaises(asyncio.CancelledError):
            await waiting_task

    async def test_wait_for_response_keeps_runtimeerror_when_not_cancelling(self):
        client = await self._new_client_for_wait(_RuntimeErrorCondition("some runtime error"))

        with self.assertRaises(RuntimeError):
            await client._wait_for_response(b"1", b"2")


if __name__ == "__main__":
    unittest.main()
