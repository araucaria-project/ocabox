import asyncio
import logging
import time

from pyaraucaria.dome_eq import dome_eq_azimuth
from ob.planrunner.base_subcommand import BaseSubCommand
from typing import Callable, Dict, Any
from ob.planrunner.status import PlanStatusEnum


logger = logging.getLogger(__name__.rsplit('.')[-1])


class DomeSlew(BaseSubCommand):

    def __init__(
            self, id: str, telescope: 'Telescope', info_callback: Dict[str, Callable], uobi: int,
            seq_data: 'Seq' or None = None, follow_tol: float = 3.0, az: float or None = None,
            slew_tolerance: float = 3.0, name: str = 'dome-slew', param: Dict[str, Any] or None = None) -> None:

        self.seq_data = seq_data
        self.az = az
        self.follow_tol = follow_tol
        self.slew_tolerance = slew_tolerance
        super().__init__(id=id, info_callback=info_callback, telescope=telescope, name=name, uobi=uobi, param=param)
        self.dome = self.telescope.get_dome()
        self.mount = self.telescope.get_mount()
        self.slew_timeout: float or None = None
        self.mount_type: str or None = None
        self.loc: Dict or None = None
        self.info_dict = {'az': self.az, 'follow_tol': self.follow_tol}
        self.create_sub_command_string(**self.info_dict)

    async def _wait_to_slew(self, azimuth) -> bool:
        logger.info(f'Starting wait_to slew az: {azimuth}')
        slew_start_time = time.time()
        while True:
            await asyncio.sleep(0.5)
            dome_az = await self.value_proof_get(
                name='sub_dome_az', awaitab=self.dome.aget_az, expect_type=float, log=True
            )
            dome_slewing = await self.value_proof_get(
                name='sub_dome_slew', awaitab=self.dome.aget_slewing, expect_type=bool, log=True
            )

            if dome_az is not None and dome_slewing is False:
                if (abs(azimuth - float(dome_az))) < self.slew_tolerance \
                        or (abs(azimuth - float(dome_az))) > 360.0 - self.slew_tolerance:
                    logger.info(f'Dome on position set: {azimuth} real: {dome_az}')
                    return True
            if time.time() > slew_start_time + self.slew_timeout:
                logger.error(f'Dome slew get timeout {self.slew_timeout}s.')
                return False

    async def get_from_config_general(self) -> None:
        self.loc = self.param['cfg_gen'].get_value(seq=['site', 'global', 'geo_location'], source='nats')
        self.mount_type = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'mount', 'type'
        ], source='nats')
        self.slew_timeout = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'dome', 'slew_timeout'
        ], source='nats')
        self.follow_tol = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'dome', 'follow_tolerance'
        ], source='nats')
        self.slew_tolerance = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'dome', 'slew_tolerance'
        ], source='nats')

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
        self.info_callback['stream_1'](f'{self.id} {self.name} started.')
        await self.journal.info(f"{self.id} {self.name} started.")
        await self.get_from_config_general()
        logger.debug(f'Mount type {self.mount_type}')
        if self.az is not None:
            az = self.az
        else:
            if self.mount_type == 'eq':
                await self.journal.info(f"For eq started")
                ra = await self.value_proof_get(name='mount_ra', awaitab=self.mount.aget_ra, expect_type=float)
                dec = await self.value_proof_get(name='mount_dec', awaitab=self.mount.aget_dec, expect_type=float)
                side_of_pier = await self.value_proof_get(
                    name='mount_sideofpier', awaitab=self.mount.aget_sideofpier, expect_type=int
                )
                logger.info(f'Dome_eq_azimuth for ra:{ra} dec:{dec}')
                pointing_params = self.param['cfg_gen'].get_value(seq=[
                    'telescopes', self.telescope.id, 'observatory', 'components', 'dome', 'pointing_params'
                ], source='nats')
                try:
                    r_dome = pointing_params['dome_radius']
                    spx = pointing_params['spx']
                    spy = pointing_params['spy']
                    gem = pointing_params['gem']
                except (LookupError, TypeError):
                    inf = f'No pointing_params for eq mount in dome in general config, quitting'
                    logger.error(inf)
                    self.skipped = True
                    await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                    self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                    await self.status_error_publish(
                        level='critical',
                        description=inf,
                        plan_runner_quits=True
                    )
                    return 2
                mount_az, info_dict = dome_eq_azimuth(
                    ra=ra, dec=dec, r_dome=r_dome, spx=spx, spy=spy,
                    gem=gem, side_of_pier=side_of_pier, latitude=self.loc['lat'],
                    longitude=self.loc['lon'], elevation=self.loc['elev']
                )
                logger.info(f'Calculated eq dome az: {mount_az}')
                logger.info(f'Calculated info dict eq dome az: {info_dict}')
            elif self.mount_type == 'az':
                mount_az = await self.value_proof_get(
                    name='sub_dome_mount_az', awaitab=self.mount.aget_az, expect_type=float
                )
            else:
                inf = f'No mount type in {self.telescope.id}, quitting'
                logger.error(inf)
                await self.journal.error(inf)
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                await self.status_error_publish(
                    level='critical',
                    description=inf,
                    plan_runner_quits=True
                )
                return 2
            dome_az = await self.value_proof_get(name='sub_dome_az', awaitab=self.dome.aget_az, expect_type=float)
            if dome_az is None:
                inf = f'{self.id} {self.name} can not get dome az, quiting.'
                self.info_callback['stream_1'](inf)
                await self.journal.error(inf)
                self.info_callback['stream_5'](f'{self.id}')
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                await self.status_error_publish(
                    level='critical',
                    description=inf,
                    plan_runner_quits=True
                )
                return 2
            if (360 > abs(mount_az - dome_az) > (360 - self.follow_tol)) or \
                    0 < (abs(mount_az - dome_az) < self.follow_tol):
                inf = f'{self.id} {self.name} in position tolerance (set az: {mount_az} dome az: {dome_az}), skipping.'
                self.info_callback['stream_1'](inf)
                self.info_callback['stream_5'](f'{self.id}')
                logger.info(inf)
                await self.journal.info(inf)
                self.skipped = True
                await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.skipped)
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                return 0
            else:
                az = mount_az
        await self.journal.info(f"{self.id} {self.name} slewing az: {az}")
        ds = await self.proof_put(awaitab=self.dome.aput_slewtoazimuth, az=az)
        if not ds:
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
            inf = f'Can not execute dome slew to azimuth, program stopping'
            logger.error(inf)
            await self.journal.error(inf)
            await self.status_error_publish(
                level='critical',
                description=inf,
                plan_runner_quits=True
            )
            return 2
        wait_slew_ok = await self._wait_to_slew(az)
        if not wait_slew_ok:
            self.skipped = True
            await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.error)
            inf = f'Dome slew get timeout {self.slew_timeout}s, program stopping.'
            logger.error(inf)
            await self.journal.error(inf)
            await self.status_error_publish(
                level='critical',
                description=inf,
                plan_runner_quits=True
            )
            return 2
        logger.info(f'{self.id} done')
        self.info_callback['stream_1'](f'{self.id} {self.name} done.')
        self.info_callback['stream_5'](f'{self.id}')
        await self.journal.info(f"{self.id} {self.name} done.")
        self.done = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
