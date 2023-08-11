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
from ob.planrunner.cycle_time_calc.cycle_time_data_build import  CycleTimeDataBuild

from pyaraucaria.coordinates import ra_to_decimal, dec_to_decimal, deg_to_decimal_deg
from ob.planrunner.seq import Seq
from ob.planrunner.subcommand import SubCommand
from ob.planrunner.coded_error import SequenceTreeError

logger = logging.getLogger(__name__.rsplit('.')[-1])

class Command(AbstractSequence):

    TYPES = {'SKYFLAT': 'flat', 'FOCUS': 'focusing', 'DOMEFLAT': 'flat',
             'DARK': 'dark', 'ZERO': 'zero', 'OBJECT': 'science', 'WAIT': 'wait', 'STOP': 'stop', 'SNAP': 'snap'}

    def __init__(self, id: str, sequence_dict: Dict[Any, Any],
                 parent: 'Sequence' or 'NightPlan', param: Dict[str, Any] or None = None) -> None:
        self.id = id
        self.sequence_dict = sequence_dict
        self.parent = parent
        self.info_callback = parent.info_callback
        self.args = self.build_args(self.sequence_dict)
        self.kwargs = self.build_kwargs(sequence_dict=self.sequence_dict, info_callback=self.info_callback, id=id)
        self.parent_kwargs = self.parent.kwargs | self.parent.parent_kwargs
        self.command_name = self.sequence_dict['command_name']
        self.subcomponents = {}
        self.telescope = parent.telescope
        self.param = param
        self.info_callback = parent.info_callback
        self._cycle_time_data_build = CycleTimeDataBuild(self.telescope.id)

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
        self.info_callback['c_commands'](
            f'{self.id};'f'{self.command_name};'
            f' {round(self.param["cycle_time"].calc_time(command_dict=self.sequence_dict))}s;{kw}')
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

        elif self.command_name == 'SNAP':
            self._write_object_skyflat_focusing()

        else:
            logger.warning(f'{self.id} command name: {self.name} is wrong')
            self.info_callback['stream_1'](f'{self.id} command name: {self.name} is wrong')
            raise SequenceTreeError

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
    def dither_on(self) -> bool:
        """
        Do dithering or not.
        :return: bool
        """
        if self.command_name == 'SKYFLAT':
            if 'dither' not in self.kwargs.keys():
                return True
            elif 'dither' in self.kwargs.keys() and self.kwargs['dither'] != 'none':
                return True
            elif 'dither' in self.kwargs.keys() and self.kwargs['dither'] == 'none':
                return False
            else:
                return False

        elif self.command_name in self.possible_dither:
            if 'dither' not in self.kwargs.keys():
                return False
            elif 'dither' in self.kwargs.keys() and self.kwargs['dither'] != 'none':
                return True
            elif 'dither' in self.kwargs.keys() and self.kwargs['dither'] == 'none':
                return False
            else:
                return False
        else:
            return False

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
        if 'az' in self.kwargs.keys():
            try:
                return float(self.kwargs['az'])
            except ValueError:
                try:
                    return deg_to_decimal_deg(self.kwargs['az'])
                except ValueError:
                    return None
        else:
            return None

    @property
    def plan_alt(self) -> float or None:
        if 'alt' in self.kwargs.keys():
            try:
                return float(self.kwargs['alt'])
            except ValueError:
                try:
                    return deg_to_decimal_deg(self.kwargs['alt'])
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
    def possible_dither(self) -> List[str]:
        """
        List of commands with possibility of dither (excluding SKYFLAT, witch is dithering in default)
        :return: List of commands name
        """
        return ['OBJECT', 'SNAP']

    @property
    def tracking(self) -> bool:
        tracking = ['on', 'off']
        default_tracking_on = ['SKYFLAT', 'OBJECT', 'SNAP', 'FOCUS']

        if 'tracking' in self.kwargs.keys():
            if self.kwargs['tracking'] in tracking:
                return self.kwargs['tracking']
            else:
                logger.warning(f'Wrong tracking value')
                self.info_callback['stream_1'](f'{self.id} Wrong tracking value, set to off')
                return False
        else:
            if self.command_name in default_tracking_on:
                return True
            else:
                return False

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
            elif self.command_name == 'SNAP':
                name = 'snap'
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
                                           tracking=self.tracking,
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

    def _write_object_skyflat_focusing(self) -> None:

        id_next = 0

        # Mount slewing radec
        if (self.plan_ra and self.plan_dec) is not None and (self.plan_az and self.plan_alt) is None:
            id_next = self._add_comp(MountSlew(id=self._op_id(id_next=id_next),
                                                   parent=self,
                                                   obj_name=self.object_name,
                                                   ra=self.plan_ra,
                                                   dec=self.plan_dec,
                                                   tracking=self.tracking,
                                                   epoch=self.epoch,
                                                   uobi=self.uobi), id_next=id_next)

        # Mount slewing altaz
        if (self.plan_ra and self.plan_dec) is None and (self.plan_az and self.plan_alt) is not None:
            id_next = self._add_comp(MountSlew(id=self._op_id(id_next=id_next),
                                               parent=self,
                                               obj_name=self.object_name,
                                               alt=self.plan_alt,
                                               az=self.plan_az,
                                               tracking=self.tracking,
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
                                                           dither=True,
                                                           dither_distance=seq_data.dither_distance,
                                                           dither_mode=seq_data.dither_mode,
                                                           tracking=self.tracking,
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
                                                            req_ra=self.plan_ra,
                                                            req_dec=self.plan_dec,
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
        d = self.telescope.get_dome()
        m = self.telescope.get_mount()
        c = self.telescope.get_camera()
        f = self.telescope.get_filterwheel()
        f_names = await self.value_proof_get(name='command_fw_names',
                                             awaitab=f.aget_names,
                                             expect_type=list)
        f_n = []
        for n in f_names.keys():
            f_n.append(str(n))
        f_pos = await self.value_proof_get(name='command_fw_pos',
                                           awaitab=f.aget_position,
                                           expect_type=int)
        f_p = f_n[f_pos]
        self._cycle_time_data_build.insert_data(name='dither', value=self.dither_on)
        self._cycle_time_data_build.insert_data(name='filter_pos', value=f_p)
        d_az = await self.value_proof_get(name='command_dome_az',
                                          awaitab=d.aget_az,
                                          expect_type=float)
        self._cycle_time_data_build.insert_data(name='dome_az_begin', value=d_az)
        m_az = await self.value_proof_get(name='command_mount_az',
                                          awaitab=m.aget_az,
                                          expect_type=float)
        self._cycle_time_data_build.insert_data(name='mount_az_begin', value=m_az)
        m_alt = await self.value_proof_get(name='command_mount_alt',
                                           awaitab=m.aget_alt,
                                           expect_type=float)
        self._cycle_time_data_build.insert_data(name='mount_alt_begin', value=m_alt)
        self._cycle_time_data_build.insert_data(name='telescope', value=self.telescope.id)
        self._cycle_time_data_build.insert_data(name='id', value=self.id)
        self._cycle_time_data_build.insert_data(name='started', value=True)
        self._cycle_time_data_build.insert_data_dict(self.sequence_dict)
        self._cycle_time_data_build.save_to_log()
        skip = await self._arun(self.subcomponents, step_id=step_id)
        self._cycle_time_data_build.insert_data(name='done', value=self.done)
        self._cycle_time_data_build.insert_data(name='skipped', value=self.skipped)
        rm1 = await self.value_proof_get(name='command_cam_rm',
                                         awaitab=c.aget_readoutmode,
                                         expect_type=int)
        self._cycle_time_data_build.insert_data(name='readoutmode', value=rm1)
        self._cycle_time_data_build.save_to_log()
        self.info_callback['stream_5'](f'{self.id}')
        logger.info(f'{self.id} done')
        return skip
