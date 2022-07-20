import asyncio
import datetime
import logging
import time

import zmq
from typing import List
from zmq.asyncio import Poller
from ob.comunication.base_communication_object import BaseCommunicationObject
from ob.comunication.message_id_deque import MessageIdDeque
from ob.comunication.message_serializer import MessageSerializer
from ob.comunication.multipart_structure import MultipartStructure
from ob.data_colection.value_call import ValueRequest, ValueResponse

logger = logging.getLogger(__name__)


class Client(BaseCommunicationObject):
    DEFAULT_NAME = 'DefaultClient'
    _TYPE = 'client'

    def __init__(self, name: str = None, port: int = None, **kwargs):
        super().__init__(name=name, port=port, **kwargs)
        # self._lock = asyncio.Lock()
        # request solver
        # OMQ
        self.frontend = self.context.socket(zmq.DEALER)
        self.frontend.connect(f"{self._get_cfg('protocol')}://{self._get_cfg('url')}:{self._port}")
        # message service
        self._msg_event = asyncio.Event()
        self._new_msgs = []
        self._create_time = 0
        self._next_id = 0

    async def get_async(self, address, timestamp: datetime or float or None = None, delta: float or None = None):
        request = ValueRequest(address=address, timestamp=timestamp, delta=delta)
        return await self.send_singlepart(request)

    def _get_msg_create_time(self) -> bytes:
        """
        Create and return message timestamp.
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

    async def _send_to_server(self, list_parts: List[bytes]) -> List[bytes]:
        # create message timestamp
        msg_create_time_b = self._get_msg_create_time()
        # create message id
        msg_id_b = self._get_msg_id()

        logger.info(f"The {self._TYPE} named {self.name} is sending request...")
        print(len(MultipartStructure.create_multipart(msg_create_time_b, msg_id_b, list_parts)))
        sending_result = await self.frontend.send_multipart(
            MultipartStructure.create_multipart(msg_create_time_b, msg_id_b, list_parts))

        logger.info(f"The {self._TYPE} named {self.name} is waiting for response...")
        while True:
            await self._msg_event.wait()
            message = self._check_message_comes(msg_create_time_b, msg_id_b)
            if message:
                break
        self._new_msgs.remove(message)

        return MultipartStructure.get_data(message)

    async def _receive_msgs(self):
        while True:
            multipart = await self.frontend.recv_multipart()
            self._new_msgs.append(multipart)
            self._msg_event.set()
            await asyncio.sleep(0)
            self._msg_event.clear()

    def _check_message_comes(self, create_time_b: bytes, id_b: bytes):
        for m in self._new_msgs:
            if MultipartStructure.get_create_time(m) == create_time_b and MultipartStructure.get_id(m) == id_b:
                return m
        return None

    async def send_multipart(self, list_part: List[ValueRequest]) -> List[ValueResponse]:
        """
        This method send request to server witch many sub-requests and return answer.

        :param list_part: list single requests
        :return: list of responses
        """
        list_byte_part = []
        for lp in list_part:
            list_byte_part.append(lp.to_byte())
        resp = await self._send_to_server(list_byte_part)
        response = []
        for r in resp:
            response.append(ValueResponse.from_byte(r))
        return response

    async def send_singlepart(self, part: ValueRequest) -> ValueResponse:
        """
        This method send request to server witch one sub-request and return answer.

        :param part: single requests
        :return: response
        """
        resp = await self._send_to_server([part.to_byte()])
        return ValueResponse.from_byte(resp[0])

# TODO dodać jakiś timeout do zapytań

# TODO zrobic kolejke w kliecie zeby byl asynchroniczny

# TODO get i put rozrozniac
