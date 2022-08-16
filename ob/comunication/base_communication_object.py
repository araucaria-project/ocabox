import logging
import time

import confuse
from abc import ABC
from typing import List

from ob.comunication.comunication_error import CommunicationTimeoutError
from ob.comunication.multipart_structure import MultipartStructure
from ob.ob_config import SingletonConfig
from zmq.asyncio import Context

logger = logging.getLogger(__name__)


class BaseCommunicationObject(ABC):
    DEFAULT_NAME = 'BaseCommunicationObject'
    _TYPE = 'default_communication_object'

    def __init__(self, name: str = None, port: int = None, **kwargs):
        self.name = name if name else self.DEFAULT_NAME
        self._port = port if port else self._get_cfg('port')
        if not self._port or not isinstance(self._port, int):
            logger.error(f"Can not get correct port for {self._TYPE}")
            raise RuntimeError
        # OMQ
        self.context = Context()
        self._front_socket = None
        # message service
        self.default_timeout = self._get_cfg('timeout')
        if self.default_timeout is None:
            logger.error(f"Can not find timeout value in settings")
            raise RuntimeError

    def _get_cfg(self, name_cfg: str, default=None, use_default_settings=True):
        """
        The method looks for a value in the configuration file and returns it.

        :param name_cfg: name of config value
        :param default: default value if key not exist in config
        :param use_default_settings: use default settings if default value is None and can not get settings
        :return: config value or None if method can't find it
        """
        try:
            value = SingletonConfig.get_config()[self._TYPE][self.name][name_cfg].get()
        except confuse.exceptions.NotFoundError:
            if default is None and use_default_settings:
                try:
                    value = SingletonConfig.get_config()[self._TYPE][self.DEFAULT_NAME][name_cfg].get()
                except confuse.exceptions.NotFoundError:
                    value = default
            else:
                value = default
        return value

    @staticmethod
    def _open_envelope(multipart: List[bytes]) -> MultipartStructure:
        raise NotImplemented

    @staticmethod
    def _pack_to_envelope(target: List[bytes], create_time: bytes, msg_id: bytes, request_timeout: bytes,
                          data_b: list) -> MultipartStructure:
        """

        :param target: address of clients should be one address or many witch empty byte separate.
        :param create_time: request create time
        :param msg_id: request id
        :param data_b: list sub-requests
        :return: multipart
        """
        raise NotImplemented

    def _get_time_to_expire(self, ms: MultipartStructure, use_default=False):
        """
        This method looks for the timeout value in multipart and returns it if it is not obsolete, otherwise it throws
        a CommunicationTimeoutError exception.

        :param ms: MultipartStructure object
        :param use_default: When set to true the default value will be taken if multipart does not contain a timeout
        value.
        :raise CommunicationTimeoutError: When the timeout value is obsolete
        :return: time to expire
        """
        try:
            time_to_expire = ms.time_to_expire()
        except CommunicationTimeoutError:
            if not use_default:
                raise
            time_to_expire = self.default_timeout

        if time_to_expire <= 0:
            raise CommunicationTimeoutError(message='The received message is already outdated.')
        return time_to_expire

    def __del__(self):
        self.context.destroy()  # without this zmq not close socket when BaseCommunicationObject is destroyed
