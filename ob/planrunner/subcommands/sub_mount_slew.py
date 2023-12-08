import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
from pyaraucaria.coordinates import ra_dec_epoch, ra_dec_2_az_alt, deg_to_decimal_deg
import random

logger = logging.getLogger(__name__.rsplit('.')[-1])


class MountSlew(SubCommand):

    def __init__(self, id: str, parent: 'Command', subcommand_name: str = 'mount-slew', **kwargs) -> None:
        self.subcommand_name = subcommand_name
        self.telescope = parent.telescope
        self.mount = self.telescope.get_mount()
        self.kwargs = kwargs
        self.ra_now: float or None = None
        self.dec_now: float or None = None
        self.alt: float
        self.az: float
        super().__init__(id=id, parent=parent, subcommand_name=subcommand_name, **kwargs)

    async def _wait_to_slew_coo(self, ra_in: float, dec_in: float) -> None:
        await asyncio.sleep(0.5)
        while True:
            ra = await self.value_proof_get(name='mount_ra', awaitab=self.mount.aget_ra, expect_type=float)
            dec = await self.value_proof_get(name='mount_dec', awaitab=self.mount.aget_dec, expect_type=float)
            slew = await self.value_proof_get(name='mount_slew', awaitab=self.mount.aget_slewing, expect_type=bool)
            await asyncio.sleep(0.5)
            if (abs(ra - ra_in) > 359.95 or (abs(ra - ra_in) < 0.05))\
                    and (abs(dec - dec_in) < 0.05) and (slew == False):
                break

    async def _wait_to_slew_alt_az(self, az_in: float, alt_in: float) -> None:
        await asyncio.sleep(0.5)
        while True:
            az = await self.value_proof_get(name='mount_az', awaitab=self.mount.aget_az, expect_type=float)
            alt = await self.value_proof_get(name='mount_alt', awaitab=self.mount.aget_alt, expect_type=float)
            slew = await self.value_proof_get(name='mount_slew', awaitab=self.mount.aget_slewing, expect_type=bool)

            if ((abs(az - az_in) > 359.0) or (abs(az - az_in)<1.0)) and (abs(alt - alt_in)<1.0) and (slew == False):
                await self.mount.aput_tracking(False)
                await self.mount.aput_slewtoaltaz_async(az=az_in, alt=alt_in)
                await asyncio.sleep(0.5)
                await self.mount.aput_tracking(False)
                break
            await asyncio.sleep(0.1)

    @staticmethod
    def ra_random_dither(ra: float, dith_val: float, mode: str = 'basic') -> float:
        # TODO dith_val = dith_val / cos(dec) ?
        if mode == 'basic':
            return ra + random.uniform(-dith_val / 60, dith_val / 60)

    @staticmethod
    def dec_random_dither(dec: float, dith_val: float, mode: str = 'basic') -> float:
        if mode == 'basic':
            return dec + random.uniform(-dith_val / 60, dith_val / 60)

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        if 'seq_data' in self.kwargs.keys():
            if self.kwargs['seq_data'].skip:
                self.skipped = True
                return 0
        self.info_callback['exec_json'](self.exec_json())
        logger.info(f'{self.id} started')
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} OBJ:{self.kwargs["obj_name"]} started')

        # TODO This OCA should be taken from settings
        OCA = {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}
        # TODO mount_min_alt should be taken from settings
        mount_min_alt = 14.9

        if 'alt' and 'az' in self.kwargs.keys():
            logger.debug(f'{self.id} started --> AltAz')
            try:
                self.az = float(self.kwargs["az"])
                self.alt = float(self.kwargs["alt"])
            except ValueError:
                try:
                    self.az = deg_to_decimal_deg(self.kwargs["az"])
                    self.alt = deg_to_decimal_deg(self.kwargs["alt"])
                except ValueError:
                    self.skipped = True
                    self.info_callback['exec_json'](self.exec_json())
                    logger.error(f"Wrong az alt format")
                    return 1
            if self.alt > mount_min_alt:
                logger.info(f'{self.id} alt:{self.alt}')
                #await self.mount.aput_unpark()
                await self.mount.aput_tracking(False)
                await self.mount.aput_slewtoaltaz_async(az=self.az, alt=self.alt)
                await self.mount.aput_tracking(False)
                await self._wait_to_slew_alt_az(az_in=self.az, alt_in=self.alt)
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
                                                     epoch=self.kwargs['epoch'])

            az, alt = ra_dec_2_az_alt(ra=self.ra_now,
                                      dec=self.dec_now,
                                      latitude=OCA['latitude'],
                                      longitude=OCA['longitude'],
                                      elevation=OCA['elevation'],
                                      epoch=self.kwargs['epoch'])
            logger.info(f'{self.id} alt:{alt}')
            if alt > mount_min_alt:
                #await self.mount.aput_unpark()
                await self.mount.aput_tracking(self.kwargs["tracking"])
                await self.mount.aput_slewtocoo_async(ra=float(self.ra_now), dec=float(self.dec_now))
                await self._wait_to_slew_coo(ra_in=float(self.ra_now), dec_in=float(self.dec_now))
                await self.mount.aput_tracking(self.kwargs["tracking"])
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

        elif 'dither' in self.kwargs.keys() and ('ra' and 'dec' not in self.kwargs.keys()):
            logger.debug(f'{self.id} started --> dither')
            ra_t = await self.value_proof_get(name='mount_ra', awaitab=self.mount.aget_ra, expect_type=float)
            dec_t = await self.value_proof_get(name='mount_dec', awaitab=self.mount.aget_dec, expect_type=float)
            ra_d = self.ra_random_dither(ra=ra_t,
                                         dith_val=self.kwargs["seq_data"].dither_distance,
                                         mode=self.kwargs["seq_data"].dither_mode)
            dec_d = self.dec_random_dither(dec=dec_t,
                                           dith_val=self.kwargs["seq_data"].dither_distance,
                                           mode=self.kwargs["seq_data"].dither_mode)
            await self.mount.aput_tracking(self.kwargs["tracking"])
            await self.mount.aput_slewtocoo_async(ra=ra_d, dec=dec_d)
            await self._wait_to_slew_coo(ra_in=ra_d, dec_in=dec_d)
            logger.info(f'{self.id} done')
            self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
            self.info_callback['stream_5'](f'{self.id}')
            self.done = True
            self.info_callback['exec_json'](self.exec_json())
            return 0

        else:
            self.info_callback['stream_1'](f'{self.id} no coordinates, skipping')
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json())
            logger.info(f'{self.id} no coordinates, intend to skip')
            return 0


