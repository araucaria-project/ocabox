import asyncio
import logging

from ob.planrunner.subcommand import SubCommand
from pyaraucaria.coordinates import ra_to_decimal, dec_to_decimal
from pyaraucaria.coordinates import ra_dec_epoch

logger = logging.getLogger(__name__.rsplit('.')[-1])


class MountSlewCoo(SubCommand):


    def __init__(self, id: str, parent: 'Command', **kwargs) -> None:
        self.subcommand_name = 'MountSlewCoo'
        self.telescope = parent.telescope
        self.id = id
        self.mount = self.telescope.get_mount('mount')
        self.kwargs = kwargs
        self.ra_now: str or None = None
        self.dec_now: str or None = None
        super().__init__(id=self.id, parent=parent, subcommand_name=self.subcommand_name, **kwargs)

    async def _wait_to_slew(self) -> None:
        #t_start = time.time()
        while True:
            #await self.subcommand_timeout(t_start)
            ra = self.mount.rightascension
            dec = self.mount.declination
            await asyncio.sleep(1)
            if (abs(ra - ra_to_decimal(self.ra_now))<0.05) and (abs(dec - dec_to_decimal(self.dec_now))<0.05):
                logger.debug(f'{self.id} {self.subcommand_name} done')
                self.info_callback['stream_1'](f'Subcommand {self.id} {self.subcommand_name} done')
                self.info_callback['stream_5'](f'{self.id}')
                break

    async def arun(self, step_id: str or None = None) -> None:

        # TODO This OCA should be in settings
        # Coordinates: latitude 24°35’53″S, longitude 70°11’47″W, and elevation 2817 m
        OCA = {'latitude': '-24:35:53', 'longitude': '-70:11:47', 'elevation': '2817'}

        logger.debug(f'{self.id} {self.subcommand_name} is started')
        self.info_callback['stream_1'](
            f'Subcommand {self.id} {self.subcommand_name} OBJ:{self.kwargs["obj_name"]}'
            f' RA:{self.kwargs["ra"]} DEC:{self.kwargs["dec"]} started')
        await self.mount.aput_tracking(True)
        ra_dec_now = ra_dec_epoch(self.kwargs["ra"],
                                  self.kwargs["dec"],
                                  OCA['latitude'],
                                  OCA['longitude'],
                                  OCA['elevation'],
                                  '2000/01/01')
        self.ra_now = ra_dec_now[0]
        self.dec_now = ra_dec_now[1]
        await self.mount.aput_slewtocoo_async(ra_to_decimal(self.ra_now), dec_to_decimal(self.dec_now))
        await self._wait_to_slew()
        await asyncio.sleep(5)