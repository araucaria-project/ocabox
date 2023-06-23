import logging
from typing import Dict, Any, List
from ob.planrunner.abstract_sequence import AbstractSequence
from ob.planrunner.subcommands.sub_mount_slew import MountSlew
from ob.planrunner.subcommands.sub_dome_slew import DomeSlew
from ob.planrunner.subcommands.sub_change_filter import ChangeFilter
from ob.planrunner.subcommands.sub_camera_exposure import CameraExposure
from ob.planrunner.subcommands.sub_mirror_cover import MirrorCover
from ob.planrunner.subcommands.sub_dome_screenlight import DomeScreenLight
from ob.planrunner.subcommands.sub_focusing import Focusing
from ob.planrunner.subcommands.sub_stop import Stop
from ob.planrunner.subcommands.sub_wait import Wait
from pyaraucaria.coordinates import az_alt_2_ra_dec, ra_to_decimal, dec_to_decimal, \
    deg_to_decimal_deg, ra_dec_2_az_alt,  deg_str_to_deg
import random
from ob.planrunner.subcommand import SubCommand

logger = logging.getLogger(__name__.rsplit('.')[-1])

class Command(AbstractSequence):

    TYPES = {'SKYFLAT': 'flat', 'FOCUS': 'focusing', 'DOMEFLAT': 'flat',
             'DARK': 'dark', 'ZERO': 'zero', 'OBJECT': 'science', 'WAIT': 'wait', 'STOP': 'stop'}

    def __init__(self, id: str, sequence_dict: Dict[Any, Any],
                 parent: 'Sequence' or 'NightPlan', param: Dict[str, Any] or None = None) -> None:
        self.id = id
        self.sequence_dict = sequence_dict
        self.parent = parent
        self.args = self.build_args(self.sequence_dict)
        self.kwargs = self.build_kwargs(self.sequence_dict)
        self.parent_kwargs = self.parent.kwargs | self.parent.parent_kwargs
        self.command_name = self.sequence_dict['command_name']
        self.subcomponents = {}
        self.telescope = parent.telescope
        self.param = param
        self.info_callback = parent.info_callback
        super().__init__(self.id, self.command_name, self.info_callback,
                         observatory=self.parent.observatory, c_type='command', kwargs=self.kwargs)
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

    def _write_subcommands(self) -> None:
        self._create_command_string()

        if self.command_name == 'OBJECT':
            self._write_object_skyflat_focusing()

        elif self.command_name == 'DOMEFLAT':
            self._write_domeflat()

        elif self.command_name == 'FOCUS':
            self._write_object_skyflat_focusing()

        elif self.command_name == 'DARK':
            self._write_zero_dark()

        elif self.command_name == 'ZERO':
            self._write_zero_dark()

        elif self.command_name == 'SKYFLAT':
            self._write_object_skyflat_focusing()

        elif self.command_name == 'WAIT':
            self._write_wait()

        elif self.command_name == 'STOP':
            self._write_stop()

        else:
            # TODO add info, that parsed plan have errors
            self.info_callback['stream_1'](f'Command {self.command_name} not recognized, check plan syntax' )

    @property
    def uobi(self) -> int:
        if 'uobi' in self.kwargs.keys():
            return self.kwargs['uobi']
        else:
            return 0

    @property
    def _dome_follow(self) -> bool:
        if 'dome_follow' in self.kwargs.keys():
            if self.kwargs['dome_follow'] == 'off':
                return False
            else:
                return True
        else:
            return True

    @property
    def epoch(self) -> str:
        if 'epoch' in self.kwargs.keys():
            return str(self.kwargs['epoch'])
        else:
            return f'2000'

    @property
    def mirror_cover_mode(self):
        modes = ['auto', 'open', 'close']
        if 'mirror_cover' in self.kwargs.keys():
            if self.kwargs['mirror_cover'] in modes:
                return self.kwargs['mirror_cover']
            else:
                return None
        else:
            return None

    @property
    def observer(self) -> str:
        if 'observer' in self.param.keys():
            return self.param['observer']
        else:
            return ''

    @property
    def screen_light_mode(self):
        modes = ['auto', 'on', 'off']
        if 'screen_light' in self.kwargs.keys():
            if self.kwargs['screen_light'] in modes:
                return self.kwargs['screen_light']
            else:
                return None
        else:
            return None

    def _op_id(self, id_next: int) -> str:
        return f'{self.id}_{self.numb(id_next)}'

    def _add_comp(self, sub: SubCommand, id_next: int) -> int:
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        return id_next + 1

    @property
    def plan_object_name(self) -> str or None:
        if len(self.args) == 3:
            name = self.args[0]
        elif len(self.args) == 1:
            name = self.args[0]
        else:
            name = None
        return name

    @property
    def plan_ra(self) -> float or None:
        if len(self.args) == 2:
            ra = ra_to_decimal(self.args[0])
        elif len(self.args) == 3:
            ra = ra_to_decimal(self.args[1])
        else:
            ra = None
        return ra

    @property
    def plan_dec(self) -> float or None:
        if len(self.args) == 2:
            dec = dec_to_decimal(self.args[1])
        elif len(self.args) == 3:
            dec = dec_to_decimal(self.args[2])
        else:
            dec = None
        return dec

    @property
    def plan_az(self) -> float or None:
        if 'alt' and 'az' in self.kwargs.keys():
            try:
                return float(self.kwargs['az'])
            except ValueError:
                try:
                    return deg_str_to_deg(self.kwargs['az'])
                except ValueError:
                    return None
        else:
            return None

    @property
    def plan_alt(self) -> float or None:
        if 'alt' and 'az' in self.kwargs.keys():
            try:
                return float(self.kwargs['alt'])
            except ValueError:
                try:
                    return deg_str_to_deg(self.kwargs['alt'])
                except ValueError:
                    return None
        else:
            return None

    @property
    def plan_seq(self):
        if 'seq' in self.kwargs.keys():
            return self._split_seq(self.kwargs['seq'])
        else:
            return None

    @property
    def domeflat_dome_az(self) -> float or None:
        # TODO take this value from settings
        if self.exp_type == 'flat':
            return 0.0
        else:
            return None

    @property
    def domeflat_mount_az(self) -> float or None:
        # TODO take this value from settings
        if self.exp_type == 'flat':
            return self.domeflat_dome_az + 180.0
        else:
            return None

    @property
    def domeflat_mount_alt(self) -> float or None:
        # TODO take this value from settings
        if self.exp_type == 'flat':
            return 15.0
        else:
            return None

    @property
    def object_name(self) -> str:
        if not self.plan_object_name:
            if self.command_name == 'SKYFLAT':
                name = 'skyflat'
            elif self.command_name == 'FOCUS':
                name = 'focusing'
            elif self.command_name == 'DOMEFLAT':
                name = 'domeflat'
            elif self.command_name == 'DARK':
                name = 'dark'
            elif self.command_name == 'ZERO':
                name = 'zero'
            else:
                name = ''
        else:
            name = self.plan_object_name
        return name

    @property
    def exp_type(self):
        return Command.TYPES[self.command_name]

    def _write_domeflat(self):

        id_next = 0

        # Dome slewing to domeflat position
        if self._dome_follow is True:
            id_next = self._add_comp(DomeSlew(id=self._op_id(id_next=id_next),
                                              parent=self,
                                              az=self.domeflat_dome_az,
                                              uobi=self.uobi), id_next=id_next)

        # Mount slewing to domeflat position
        id_next = self._add_comp(MountSlew(id=self._op_id(id_next=id_next),
                                           parent=self,
                                           obj_name=self.object_name,
                                           alt=self.domeflat_mount_alt,
                                           az=self.domeflat_mount_az,
                                           tracking=False,
                                           epoch=self.epoch,
                                           uobi=self.uobi
                                           ), id_next=id_next)

        # Turn screen light on
        if self.screen_light_mode in ['auto', 'on']:
            id_next = self._add_comp(DomeScreenLight(id=self._op_id(id_next=id_next),
                                                     parent=self,
                                                     light=True,
                                                     uobi=self.uobi), id_next=id_next)

        # Open mirror cover
        if self.mirror_cover_mode in ['auto', 'open']:
            id_next = self._add_comp(MirrorCover(id=self._op_id(id_next=id_next),
                                                 parent=self,
                                                 open=True,
                                                 uobi=self.uobi), id_next=id_next)

        # Camera exposure sequences
        if self.plan_seq:
            for s in self.plan_seq:
                seq_data = Seq(seq=s, parent=self)

                # Change filter
                id_next = self._add_comp(ChangeFilter(id=self._op_id(id_next=id_next),
                                                      parent=self,
                                                      filter=seq_data.filter,
                                                      uobi=self.uobi), id_next=id_next)

                for ex in range(1, seq_data.exp_no + 1):
                    # Camera single sequence, single exposure

                    # Camera exposure
                    id_next = self._add_comp(CameraExposure(id=self._op_id(id_next=id_next),
                                                            parent=self,
                                                            sub_exp=ex,
                                                            exp_time=seq_data.exp_time,
                                                            exp_no=seq_data.exp_no,
                                                            type=self.exp_type,
                                                            light=True,
                                                            obj_name=self.object_name,
                                                            req_ra='',
                                                            req_dec='',
                                                            epoch=self.epoch,
                                                            filter=seq_data.filter,
                                                            auto_exposure=False,
                                                            observer=self.observer,
                                                            uobi=self.uobi), id_next=id_next)

        # Turning off light
        if self.screen_light_mode in ['auto', 'off']:
            id_next = self._add_comp(DomeScreenLight(id=self._op_id(id_next=id_next),
                                                     parent=self,
                                                     light=False,
                                                     uobi=self.uobi), id_next=id_next)

        # Close mirror covers
        if self.mirror_cover_mode in ['close']:
            id_next = self._add_comp(MirrorCover(id=self._op_id(id_next=id_next),
                                                 parent=self,
                                                 open=False,
                                                 uobi=self.uobi), id_next=id_next)
        del seq_data

    def _write_object_skyflat_focusing(self) -> None:

        id_next = 0

        # Mount slewing radec
        if self.plan_ra and self.plan_dec:
            id_next = self._add_comp(MountSlew(id=self._op_id(id_next=id_next),
                                                   parent=self,
                                                   obj_name=self.object_name,
                                                   ra=self.plan_ra,
                                                   dec=self.plan_dec,
                                                   epoch=self.epoch,
                                                   uobi=self.uobi), id_next=id_next)
        # Mount slewing altaz
        elif self.plan_az and self.plan_alt:
            id_next = self._add_comp(MountSlew(id=self._op_id(id_next=id_next),
                                               parent=self,
                                               obj_name=self.object_name,
                                               alt=self.plan_alt,
                                               az=self.plan_az,
                                               tracking=True,
                                               epoch=self.epoch,
                                               uobi=self.uobi), id_next=id_next)
        # No coordinates - no slewing
        else:
            pass

        # Dome follow
        if self._dome_follow is True:
            id_next = self._add_comp(DomeSlew(id=self._op_id(id_next=id_next),
                                              parent=self,
                                              follow_tol=2.0,
                                              uobi=self.uobi), id_next=id_next)

        # Mirror cover
        if self.mirror_cover_mode in ['auto', 'open']:
            id_next = self._add_comp(MirrorCover(id=self._op_id(id_next=id_next),
                                                 parent=self,
                                                 open=True,
                                                 uobi=self.uobi), id_next=id_next)

        # Camera exposure sequences
        if self.plan_seq:
            for s in self.plan_seq:
                seq_data = Seq(seq=s, parent=self)

                # Change filter
                id_next = self._add_comp(ChangeFilter(id=self._op_id(id_next=id_next),
                                                      parent=self,
                                                      filter=seq_data.filter,
                                                      uobi=self.uobi), id_next=id_next)

                for ex in range(1, seq_data.exp_no + 1):
                    # Camera single sequence, single exposure

                    # Focusig
                    if self.command_name == 'FOCUS':
                        id_next = self._add_comp(Focusing(id=self._op_id(id_next=id_next),
                                                          parent=self,
                                                          position=seq_data.focus_position(exp_no=ex),
                                                          uobi=self.uobi), id_next=id_next)

                    # Dithering
                    if seq_data.dither_this_exp(ex=ex):

                        # Mount slew dithering
                        id_next = self._add_comp(MountSlew(id=self._op_id(id_next=id_next),
                                                           parent=self,
                                                           obj_name=self.object_name,
                                                           ra=seq_data.ra_dither,
                                                           dec=seq_data.dec_dither,
                                                           epoch=self.epoch,
                                                           uobi=self.uobi), id_next=id_next)

                    # Dome follow between exposures
                    if self._dome_follow is True and (ex > 1):
                        id_next = self._add_comp(DomeSlew(id=self._op_id(id_next=id_next),
                                                          parent=self,
                                                          follow_tol=3.0,
                                                          uobi=self.uobi), id_next=id_next)

                    # Camera exposure
                    id_next = self._add_comp(CameraExposure(id=self._op_id(id_next=id_next),
                                                            parent=self,
                                                            sub_exp=ex,
                                                            exp_time=seq_data.exp_time,
                                                            exp_no=seq_data.exp_no,
                                                            type=self.exp_type,
                                                            light=True,
                                                            obj_name=self.object_name,
                                                            req_ra=seq_data.ra_final,
                                                            req_dec=seq_data.dec_final,
                                                            epoch=self.epoch,
                                                            filter=seq_data.filter,
                                                            focus_id=seq_data.focus_id,
                                                            auto_exposure=seq_data.auto_exposure,
                                                            observer=self.observer,
                                                            uobi=self.uobi), id_next=id_next)

        # Mirror cover close
        if self.mirror_cover_mode in ['close']:
            id_next = self._add_comp(MirrorCover(id=self._op_id(id_next=id_next),
                                                 parent=self,
                                                 open=False,
                                                 uobi=self.uobi), id_next=id_next)
        del seq_data

    def _write_zero_dark(self) -> None:

        id_next = 0

        # Mirror cover
        if self.mirror_cover_mode in ['auto', 'close']:
            id_next = self._add_comp(MirrorCover(id=self._op_id(id_next=id_next),
                                                 parent=self,
                                                 open=False,
                                                 uobi=self.uobi), id_next=id_next)

        # Camera exposure sequences
        if self.plan_seq:
            for s in self.plan_seq:
                seq_data = Seq(seq=s, parent=self)

                # Change filter
                id_next = self._add_comp(ChangeFilter(id=self._op_id(id_next=id_next),
                                                      parent=self,
                                                      filter=seq_data.filter,
                                                      uobi=self.uobi), id_next=id_next)

                for ex in range(1, seq_data.exp_no + 1):
                    # Camera single sequence, single exposure

                    # Camera exposure
                    id_next = self._add_comp(CameraExposure(id=self._op_id(id_next=id_next),
                                                            parent=self,
                                                            sub_exp=ex,
                                                            exp_time=seq_data.exp_time,
                                                            exp_no=seq_data.exp_no,
                                                            type=self.exp_type,
                                                            light=False,
                                                            obj_name=self.object_name,
                                                            req_ra='',
                                                            req_dec='',
                                                            epoch=self.epoch,
                                                            filter=seq_data.filter,
                                                            auto_exposure=False,
                                                            observer=self.observer,
                                                            uobi=self.uobi), id_next=id_next)

        del seq_data

    def _write_wait(self):
        id_next = 0
        if len(self.kwargs.keys()) == 1:
            key = list(self.kwargs.keys())[0]
            id_next = self._add_comp(Wait(id=self._op_id(id_next=id_next),
                                          parent=self,
                                          key=key,
                                          value=self.kwargs[key]), id_next=id_next)
        else:
            pass

    def _write_stop(self):
        id_next = 0
        id_next = self._add_comp(Stop(id=self._op_id(id_next=id_next), parent=self), id_next=id_next)

    @staticmethod
    def _split_seq(seq):
        if str(seq).find(','):
            seq_list = list(seq.split(','))
        else:
            seq_list = list(seq)
        return seq_list

    async def arun(self, step_id: str or None = None) -> int:
        self.info_callback['stream_1'](f'Command {self.id} {self.command_name} started')
        logger.info(f'{self.id} {self.command_name} {self.args} {self.kwargs} started')
        skip = await self._arun(self.subcomponents, step_id=step_id)
        self.info_callback['stream_5'](f'{self.id}')
        logger.info(f'{self.id} done')
        return skip


