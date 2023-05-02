import asyncio
import logging
import time

import param
from astropy.time import Time

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest

logger = logging.getLogger(__name__.rsplit('.')[-1])

param.parameterized.async_executor = lambda f: asyncio.create_task(f())

class EphemerisData(param.Parameterized):
    utc = param.Number(default=None, doc="UTC time timestamp")

    def __init__(self, **params):
        super().__init__(**params)
        self.task = None
        self.stop_runing_event = asyncio.Event()

    def run(self):
        self.stop_runing_event = asyncio.Event()
        logger.info(f'Starting {self}')
        try:
            self.task = asyncio.create_task(self._run())
        except Exception as e:
            logger.error(f'Error starting {self}: {e}')
            raise

    async def _run(self):
        logger.info(f'Task starting {self}')
        while not self.stop_runing_event.is_set():
            t = Time.now()
            self.utc = t.utc.unix

            await asyncio.wait([self.stop_runing_event.wait(), asyncio.sleep(1)],
                               return_when=asyncio.FIRST_COMPLETED)

    def stop(self):
        self.stop_runing_event.set()
        if self.task is not None:
            t = self.task
            self.task = None
            asyncio.run(t)
            logger.info(f'Stopped {self}')
        else:
            logger.warning('Task EphemerisData is not running, so it can not be stopped')

    def __del__(self):
        self.stop()



class TreeEphemeris(TreeProvider):
    """
    This module provides current information about sky position of the celestial object and current time in  various timescales.
    address commands:
        - method1 - do stuff 1
        - method2 - do stuff 2
    """

    def __init__(self, component_name: str, source_name: str, **kwargs):
        self.data = EphemerisData()
        # self.data.run()
        self.data.param.watch(self.on_utc_changed, 'utc')
        super().__init__(component_name=component_name, source_name=source_name, subcontractor=None, **kwargs)
        logger.info(f'Created {self}')

    async def on_utc_changed(self, event: param.Event):
        logger.debug(f'UTC changed to {self.data.utc}')
        # TODO: send notification to subscribers, or update cache value?

    async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
        user = request.user
        request_type = request.request_type
        try:
            command = request.address[request.index]
        except IndexError:
            raise AddressError(code=1001, message='The address does not contain a command.')

        if command == 'utc':
            # t = Time.now()
            # return Value(v=t.utc.unix, ts=time.time())
            return Value(v=self.data.utc, ts=time.time())

        if command == 'method2':
            timeout_control = "response string"
            return Value(v=timeout_control, ts=time.time())
        raise AddressError(code=1002, message=f'Unrecognised method for module {self.get_name()}')

    async def run(self):
        self.data.run()
        return await super().run()

    async def stop(self):
        self.data.stop()
        return await super().stop()




