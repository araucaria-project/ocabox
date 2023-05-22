import asyncio
import logging
from ob.planrunner.subcommand import SubCommand
import math
from pyaraucaria.coordinates import site_sidereal_time, deg_str_to_deg, hourangle_to_decimal_deg,\
    ra_dec_2_az_alt, ra_to_sexagesimal, dec_to_sexagesimal


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


    def dome_eq_azimuth(self, ra: float, dec: float, r_dome: float, spx: float, spy: float,
                               gem: float, latitude: str, longitude: str, elevation: str) -> float:
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
        _, az = ra_dec_2_az_alt(ra=ra_to_sexagesimal(ra), dec=dec_to_sexagesimal(dec),
                                longitude=longitude, latitude=latitude, elevation=elevation, epoch='2000')
        logger.info(f'Dome_eq_azimuth az:{az}')

        # Calculating dome vector
        az_rad = math.radians(deg_str_to_deg(az))
        vector_dome_x = math.sin(az_rad) * r_dome
        vector_dome_y = math.cos(az_rad) * r_dome
        vector_dome = [vector_dome_x, vector_dome_y]
        logger.info(f'Dome_eq_azimuth vector_dome:{vector_dome}')

        # Calculating gem vector
        # Get sidereal for site
        s_sidereal = site_sidereal_time(longitude=longitude, latitude=latitude, elevation=elevation, deg_output=True)
        logger.info(f'Dome_eq_azimuth site_sidereal:{s_sidereal}')

        # +/- rotation for north/south hemisphere
        if deg_str_to_deg(latitude) > 0:
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
                          math.sin(math.radians(abs(deg_str_to_deg(latitude))))
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
            dome_az = self.dome.azimuth
            dome_slewing = self.dome.slewing
            await asyncio.sleep(0.5)
            if dome_az is not None and dome_slewing==False:
                if (abs(azimuth - float(dome_az)))<2.0 or (abs(azimuth - float(dome_az)))>358.0:
                    break

    async def arun(self, step_id: str or None = None) -> int:
        self.started = True
        self.info_callback['exec_json'](self.exec_json())
        logger.info(f'{self.id} started')
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} started')
        # TODO get mount kind and parameters from settings
        if 'az' in self.kwargs.keys():
            az = self.kwargs['az']
        elif 'follow_tol' in self.kwargs.keys():
            if self.kwargs['follow_tol']<abs(self.mount.azimuth - self.dome.azimuth):
                az = self.mount.azimuth
            else:
                self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} dome in position tolerance, skipping')
                self.info_callback['stream_5'](f'{self.id}')
                logger.info(f'{self.id} dome in position tolerance, skipping')
                self.skipped = True
                self.info_callback['exec_json'](self.exec_json())
                return 0
        else:
            az = self.mount.azimuth

        # TODO config? At lest in final server-side version...
        if self.telescope.id == 'wk06':
        #if self.telescope.id=='dev':
            OCA = {'latitude': '-24:35:53', 'longitude': '-70:11:47', 'elevation': '2817'}
            ra = self.mount.rightascension
            dec = self.mount.declination
            logger.info(f'Dome_eq_azimuth for ra:{ra} dec:{dec}')
            r_dome = 3500.0
            spx = -250.0
            spy = 200.0
            gem = 680.0
            latitude = OCA['latitude']
            longitude = OCA['longitude']
            elevation = OCA['elevation']
            az = self.dome_eq_azimuth(ra=ra, dec=dec, r_dome=r_dome, spx=spx, spy=spy,
                        gem=gem, latitude=latitude, longitude=longitude, elevation=elevation)
            logger.info(f'After Dome_eq_azimuth az:{az}')
        else:
            pass
        # TODO maybe use synctoazimuth (if yes add to ocaboxapi)
        await self.dome.aput_slewtoazimuth(az)
        await self._wait_to_slew(az)
        logger.info(f'{self.id} done')
        self.info_callback['stream_1'](f'{self.id} {self.subcommand_name} done')
        self.info_callback['stream_5'](f'{self.id}')
        self.done = True
        self.info_callback['exec_json'](self.exec_json())
        return 0

