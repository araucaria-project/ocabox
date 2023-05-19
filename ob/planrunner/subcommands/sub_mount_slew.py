import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.coordinates import ra_to_decimal, dec_to_decimal, ra_dec_epoch, ra_dec_2_az_alt, deg_str_to_deg

logger = logging.getLogger(__name__.rsplit('.')[-1])


class MountSlew(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'mount-slew', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.id = id
        self.mount = self.telescope.get_mount()
        self.kwargs = kwargs
        self.ra_now: str or None = None
        self.dec_now: str or None = None
        self.alt: float
        self.az: float
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name,
                         started=self.started, done=self.done, skipped=self.skipped, **kwargs)

    async def _wait_to_slew_coo(self) -> None:
        await asyncio.sleep(1)
        while True:
            ra = self.mount.rightascension
            dec = self.mount.declination
            slew = self.mount.slewing
            await asyncio.sleep(0.5)
            if (abs(ra - ra_to_decimal(self.ra_now)) < 0.05) and \
                    (abs(dec - dec_to_decimal(self.dec_now)) < 0.05) and (slew == False):
                break

    async def _wait_to_slew_alt_az(self) -> None:
        await asyncio.sleep(1)
        while True:
            az = self.mount.azimuth
            alt = self.mount.altitude
            slew = self.mount.slewing
            await asyncio.sleep(0.5)
            if (abs(az - self.az)<1) and (abs(alt - self.alt)<1) and (slew == False):
                await self.mount.aput_tracking(False)
                await self.mount.aput_slewtoaltaz_async(self.az, self.alt)
                await self.mount.aput_tracking(False)
                break

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        logger.info(f'{self.id} started')
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} OBJ:{self.kwargs["obj_name"]} started')

        # TODO This OCA should be taken from settings
        OCA = {'latitude': '-24:35:53', 'longitude': '-70:11:47', 'elevation': '2817'}
        # TODO mount_min_alt should be taken from settings
        mount_min_alt = 14.9

        if 'alt' and 'az' in self.kwargs.keys():
            logger.debug(f'{self.id} started --> AltAz')
            try:
                self.az = float(self.kwargs["az"])
                self.alt = float(self.kwargs["alt"])
            except ValueError:
                try:
                    self.az = deg_str_to_deg(self.kwargs["az"])
                    self.alt = deg_str_to_deg(self.kwargs["alt"])
                except ValueError:
                    self.skipped = True
                    self.info_callback['exec_json'](self.exec_json())
                    logger.error(f"Wrong az alt format")
                    return 1
            if self.alt > mount_min_alt:
                await self.mount.aput_tracking(False)
                await self.mount.aput_slewtoaltaz_async(self.az, self.alt)
                await self.mount.aput_tracking(False)
                await self._wait_to_slew_alt_az()
                if "tracking" in self.kwargs.keys():
                    await asyncio.sleep(5)
                    await self.mount.aput_tracking(self.kwargs["tracking"])
                    self.info_callback['stream_1'](
                        f'{self.id} {self.subcommand_name} tracking={self.kwargs["tracking"]}')
                logger.info(f'{self.id} done')
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                self.done = True
                self.info_callback['exec_json'](self.exec_json())
                return 0
            else:
                self.info_callback['stream_1'](f'{self.id} target is below allowed alt:{self.alt}, skipping')
                self.info_callback['stream_5'](f'{self.id}')
                self.skipped = True
                logger.info(f'{self.id} target is below allowed alt:{self.alt}, skipping')
                self.info_callback['exec_json'](self.exec_json())
                return 1

        elif 'ra' and 'dec' in self.kwargs.keys():
            logger.debug(f'{self.id} started --> RaDec')
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
            if deg_str_to_deg(alt) > mount_min_alt:
                await self.mount.aput_tracking(True)
                await self.mount.aput_slewtocoo_async(ra_to_decimal(self.ra_now), dec_to_decimal(self.dec_now))
                await self._wait_to_slew_coo()
                logger.info(f'{self.id} done')
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                self.done = True
                self.info_callback['exec_json'](self.exec_json())
                return 0
            else:
                self.info_callback['stream_1'](f'{self.id} target is below allowed alt:{alt}, skipping')
                self.info_callback['stream_5'](f'{self.id}')
                self.skipped = True
                self.info_callback['exec_json'](self.exec_json())
                logger.info(f'{self.id} target is below allowed alt:{alt}, skipping')
                return 1
        else:
            self.info_callback['stream_1'](f'{self.id} no coordinates, skipping')
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json())
            logger.info(f'{self.id} no coordinates, intend to skip')
            return 0


