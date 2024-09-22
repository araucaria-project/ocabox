import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand
from pyaraucaria.coordinates import ra_dec_epoch, ra_dec_2_az_alt, deg_to_decimal_deg
import random
from typing import Callable, Dict, Any
from ob.planrunner.status import PlanStatusEnum


logger = logging.getLogger(__name__.rsplit('.')[-1])


class MountSlew(BaseSubCommand):

    def __init__(
            self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
            obj_name: str, uobi: int, epoch: str, tracking: bool,
            dithering: bool = False, seq_data: 'Seq' or None = None,
            ra: float or None = None, dec: float or None = None,
            az: float or None = None, alt: float or None = None,
            name: str = 'mount-slew', param: Dict[str, Any] or None = None) -> None:

        self.obj_name = obj_name
        self.seq_data = seq_data
        self.ra = ra
        self.dec = dec
        self.epoch = epoch
        self.tracking = tracking
        self.dithering = dithering
        self.alt = alt
        self.az = az
        self.ra_now: float or None = None
        self.dec_now: float or None = None
        super().__init__(id=id, info_callback=info_callback, telescope=telescope, name=name, uobi=uobi, param=param)
        self.mount = self.telescope.get_mount()
        self.info_dict = { 'obj_name': self.obj_name,
                            'seq_data': self.seq_data,
                            'ra': self.ra,
                            'dec': self.dec,
                            'epoch': self.epoch,
                            'tracking': self.tracking,
                            'dither': self.dithering,
                            'alt': self.alt,
                            'az': self.az}
        self.create_sub_command_string(**self.info_dict)

    async def _wait_to_slew_coo(self, ra_in: float, dec_in: float,
                                slew_wait_only: bool = False, tolerance: float = 0.05) -> None:
        await asyncio.sleep(1)
        while True:
            ra = await self.value_proof_get(name='mount_ra', awaitab=self.mount.aget_ra, expect_type=float)
            dec = await self.value_proof_get(name='mount_dec', awaitab=self.mount.aget_dec, expect_type=float)
            slew = await self.value_proof_get(name='mount_slew', awaitab=self.mount.aget_slewing, expect_type=bool)
            if not slew_wait_only:
                if ((abs(ra - ra_in) > (360 - tolerance)) or (abs(ra - ra_in) < tolerance))\
                        and (abs(dec - dec_in) < tolerance) and (slew is False):
                    break
            else:
                if slew is False:
                    break

    async def _wait_to_slew_alt_az(self, az_in: float, alt_in: float) -> None:
        await asyncio.sleep(0.5)
        while True:
            az = await self.value_proof_get(name='mount_az', awaitab=self.mount.aget_az, expect_type=float)
            alt = await self.value_proof_get(name='mount_alt', awaitab=self.mount.aget_alt, expect_type=float)
            slew = await self.value_proof_get(name='mount_slew', awaitab=self.mount.aget_slewing, expect_type=bool)

            if ((abs(az - az_in) > 359.0) or (abs(az - az_in) < 1.0)) and (abs(alt - alt_in) < 1.0) and (slew is False):
                await self.proof_put(awaitab=self.mount.aput_tracking, track=False)
                await self.proof_put(awaitab=self.mount.aput_slewtoaltaz_async, az=az_in, alt=alt_in)
                await asyncio.sleep(0.5)
                await self.proof_put(awaitab=self.mount.aput_tracking, track=False)
                break
            await asyncio.sleep(0.1)

    @staticmethod
    def ra_random_dither(ra: float, dith_val: float, mode: str = 'basic') -> float:
        # TODO dith_val = dith_val / cos(dec) ?
        if mode == 'basic':
            m = 0.000001
            diff = random.uniform(-dith_val / 60, dith_val / 60)
            if abs(diff) < m:
                diff = m
            return ra + diff

    @staticmethod
    def dec_random_dither(dec: float, dith_val: float, mode: str = 'basic') -> float:
        if mode == 'basic':
            m = 0.000001
            diff = random.uniform(-dith_val / 60, dith_val / 60)
            if abs(diff) < m:
                diff = m
            return dec + diff

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.running)
        if self.seq_data:
            if self.seq_data.skip:
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                return 0
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        logger.info(f'{self.id} started')
        self.info_callback['stream_1'](f'{self.id} {self.name} started')
        await self.journal.info(f'{self.id} {self.name} started.')
        loc = self.param['cfg_gen'].get_value(seq=['site', 'global', 'geo_location'], source='nats')
        # TODO mount_min_alt should be taken from settings
        mount_min_alt = 14.9

        if self.alt is not None and self.az is not None and self.dithering is False:
            logger.debug(f'{self.id} {self.name} Alt: {self.alt} Az: {self.az}')
            await self.journal.debug(f'{self.id} {self.name} Alt: {self.alt} Az: {self.az}')
            try:
                az = float(self.az)
                alt = float(self.alt)
            except ValueError:
                try:
                    az = deg_to_decimal_deg(self.az)
                    alt = deg_to_decimal_deg(self.alt)
                except ValueError:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                    self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                    logger.error(f"Wrong az alt format")
                    await self.journal.error(f"{self.id} {self.name} wrong az alt format.")
                    return 1
            if alt > mount_min_alt:
                tr0 = await self.proof_put(awaitab=self.mount.aput_tracking, track=False)
                if not tr0:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not execute tracking, program stopping'
                    logger.error(inf)
                    await self.journal.error(inf)
                    return 2
                sl0 = await self.proof_put(awaitab=self.mount.aput_slewtoaltaz_async, az=az, alt=alt)
                if not sl0:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not slew altaz mount, program stopping'
                    logger.error(inf)
                    await self.journal.error(inf)
                    return 2
                tr1 = await self.proof_put(awaitab=self.mount.aput_tracking, track=False)
                if not tr1:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not execute tracking, program stopping'
                    logger.error(inf)
                    await self.journal.error(inf)
                    return 2
                await self._wait_to_slew_alt_az(az_in=az, alt_in=alt)
                if self.tracking is not None:
                    await asyncio.sleep(5)
                    # await self.mount.aput_tracking(self.tracking)
                    tr2 = await self.proof_put(awaitab=self.mount.aput_tracking, track=self.tracking)
                    if not tr2:
                        self.skipped = True
                        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                        inf = f'Can not execute tracking, program stopping'
                        logger.error(inf)
                        await self.journal.error(inf)
                        return 2
                    self.info_callback['stream_1'](f'{self.id} {self.name} tracking: {self.tracking}.')
                    await self.journal.debug(f'{self.id} {self.name} tracking: {self.tracking}.')
                logger.info(f'{self.id} done')
                self.info_callback['stream_1'](f'{self.id} {self.name} done')
                self.info_callback['stream_5'](f'{self.id}')
                await self.journal.info(f'{self.id} {self.name} done.')
                self.done = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                return 0
            else:
                self.info_callback['stream_1'](f'{self.id} {self.name} target is below allowed alt:{alt}, skipping')
                self.info_callback['stream_5'](f'{self.id}')
                await self.journal.warning(f'{self.id} {self.name} target is below allowed alt: {alt}, skipping')
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                logger.info(f'{self.id} {self.name} target is below allowed alt:{alt}, skipping')
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                return 1

        elif self.ra is not None and self.dec is not None and self.dithering is False:
            self.ra_now, self.dec_now = ra_dec_epoch(ra=self.ra, dec=self.dec, epoch=self.epoch)
            await self.journal.debug(f'{self.id} {self.name} Ra now: {self.ra_now} Dec now: {self.dec_now}')
            az, alt = ra_dec_2_az_alt(
                ra=self.ra_now, dec=self.dec_now, latitude=loc['lat'], longitude=loc['lon'],
                elevation=loc['elev'], epoch=self.epoch
            )
            if alt > mount_min_alt:
                tr3 = await self.proof_put(awaitab=self.mount.aput_tracking, track=self.tracking)
                if not tr3:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not execute tracking, program stopping'
                    logger.error(inf)
                    await self.journal.error(inf)
                    return 2
                sl1 = await self.proof_put(
                    awaitab=self.mount.aput_slewtocoo_async, ra=float(self.ra_now), dec=float(self.dec_now)
                )
                if not sl1:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not mount coo slew, program stopping'
                    logger.error(inf)
                    await self.journal.error(inf)
                    return 2
                await self._wait_to_slew_coo(ra_in=float(self.ra_now), dec_in=float(self.dec_now))
                tr4 = await self.proof_put(awaitab=self.mount.aput_tracking, track=self.tracking)
                if not tr4:
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    inf = f'Can not execute tracking, program stopping'
                    logger.error(inf)
                    await self.journal.error(inf)
                    return 2
                logger.info(f'{self.id} done')
                self.info_callback['stream_1'](f'{self.id} {self.name} done')
                self.info_callback['stream_5'](f'{self.id}')
                await self.journal.info(f'{self.id} {self.name} done')
                self.done = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                return 0
            else:
                self.info_callback['stream_1'](f'{self.id} target is below allowed alt:{alt}, skipping')
                self.info_callback['stream_5'](f'{self.id}')
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                logger.info(f'{self.id} {self.name} target is below allowed alt:{alt}, skipping')
                await self.journal.warning(f'{self.id} {self.name} target is below allowed alt: {alt}, skipping')
                return 1

        elif self.dithering is True:
            logger.info(f'{self.id} started dither')
            ra_t = await self.value_proof_get(name='mount_ra', awaitab=self.mount.aget_ra, expect_type=float)
            dec_t = await self.value_proof_get(name='mount_dec', awaitab=self.mount.aget_dec, expect_type=float)
            ra_d = self.ra_random_dither(
                ra=ra_t, dith_val=self.seq_data.dither_distance, mode=self.seq_data.dither_mode
            )
            dec_d = self.dec_random_dither(
                dec=dec_t, dith_val=self.seq_data.dither_distance, mode=self.seq_data.dither_mode
            )
            await self.journal.debug(
                f'{self.id} {self.name} RA dit: {round(ra_d - ra_t, 3)} DEC dit: {round(dec_d - dec_t, 3)}'
            )
            tr5 = await self.proof_put(awaitab=self.mount.aput_tracking, track=self.tracking)
            if not tr5:
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                inf = f'Can not execute tracking, program stopping'
                logger.error(inf)
                await self.journal.error(inf)
                return 2
            sl2= await self.proof_put(awaitab=self.mount.aput_slewtocoo_async, ra=ra_d, dec=dec_d)
            if not sl2:
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                inf = f'Can not mount coo slew, program stopping'
                logger.error(inf)
                await self.journal.error(inf)
                return 2
            await self._wait_to_slew_coo(ra_in=ra_d, dec_in=dec_d, slew_wait_only=True)
            logger.info(f'{self.id} dither done')
            await self.journal.info(f'{self.id} {self.name} done')
            self.info_callback['stream_1'](f'{self.id} {self.name} done')
            self.info_callback['stream_5'](f'{self.id}')
            self.done = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            return 0
        else:
            self.info_callback['stream_1'](f'{self.id} no coordinates, skipping')
            self.info_callback['stream_5'](f'{self.id}')
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
            self.info_callback['exec_json'](self.exec_json(**self.info_dict))
            logger.info(f'{self.id} {self.name} no coordinates and dither, skipping')
            await self.journal.warning(f'{self.id} {self.name} no coordinates and dither, skipping')
            return 0
