import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Command(ABC):
    _NAME = "DEFAULT"
    # --- arg keys ---
    _NAME_KEY = "command_name"
    _ARGS_KEY = "args"
    _KWARGS_KEY = "kwargs"

    def __init__(self, command_dict: dict, plan_data, previous_command, id_: str = None,
                 loop: asyncio.AbstractEventLoop = None,
                 **kwargs):
        self._loop = loop
        self._plan_data = plan_data
        if id_ is None:
            id_ = plan_data.generate_next_id()
        self._id = id_
        self.previous_command = previous_command
        self._command_dict: dict = command_dict

        # --- --- --- --- --- --- --- --- --- --- ---
        self._needed_modules = []
        self._finish_locking: Optional[asyncio.Future] = None
        self._finish: Optional[asyncio.Future] = None

    @property
    def res_mngr(self):
        return self._plan_data.access_resource_manager

    @property
    def plan_log(self) -> logging.Logger:
        return self._plan_data.plan_log

    @property
    def tsk_mngr(self):
        return self._plan_data.task_mngr

    @classmethod
    def get_name(cls) -> str:
        """Method returning a command name"""
        return cls._NAME

    def log(self, msg, lvl: Optional[int] = None):
        lvl = logging.DEBUG if lvl in None else lvl
        self.plan_log.log(msg=f"[{self._id}][{self.get_name()}] {msg}", level=lvl)

    def get_id(self):
        return self._id

    def get_kwargs(self) -> dict:
        """Method returns loaded kwargs"""
        return self._command_dict.get(self._KWARGS_KEY, {})

    def get_args(self) -> list:
        """Method returns loaded args"""
        return self._command_dict.get(self._ARGS_KEY, {})

    async def a_init(self):
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.error(f"Can not find running async loop.")
                raise  # todo może jakiś inny błąd?
        self._finish_locking = self._loop.create_future()
        self._finish = self._loop.create_future()

    async def wait_to_lock_all_resources(self):
        fut = self._finish_locking
        if fut is not None:
            await fut
        raise RuntimeError  # todo zrobić potem jakiś lokalny błąd

    async def wait_to_finish(self):
        fut = self._finish_locking
        if fut is not None:
            await fut
        raise RuntimeError  # todo zrobić potem jakiś lokalny błąd

    async def _wait_for_permission_to_locking(self):
        # No pre-command has been wired, so you can start right now
        if self.previous_command is None:
            return
        # wait for pre-command end
        await self.previous_command.wait_to_lock_all_resources()

    async def _wait_for_previous_command_finish(self):
        if self.previous_command is None:
            return
        await self.previous_command.wait_to_finish()

    def _unlock_next_command(self):
        if self._finish_locking is not None:
            self._finish_locking.set_result(True)  # all locks were used

    def _set_self_finish(self):
        if self._finish is not None:
            self._finish.set_result(True)  # all locks were used

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

    async def run(self):
        try:
            await self.a_init()
            if self._loop is None:
                # todo  ustawić status na skończony
                return
            await self._run_body()
        finally:
            self._unlock_next_command()  # unlock in the end
            self._set_self_finish()  # command finished

    @abstractmethod
    async def _run_body(self):
        pass
