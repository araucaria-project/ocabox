import asyncio
import logging
import time
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.coordinates import ra_to_decimal, dec_to_decimal, ra_dec_epoch , ra_dec_2_az_alt, deg_str_to_deg

logger = logging.getLogger(__name__.rsplit('.')[-1])


class MountSlewCoo(SubCommand):


    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'mount-slew-coo', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.id = id
        self.mount = self.telescope.get_mount('mount')
        self.kwargs = kwargs
        self.ra_now: str or None = None
        self.dec_now: str or None = None
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)

    async def _wait_to_slew(self) -> None:
        t_start = time.time()
        while True:
            await self.subcommand_timeout(t_start)
            ra = self.mount.rightascension
            dec = self.mount.declination
            await asyncio.sleep(0.5)
            if (abs(ra - ra_to_decimal(self.ra_now))<0.05) and (abs(dec - dec_to_decimal(self.dec_now))<0.05):
                logger.debug(f'{self.id} {self.subcommand_name} done')
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                break

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        # TODO This OCA should be taken from settings
        OCA = {'latitude': '-24:35:53', 'longitude': '-70:11:47', 'elevation': '2817'}

        logger.debug(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](
            f'{self.id} {self.subcommand_name} OBJ:{self.kwargs["obj_name"]}'
            f' RA:{self.kwargs["ra"]} DEC:{self.kwargs["dec"]} started')
        self.ra_now, self.dec_now = ra_dec_epoch(ra=self.kwargs["ra"],
                                                  dec=self.kwargs["dec"],
                                                  latitude=OCA['latitude'],
                                                  longitude=OCA['longitude'],
                                                  elevation=OCA['elevation'],
                                                  epoch=self.kwargs['epoch'])
        az, alt = ra_dec_2_az_alt(ra=self.ra_now,
                                  dec=self.dec_now,
                                  latitude=OCA['latitude'],
                                  longitude=OCA['longitude'],
                                  elevation=OCA['elevation'],
                                  epoch=self.kwargs['epoch'])
        if deg_str_to_deg(alt) > 0:
            await self.mount.aput_tracking(True)
            await self.mount.aput_slewtocoo_async(ra_to_decimal(self.ra_now), dec_to_decimal(self.dec_now))
            await self._wait_to_slew()
            self.done = True
            self.info_callback['exec_json'](self.exec_json())
            return 0
        else:
            self.info_callback['stream_1'](f'{self.id} Target is below horizon alt:{alt}, intend to skip')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json())
            return 1