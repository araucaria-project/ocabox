from __future__ import annotations

import logging
from typing import Callable, Optional

import param

from ocaboxapi.abstelescope import AbstractTelescope
from ocaboxapi.component import Component, OcaBoxParam

logger = logging.getLogger('telcomponent')


class TelescopeComponent(Component):
    id = param.String()
    connected = OcaBoxParam(default=False, doc="Is component connected")
    name = OcaBoxParam(default='', doc="Component name")
    description = OcaBoxParam(default='', doc="Component description")

    def __init__(self, **params):
        if 'telescope' not in params:
            raise ValueError('TelescopeComponent must have telescope parameter')
        self.telescope: AbstractTelescope = params['telescope']
        del params['telescope']
        if 'observatory' not in params:
            params['observatory'] = self.telescope.observatory
        super().__init__(**params)

    @property
    def tel_addr(self) -> str:
        return self.telescope.tel_addr

    def my_address(self):
        """ Return address of this component """
        return f'{self.tel_addr}.{self.id}'

    async def asubscribe_connected(self, callback: Optional[Callable] = None,
                                   time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing connected from {self.tel_addr}')
        await self.subscribe('connected', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_connected(self) -> bool:
        logger.debug(f'Getting  connected from {self.tel_addr}')
        ret = await self.aget_value('connected')
        return ret

    async def aput_connect(self, connect: bool):
        logger.debug(f'Putting  connect = {connect} to {self.tel_addr}')
        await self.aput_value('connected', Connected=connect)

    async def asubscribe_name(self, callback: Optional[Callable] = None,
                              time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing name from {self.tel_addr}')
        await self.subscribe('name', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_name(self) -> str:
        logger.debug(f'Getting name from {self.tel_addr}')
        ret = await self.aget_value('name')
        return ret

    async def asubscribe_description(self, callback: Optional[Callable] = None,
                                     time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing description from {self.tel_addr}')
        await self.subscribe('description', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_description(self) -> str:
        logger.debug(f'Getting  description from {self.tel_addr}')
        ret = await self.aget_value('description')
        return ret
