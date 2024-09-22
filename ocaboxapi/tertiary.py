import logging

from ocaboxapi.telescopecomponent import TelescopeComponent

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Tertiary(TelescopeComponent):

    async def aput_selectnasmythport(self, position: int) -> None:
        logger.debug(f'Putting tertiary selectnasmythport to position {position} in {self.tel_addr}')
        await self.aput_value('selectnasmythport', Position=position)
