from abc import ABC, abstractmethod

import obs_pln_parser.command_Sequence


class Command(ABC):
    _NAME = "DEFAULT"

    def __int__(self, kw_args: dict, ln: str, commands: list = None, label: str = "", message: str = "", **kwargs):
        self._kwargs: dict = {}
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

    MAP_COMMANDS: dict = {
        "SEQUENCE": obs_pln_parser.command_Sequence.CommandSequence,
    }