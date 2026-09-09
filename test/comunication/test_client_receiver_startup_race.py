import asyncio
import types
import unittest

from obcom.comunication.comunication_error import CommunicationRuntimeError

from ob.comunication.client import Client


class _BlockingFrontSocket:
    """A socket whose receive never completes: the receiver task stays alive but idle."""
    LAST_ENDPOINT = "tcp://fake-endpoint:1234"

    async def recv_multipart(self):
        await asyncio.Event().wait()

    async def send_multipart(self, parts):
        return None

    def close(self):
        return None


class TestReceiverStartupRace(unittest.IsolatedAsyncioTestCase):
    """The first request after the receiver is (re)started must wait for a reply, not declare the
    receiver dead. The receiver task is created by `_stand_in_line`, and the requester continues in
    the same loop turn, before the receiver task has run its first step."""

    @staticmethod
    def _make_client():
        client = Client.__new__(Client)
        client._loop = asyncio.get_running_loop()
        client._msg_con = None
        client._recv_lock = None
        client._new_msgs = []
        client._cleaning_length = 10
        client._front_socket = _BlockingFrontSocket()
        client.context = types.SimpleNamespace(destroy=lambda: None)
        client._name = "test-client"
        client._receive_task = None
        client._is_working_receive_task = False
        client._waiting_amount = 0
        return client

    async def test_first_request_waits_instead_of_failing(self):
        client = self._make_client()
        await client._stand_in_line()
        try:
            with self.assertRaises(TimeoutError):
                async with asyncio.timeout(0.05):
                    await client._wait_for_response(b'\x00', b'\x00')
        except CommunicationRuntimeError as e:
            self.fail(f"receiver declared dead before its first step: {e}")
        finally:
            await client._skip_the_line()

    async def test_stopped_receiver_is_still_detected(self):
        client = self._make_client()
        await client._stand_in_line()
        await client._skip_the_line()  # last waiter gone: receiver cancelled and awaited
        with self.assertRaises(CommunicationRuntimeError):
            await client._wait_for_response(b'\x00', b'\x00')


if __name__ == '__main__':
    unittest.main()
