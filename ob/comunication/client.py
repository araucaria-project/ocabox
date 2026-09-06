import asyncio
import logging
import time
import zmq
from contextlib import suppress
from typing import List
from obcom.comunication.base_zmq_communication_object import BaseZmqCommunicationObject
from obcom.comunication.comunication_error import CommunicationRuntimeError, CommunicationTimeoutError
from obcom.comunication.message_serializer import MessageSerializer
from obcom.comunication.multipart_structure import MultipartStructure

from ob.util_functions.asyncio_util_functions import wait_for_psce

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Client(BaseZmqCommunicationObject):
    DEFAULT_NAME = 'DefaultClient'
    TYPE = 'client'
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = "5559"
    DEFAULT_PROTOCOL = "tcp"

    def __init__(self, name: str = None, port: int = None, host: str = None, **kwargs):
        port = port if port is not None else self.DEFAULT_PORT
        super().__init__(name=name, port=port, **kwargs)
        # connection data
        self._host = host if host else self.DEFAULT_HOST
        if not self._host or not isinstance(self._host, str):
            logger.error(f"Can not get correct host ({self._host}) for {self.TYPE}")
            raise RuntimeError
        self._protocol = self.DEFAULT_PROTOCOL
        if not self._host or not isinstance(self._host, str):
            logger.error(f"Can not get correct protocol ({self._protocol}) for {self.TYPE}")
            raise RuntimeError
        # OMQ
        self._front_socket = self.context.socket(zmq.DEALER)
        # IMPORTANT Pending messages shall be discarded immediately when the socket is closed
        self._front_socket.setsockopt(zmq.LINGER, 0)
        connect_string = f"{self._protocol}://{self._host}:{self._port}"
        self._front_socket.connect(connect_string)
        logger.info(f'Connecting to TIC server at {connect_string}')
        # message service
        self._msg_con = None
        self._recv_lock = None
        self._new_msgs: List[MultipartStructure] = []
        self._cleaning_length = 10
        self._create_time = 0
        self._next_id: int = 0
        self._receive_task: asyncio.Task or None = None
        self._is_working_receive_task = False
        self._loop = None
        self._waiting_amount = 0

    def _get_loop(self):
        """
        :raise CommunicationRuntimeError
        :return: asyncio.Loop
        """
        if self._loop is None:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # this shouldn't happen
                logger.error(f"Can not get current async loop, something goes wrong. "
                             f"Check that you are not trying to use the same client in 2 different threads")
                raise CommunicationRuntimeError(message='Can not get current async loop')
            self._loop = loop
        return self._loop

    @property
    def _msg_condition(self) -> asyncio.Condition:
        """Warning Can be used only when async loop is already created in background otherwise it creates a new loop"""
        self._get_loop()  # init a loop property
        if self._msg_con is None:
            self._msg_con = asyncio.Condition()
            logger.debug(f"<{self.TYPE}><{self.name}> created condition")
        return self._msg_con

    @property
    def _receiver_lock(self) -> asyncio.Lock:
        """Warning Can be used only when async loop is already created in background otherwise it creates a new loop"""
        self._get_loop()  # init a loop property
        if self._recv_lock is None:
            self._recv_lock = asyncio.Lock()
            logger.debug(f"<{self.TYPE}><{self.name}> created receiver lock")
        return self._recv_lock

    def _get_msg_create_time(self) -> bytes:
        """
        Create and return message timestamp. This is needed to distinguish between incoming messages.
        It is used like id.

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

    async def _send_to_server(self, ms: MultipartStructure, time_to_expire: float,
                              no_wait: bool = False) -> MultipartStructure or None:
        """

        :param ms:
        :param no_wait:
        :raise CommunicationRuntimeError:
        :raise CommunicationTimeoutError:
        :return: MultipartStructure or None
        """
        logger.debug(f"<{self.TYPE}><{self.name}> sending request... ({ms.create_time} | {ms.id_})")
        sending_result = await self._front_socket.send_multipart(ms.multipart)
        logger.debug(f"<{self.TYPE}><{self.name}> message was send. The request ID: ({ms.create_time} | {ms.id_})")
        if not no_wait:
            try:
                await self._stand_in_line()  # can raise CommunicationRuntimeError
                try:
                    # WARNING: do not use the 'asyncio.wait_for()' method, instead use 'wait_for_psce()'
                    # read more in the method description !!!
                    return await wait_for_psce(self._wait_for_response(ms.create_time, ms.id_), timeout=time_to_expire)
                except asyncio.TimeoutError:
                    # The timer and the receiver's callbacks can be due at the same wake-up if the local event
                    # loop was blocked (busy TOI/Qt work, image rendering, etc.). In that case the reply may
                    # already be sitting in the mailbox even though the timer fired first. Yield one loop turn
                    # so a `recv_multipart` future that resolved during the freeze lets '_receive_msgs' run its
                    # append step, then check the mailbox before declaring the router silent.
                    await asyncio.sleep(0)  # let a pending _receive_msgs append step run
                    message = self._take_message_from_mailbox(ms.create_time, ms.id_)
                    if message is not None:
                        logger.debug(f"<{self.TYPE}><{self.name}> reply for ({ms.create_time} | {ms.id_}) was "
                                     f"already in the mailbox when the timer fired — local loop lag, not a "
                                     f"timeout")
                        return message
                    # logger.info(f"the response did not come before timeout {self.timeout}s")
                    raise CommunicationTimeoutError(
                        message=f"Timeout of {time_to_expire:.3}s expired when waiting for response from TIC server {self._front_socket.LAST_ENDPOINT}")
                except CommunicationRuntimeError:
                    raise
            except CommunicationRuntimeError:
                raise
            finally:
                await self._skip_the_line()
        else:
            return None

    async def _wait_for_response(self, msg_create_time_b: bytes, msg_id_b: bytes) -> MultipartStructure:
        logger.debug(f"<{self.TYPE}><{self.name}> waiting for response...")
        condition = self._msg_condition
        if condition is None:
            logger.debug(f"<{self.TYPE}><{self.name}> in wait for response _msg_condition is None")
            raise CommunicationRuntimeError(message=f"The condition has not been set")

        try:
            async with condition:
                while True:
                    if not self._receive_task or self._receive_task.done() or not self._is_working_receive_task:
                        logger.error(f"The receive task was stopped before retrieve some waiting messages")
                        raise CommunicationRuntimeError(message=f"The receive task was stopped before retrieve some waiting"
                                                                f"messages")
                    # first check if the message is already there
                    message = self._take_message_from_mailbox(msg_create_time_b, msg_id_b)
                    if message:
                        logger.debug(f"<{self.TYPE}><{self.name}> response comes")
                        break
                    await condition.wait()
                    await asyncio.sleep(0)  # this will allow other tasks to do something
        except RuntimeError as error:
            current_task = asyncio.current_task()
            current_task_cancelling = getattr(current_task, "cancelling", None)
            if current_task is not None and callable(current_task_cancelling) and current_task_cancelling() > 0:
                raise asyncio.CancelledError() from error
            raise
        return message

    def _take_message_from_mailbox(self, create_time_b: bytes, id_b: bytes) -> MultipartStructure or None:
        """
        Look into the mailbox for a message matching (create_time_b, id_b) and, if found, remove it from
        '_new_msgs' and return it. This is the single place that removes a matched message from the mailbox,
        used both by '_wait_for_response' (normal path) and '_send_to_server' (post-timeout mailbox check).

        :return: MultipartStructure or None
        """
        message = self._check_message_comes(create_time_b, id_b)
        if message is not None:
            self._new_msgs.remove(message)
        return message

    async def _receive_msgs(self):
        try:
            self._is_working_receive_task = True
            while True:
                multipart = await self._front_socket.recv_multipart()
                try:
                    if len(self._new_msgs) >= self._cleaning_length:
                        self._clear_old_msg()
                    ms = self._open_envelope(multipart)
                    logger.debug(f"<{self.TYPE}><{self.name}> new message comes to client socket")
                    self._new_msgs.append(ms)
                except ValueError:
                    logger.error(f"<{self.TYPE}><{self.name}> received message is corrupted, it will be discarded.")
                condition = self._msg_condition
                async with condition:
                    condition.notify_all()
                await asyncio.sleep(0)  # this will allow other tasks to react
        # catch Cancelled of a task and set the flag to true to wake up all pending tasks and let them finish
        except asyncio.CancelledError:
            raise
        finally:
            self._is_working_receive_task = False
            condition = self._msg_condition
            async with condition:
                condition.notify_all()

    async def _stand_in_line(self):
        """

        :raise CommunicationRuntimeError:
        :return:
        """
        async with self._receiver_lock:
            self._waiting_amount += 1
            if not self._receive_task:
                await self._run_receiver()

    async def _skip_the_line(self):
        async with self._receiver_lock:
            self._waiting_amount -= 1
            if self._waiting_amount == 0:
                await self._stop_receiver()

    async def _run_receiver(self):
        """
        This method start receiver task

        :raise CommunicationRuntimeError:
        :return: None
        """
        loop = self._get_loop()
        self._receive_task = loop.create_task(self._receive_msgs())
        logger.debug(f"<{self.TYPE}><{self.name}> run receiver")

    async def _stop_receiver(self):
        """
        This method stop current receiver task

        :return: None
        """
        task = self._receive_task
        if task:
            task.cancel()
            logger.debug(f"<{self.TYPE}><{self.name}> stop receiver")
            self._receive_task = None
        # last query, wait for the receive task to close before returning a response.
        # IN CASE OF PERFORMANCE PROBLEMS, rethink the options witch 'await asyncio.sleep(0)'
        with suppress(asyncio.CancelledError):
            await task  # WARNING, If this fragment is removed, condition cannot be set to none
        if task.done():
            logger.debug(f"<{self.TYPE}><{self.name}> retrieve task was stopped")

    def _clear_old_msg(self):
        """This method cleaning the _new_msgs list from old messages witch no one wanting for."""
        for msg in self._new_msgs:
            if msg.is_expire():
                self._new_msgs.remove(msg)

    def _check_message_comes(self, create_time_b: bytes, id_b: bytes) -> MultipartStructure or None:
        for m in self._new_msgs:
            if m.create_time == create_time_b and m.id_ == id_b:
                return m
        return None

    async def send_multipart(self, list_part: List[bytes], request_timeout: float = None,
                             no_wait: bool = False) -> List[bytes] or None:
        """
        This method send request to server witch many sub-requests and return answer.

        :param no_wait: If 'true' than request will be sent and client will not wait for response
        :param request_timeout: waiting for answer timeout
        :param list_part: list single requests
        :raise CommunicationRuntimeError:
        :raise CommunicationTimeoutError:
        :return: list of responses
        """
        return await self._send_multipart(list_part=list_part, request_timeout=request_timeout, no_wait=no_wait)

    async def _send_multipart(self, list_part: List[bytes], request_timeout: float = None,
                              no_wait: bool = False, service_msg: bool = False) -> List[bytes] or None:
        """
        :param no_wait:
        :param request_timeout:
        :param list_part:
        :raise CommunicationRuntimeError:
        :raise CommunicationTimeoutError:
        :return:
        """
        # create message timestamp
        msg_create_time_b = self._get_msg_create_time()
        # create message id
        msg_id_b = self._get_msg_id()
        serv_msg_b = MessageSerializer.pack_b(service_msg)
        # create message timeout
        if request_timeout is None:
            request_timeout = time.time() + self.default_timeout
            logger.debug(f"Timeout will be set to the default value (The request will expire in {self.default_timeout} "
                        f"second)")
        request_timeout_b = MessageSerializer.pack_b(request_timeout)
        # TODO If some performance problems occurs, here it is place to change potentially unneeded deserialization
        ms = self._pack_to_envelope([], msg_create_time_b, msg_id_b, request_timeout_b, serv_msg_b, list_part)
        try:
            resp = await self._send_to_server(ms, time_to_expire=self._get_time_to_expire(ms), no_wait=no_wait)
        except CommunicationRuntimeError:
            raise
        except CommunicationTimeoutError:
            raise
        if not no_wait:
            return resp.data
        else:
            return None

    async def ping_server(self, request_timeout: float = None) -> None or float:
        """
        The method checks if the server is responding, if everything is ok it will return the response time.
        Otherwise, it will give None.

        :param request_timeout: waiting for answer timeout
        :return: None or time in milliseconds
        """
        request = {"command": "is_alive"}
        list_part = [MessageSerializer.pack_b(request)]
        start = time.time()
        try:
            response = await self._send_multipart(list_part=list_part, request_timeout=request_timeout,
                                                  service_msg=True, no_wait=False)
        except CommunicationTimeoutError:
            return None
        except CommunicationRuntimeError:
            return None
        end = time.time()
        if response and isinstance(response, list) and len(response) > 0:
            result = MessageSerializer.unpack_b(response[0])
            if result.get('response', False):
                r = (end - start)/1000
            else:
                logger.warning(f"the server returned corrupted data")
                r = None
        else:
            r = None
            logger.warning(f"the server returned corrupted data")
        return r

    async def reload_nats_config(self, request_timeout: float = None) -> bool:
        """
        The method sends a request to the server to resend the configuration to nats.

        :param request_timeout: waiting for answer timeout
        :return: result of request
        """
        out = False
        request = {"command": "reload_config"}
        list_part = [MessageSerializer.pack_b(request)]
        try:
            response = await self._send_multipart(list_part=list_part, request_timeout=request_timeout,
                                                  service_msg=True, no_wait=False)
        except (CommunicationTimeoutError, CommunicationRuntimeError):
            logger.warning(f"the server not response for reload_config request")
            return False

        if response and isinstance(response, list) and len(response) > 0:
            result = MessageSerializer.unpack_b(response[0])

            logger.debug(f"the server returned '{result.get('response')}' for reload_config request ")
            out = result.get('response', False)
        else:
            out = False
            logger.warning(f"the server returned corrupted data for request reload_config")
        return out

    async def send_singlepart(self, part: bytes, request_timeout: float = None, no_wait: bool = False) -> bytes:
        """
        This method send request to server witch one sub-request and return answer.

        :param no_wait: If 'true' than request will be sent and client will not wait for response
        :param request_timeout: waiting for answer timeout
        :param part: single requests
        :raise CommunicationRuntimeError:
        :raise CommunicationTimeoutError:
        :return: response
        """
        messages = await self.send_multipart([part], request_timeout=request_timeout, no_wait=no_wait)
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
    def _pack_to_envelope(target: List[bytes], create_time: bytes, msg_id: bytes, request_timeout: bytes,
                          service_msg: bytes, data_b: list) -> MultipartStructure:
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
        return MultipartStructure.from_parts(create_time=create_time, id_=msg_id, data=data_b, service_msg=service_msg,
                                             request_timeout=request_timeout, prefix_data=target)

    def __del__(self):
        self._front_socket.close()
        super().__del__()
