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
    # name = OcaBoxParam(default='', doc="Component name")
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

    @property
    def component_name(self) -> str:
        """The component's name in the telescope configuration."""
        return self.id

    @property
    def config(self) -> dict:
        """This component's configuration as TIC publishes it: ``tel.get_camera().config['camera_model']``."""
        return self.telescope.component_config(self.component_name)

    @property
    def kind(self) -> str | None:
        """``kind:`` of the component in the configuration (``camera``, ``filterwheel``, ``rotator`` …)."""
        return self.config.get('kind')

    @property
    def flags(self) -> tuple[str, ...]:
        """``flags:`` of the component in the configuration; empty when it has none."""
        return tuple(self.config.get('flags') or ())

    async def asubscribe_connected(self, callback: Optional[Callable] = None,
                                   time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing connected from {self.tel_addr}')
        return await self.subscribe('connected', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_connected(self, time_of_data_tolerance: float | None = None) -> bool:
        logger.debug(f'Getting  connected from {self.tel_addr}')
        ret = await self.aget_value('connected', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def aput_connect(self, connect: bool):
        logger.debug(f'Putting  connect = {connect} to {self.tel_addr}')
        await self.aput_value('connected', Connected=connect)

    async def asubscribe_name(self, callback: Optional[Callable] = None,
                              time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing name from {self.tel_addr}')
        return await self.subscribe('name', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_name(self, time_of_data_tolerance: float | None = None) -> str:
        logger.debug(f'Getting name from {self.tel_addr}')
        ret = await self.aget_value('name', time_of_data_tolerance=time_of_data_tolerance)
        return ret

    async def asubscribe_description(self, callback: Optional[Callable] = None,
                                     time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing description from {self.tel_addr}')
        return await self.subscribe('description', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_description(self, time_of_data_tolerance: float | None = None) -> str:
        logger.debug(f'Getting  description from {self.tel_addr}')
        ret = await self.aget_value('description', time_of_data_tolerance=time_of_data_tolerance)
        return ret

