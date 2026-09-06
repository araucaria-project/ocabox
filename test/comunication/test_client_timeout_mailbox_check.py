import asyncio
import time
import types
import unittest

from obcom.comunication.comunication_error import CommunicationTimeoutError
from obcom.comunication.message_serializer import MessageSerializer
from obcom.comunication.multipart_structure import MultipartStructure

from ob.comunication.client import Client


class _FakeFrontSocket:
    LAST_ENDPOINT = "tcp://fake-endpoint:1234"

    async def send_multipart(self, parts):
        return None

    def close(self):
        return None


class _StubClient(Client):
    """
    A Client subclass that bypasses the real receiver task machinery (socket recv loop) while still
    tracking `_waiting_amount`, so tests can focus on the timeout/mailbox-check logic in
    `_send_to_server` without needing a real ZMQ receiver task.
    """

    async def _stand_in_line(self):
        self._waiting_amount += 1

    async def _skip_the_line(self):
        self._waiting_amount -= 1


class TestClientTimeoutMailboxCheck(unittest.IsolatedAsyncioTestCase):

    @staticmethod
    def _make_client():
        client = _StubClient.__new__(_StubClient)
        client._loop = asyncio.get_running_loop()
        client._msg_con = None
        client._recv_lock = None
        client._new_msgs = []
        client._front_socket = _FakeFrontSocket()
        client.context = types.SimpleNamespace(destroy=lambda: None)
        client._name = "test-client"
        client._waiting_amount = 0
        return client

    @staticmethod
    def _make_envelope(create_time: float, msg_id: int):
        create_time_b = MessageSerializer.pack_b(int(create_time))
        id_b = MessageSerializer.pack_b(msg_id)
        timeout_b = MessageSerializer.pack_b(time.time() + 100)
        return MultipartStructure.from_parts(create_time=create_time_b, id_=id_b, data=[b'reply-data'],
                                             request_timeout=timeout_b, prefix_data=[])

    def _patch_wait_for_psce(self, schedule_append=None):
        """Patch the module-level `wait_for_psce` used by `_send_to_server` so it raises
        `asyncio.TimeoutError` immediately (as it would after the real timer fires), optionally
        scheduling a mailbox append via `call_soon` first, so the append only becomes visible after
        the `except asyncio.TimeoutError: await asyncio.sleep(0)` yield in `_send_to_server`."""
        import ob.comunication.client as client_module

        async def _fake_wait_for_psce(fut, timeout):
            fut.close()  # avoid "coroutine was never awaited" warnings
            if schedule_append is not None:
                asyncio.get_running_loop().call_soon(schedule_append)
            raise asyncio.TimeoutError

        original = client_module.wait_for_psce
        client_module.wait_for_psce = _fake_wait_for_psce
        self.addCleanup(setattr, client_module, "wait_for_psce", original)

    async def test_reply_in_mailbox_at_timeout_is_returned(self):
        """Reply present at timeout -> returned, no exception raised."""
        client = self._make_client()
        ms = self._make_envelope(create_time=time.time(), msg_id=1)
        reply = self._make_envelope(create_time=MessageSerializer.unpack_b(ms.create_time), msg_id=1)

        self._patch_wait_for_psce(schedule_append=lambda: client._new_msgs.append(reply))

        with self.assertLogs("client", level="DEBUG") as log_ctx:
            result = await client._send_to_server(ms, time_to_expire=0.05)

        self.assertIs(result, reply)
        self.assertEqual(client._new_msgs, [])
        self.assertEqual(client._waiting_amount, 0)
        self.assertTrue(any("was already in the mailbox" in msg for msg in log_ctx.output))

    async def test_no_reply_still_raises_timeout(self):
        """No reply anywhere -> CommunicationTimeoutError is still raised."""
        client = self._make_client()
        ms = self._make_envelope(create_time=time.time(), msg_id=2)

        self._patch_wait_for_psce(schedule_append=None)

        with self.assertRaises(CommunicationTimeoutError):
            await client._send_to_server(ms, time_to_expire=0.05)

        self.assertEqual(client._new_msgs, [])
        self.assertEqual(client._waiting_amount, 0)

    async def test_foreign_reply_in_mailbox_is_not_mistaken(self):
        """Mailbox holds an envelope with another id at timeout -> still a timeout error, and the
        foreign envelope is left untouched in `_new_msgs`."""
        client = self._make_client()
        ms = self._make_envelope(create_time=time.time(), msg_id=3)
        foreign = self._make_envelope(create_time=time.time(), msg_id=999)

        self._patch_wait_for_psce(schedule_append=lambda: client._new_msgs.append(foreign))

        with self.assertRaises(CommunicationTimeoutError):
            await client._send_to_server(ms, time_to_expire=0.05)

        self.assertEqual(client._new_msgs, [foreign])
        self.assertEqual(client._waiting_amount, 0)


if __name__ == "__main__":
    unittest.main()
