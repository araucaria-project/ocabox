import asyncio
import logging
from abc import ABC

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Command(ABC):
    _NAME = "DEFAULT"
    _NAME_KEY = "command_name"
    _ARGS_KEY = "args"
    _KWARGS_KEY = "kwargs"

    def __init__(self, command_dict: dict, plan_data, id_: str = None, previous_command=None,
                 loop: asyncio.AbstractEventLoop = None,
                 **kwargs):
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.error(f"Can not find running async loop.")
                raise  # todo może jakiś inny błąd?
        self._loop = loop
        self._plan_data = plan_data
        if id_ is None:
            id_ = plan_data.generate_next_id()
        self._id = id_
        self.previous_command = previous_command
        self._command_dict: dict = command_dict

        # --- --- --- --- --- --- --- --- --- --- ---
        self._needed_modules_list = []
        self._finish_locking: asyncio.Future = None
        self._finish: asyncio.Future = None

    def get_resource_manager(self):
        return self._plan_data.resource_manager

    @classmethod
    def get_name(cls) -> str:
        """Method returning a command name"""
        return cls._NAME

    def get_kwargs(self) -> dict:
        """Method returns loaded kwargs"""
        return self._command_dict.get(self._KWARGS_KEY, {})

    def get_args(self) -> list:
        """Method returns loaded args"""
        return self._command_dict.get(self._ARGS_KEY, {})

    async def a_init(self):
        self._finish_locking = self._loop.create_future()
        self._finish = self._loop.create_future()

    async def lock_all_resources(self):
        fut = self._finish_locking
        if fut is not None:
            await fut
        raise RuntimeError  # todo zrobić potem jakiś lokalny błąd

    @staticmethod
    def build_command(dic, plan_data, id_: str = None, previous_command=None,
                      loop: asyncio.AbstractEventLoop = None, **kwargs):
        # todo pokombinować coś z __new__() w wolnej chwili
        command_map = plan_data.map_commands
        command_type = dic.get(Command._NAME_KEY, None)
        if command_type and command_type in command_map:
            command_class = command_map.get(command_type)(command_dict=dic, plan_data=plan_data, id_=id_,
                                                          previous_command=previous_command,
                                                          loop=loop, **kwargs)
        else:
            command_class = None
        return command_class
