import asyncio
import logging
from ob.planrunner.base_subcommand import BaseSubCommand
import math
from pyaraucaria.coordinates import site_sidereal_time, ra_dec_2_az_alt
from typing import Callable, Dict


logger = logging.getLogger(__name__.rsplit('.')[-1])


class DomeSlew(BaseSubCommand):

    def __init__(self, id: str, telescope: 'Telescope',  info_callback: Dict[str, Callable],
                 uobi: int, seq_data: 'Seq' or None = None,
                 follow_tol: float or None = None, az: float or None = None, name: str = 'dome-slew') -> None:
        self.seq_data = seq_data
        self.az = az
        self.follow_tol = follow_tol
        super().__init__(id=id, info_callback=info_callback, telescope=telescope, name=name, uobi=uobi)
        self.dome = self.telescope.get_dome()
        self.mount = self.telescope.get_mount()
        self.info_dict = {'az': self.az, 'follow_tol': self.follow_tol}
        self.create_sub_command_string(**self.info_dict)

    def dome_eq_azimuth(self, ra: float, dec: float, r_dome: float, spx: float, spy: float,
                               gem: float, latitude: float, longitude: float, elevation: float) -> float:
        """
        Func calculate dome azimuth for eq mounts.
        :param ra: mount ra
        :param dec: mount dec
        :param r_dome: dome radius
        :param spx: ra/dec point location E(+), W(-) (in Sequence soft. "Scope position Y" - be aware of +/-)
        :param spy: ra/dec point location N(+), S(-) (in Sequence soft. "Scope position X" - be aware of +/-)
        :param gem: distance from ra/dec point to telescope axis (in Sequence soft. "GEM Axis Offset - r")
        :param latitude: site latitude
        :param longitude: site longitude
        :param elevation: site elevation
        :return: corrected dome azimuth
        """

        # Azimuth calc
        _, az = ra_dec_2_az_alt(ra=ra,
                                dec=dec,
                                longitude=longitude,
                                latitude=latitude,
                                elevation=elevation,
                                epoch='2000')

        logger.info(f'Dome_eq_azimuth az:{az}')

        # Calculating dome vector
        az_rad = math.radians(az)
        vector_dome_x = math.sin(az_rad) * r_dome
        vector_dome_y = math.cos(az_rad) * r_dome
        vector_dome = [vector_dome_x, vector_dome_y]
        logger.info(f'Dome_eq_azimuth vector_dome:{vector_dome}')

        # Calculating gem vector
        # Get sidereal for site
        s_sidereal = site_sidereal_time(longitude=longitude,
                                        latitude=latitude,
                                        elevation=elevation)
        logger.info(f'Dome_eq_azimuth site_sidereal:{s_sidereal}')

        # +/- rotation for north/south hemisphere
        if latitude > 0:
            side = -1
        else:
            side = 1
        logger.info(f'Dome_eq_azimuth site +/- rotation for north/south hemisphere:{side}')

        ra_from_north_angle = s_sidereal + (side * 90) - ra
        if ra_from_north_angle > 360:
            ra_from_north_angle = ra_from_north_angle - 360
        logger.info(f'Dome_eq_azimuth ra_from_north_angle:{ra_from_north_angle}')

        vector_gem_xy_x = -math.sin(math.radians(ra_from_north_angle)) * gem
        vector_gem_xy_y = -math.cos(math.radians(ra_from_north_angle)) * gem * \
                          math.sin(math.radians(abs(latitude)))
        vector_gem = [vector_gem_xy_x, vector_gem_xy_y]
        logger.info(f'Dome_eq_azimuth vector_gem:{vector_gem}')

        # Calculating spx_spy vector
        vector_spx_spy = [spx, spy]
        logger.info(f'Dome_eq_azimuth vector_spx_spy:{vector_spx_spy}')

        # Sum vectors
        vector_final = [vector_dome[0] + vector_spx_spy[0] + vector_gem[0],
                        vector_dome[1] + vector_spx_spy[1] + vector_gem[1]]
        logger.info(f'Dome_eq_azimuth vector_final:{vector_final}')

        # Final azimuth calculation
        if vector_final[0] >= 0 and vector_final[1] >= 0:
            new_dome_az = math.degrees(math.atan(vector_final[0] / vector_final[1]))
        elif vector_final[0] >= 0 and vector_final[1] < 0:
            new_dome_az = math.degrees(math.atan(vector_final[0] / vector_final[1])) + 180
        elif vector_final[0] < 0 and vector_final[1] < 0:
            new_dome_az = math.degrees(math.atan(vector_final[0] / vector_final[1])) + 180
        else:
            new_dome_az = math.degrees(math.atan(vector_final[0] / vector_final[1])) + 360

        logger.info(f'Dome_eq_azimuth new_dome_az:{new_dome_az}')
        return new_dome_az


    async def _wait_to_slew(self, azimuth) -> None:

        while True:
            dome_az = await self.value_proof_get(name='sub_dome_az', awaitab=self.dome.aget_az, expect_type=float)
            dome_slewing = await self.value_proof_get(name='sub_dome_slew',
                                                      awaitab=self.dome.aget_slewing,
                                                      expect_type=bool)
            await asyncio.sleep(0.5)
            if dome_az is not None and dome_slewing==False:
                if (abs(azimuth - float(dome_az)))<2.0 or (abs(azimuth - float(dome_az)))>358.0:
                    break

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        if self.seq_data:
            if self.seq_data.skip:
                self.skipped = True
                return 0
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        logger.info(f'{self.id} started')
        self.info_callback['stream_1'](f'{self.id} {self.name} started')
        # TODO get mount kind and parameters from settings
        if self.az:
            az = self.az
        elif self.follow_tol:
            mount_az = await self.value_proof_get(name='mount_az', awaitab=self.mount.aget_az, expect_type=float)
            dome_az = await self.value_proof_get(name='sub_dome_az', awaitab=self.dome.aget_az, expect_type=float)
            if self.follow_tol < abs(mount_az - dome_az):
                az = mount_az
            else:
                self.info_callback['stream_1'](f'{self.id} {self.name} dome in position tolerance, skipping')
                self.info_callback['stream_5'](f'{self.id}')
                logger.info(f'{self.id} dome in position tolerance, skipping')
                self.skipped = True
                self.info_callback['exec_json'](self.exec_json(**self.info_dict))
                return 0
        else:
            az = await self.value_proof_get(name='mount_az', awaitab=self.mount.aget_az, expect_type=float)

        # TODO config? At lest in final server-side version...
        if self.telescope.id == 'wk06':
        #if self.telescope.id=='dev':
            OCA = {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}

            ra = await self.value_proof_get(name='mount_ra', awaitab=self.mount.aget_ra, expect_type=float)
            dec = await self.value_proof_get(name='mount_dec', awaitab=self.mount.aget_dec, expect_type=float)
            logger.info(f'Dome_eq_azimuth for ra:{ra} dec:{dec}')
            r_dome = 3500.0
            spx = -250.0
            spy = 200.0
            gem = 680.0
            az = self.dome_eq_azimuth(ra=ra,
                                      dec=dec,
                                      r_dome=r_dome,
                                      spx=spx,
                                      spy=spy,
                                      gem=gem,
                                      latitude=OCA['latitude'],
                                      longitude=OCA['longitude'],
                                      elevation=OCA['elevation']
                                      )
            logger.info(f'After Dome_eq_azimuth az:{az}')
        else:
            pass
        # TODO maybe use synctoazimuth (if yes add to ocaboxapi)
        await self.dome.aput_slewtoazimuth(az)
        await self._wait_to_slew(az)
        logger.info(f'{self.id} done')
        self.info_callback['stream_1'](f'{self.id} {self.name} done')
        self.info_callback['stream_5'](f'{self.id}')
        self.done = True
        self.info_callback['exec_json'](self.exec_json(**self.info_dict))
        return 0
