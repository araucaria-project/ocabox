import asyncio
import logging
from abc import ABC, abstractmethod
from ob.data_colection.resource_manager.resource_manager import ResourceManager

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Command(ABC):
    _NAME = "DEFAULT"

    def __init__(self, kw_args: dict, ln: str, previous_command=None, commands: list = None, loop: asyncio.AbstractEventLoop = None, resource_manager: ResourceManager = None,
                 **kwargs):
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.error(f"Can not find running async loop.")
                raise  # todo może jakiś inny błąd?
        self._loop = loop
        # todo może resource_manager powinien się nazywać acces_menager
        self._res_m: ResourceManager = resource_manager
        self._needed_modules_list = []
        self._finish_locking: asyncio.Future = None
        self._finish: asyncio.Future = None
        self._kwargs: dict = {}
        self.previous_command = previous_command
        super().__init__(**kwargs)

    def get_kwargs(self) -> dict:
        """Method returns loaded kwargs"""
        return self._kwargs

    @classmethod
    def get_name(cls) -> str:
        """Method returning a command name"""
        return cls._NAME

    @abstractmethod
    def read_kwargs(self):
        pass

    async def a_init(self):
        self._finish_locking = self._loop.create_future()
        self._finish = self._loop.create_future()

    async def lock_all_resources(self):
        fut = self._finish_locking
        if fut is not None:
            await fut
        raise RuntimeError  # todo zrobić potem jakiś lokalny błąd