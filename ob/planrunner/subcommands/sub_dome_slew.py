import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
import time


logger = logging.getLogger(__name__.rsplit('.')[-1])


class DomeSlew(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'dome-slew', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.dome = self.telescope.get_dome()
        self.mount = self.telescope.get_mount()
        self.kwargs = kwargs
        self.id = id
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)

    async def _wait_to_slew(self, azimuth) -> None:

        while True:

            dome_az = self.dome.azimuth
            dome_slewing = self.dome.slewing
            await asyncio.sleep(0.5)
            if dome_az is not None and dome_slewing==False:
                if (abs(azimuth - float(dome_az)))<2.0 or (abs(azimuth - float(dome_az)))>358.0:
                    logger.debug(f'{self.id} {self.subcommand_name} is done')
                    self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                    self.info_callback['stream_5'](f'{self.id}')
                    break

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        logger.debug(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} started')
        # TODO maybe use synctoazimuth (if yes add to ocaboxapi)
        if 'az' in self.kwargs.keys():
            az = self.kwargs['az']
        elif 'follow_tol' in self.kwargs.keys():
            if self.kwargs['follow_tol']<abs(self.mount.azimuth - self.dome.azimuth):
                az = self.mount.azimuth
            else:
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} no need')
                self.info_callback['stream_5'](f'{self.id}')
                self.skipped = True
                self.info_callback['exec_json'](self.exec_json())
                return 0
        else:
            az = self.mount.azimuth
        await self.dome.aput_slewtoazimuth(az)
        await self._wait_to_slew(az)
        self.done = True
        self.info_callback['exec_json'](self.exec_json())
        return 0
