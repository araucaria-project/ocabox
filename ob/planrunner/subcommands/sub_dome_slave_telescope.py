import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
import time

logger = logging.getLogger(__name__.rsplit('.')[-1])


class DomeSlaveTelescope(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'dome slave telescope', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.mount = self.telescope.get_mount('mount')
        self.dome = self.telescope.get_dome('dome')
        self.kwargs = kwargs
        self.id = id
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name, **kwargs)

    async def _wait_to_slew(self) -> None:
        t_start = time.time()
        while True:
            await self.subcommand_timeout(t_start)
            mount_az = self.mount.azimuth
            dome_az = self.dome.azimuth
            await asyncio.sleep(1)
            if (abs(mount_az - dome_az) < 0.05):
                logger.debug(f'{self.id} {self.subcommand_name} is done')
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                break

    async def arun(self, step_id: str or None = None) -> int:
        logger.debug(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} started')
        mount_az = self.mount.azimuth
        # TODO maybe use synctoazimuth (if yes add to ocaboxapi)
        await self.dome.aput_slewtoazimuth(mount_az)
        await self._wait_to_slew()
        await asyncio.sleep(5)
        return 0
