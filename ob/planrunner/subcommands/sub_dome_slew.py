import asyncio
import logging
import math

from pyaraucaria.coordinates import ra_dec_2_az_alt, site_sidereal_time

from ob.planrunner.base_subcommand import BaseSubCommand
# from pyaraucaria.dome_eq import dome_eq_azimuth
from typing import Callable, Dict, Any, Tuple
from ob.planrunner.status import PlanStatusEnum


logger = logging.getLogger(__name__.rsplit('.')[-1])


class DomeSlew(BaseSubCommand):

    def __init__(self, id: str, telescope: 'Telescope', info_callback: Dict[str, Callable],
                 uobi: int, seq_data: 'Seq' or None = None,
                 follow_tol: float = 3.0, az: float or None = None,
                 name: str = 'dome-slew', param: Dict[str, Any] or None = None) -> None:
        self.seq_data = seq_data
        self.az = az
        self.follow_tol = follow_tol  # TODO take from settings
        super().__init__(id=id, info_callback=info_callback, telescope=telescope,
                         name=name, uobi=uobi, param=param)
        self.dome = self.telescope.get_dome()
        self.mount = self.telescope.get_mount()
        self.info_dict = {'az': self.az, 'follow_tol': self.follow_tol}
        self.create_sub_command_string(**self.info_dict)

    @staticmethod
    def dome_eq_azimuth(ra: float, dec: float, r_dome: float, spx: float, spy: float, gem: float,
                        side_of_pier: int, latitude: float, longitude: float,
                        elevation: float, epoch: str = '2000') -> Tuple[float, Dict]:
        """
        Func. calculate dome position for eq mount.
        @param ra: Ra of telescope [deg]
        @param dec: Dec of telescope [deg]
        @param r_dome: Radius of dome [mm]
        @param spx: X distance from dome center to intersection of ra - dec axes: (+) when on E, (-) when on W [mm]
        @param spy: Y distance from dome center to intersection of ra - dec axes: (+) when on N, (-) when on S [mm]
        @param gem: Distance from intersection of ra - dec axes point to telescope optical axis (absolute value) [mm]
        @param side_of_pier: Side of telescope pier position. On east = 0, on west = 1
        @param latitude: Site latitude [deg]
        @param longitude: Site longitude [deg]
        @param elevation: Site elevation [m]
        @param epoch: Epoch for radec, example: '2000'
        @return: Eq mount dome azimuth [deg]
        """

        # Calc. az alt from ra, dec and epoch
        az, alt = ra_dec_2_az_alt(ra=ra,
                                  dec=dec,
                                  longitude=longitude,
                                  latitude=latitude,
                                  elevation=elevation,
                                  epoch=epoch)

        # Calc. dome azimuth vector
        az_rad = math.radians(az)
        dome_azimuth_vector_x = math.sin(az_rad) * r_dome
        dome_azimuth_vector_y = math.cos(az_rad) * r_dome
        dome_azimuth_vector = [dome_azimuth_vector_x, dome_azimuth_vector_y]

        # Calc. alt az target point on xy plane (as vector)
        target_point = [r_dome * math.cos(math.radians(-(az - 90))) * math.sin(math.radians(90 - alt)),
                        r_dome * math.sin(math.radians(-(az - 90))) * math.sin(math.radians(90 - alt))]

        # Get sidereal tome for site
        s_sidereal = site_sidereal_time(longitude=longitude,
                                        latitude=latitude,
                                        elevation=elevation)

        # Calc. angle between ra and sidereal + side of pier
        if int(side_of_pier) not in [0, 1]:
            side_of_pier = 0
        ra_to_sidereal_angle = abs(ra - s_sidereal) + int(side_of_pier) * 180

        # Calc. vector gem
        x = math.cos(math.radians(ra_to_sidereal_angle)) * gem
        y = math.sin(math.radians(ra_to_sidereal_angle)) * gem
        # North or south hemisphere location
        n_s = - (latitude / abs(latitude))
        vector_gem = [x, n_s * y * math.cos(math.radians(abs(latitude)))]
        vector_spx_spy = [spx, spy]

        # Calc. new dome vector
        new_dome_vector = [target_point[0] + vector_spx_spy[0] + vector_gem[0],
                           target_point[1] + vector_spx_spy[1] + vector_gem[1]]

        # Final azimuth calculation
        if new_dome_vector[0] >= 0 and new_dome_vector[1] >= 0:
            new_dome_az = math.degrees(math.atan(new_dome_vector[0] / new_dome_vector[1]))
        elif new_dome_vector[0] >= 0 > new_dome_vector[1]:
            new_dome_az = math.degrees(math.atan(new_dome_vector[0] / new_dome_vector[1])) + 180
        elif new_dome_vector[0] < 0 and new_dome_vector[1] < 0:
            new_dome_az = math.degrees(math.atan(new_dome_vector[0] / new_dome_vector[1])) + 180
        else:
            new_dome_az = math.degrees(math.atan(new_dome_vector[0] / new_dome_vector[1])) + 360

        # Compose info dict
        info_dict = {
            'vector_final': new_dome_vector,
            'dome_azimuth_vector': dome_azimuth_vector,
            'vector_gem': vector_gem,
            'target_point': target_point,
            's_sidereal': s_sidereal
        }

        return new_dome_az, info_dict

    async def _wait_to_slew(self, azimuth) -> None:

        while True:
            dome_az = await self.value_proof_get(name='sub_dome_az', awaitab=self.dome.aget_az, expect_type=float)
            dome_slewing = await self.value_proof_get(name='sub_dome_slew',
                                                      awaitab=self.dome.aget_slewing,
                                                      expect_type=bool)
            await asyncio.sleep(0.5)
            if dome_az is not None and dome_slewing is False:
                if (abs(azimuth - float(dome_az))) < 2.0 or (abs(azimuth - float(dome_az))) > 358.0:
                    break

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
        mount_type = self.gen_conf.get_value([self.telescope.id, 'mount', 'type'])
        if self.az is not None:
            az = self.az
        else:
            if mount_type == 'eq':
                await self.journal.info(f"For eq started")
                observ_loc = self.gen_conf.get_value(['observatory_location'])
                ra = await self.value_proof_get(name='mount_ra', awaitab=self.mount.aget_ra, expect_type=float)
                dec = await self.value_proof_get(name='mount_dec', awaitab=self.mount.aget_dec, expect_type=float)
                side_of_pier = await self.value_proof_get(name='mount_sideofpier', awaitab=self.mount.aget_sideofpier,
                                                          expect_type=int)
                logger.info(f'Dome_eq_azimuth for ra:{ra} dec:{dec}')
                r_dome = self.gen_conf.get_value([self.telescope.id, 'dome', 'r_dome'])
                spx = self.gen_conf.get_value([self.telescope.id, 'dome', 'spx'])
                spy = self.gen_conf.get_value([self.telescope.id, 'dome', 'spy'])
                gem = self.gen_conf.get_value([self.telescope.id, 'dome', 'gem'])
                mount_az, info_dict = self.dome_eq_azimuth(
                    ra=ra, dec=dec, r_dome=r_dome, spx=spx, spy=spy,
                    gem=gem, side_of_pier=side_of_pier, latitude=observ_loc['latitude'],
                    longitude=observ_loc['longitude'], elevation=observ_loc['elevation']
                )
                logger.info(f'Calculated eq dome az:{mount_az}')
                logger.info(f'Calculated info dict eq dome az:{info_dict}')
            else:
                mount_az = await self.value_proof_get(name='sub_dome_mount_az',
                                                      awaitab=self.mount.aget_az, expect_type=float)
            dome_az = await self.value_proof_get(name='sub_dome_az', awaitab=self.dome.aget_az, expect_type=float)

            if (360 > abs(mount_az - dome_az) > (360 - self.follow_tol)) or \
                    0 < (abs(mount_az - dome_az) < self.follow_tol):
                az = mount_az
                inf = f'{self.id} {self.name} in position tolerance, skipping.'
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

        await self.journal.debug(f"{self.id} {self.name} slewing az: {az}")
        await self.dome.aput_slewtoazimuth(az)
        await self._wait_to_slew(az)
        logger.info(f'{self.id} done')
        self.info_callback['stream_1'](f'{self.id} {self.name} done.')
        self.info_callback['stream_5'](f'{self.id}')
        await self.journal.info(f"{self.id} {self.name} done.")
        self.done = True
        await self.param['plan_status'].upd_status(id=self.id, value=PlanStatusEnum.done)
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
