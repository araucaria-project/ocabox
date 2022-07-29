import asyncio
import logging
import time
import zmq
from typing import List
from ob.comunication.base_communication_object import BaseCommunicationObject
from ob.comunication.comunication_error import ClientRuntimeError, ClientTimeoutError
from ob.comunication.message_serializer import MessageSerializer
from ob.comunication.multipart_structure import MultipartStructure

logger = logging.getLogger(__name__)


class Client(BaseCommunicationObject):
    DEFAULT_NAME = 'DefaultClient'
    _TYPE = 'client'

    def __init__(self, name: str = None, port: int = None, **kwargs):
        super().__init__(name=name, port=port, **kwargs)
        # OMQ
        self._front_socket = self.context.socket(zmq.DEALER)
        self._front_socket.connect(f"{self._get_cfg('protocol')}://{self._get_cfg('url')}:{self._port}")
        # message service
        self._msg_event: asyncio.Event = asyncio.Event()
        self._new_msgs: List[MultipartStructure] = []
        self._create_time = 0
        self._next_id: int = 0
        self._receive_task: asyncio.Task or None = None
        self._loop = None
        self._waiting_amount = 0

    def _get_msg_create_time(self) -> bytes:
        """
        Create and return message timestamp

        :return: message timestamp
        """
        msg_create_time = int(time.time())
        if self._create_time != msg_create_time:
            self._next_id = 0
            self._create_time = msg_create_time
        return MessageSerializer.pack_b(msg_create_time)

    def _get_msg_id(self) -> bytes:
        """
        Create and return message id

        :return: message id
        """
        # create message id
        msg_id = self._next_id
        self._next_id += 1
        return MessageSerializer.pack_b(msg_id)

    async def _send_to_server(self, ms: MultipartStructure, no_wait: bool = False) -> MultipartStructure:
        """

        :param ms:
        :param no_wait:
        :raise ClientRuntimeError:
        :raise ClientTimeoutError:
        :return: MultipartStructure or None
        """
        logger.info(f"The {self._TYPE} named {self.name} is sending request...")
        sending_result = await self._front_socket.send_multipart(ms.multipart)
        logger.info(f"The {self._TYPE} named {self.name} sent the request")
        if not no_wait:
            try:
                await self._stand_in_line()  # ca raise RuntimeError
                try:
                    return await asyncio.wait_for(self._wait_for_response(ms.create_time, ms.id_), timeout=self.timeout)
                except asyncio.TimeoutError:
                    # logger.info(f"the response did not come before timeout {self.timeout}s")
                    raise ClientTimeoutError(message=f"The response did not come before timeout {self.timeout}s")
                except ClientRuntimeError:
                    raise
            except ClientRuntimeError:
                raise
            finally:
                await self._skip_the_line()
        raise ClientRuntimeError

    async def _wait_for_response(self, msg_create_time_b: bytes, msg_id_b: bytes) -> MultipartStructure:
        logger.info(f"The {self._TYPE} named {self.name} is waiting for response...")
        while True:
            if not self._receive_task or self._receive_task.done():  # sanity check
                logger.error(f"The receive task was stopped before retrieve some waiting messages")
                raise ClientRuntimeError(message=f"The receive task was stopped before retrieve some waiting messages")
            await asyncio.sleep(0)  # this will allow other tasks to change event
            await self._msg_event.wait()
            message = self._check_message_comes(msg_create_time_b, msg_id_b)
            if message:
                break
        self._new_msgs.remove(message)
        return message

    async def _receive_msgs(self):
        while True:
            multipart = await self._front_socket.recv_multipart()
            try:
                ms = self._open_envelope(multipart)
                self._new_msgs.append(ms)
            except ValueError:
                logger.error(f"The received message is corrupted, it will be discarded.")
            # this try is for situation when task will be canceled when sleep always should set event to false (clear)
            try:
                self._msg_event.set()
                await asyncio.sleep(0)  # this will allow other tasks to react to the event
            finally:
                self._msg_event.clear()

    async def _stand_in_line(self):
        """

        :raise ClientRuntimeError:
        :return:
        """
        self._waiting_amount += 1
        if not self._receive_task:
            await self._run_receiver()

    async def _skip_the_line(self):
        self._waiting_amount -= 1
        if self._waiting_amount == 0:
            await self._stop_receiver()

    async def _run_receiver(self):
        """
        This method start receiver task

        :raise ClientRuntimeError:
        :return: None
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # this shouldn't happen
            logger.error(f"Can not get current async loop, something goes wrong")
            raise ClientRuntimeError(message='Can not get current async loop')
        self._loop = loop
        self._receive_task = loop.create_task(self._receive_msgs())

    async def _stop_receiver(self):
        """
        This method stop current receiver task

        :return: None
        """
        task = self._receive_task
        if task:
            task.cancel()
            self._receive_task = None
            self._loop = None
            await asyncio.sleep(0)
            if task.done():
                logger.info(f"The retrieve task was stopped")

    def _check_message_comes(self, create_time_b: bytes, id_b: bytes) -> MultipartStructure or None:
        for m in self._new_msgs:
            if m.create_time == create_time_b and m.id_ == id_b:
                return m
        return None

    async def send_multipart(self, list_part: List[bytes], no_wait: bool = False) -> List[bytes]:
        """
        This method send request to server witch many sub-requests and return answer.

        :param no_wait: If 'true' than request will be sent and client will not wait for response
        :param list_part: list single requests
        :raise ClientRuntimeError:
        :raise ClientTimeoutError:
        :return: list of responses
        """
        # create message timestamp
        msg_create_time_b = self._get_msg_create_time()
        # create message id
        msg_id_b = self._get_msg_id()
        ms = self._pack_to_envelope([], msg_create_time_b, msg_id_b, list_part)
        try:
            resp = await self._send_to_server(ms, no_wait=no_wait)
        except ClientRuntimeError:
            raise
        except ClientTimeoutError:
            raise
        return resp.data

    async def send_singlepart(self, part: bytes, no_wait: bool = False) -> bytes:
        """
        This method send request to server witch one sub-request and return answer.

        :param no_wait: If 'true' than request will be sent and client will not wait for response
        :param part: single requests
        :raise ClientRuntimeError:
        :raise ClientTimeoutError:
        :return: response
        """
        messages = await self.send_multipart([part], no_wait=no_wait)
        return messages[0]

    @staticmethod
    def _open_envelope(multipart: List[bytes]) -> MultipartStructure:
        ms = MultipartStructure(multipart, 0)
        try:
            ms.validate()
        except ValueError as e:
            # envelope is damaged
            raise
        return ms

    @staticmethod
    def _pack_to_envelope(target: List[bytes], create_time: bytes, msg_id: bytes, data_b: list) -> MultipartStructure:
        """

        :param target: Not used. Always be empty []
        :param create_time: request create time
        :param msg_id: request id
        :param data_b: list sub-requests
        :return: multipart
        """
        target = []
        if not data_b:
            data_b = [b'']
            logger.warning(f'No data to send. Task send empty bit to router. ')
        return MultipartStructure.from_parts(create_time, msg_id, data_b, target)

# TODO dodać jakiś timeout do zapytań

# TODO zrobic kolejke w kliecie zeby byl asynchroniczny

# TODO get i put rozrozniac
