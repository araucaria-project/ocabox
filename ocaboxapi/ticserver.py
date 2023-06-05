from __future__ import annotations
import logging
import time
from datetime import datetime
from typing import Callable, List
from ocaboxapi.telescopecomponent import Component, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class TicServer(Component):

    loglevel = OcaBoxParam(default=None, doc="Loglevel of the TIC server")
    loglevels = OcaBoxParam(default=None, doc="Named possible Loglevels of the TIC server")

    async def aget_loglevel(self) -> str:
        """Returns loglevel of the TIC server"""
        logger.debug(f'Getting loglevel from {self.my_address()}')
        ret = await self.aget_value('loglevel')
        return ret

    async def aput_loglevel(self, level: str|int) -> None:
        """Sets loglevel of the TIC server"""
        logger.debug(f'Setting loglevel to {level} from {self.my_address()}')
        await self.aput_value('loglevel', level=level)

    async def aget_loglevels(self) -> str:
        """Named possible Loglevels of the TIC server"""
        logger.debug(f'Getting loglevels from {self.my_address()}')
        ret = await self.aget_value('loglevels')
        return ret

    async def aput_shutdown(self) -> None:
        """Shutdown the TIC server (may restart if starts automatically)"""
        logger.debug(f'Shutting down {self.my_address()}')
        await self.aput_value('shutdown')