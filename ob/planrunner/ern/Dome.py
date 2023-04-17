import asyncio
import logging

from ob.data_colection.resource_manager.resource_manager import AccessResourceManager

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Dome:
    RESOURCE_NAME = AccessResourceManager.DOME

    def __init__(self, nr: int, ra: str, dec: str, subcommand_name: str = 'dome slew coo', **kwargs) -> None:
        self.nr: int = nr
        self.subcommand_name = subcommand_name
        self.kwargs = kwargs
        self.ra: str = ra
        self.dec: str = dec
        super().__init__(**kwargs)

    async def wait_to_slew(self) -> bool:
        # tu czekamy na pozycję
        await asyncio.sleep(1)
        return True

    async def go_to_position(self):
        # tu wysyłamy put żeby teleskop się ustawił na pozycję
        return True
