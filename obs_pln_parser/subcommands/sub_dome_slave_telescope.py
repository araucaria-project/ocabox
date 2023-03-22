import asyncio
import logging
from obs_pln_parser.subcommand import SubCommand


log = logging.getLogger(__name__.rsplit('.')[-1])


class DomeSlaveTelescope(SubCommand):

    def __init__(self, id: str, parent: 'Command', **kwargs) -> None:
        self.subcommand_name = 'DomeSlaveTelescope'
        self.telescope = parent.telescope
        self.mount = self.telescope.get_mount('mount')
        self.dome = self.telescope.get_dome('dome')
        self.kwargs = kwargs
        self.id = id
        super().__init__(id=id, parent=parent, subcommand_name=self.subcommand_name, **kwargs)

    async def _wait_to_slew(self) -> None:
        while True:
            mount_az = self.mount.azimuth
            dome_az = self.dome.azimuth
            await asyncio.sleep(1)
            if (abs(mount_az - dome_az) < 0.05):
                log.debug(f'{self.id} {self.subcommand_name} is done')
                self.info_callback['stream_1'](f'Subcommand {self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                break

    async def arun(self, step_id: str or None = None) -> None:
        log.debug(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](f'Subcommand {self.id} {self.subcommand_name} started')
        mount_az = self.mount.azimuth
        # TODO maybe use synctoazimuth (if yes add to ocaboxapi)
        await self.dome.aput_slewtoazimuth(mount_az)
        await self._wait_to_slew()
        await asyncio.sleep(5)
