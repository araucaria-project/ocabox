import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.coordinates import deg_to_decimal_deg
logger = logging.getLogger(__name__.rsplit('.')[-1])
import time

class MountSlewToAltAz(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str or None = None, **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.id = id
        self.mount = self.telescope.get_mount('mount')
        self.kwargs = kwargs
        self.alt: float = 0.0
        self.az: float = 0.0
        super().__init__(id=self.id, parent=parent, subcommand_name=subcommand_name, **kwargs)

    async def _wait_to_slew(self) -> None:
        t_start = time.time()
        while True:
            await self.subcommand_timeout(t_start)
            az = self.mount.azimuth
            alt = self.mount.altitude
            await asyncio.sleep(1)
            if (abs(az - self.az)<0.5) and (abs(alt - self.alt)<0.5):
                await self.mount.aput_tracking(False)
                await self.mount.aput_slewtoaltaz_async(self.az, self.alt)
                await self.mount.aput_tracking(False)
                logger.info(f'{self.id} {self.subcommand_name} is done')
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                break

    async def arun(self, step_id: str or None = None) -> int:
        logger.info(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](
            f'{self.id} {self.subcommand_name} ALT:{self.kwargs["alt"]} AZ:{self.kwargs["az"]} started')
        if isinstance(self.kwargs["alt"], str) and isinstance(self.kwargs["az"], str):
            self.az = deg_to_decimal_deg(self.kwargs["az"])
            self.alt = deg_to_decimal_deg(self.kwargs["alt"])
        elif isinstance(self.kwargs["alt"], float) and isinstance(self.kwargs["az"], float):
            self.az = self.kwargs["az"]
            self.alt = self.kwargs["alt"]
        else:
            return 1
        if self.alt > 0:
            await self.mount.aput_tracking(False)
            await self.mount.aput_unpark()
            await self.mount.aput_slewtoaltaz_async(self.az, self.alt)
            await self.mount.aput_tracking(False)
            await self._wait_to_slew()
            await self.mount.aput_tracking(self.kwargs["tracking"])
            await asyncio.sleep(5)
            return 0
        else:
            return 1