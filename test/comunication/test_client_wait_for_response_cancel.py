import asyncio
import sys
import types
import unittest


def _install_obcom_stubs():
    if "obcom" in sys.modules:
        return

    obcom_module = types.ModuleType("obcom")
    comunication_module = types.ModuleType("obcom.comunication")
    base_module = types.ModuleType("obcom.comunication.base_zmq_communication_object")
    cycle_query_module = types.ModuleType("obcom.comunication.cycle_query")
    error_module = types.ModuleType("obcom.comunication.comunication_error")
    error_policy_module = types.ModuleType("obcom.comunication.error_policy")
    serializer_module = types.ModuleType("obcom.comunication.message_serializer")
    multipart_module = types.ModuleType("obcom.comunication.multipart_structure")
    obcom_module.__path__ = []
    comunication_module.__path__ = []

    class BaseZmqCommunicationObject:
        def __del__(self):
            return

    class CommunicationRuntimeError(RuntimeError):
        def __init__(self, message=""):
            super().__init__(message)

    class CommunicationTimeoutError(RuntimeError):
        pass

    class MessageSerializer:
        @staticmethod
        def pack_b(value):
            return str(value).encode()

    class MultipartStructure:
        pass

    class PeriodicCycleQuery:
        pass

    class ConditionalCycleQuery:
        pass

    class Backoff:
        pass

    class Budget:
        pass

    class ErrorPolicy:
        pass

    class LogPolicy:
        pass

    class SeverityAction:
        pass

    class SeverityRule:
        pass

    base_module.BaseZmqCommunicationObject = BaseZmqCommunicationObject
    cycle_query_module.PeriodicCycleQuery = PeriodicCycleQuery
    cycle_query_module.ConditionalCycleQuery = ConditionalCycleQuery
    error_module.CommunicationRuntimeError = CommunicationRuntimeError
    error_module.CommunicationTimeoutError = CommunicationTimeoutError
    error_policy_module.Backoff = Backoff
    error_policy_module.Budget = Budget
    error_policy_module.ErrorPolicy = ErrorPolicy
    error_policy_module.LogPolicy = LogPolicy
    error_policy_module.SeverityAction = SeverityAction
    error_policy_module.SeverityRule = SeverityRule
    serializer_module.MessageSerializer = MessageSerializer
    multipart_module.MultipartStructure = MultipartStructure

    sys.modules["obcom"] = obcom_module
    sys.modules["obcom.comunication"] = comunication_module
    sys.modules["obcom.comunication.base_zmq_communication_object"] = base_module
    sys.modules["obcom.comunication.cycle_query"] = cycle_query_module
    sys.modules["obcom.comunication.comunication_error"] = error_module
    sys.modules["obcom.comunication.error_policy"] = error_policy_module
    sys.modules["obcom.comunication.message_serializer"] = serializer_module
    sys.modules["obcom.comunication.multipart_structure"] = multipart_module


_install_obcom_stubs()

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
        client.name = "test-client"
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