class Seq:

    """
    Class representing camera single sequence parameters
    """

    def __init__(self, seq: str, parent: Command):
        self._seq: str = seq
        self._focus_id: int or None = None
        self.parent_kwargs: Dict = parent.kwargs
        self.parent: Command = parent
        self.set_focus_id()

    @property
    def site_coo(self) -> Dict[str, float]:
        # TODO Take this from settings
        return {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817}

    @property
    def if_radec(self) -> bool:
        if self.parent.plan_ra and self.parent.plan_dec:
            return True
        else:
            return False

    def if_altaz(self) -> bool:
        if self.parent.plan_az and self.parent.plan_alt:
            return True
        else:
            return False

    @staticmethod
    def ra_random_dither(ra: float, dith_val: float, mode: str = 'basic') -> float:
        # TODO dith_val = dith_val / cos(dec) ?
        if mode == 'basic':
            return ra + random.uniform(-dith_val / 60, dith_val / 60)

    @staticmethod
    def dec_random_dither(dec: float, dith_val: float, mode: str = 'basic') -> float:
        if mode == 'basic':
            return dec + random.uniform(-dith_val / 60, dith_val / 60)

    @property
    def ra_dither(self) -> float or None:
        if self.dither_on:
            if self.if_radec:
                return self.ra_random_dither(ra=self.parent.plan_ra,
                                             dith_val=self.dither_distance,
                                             mode=self.dither_mode)
            elif self.if_altaz:
                ra, _ = az_alt_2_ra_dec(alt=self.parent.plan_alt,
                                        az=self.parent.plan_az,
                                        latitude=self.site_coo['latitude'],
                                        longitude=self.site_coo['longitude'],
                                        elevation=self.site_coo['elevation'])
                return self.ra_random_dither(ra=ra,
                                             dith_val=self.dither_distance,
                                             mode=self.dither_mode)
            else:
                return None
        else:
            return None

    @property
    def dec_dither(self) -> float or None:
        if self.dither_on:
            if self.if_radec:
                return self.dec_random_dither(dec=self.parent.plan_dec,
                                              dith_val=self.dither_distance,
                                              mode=self.dither_mode)
            elif self.if_altaz:
                _, dec = az_alt_2_ra_dec(alt=self.parent.plan_alt,
                                         az=self.parent.plan_az,
                                         latitude=self.site_coo['latitude'],
                                         longitude=self.site_coo['longitude'],
                                         elevation=self.site_coo['elevation'])
                return self.dec_random_dither(dec=dec,
                                              dith_val=self.dither_distance,
                                              mode=self.dither_mode)
            else:
                return None
        else:
            return None

    @property
    def ra_final(self) -> float:
        if self.dither_on:
            return self.ra_dither
        else:
            return self.parent.plan_ra

    @property
    def dec_final(self) -> float:
        if self.dither_on:
            return self.dec_dither
        else:
            return self.parent.plan_dec

    @property
    def focus_id(self) -> int or None:
        return self._focus_id

    def set_focus_id(self):
        self._focus_id = random.randrange(0, 100000)

    @property
    def focus_list(self) -> List[str] or None:
        """
        Input format focus_target/focus_step
        :return: [focus_target/focus_step]
        """
        if 'pos' in self.parent_kwargs.keys():
            return list(self.parent_kwargs['pos'].split('/'))
        else:
            return None

    @property
    def focus_target(self) -> int or None:
        if self.focus_list:
            return int(self.focus_list[0])
        else:
            return None

    def focus_position(self, exp_no: int) -> float or None:
        if self.focus_values_list:
            return self.focus_values_list[exp_no - 1]
        else:
            return None

    @property
    def focus_min(self) -> int or None:
        if self.focus_list:
            return int(round(self.focus_target - (self.focus_step * ((self.exp_no - 1) / 2))))
        else:
            return None

    @property
    def focus_step(self) -> int or None:
        if self.focus_list:
            return int(self.focus_list[1])
        else:
            return None

    @property
    def focus_values_list(self) -> List[str] or None:
        if self.focus_list:
            f = []
            for n in range(0, self.exp_no):
                f.append(self.focus_min + (self.focus_step * n))
            return f
        else:
            return None

    @property
    def seq_list(self) -> List[str]:
        return list(self._seq.split('/'))

    @property
    def exp_no(self) -> int:
        return int(self.seq_list[0])

    @property
    def filter(self) -> str or int:
        return self.seq_list[1]

    @property
    def exp_time(self) -> float or None:
        try:
            return float(self.seq_list[2])
        except ValueError:
            return None

    @property
    def auto_exposure(self) -> bool:
        if self.seq_list[2] == 'a':
            return True
        else:
            return False

    @property
    def dither_list(self) -> List[str] or None:
        # [dither_mode, dither_every_sub, dither_distance]
        if 'dither' in self.parent_kwargs.keys():
            if self.parent_kwargs['dither'] == 'none':
                return None
            else:
                return list(self.parent_kwargs['dither'].split('/'))
        else:
            return None

    @property
    def dither_mode(self) -> str:
        if self.dither_list:
            return str(self.dither_list[0])
        else:
            # TODO get from settings
            return 'basic'

    @property
    def dither_every_sub(self) -> int:
        if self.dither_list:
            return int(self.dither_list[1])
        else:
            # TODO get from settings
            return 1

    @property
    def dither_distance(self) -> float:
        if self.dither_list:
            return float(self.dither_list[2])
        else:
            # TODO get from settings
            return 1.0

    @property
    def dither_on(self) -> bool:
        """
        Do dithering or not.
        :return: bool
        """
        if self.parent.command_name == 'SKYFLAT':
            if 'dither' not in self.parent_kwargs.keys():
                return True
            elif 'dither' in self.parent_kwargs.keys() and self.parent_kwargs['dither'] != 'none':
                return True
            elif 'dither' in self.parent_kwargs.keys() and self.parent_kwargs['dither'] =='none':
                return False
            else:
                return False

        elif self.parent.command_name == 'OBJECT':
            if 'dither' not in self.parent_kwargs.keys():
                return False
            elif 'dither' in self.parent_kwargs.keys() and self.parent_kwargs['dither'] != 'none':
                return True
            elif 'dither' in self.parent_kwargs.keys() and self.parent_kwargs['dither'] == 'none':
                return False
            else:
                return False
        else:
            return False

    def dither_this_exp(self, ex: int) -> bool:
        if (ex % self.dither_every_sub == 0) and self.dither_on and (ex > 1):
            return True
        else:
            return False


