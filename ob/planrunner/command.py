import logging
from typing import Dict, Any
from ob.planrunner.abstract_sequence import AbstractSequence
from ob.planrunner.subcommands.sub_mount_slew import MountSlew
from ob.planrunner.subcommands.sub_dome_slew import DomeSlew
from ob.planrunner.subcommands.sub_change_filter import ChangeFilter
from ob.planrunner.subcommands.sub_camera_exposure import CameraExposure
from ob.planrunner.subcommands.sub_mirror_cover import MirrorCover
from ob.planrunner.subcommands.sub_dome_screenlight import DomeScreenLight
from ob.planrunner.subcommands.sub_focusing import Focusing
from pyaraucaria.coordinates import az_alt_2_ra_dec, ra_to_decimal, dec_to_decimal, deg_to_decimal_deg, ra_dec_2_az_alt
import random

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Command(AbstractSequence):

    def __init__(self, id: str, sequence_dict: Dict[Any, Any],
                 parent: 'Sequence' or 'NightPlan') -> None:
        self.id = id
        self.sequence_dict = sequence_dict
        self.parent = parent
        self.args = self.build_args(self.sequence_dict)
        self.kwargs = self.build_kwargs(self.sequence_dict)
        self.parent_kwargs = self.parent.kwargs | self.parent.parent_kwargs
        self.command_name = self.sequence_dict['command_name']
        self.subcomponents = {}
        self.telescope = parent.telescope
        self.info_callback = parent.info_callback
        super().__init__(self.id, self.command_name, self.info_callback, observatory=self.parent.observatory)
        self._write_subcommands()

    def _create_command_string(self):
        kw = ''
        for n in self.args:
            kw = f'{kw} {n}'
        for n in self.kwargs.keys():
            kw = f'{kw} {n}={self.kwargs[n]}'
        for n in self.parent_kwargs.keys():
            kw = f'{kw} {n}={self.parent_kwargs[n]}'
        self.info_callback['c_commands'](f'{self.id};{self.command_name};{kw}')
        logger.info(f'{self.id} {self.command_name} {self.args} {self.kwargs} is written')

    @staticmethod
    def ra_random_dither(ra: float, dith_val: float, mode: str = 'basic') -> float:
        #TODO dith_val = dith_val / cos(dec) ?
        if mode == 'basic':
            return ra + random.uniform(-dith_val / 60, dith_val / 60)

    @staticmethod
    def dec_random_dither(dec: float, dith_val: float, mode: str = 'basic') -> float:
        if mode == 'basic':
            return dec + random.uniform(-dith_val / 60, dith_val / 60)

    def _write_subcommands(self) -> None:
        self._create_command_string()

        if self.command_name == 'OBJECT':
            self._write_object_skyflat_focusing('object')

        elif self.command_name == 'DOMEFLAT':
            self._write_domeflat()

        elif self.command_name == 'FOCUS':
            self._write_object_skyflat_focusing('focusing')

        elif self.command_name == 'DARK':
            self._write_zero_dark('dark')

        elif self.command_name == 'ZERO':
            self._write_zero_dark('zero')

        elif self.command_name == 'SKYFLAT':
            self._write_object_skyflat_focusing('skyflat')

        elif self.command_name == 'MARKER':
            self._write_marker()

        else:
            # TODO add info, that parsed plan have errors
            self.info_callback['stream_1'](f'Command {self.command_name} not recognized, check plan syntax' )

    def _write_domeflat(self):
        id_next = 0

        # Slew to altaz
        # TODO turn on domeflat lamp, set brightness (value also from some config? or kwarg?)
        # TODO get Alt Az domeflat position from some config
        dome_az = 0.0
        tel_flat_az = dome_az + 180
        dome_flat_alt = 15.0
        sub = DomeSlew(f'{self.id}_{self.numb(id_next)}', self, az=dome_az)
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        id_next += 1

        sub = MountSlew(f'{self.id}_{self.numb(id_next)}',
                        self,
                        obj_name='domeflat',
                        alt=dome_flat_alt,
                        az=tel_flat_az,
                        tracking=False,
                        epoch='2000'
                        )
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        id_next += 1

        if 'screen_light' in self.kwargs.keys():
            if self.kwargs['screen_light'] == 'auto':
                sub = DomeScreenLight(f'{self.id}_{self.numb(id_next)}', self, light=True)
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

        if 'mirror_cover' in self.kwargs.keys():
            if self.kwargs['mirror_cover'] == 'auto':
                sub = MirrorCover(f'{self.id}_{self.numb(id_next)}', self, open=True)
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

        # Camera exposure
        if 'seq' in self.kwargs:
            seq_list = self._split_seq(self.kwargs['seq'])
            for n in seq_list:
                par = list(n.split('/'))

                sub = ChangeFilter(f'{self.id}_{self.numb(id_next)}',
                                   self,
                                   filter=par[1])
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

                for ex in range(1, int(par[0]) + 1):
                    sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                         self,
                                         sub_exp=ex,
                                         exp_time=float(par[2]),
                                         exp_no=int(par[0]),
                                         type='flat',
                                         light=True,
                                         obj_name='domeflat',
                                         req_ra='',
                                         req_dec='',
                                         epoch='2000',
                                         filter=par[1]
                                         )
                    self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                    id_next += 1

        if 'screen_light' in self.kwargs.keys():
            if self.kwargs['screen_light'] == 'auto':
                sub = DomeScreenLight(f'{self.id}_{self.numb(id_next)}', self, light=False)
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

    def _write_object_skyflat_focusing(self, subcommand_name: str) -> None:

        id_next = 0
        obj_name = ''
        req_ra = ''
        req_dec = ''

        if len(self.args) >= 2:

            if len(self.args) == 2:
                req_ra = self.args[0]
                req_dec = self.args[1]
            elif len(self.args) == 3:
                obj_name = self.args[0]
                req_ra = self.args[1]
                req_dec = self.args[2]
            else:
                # TODO syntax error
                pass

            if subcommand_name == 'skyflat':
                obj_name = 'skyflat'
            elif subcommand_name == 'focusing':
                obj_name = 'focusing'

            sub = MountSlew(f'{self.id}_{self.numb(id_next)}',
                            self,
                            obj_name=obj_name,
                            ra=ra_to_decimal(req_ra),
                            dec=dec_to_decimal(req_dec),
                            epoch='2000')
            self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
            id_next += 1

        else:
            if len(self.args) == 1:
                obj_name = self.args[0]
            else:
                obj_name = ''

            if subcommand_name == 'skyflat':
                obj_name = 'skyflat'
            elif subcommand_name == 'focusing':
                obj_name = 'focusing'

            if 'alt' and 'az' in self.kwargs.keys():
                sub = MountSlew(f'{self.id}_{self.numb(id_next)}',
                                self,
                                obj_name=obj_name,
                                alt=self.kwargs['alt'],
                                az=self.kwargs['az'],
                                tracking=True,
                                epoch='2000')
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

            else:
                # TODO syntax error
                pass

        sub = DomeSlew(f'{self.id}_{self.numb(id_next)}', self, follow_tol=2.0)
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        id_next += 1

        if 'mirror_cover' in self.kwargs.keys():
            if self.kwargs['mirror_cover'] == 'auto':
                sub = MirrorCover(f'{self.id}_{self.numb(id_next)}', self, open=True)
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

        # Camera exposure
        if 'seq' in self.kwargs:
            seq_list = self._split_seq(self.kwargs['seq'])
            for n in seq_list:
                par = list(n.split('/'))

                sub = ChangeFilter(f'{self.id}_{self.numb(id_next)}',
                                   self,
                                   filter=par[1])
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

                sub_numb = int(par[0])

                foc_list = []
                focus_id = 0
                if subcommand_name == 'focusing':
                    foc_par = list(self.kwargs['pos'].split('/'))
                    foc_target = int(foc_par[0])
                    foc_step = int(foc_par[1])
                    foc_min = int(round(foc_target-(foc_step*((sub_numb-1)/2))))

                    for n in range(0, sub_numb):
                        foc_list.append(foc_min+(foc_step*n))
                    focus_id = random.randrange(0,100000)

                for ex in range(1, sub_numb+1):
                    ra_dit = None
                    dec_dit = None
                    # If focusing, set focuser position
                    if subcommand_name == 'focusing':
                        sub = Focusing(f'{self.id}_{self.numb(id_next)}', self, position=foc_list[ex-1])
                        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                        id_next += 1

                    # Dithering start - kwarg dither=basic/1/1 kind/for_every_sub/distance_in_minutes
                    if (subcommand_name == 'skyflat' and 'dither' not in self.kwargs.keys()) or \
                            (subcommand_name == 'skyflat' and self.kwargs['dither'] != 'none' ) or \
                             (subcommand_name != 'skyflat' and 'dither' in self.kwargs.keys()):

                        if subcommand_name == 'skyflat' and 'dither' not in self.kwargs.keys():
                            dit_mode = 'basic'
                            for_every_sub = 1
                            dit_dist = 1.0
                        else:
                            dit_lst = list(self.kwargs['dither'].split('/'))
                            dit_mode = str(dit_lst[0])
                            for_every_sub = int(dit_lst[1])
                            dit_dist = float(dit_lst[2])

                        if ex % for_every_sub == 0:

                            if 'alt' and 'az' in self.kwargs.keys():
                                # TODO get OCA values from settings
                                OCA = {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}
                                try:
                                    az = float(self.kwargs["az"])
                                    alt = float(self.kwargs["alt"])
                                except ValueError:
                                    try:
                                        az = deg_to_decimal_deg(self.kwargs["az"])
                                        alt = deg_to_decimal_deg(self.kwargs["alt"])
                                    except ValueError:
                                        az=None
                                        alt=None
                                        logger.error(f"Wrong az alt format")
                                if isinstance(az, float) and isinstance(az, float):
                                    req_ra_a, req_dec_a = az_alt_2_ra_dec(alt=alt,
                                                                      az=az,
                                                                      latitude=OCA['latitude'],
                                                                      longitude=OCA['longitude'],
                                                                      elevation=OCA['elevation'])
                                    ra_dit = self.ra_random_dither(ra=req_ra_a, dith_val=dit_dist, mode=dit_mode)
                                    dec_dit = self.ra_random_dither(ra=req_ra_a, dith_val=dit_dist, mode=dit_mode)
                                    sub = MountSlew(f'{self.id}_{self.numb(id_next)}',
                                                    self,
                                                    obj_name=obj_name,
                                                    ra=ra_dit,
                                                    dec=dec_dit,
                                                    epoch='2000')
                                    self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                                    id_next += 1

                            elif req_ra and req_dec is not None:
                                req_ra = ra_to_decimal(req_ra)
                                req_dec = dec_to_decimal(req_dec)
                                ra_dit = self.ra_random_dither(ra=req_ra, dith_val=dit_dist, mode=dit_mode)
                                dec_dit = self.dec_random_dither(dec=req_dec, dith_val=dit_dist, mode=dit_mode)
                                sub = MountSlew(f'{self.id}_{self.numb(id_next)}',
                                                self,
                                                obj_name=obj_name,
                                                ra=ra_dit,
                                                dec=dec_dit,
                                                epoch='2000')
                                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                                id_next += 1
                            else:
                                pass
                        else:
                            pass

                    sub = DomeSlew(f'{self.id}_{self.numb(id_next)}', self, follow_tol=3.0)
                    self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                    id_next += 1

                    if subcommand_name == 'skyflat':
                        type = 'skyflat'
                    elif subcommand_name == 'focusing':
                        type = 'focusing'
                    else:
                        type = 'science'

                    if par[2] == 'a':
                        exp_t = 'a'
                    else:
                        exp_t = float(par[2])
                    if ra_dit and ra_dit:
                        req_ra = ra_dit
                        req_dec = dec_dit
                    sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                         self,
                                         sub_exp=ex,
                                         exp_time=exp_t,
                                         exp_no=sub_numb,
                                         type=type,
                                         light=True,
                                         obj_name=obj_name,
                                         req_ra=req_ra,
                                         req_dec=req_dec,
                                         epoch='2000',
                                         filter=par[1],
                                         focus_id=focus_id
                                         )
                    self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                    id_next += 1

    def _write_zero_dark(self, subcommand_name: str) -> None:

        id_next = 0

        if 'mirror_cover' in self.kwargs.keys():
            if self.kwargs['mirror_cover'] == 'auto':
                sub = MirrorCover(f'{self.id}_{self.numb(id_next)}', self, open=False)
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

        # Camera exposure
        if 'seq' in self.kwargs:
            seq_list = self._split_seq(self.kwargs['seq'])
            for n in seq_list:
                par = list(n.split('/'))

                sub = ChangeFilter(f'{self.id}_{self.numb(id_next)}',
                                   self,
                                   filter=par[1])
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

                for ex in range(1, int(par[0]) + 1):
                    sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                         self,
                                         sub_exp=ex,
                                         exp_time=float(par[2]),
                                         exp_no=int(par[0]),
                                         type=subcommand_name,
                                         light=False,
                                         obj_name=subcommand_name,
                                         req_ra='',
                                         req_dec='',
                                         epoch='2000',
                                         filter=par[1]
                                         )
                    self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                    id_next += 1

    def _write_marker(self):
        pass

    @staticmethod
    def _split_seq(seq):
        if str(seq).find(','):
            seq_list = list(seq.split(','))
        # elif str(seq).find('%'):
        #    seq_list = list(seq.split('%'))
        else:
            seq_list = list(seq)
        return seq_list

    async def arun(self, step_id: str or None = None) -> int:
        self.info_callback['stream_1'](f'Command {self.id} {self.command_name} started')
        logger.info(f'{self.id} {self.command_name} {self.args} {self.kwargs} started')
        await self._arun(self.subcomponents, step_id=step_id)
        self.info_callback['stream_5'](f'{self.id}')
        logger.info(f'{self.id} done')
        return 0

    async def stop(self):
        await self.parent.stop()





