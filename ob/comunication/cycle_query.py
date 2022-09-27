import asyncio
import logging
import time
from typing import List

from ob.comunication.comunication_error import CommunicationRuntimeError, CommunicationTimeoutError
from ob.data_colection.address import AddressError
from ob.data_colection.response_error import ResponseError
from ob.data_colection.value_call import ValueRequest, ValueResponse
from ob.ob_config import SingletonConfig

logger = logging.getLogger(__name__)


class CycleQuery:
    """
    This class represents a circular query. It can only be created in a running asynchronous event loop or elsewhere
    when the asynchronous event loop is delivered in an argument. the class provides a methods 'wait_for_response' and
    'get_response' thanks to which one can wait for the next message for any number of tasks.

    :param client: client object
    :param list_request: list of requests to cycle send
    :param delay: request delay, default is getting from config file
    :param loop: async loop
    :param log_missed_msg: If is False missed messages will be skipped. Default False
    :raise CommunicationRuntimeError: if not provide async loop and czn not get existing loop
    """
    def __init__(self, client, list_request: List[ValueRequest], delay: float or None = None, loop=None,
                 log_missed_msg: bool = False, **kwargs):
        self._client = client
        self._event: asyncio.Event = asyncio.Event()
        self._last_msg: List[bytes] or None = None
        if delay is None or delay <= 0:
            delay = SingletonConfig.get_config()['comunication'][type(self).__name__]['default_delay'].get()
        self._delay: float = delay
        self._max_missed_msg: int = 2
        self._task: asyncio.Task or None = None
        self._loop = loop
        self._set_loop()  # can raise CommunicationRuntimeError
        self._list_request: List[ValueRequest] = list_request
        self._errors = None
        self._log_missed_msg: bool = log_missed_msg

    # TODO co jeśli user zapomni zatrzymać petle? MIKOŁAJ

    async def wait_for_response(self) -> List[bytes]:
        """
        This method waits for the next recursive query and returns it when it comes as raw bytes.

        :raise CommunicationRuntimeError: when cycle request loop was stopped or message can't retrieve for other reason
        :return: new response as list of bytes
        """
        if not self.is_stopped() and not self._task.done():
            await self._event.wait()
            await asyncio.sleep(0)  # let main task set event to false before return control to client's tasks
            if self._errors:
                raise self._errors
            return self._last_msg
        raise CommunicationRuntimeError

    async def get_response(self) -> List[ValueResponse] or None:
        """
        This is a high level equivalent of the method 'wait_for_response'.

        :raise CommunicationRuntimeError: when cycle request loop was stopped or message can't retrieve for other reason
        :return: new response as object ValueResponse
        """
        resp = await self.wait_for_response()
        if resp is None:
            return None
        vr = []
        for r in resp:
            try:
                vr.append(ValueResponse.from_byte(r))
            except (ValueError, AddressError, TypeError):
                # can not create ValueRequest object (data is damaged) - return empty response witch error
                logger.info('Can not convert request dictionary to request object.')
                re = ResponseError(4001, 'Can not build request from ordered data', repr(self._client), 'CRITICAL')
                vr.append(ValueResponse('', None, False, re))
        return vr

    async def _send_message(self):
        missed = 0
        start_time = time.time()
        self._errors = None
        while True:
            wait_range = start_time + self._delay - time.time()
            if wait_range > 0:
                await asyncio.sleep(wait_range)
            start_time = time.time()
            # move request time of data tolerance
            self._change_time(start_time)
            # make query
            try:
                list_part = [r.to_byte() for r in self._list_request]
                result = await self._client.send_multipart(list_part=list_part,
                                                           request_timeout=start_time + self._delay)
                self._last_msg = result
                missed = 0
                self._event.set()
            except CommunicationRuntimeError as e:
                self._errors = e
                self._last_msg = None
                self._event.set()
                raise
            except CommunicationTimeoutError:
                missed += 1
                self._last_msg = None
                logger.warning(f'Message missed')
                if self._log_missed_msg:
                    self._event.set()
            except Exception:
                self._last_msg = None
                self._errors = CommunicationRuntimeError(message='Unrecognized error')
                self._event.set()
                raise
            if missed > self._max_missed_msg:
                logger.error("Too many missed messages at same time")
                self._errors = CommunicationRuntimeError(message='Too many missed messages at same time')
                self._event.set()
                break
            await asyncio.sleep(0)
            self._event.clear()

    def _change_time(self, time_now):
        for r in self._list_request:
            r.time_of_data = time_now

    def _run(self):
        self._task = self._loop.create_task(self._send_message())
        self._event.clear()

    def _set_loop(self):
        """

        :raise CommunicationRuntimeError:
        """
        if not self._loop:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.error(f"Can not get current async loop, something goes wrong")
                raise CommunicationRuntimeError(message='Can not get current async loop')

    def start(self):
        """
        Method starts cycle query if not started yet.
        """
        if self.is_stopped():
            self._run()
        else:
            logger.warning("This cycle query is already started")

    def stop(self):
        """Method stop cycle query."""
        if not self.is_stopped() and not self._task.done():
            self._task.cancel()
            self._event.set()

    def is_stopped(self):
        """
        Method return true if cycle query is actually running.

        :return: True if running
        """
        if self._task and self._task in asyncio.all_tasks(self._loop):
            return False
        return True

    def __del__(self):
        self.stop()
