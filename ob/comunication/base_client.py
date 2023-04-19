import asyncio
import logging
from abc import ABC
from typing import List

from ob.comunication.base_communication_object import BaseCommunicationObject
from ob.comunication.multipart_structure import MultipartStructure

logger = logging.getLogger(__name__.rsplit('.')[-1])


class BaseClient(BaseCommunicationObject, ABC):
    DEFAULT_NAME = 'BaseClient'
    TYPE = 'client'

    def __init__(self, name: str = None, **kwargs):
        super().__init__(name=name, **kwargs)

        # # message service
        # self._msg_con = None
        # self._recv_lock = None
        # self._new_msgs: List[MultipartStructure] = []
        # self._cleaning_length = 10
        # self._create_time = 0
        # self._next_id: int = 0
        # self._receive_task: asyncio.Task or None = None
        # self._is_working_receive_task = False
        # self._loop = None
        # self._waiting_amount = 0
