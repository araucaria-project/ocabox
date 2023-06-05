from __future__ import annotations

import inspect
import logging
import os
from logging.handlers import RotatingFileHandler

import time as time_module

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.coded_error import TreeOtherError
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest

logger = logging.getLogger(__name__.rsplit('.')[-1])

class TreeOcaboxController(TreeProvider):
    """
    This module Controls ocabox server itself
    """
    COMPONENT_DEFAULT_NAME = 'TreeOcaboxController'

    def __init__(self, component_name: str, source_name: str, **kwargs):
        super().__init__(component_name=component_name, source_name=source_name, subcontractor=None, **kwargs)
        logger.info(f'Created {self}')

    async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
        user = request.user
        request_type = request.request_type

        try:
            command = request.address[request.index]
        except IndexError:
            raise AddressError(code=1001, message='The address does not contain a command.')

        if command == 'loglevel':
            if request_type == 'PUT':
                try:
                    level: str|int = request.request_data['level']
                except KeyError:
                    raise TreeOtherError(code=4007,
                                         message=f'{self.get_name()}: Missing "level" parameter in {command} request.')
                try:
                    if isinstance(level, str):
                        level = level.upper()
                    logging.getLogger().setLevel(level)
                except ValueError:
                    raise TreeOtherError(code=4008,
                                         message=f'{self.get_name()}: Invalid "level" value ({level}) in {command} request.')
                logger.info(f'Loglevel set to {level} by commnd {command} from {user}')
            num_level = logging.getLogger().getEffectiveLevel()
            ret = logging.getLevelName(num_level)
            return Value(v=ret, ts=time_module.time())
        elif command == 'loglevels' and request_type == 'GET':
            ret = [n for v,n in sorted(logging._levelToName.items())]
            return Value(v=ret, ts=time_module.time())
        elif command == 'shutdown' and request_type == 'PUT':
            logger.error(f'Shut down requested, but it is not implemented yet')
            pass
        raise AddressError(code=1002,
                           message=f'Unrecognised method {request_type}:{command} for module {self.get_name()}')

    async def run(self):
        pass

    async def stop(self):
        pass
