import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.coordinates import ra_to_decimal, dec_to_decimal

log = logging.getLogger(__name__.rsplit('.')[-1])


class MountSlewCoo(SubCommand):

    def __init__(self, id: str, parent: 'Command', **kwargs) -> None:
        self.subcommand_name = 'MountSlewCoo'
        self.telescope = parent.telescope
        self.id = id
        self.mount = self.telescope.get_mount('mount')
        self.kwargs = kwargs
        super().__init__(id=self.id, parent=parent, subcommand_name=self.subcommand_name, **kwargs)

    async def _wait_to_slew(self) -> None:
        while True:
            ra = self.mount.rightascension
            dec = self.mount.declination
            await asyncio.sleep(1)
            if (abs(ra - ra_to_decimal(self.kwargs["ra"]))<0.05) and (abs(dec - dec_to_decimal(self.kwargs["dec"]))<0.05):
                log.debug(f'{self.id} {self.subcommand_name} is done')
                self.info_callback['stream_1'](f'Subcommand {self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                break

    async def arun(self, step_id: str or None = None) -> None:
        log.debug(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](
            f'Subcommand {self.id} {self.subcommand_name} OBJ:{self.kwargs["obj_name"]}'
            f' RA:{self.kwargs["ra"]} DEC:{self.kwargs["dec"]} started')
        # TODO tracking yes/no
        await self.mount.aput_tracking(True)
        await self.mount.aput_slewtocoo_async(ra_to_decimal(self.kwargs["ra"]), dec_to_decimal(self.kwargs["dec"]))
        await self._wait_to_slew()
        await asyncio.sleep(5)