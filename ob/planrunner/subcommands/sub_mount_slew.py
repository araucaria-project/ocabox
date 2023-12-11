import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand
from pyaraucaria.coordinates import ra_dec_epoch, ra_dec_2_az_alt, deg_to_decimal_deg
import random
from typing import Callable, Dict


logger = logging.getLogger(__name__.rsplit('.')[-1])


class MountSlew(BaseSubCommand):

    def __init__(self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
                 obj_name: str, uobi: int,
                 dither: bool or None = None, seq_data: 'Seq' or None = None,
                 ra: float or None = None, dec: float or None = None,
                 az: float or None = None, alt: float or None = None,
                 epoch: str or None = None, tracking: bool or None = None,
                 name: str = 'mount-slew') -> None:
        self.obj_name = obj_name
        self.seq_data = seq_data
        self.ra = ra
        self.dec = dec
        self.epoch = epoch
        self.tracking = tracking
        self.dither = dither
        self.alt = alt
        self.az = az
        self.ra_now: float or None = None
        self.dec_now: float or None = None
        super().__init__(id=id, info_callback=info_callback, telescope=telescope, name=name, uobi=uobi)
        self.mount = self.telescope.get_mount()
        self.info_dict = { 'obj_name': self.obj_name,
                            'seq_data': self.seq_data,
                            'ra': self.ra,
                            'dec': self.dec,
                            'epoch': self.epoch,
                            'tracking': self.tracking,
                            'dither': self.dither,
                            'alt': self.alt,
                            'az': self.az}
        self.create_sub_command_string(**self.info_dict)

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
        if self.seq_data:
            if self.seq_data.skip:
                self.skipped = True
                return 0
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        logger.info(f'{self.id} started')
        self.info_callback['stream_1'](f'{self.id} {self.name} OBJ:{self.obj_name} started')

        # TODO This OCA should be taken from settings
        OCA = {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}
        # TODO mount_min_alt should be taken from settings
        mount_min_alt = 14.9

        if self.alt is not None and self.az is not None:
            logger.debug(f'{self.id} started --> AltAz')
            try:
                az = float(self.az)
                alt = float(self.alt)
            except ValueError:
                try:
                    az = deg_to_decimal_deg(self.az)
                    alt = deg_to_decimal_deg(self.alt)
                except ValueError:
                    self.skipped = True
                    self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                    logger.error(f"Wrong az alt format")
                    return 1
            if alt > mount_min_alt:
                logger.info(f'{self.id} alt:{alt}')
                #await self.mount.aput_unpark()
                await self.mount.aput_tracking(False)
                await self.mount.aput_slewtoaltaz_async(az=az, alt=alt)
                await self.mount.aput_tracking(False)
                await self._wait_to_slew_alt_az(az_in=az, alt_in=alt)
                if self.tracking is not None:
                    await asyncio.sleep(5)
                    await self.mount.aput_tracking(self.tracking)
                    self.info_callback['stream_1'](
                        f'{self.id} {self.name} tracking={self.tracking}')
                logger.info(f'{self.id} done')
                self.info_callback['stream_1'](f'{self.id} {self.name} done')
                self.info_callback['stream_5'](f'{self.id}')
                self.done = True
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                return 0
            else:
                self.info_callback['stream_1'](f'{self.id} target is below allowed alt:{alt}, skipping')
                self.info_callback['stream_5'](f'{self.id}')
                self.skipped = True
                logger.info(f'{self.id} target is below allowed alt:{alt}, skipping')
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                return 1

        elif self.ra is not None and self.dec is not None and self.epoch is not None:
            logger.debug(f'{self.id} started --> RaDec')
            self.ra_now, self.dec_now = ra_dec_epoch(ra=self.ra,
                                                     dec=self.dec,
                                                     epoch=self.epoch)

            az, alt = ra_dec_2_az_alt(ra=self.ra_now,
                                      dec=self.dec_now,
                                      latitude=OCA['latitude'],
                                      longitude=OCA['longitude'],
                                      elevation=OCA['elevation'],
                                      epoch=self.epoch)
            logger.info(f'{self.id} alt:{alt}')
            if alt > mount_min_alt:
                #await self.mount.aput_unpark()
                await self.mount.aput_tracking(self.tracking)
                await self.mount.aput_slewtocoo_async(ra=float(self.ra_now), dec=float(self.dec_now))
                await self._wait_to_slew_coo(ra_in=float(self.ra_now), dec_in=float(self.dec_now))
                await self.mount.aput_tracking(self.tracking)
                logger.info(f'{self.id} done')
                self.info_callback['stream_1'](f'{self.id} {self.name} done')
                self.info_callback['stream_5'](f'{self.id}')
                self.done = True
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                return 0
            else:
                self.info_callback['stream_1'](f'{self.id} target is below allowed alt:{alt}, skipping')
                self.info_callback['stream_5'](f'{self.id}')
                self.skipped = True
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                logger.info(f'{self.id} target is below allowed alt:{alt}, skipping')
                return 1

        elif self.dither is True and (self.ra is None and self.dec is None):
            logger.debug(f'{self.id} started --> dither')
            ra_t = await self.value_proof_get(name='mount_ra', awaitab=self.mount.aget_ra, expect_type=float)
            dec_t = await self.value_proof_get(name='mount_dec', awaitab=self.mount.aget_dec, expect_type=float)
            ra_d = self.ra_random_dither(ra=ra_t,
                                         dith_val=self.seq_data.dither_distance,
                                         mode=self.seq_data.dither_mode)
            dec_d = self.dec_random_dither(dec=dec_t,
                                           dith_val=self.seq_data.dither_distance,
                                           mode=self.seq_data.dither_mode)
            await self.mount.aput_tracking(self.tracking)
            await self.mount.aput_slewtocoo_async(ra=ra_d, dec=dec_d)
            await self._wait_to_slew_coo(ra_in=ra_d, dec_in=dec_d)
            logger.info(f'{self.id} done')
            self.info_callback['stream_1'](f'{self.id} {self.name} done')
            self.info_callback['stream_5'](f'{self.id}')
            self.done = True
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0

        else:
            self.info_callback['stream_1'](f'{self.id} no coordinates, skipping')
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            logger.info(f'{self.id} no coordinates, intend to skip')
            return 0
