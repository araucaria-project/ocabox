import asyncio
import logging
from planrunner.subcommand import SubCommand

log = logging.getLogger(__name__.rsplit('.')[-1])


class MountSlewToAltAz(SubCommand):

    def __init__(self, id: str, parent: 'Command', **kwargs) -> None:
        self.subcommand_name = 'MountSlewToAltAz'
        self.telescope = parent.telescope
        self.id = id
        self.mount = self.telescope.get_mount('mount')
        self.kwargs = kwargs
        super().__init__(id=self.id, parent=parent, subcommand_name=self.subcommand_name, **kwargs)

    async def _wait_to_slew(self) -> None:
        while True:
            az = self.mount.azimuth
            alt = self.mount.altitude
            await asyncio.sleep(1)
            if (abs(az - self.kwargs["az"])<0.05) and (abs(alt - self.kwargs["alt"])<0.05):
                log.info(f'{self.id} {self.subcommand_name} is done')
                self.info_callback['stream_1'](f'Subcommand {self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                break

    async def arun(self, step_id: str or None = None) -> None:
        log.info(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](
            f'Subcommand {self.id} {self.subcommand_name} ALT:{self.kwargs["alt"]} AZ:{self.kwargs["az"]} started')
        await self.mount.aput_tracking(False)
        await self.mount.aput_slewtoaltaz_async(self.kwargs["az"], self.kwargs["alt"])
        await self._wait_to_slew()
        await asyncio.sleep(5)