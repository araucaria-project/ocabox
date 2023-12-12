import logging
from typing import Dict, Any, List, Callable
from ob.planrunner.base_sequence import BaseSequence
from ob.planrunner.subcommands.sub_mount_slew import MountSlew
from ob.planrunner.subcommands.sub_dome_slew import DomeSlew
from ob.planrunner.subcommands.sub_change_filter import ChangeFilter
from ob.planrunner.subcommands.sub_camera_exposure import CameraExposure
from ob.planrunner.subcommands.sub_mirror_cover import MirrorCover
from ob.planrunner.subcommands.sub_dome_screenlight import DomeScreenLight
from ob.planrunner.subcommands.sub_focusing import Focusing
from ob.planrunner.subcommands.sub_stop import Stop
from ob.planrunner.subcommands.sub_wait import Wait
from ob.planrunner.cycle_time_calc.cycle_time_data_build import CycleTimeDataBuild
from pyaraucaria.coordinates import ra_to_decimal, dec_to_decimal, deg_to_decimal_deg
from ob.planrunner.seq import Seq
from ob.planrunner.base_subcommand import BaseSubCommand
from ob.planrunner.coded_error import SequenceTreeError


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Command(BaseSequence):

    TYPES = {'SKYFLAT': 'flat', 'FOCUS': 'focusing', 'DOMEFLAT': 'flat',
             'DARK': 'dark', 'ZERO': 'zero', 'OBJECT': 'science', 'WAIT': 'wait', 'STOP': 'stop', 'SNAP': 'snap'}

    def __init__(self, id: str, sequence_dict: Dict[Any, Any], telescope: 'Telescope',
                 info_callback: Dict[str, Callable], param: Dict[str, Any] or None = None) -> None:
        self._cycle_time_data_build = CycleTimeDataBuild(
            telescope=telescope.id,
            base_folder=telescope.observatory.get_app_cfg(key='base_cycle_time_calc_dir'))
        super().__init__(id=id, name=sequence_dict['command_name'], info_callback=info_callback,
                         telescope=telescope, sequence_dict=sequence_dict, c_type='command', param=param)
        self.build_args(self.sequence_dict)
        self.build_kwargs(sequence_dict=self.sequence_dict)
        self._write_subcommands()

    def _create_command_string(self):
        kw = ''
        for n in self.args:
            kw = f'{kw} {n}'
        for n in self.kwargs.keys():
            if n != 'seq_data':
                kw = f'{kw} {n}={self.kwargs[n]}'
        self.info_callback['c_commands'](
            f'{self.id};'f'{self.name};'
            f' {round(self.param["cycle_time"].calc_time(command_dict=self.sequence_dict))}s;{kw}')
        logger.info(f'{self.id} {self.name} {self.args} {self.kwargs} is written')

    def _write_subcommands(self) -> None:
        self._create_command_string()

        if self.name == 'OBJECT':
            self._write_object_skyflat_focusing()

        elif self.name == 'DOMEFLAT':
            self._write_domeflat()

        elif self.name == 'FOCUS':
            self._write_object_skyflat_focusing()

        elif self.name == 'DARK':
            self._write_zero_dark()

        elif self.name == 'ZERO':
            self._write_zero_dark()

        elif self.name == 'SKYFLAT':
            self._write_object_skyflat_focusing()

        elif self.name == 'WAIT':
            self._write_wait()

        elif self.name == 'STOP':
            self._write_stop()

        elif self.name == 'SNAP':
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
        if self.name == 'SKYFLAT':
            try:
                d = self.kwargs['dither']
                if d == 'off':
                    return False
                else:
                    return True
            except KeyError:
                return True

        elif self.name in self.possible_dither:
            try:
                d = self.kwargs['dither']
                if d == 'off':
                    return False
                else:
                    return True
            except KeyError:
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

    def _add_comp(self, sub: BaseSubCommand, id_next: int) -> int:
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
                if self.kwargs['tracking'] == 'on':
                    return True
                elif self.kwargs['tracking'] == 'off':
                    return False
                else:
                    return False
            else:
                logger.warning(f'Wrong tracking value')
                self.info_callback['stream_1'](f'{self.id} Wrong tracking value, set to off')
                return False
        else:
            if self.name in default_tracking_on:
                return True
            else:
                return False

    @property
    def object_name(self) -> str:
        if not self.plan_object_name:
            if self.name == 'SKYFLAT':
                name = 'skyflat'
            elif self.name == 'FOCUS':
                name = 'focusing'
            elif self.name == 'DOMEFLAT':
                name = 'domeflat'
            elif self.name == 'DARK':
                name = 'dark'
            elif self.name == 'ZERO':
                name = 'zero'
            elif self.name == 'SNAP':
                name = 'snap'
            else:
                name = ''
        else:
            name = self.plan_object_name
        return name

    @property
    def exp_type(self):
        return Command.TYPES[self.name]

    def _write_domeflat(self):

        id_next = 0

        # Dome slewing to domeflat position
        if self._dome_follow is True:
            id_next = self._add_comp(DomeSlew(id=self._op_id(id_next=id_next),
                                              telescope=self.telescope,
                                              info_callback=self.info_callback,
                                              az=self.domeflat_dome_az,
                                              param=self.param,
                                              uobi=self.uobi), id_next=id_next)

        # Mount slewing to domeflat position
        id_next = self._add_comp(MountSlew(id=self._op_id(id_next=id_next),
                                           telescope=self.telescope,
                                           info_callback=self.info_callback,
                                           obj_name=self.object_name,
                                           alt=self.domeflat_mount_alt,
                                           az=self.domeflat_mount_az,
                                           tracking=self.tracking,
                                           epoch=self.epoch,
                                           param=self.param,
                                           uobi=self.uobi
                                           ), id_next=id_next)

        # Turn screen light on
        if self.screen_light_mode in ['auto', 'on']:
            id_next = self._add_comp(DomeScreenLight(id=self._op_id(id_next=id_next),
                                                     telescope=self.telescope,
                                                     info_callback=self.info_callback,
                                                     light=True,
                                                     param=self.param,
                                                     uobi=self.uobi), id_next=id_next)

        # Open mirror cover
        if self.mirror_cover_mode in ['auto', 'open']:
            id_next = self._add_comp(MirrorCover(id=self._op_id(id_next=id_next),
                                                 telescope=self.telescope,
                                                 info_callback=self.info_callback,
                                                 open=True,
                                                 param=self.param,
                                                 uobi=self.uobi), id_next=id_next)

        # Camera exposure sequences
        if self.plan_seq:
            for s in self.plan_seq:
                seq_data = Seq(seq=s, command_kwargs=self.kwargs)

                # Change filter
                id_next = self._add_comp(ChangeFilter(id=self._op_id(id_next=id_next),
                                                      telescope=self.telescope,
                                                      info_callback=self.info_callback,
                                                      filter=seq_data.filter,
                                                      param=self.param,
                                                      uobi=self.uobi), id_next=id_next)

                for ex in range(1, seq_data.exp_no + 1):
                    # Camera single sequence, single exposure

                    # Camera exposure
                    id_next = self._add_comp(CameraExposure(id=self._op_id(id_next=id_next),
                                                            telescope=self.telescope,
                                                            info_callback=self.info_callback,
                                                            sub_exp=ex,
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
                                                            seq_data=seq_data,
                                                            param=self.param,
                                                            uobi=self.uobi), id_next=id_next)

        # Turning off light
        if self.screen_light_mode in ['auto', 'off']:
            id_next = self._add_comp(DomeScreenLight(id=self._op_id(id_next=id_next),
                                                     telescope=self.telescope,
                                                     info_callback=self.info_callback,
                                                     light=False,
                                                     param=self.param,
                                                     uobi=self.uobi), id_next=id_next)

        # Close mirror covers
        if self.mirror_cover_mode in ['close']:
            id_next = self._add_comp(MirrorCover(id=self._op_id(id_next=id_next),
                                                 telescope=self.telescope,
                                                 info_callback=self.info_callback,
                                                 open=False,
                                                 param=self.param,
                                                 uobi=self.uobi), id_next=id_next)

    def _write_object_skyflat_focusing(self) -> None:

        id_next = 0

        # Mount slewing radec
        if (self.plan_ra and self.plan_dec) is not None and (self.plan_az and self.plan_alt) is None:
            id_next = self._add_comp(MountSlew(id=self._op_id(id_next=id_next),
                                               telescope=self.telescope,
                                               info_callback=self.info_callback,
                                               obj_name=self.object_name,
                                               ra=self.plan_ra,
                                               dec=self.plan_dec,
                                               tracking=self.tracking,
                                               epoch=self.epoch,
                                               param=self.param,
                                               uobi=self.uobi), id_next=id_next)

        # Mount slewing altaz
        if (self.plan_ra and self.plan_dec) is None and (self.plan_az and self.plan_alt) is not None:
            id_next = self._add_comp(MountSlew(id=self._op_id(id_next=id_next),
                                               telescope=self.telescope,
                                               info_callback=self.info_callback,
                                               obj_name=self.object_name,
                                               alt=self.plan_alt,
                                               az=self.plan_az,
                                               tracking=self.tracking,
                                               epoch=self.epoch,
                                               param=self.param,
                                               uobi=self.uobi), id_next=id_next)
        # No coordinates - no slewing
        else:
            pass

        # Dome follow
        if self._dome_follow is True:
            id_next = self._add_comp(DomeSlew(id=self._op_id(id_next=id_next),
                                              telescope=self.telescope,
                                              info_callback=self.info_callback,
                                              param=self.param,
                                              uobi=self.uobi), id_next=id_next)

        # Mirror cover
        if self.mirror_cover_mode in ['auto', 'open']:
            id_next = self._add_comp(MirrorCover(id=self._op_id(id_next=id_next),
                                                 telescope=self.telescope,
                                                 info_callback=self.info_callback,
                                                 open=True,
                                                 param=self.param,
                                                 uobi=self.uobi), id_next=id_next)

        # Camera exposure sequences
        if self.plan_seq:
            for s in self.plan_seq:
                seq_data = Seq(seq=s, command_kwargs=self.kwargs)

                # Change filter
                id_next = self._add_comp(ChangeFilter(id=self._op_id(id_next=id_next),
                                                      telescope=self.telescope,
                                                      info_callback=self.info_callback,
                                                      filter=seq_data.filter,
                                                      param=self.param,
                                                      uobi=self.uobi), id_next=id_next)

                for ex in range(1, seq_data.exp_no + 1):
                    # Camera single sequence, single exposure

                    # Focusig
                    if self.name == 'FOCUS':
                        id_next = self._add_comp(Focusing(id=self._op_id(id_next=id_next),
                                                          telescope=self.telescope,
                                                          info_callback=self.info_callback,
                                                          position=seq_data.focus_position(exp_no=ex),
                                                          param=self.param,
                                                          uobi=self.uobi), id_next=id_next)

                    # Dithering
                    if seq_data.dither_this_exp(ex=ex) is True and self.dither_on is True:

                        # Mount slew dithering
                        id_next = self._add_comp(MountSlew(id=self._op_id(id_next=id_next),
                                                           telescope=self.telescope,
                                                           info_callback=self.info_callback,
                                                           obj_name=self.object_name,
                                                           dithering=True,
                                                           tracking=self.tracking,
                                                           epoch=self.epoch,
                                                           seq_data=seq_data,
                                                           param=self.param,
                                                           uobi=self.uobi), id_next=id_next)

                    # Dome follow between exposures
                    if self._dome_follow is True and (ex > 1):
                        id_next = self._add_comp(DomeSlew(id=self._op_id(id_next=id_next),
                                                          telescope=self.telescope,
                                                          info_callback=self.info_callback,
                                                          seq_data=seq_data,
                                                          param=self.param,
                                                          uobi=self.uobi), id_next=id_next)

                    # Camera exposure
                    id_next = self._add_comp(CameraExposure(id=self._op_id(id_next=id_next),
                                                            telescope=self.telescope,
                                                            info_callback=self.info_callback,
                                                            sub_exp=ex,
                                                            exp_no=seq_data.exp_no,
                                                            type=self.exp_type,
                                                            light=True,
                                                            obj_name=self.object_name,
                                                            req_ra=self.plan_ra,
                                                            req_dec=self.plan_dec,
                                                            epoch=self.epoch,
                                                            filter=seq_data.filter,
                                                            auto_exposure=seq_data.auto_exposure,
                                                            observer=self.observer,
                                                            seq_data=seq_data,
                                                            param=self.param,
                                                            uobi=self.uobi), id_next=id_next)

        # Mirror cover close
        if self.mirror_cover_mode in ['close']:
            id_next = self._add_comp(MirrorCover(id=self._op_id(id_next=id_next),
                                                 telescope=self.telescope,
                                                 info_callback=self.info_callback,
                                                 open=False,
                                                 param=self.param,
                                                 uobi=self.uobi), id_next=id_next)

    def _write_zero_dark(self) -> None:

        id_next = 0

        # Mirror cover
        if self.mirror_cover_mode in ['auto', 'close']:
            id_next = self._add_comp(MirrorCover(id=self._op_id(id_next=id_next),
                                                 telescope=self.telescope,
                                                 info_callback=self.info_callback,
                                                 open=False,
                                                 param=self.param,
                                                 uobi=self.uobi), id_next=id_next)

        # Camera exposure sequences
        if self.plan_seq:
            for s in self.plan_seq:
                seq_data = Seq(seq=s, command_kwargs=self.kwargs)

                # Change filter
                id_next = self._add_comp(ChangeFilter(id=self._op_id(id_next=id_next),
                                                      telescope=self.telescope,
                                                      info_callback=self.info_callback,
                                                      filter=seq_data.filter,
                                                      param=self.param,
                                                      uobi=self.uobi), id_next=id_next)

                for ex in range(1, seq_data.exp_no + 1):
                    # Camera single sequence, single exposure

                    # Camera exposure
                    id_next = self._add_comp(CameraExposure(id=self._op_id(id_next=id_next),
                                                            telescope=self.telescope,
                                                            info_callback=self.info_callback,
                                                            sub_exp=ex,
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
                                                            seq_data=seq_data,
                                                            param=self.param,
                                                            uobi=self.uobi), id_next=id_next)

    def _write_wait(self):
        id_next = 0
        if len(self.kwargs.keys()) == 1:
            key = list(self.kwargs.keys())[0]
            id_next = self._add_comp(Wait(id=self._op_id(id_next=id_next),
                                          telescope=self.telescope,
                                          info_callback=self.info_callback,
                                          key=key,
                                          value=self.kwargs[key],
                                          param=self.param,
                                          uobi=self.uobi), id_next=id_next)
        else:
            pass

    def _write_stop(self):
        id_next = 0
        id_next = self._add_comp(Stop(id=self._op_id(id_next=id_next),
                                      telescope=self.telescope,
                                      info_callback=self.info_callback,
                                      param=self.param,
                                      uobi=self.uobi), id_next=id_next)

    @staticmethod
    def _split_seq(seq):
        if str(seq).find(','):
            seq_list = list(seq.split(','))
        else:
            seq_list = list(seq)
        return seq_list

    @staticmethod
    def fw_named(f_pos: int, f_names: Dict) -> str or int:
        if f_names is not None:
            inv_f_map = {v: k for k, v in f_names.items()}
        else:
            inv_f_map = {}
        if f_pos in inv_f_map.keys():
            return inv_f_map[f_pos]
        else:
            return f_pos

    async def arun(self, step_id: str or None = None) -> int:
        self.info_callback['stream_1'](f'Command {self.id} {self.name} started.')

        await self.journal.info(f'{self.id} {self.name} started.')
        logger.info(f'{self.id} {self.name} started.')
        d = self.telescope.get_dome()
        m = self.telescope.get_mount()
        c = self.telescope.get_camera()
        f = self.telescope.get_filterwheel()
        f_pos = await self.value_proof_get(name='command_fw_pos',
                                           awaitab=f.aget_position,
                                           expect_type=int)
        f_names = await f.aget_names()
        d_az = await self.value_proof_get(name='command_dome_az',
                                          awaitab=d.aget_az,
                                          expect_type=float)
        m_az = await self.value_proof_get(name='command_mount_az',
                                          awaitab=m.aget_az,
                                          expect_type=float)
        m_alt = await self.value_proof_get(name='command_mount_alt',
                                           awaitab=m.aget_alt,
                                           expect_type=float)
        f = str(self.fw_named(f_pos=f_pos, f_names=f_names))
        self._cycle_time_data_build.insert_data(name='dome_az_begin', value=d_az)
        self._cycle_time_data_build.insert_data(name='mount_az_begin', value=m_az)
        self._cycle_time_data_build.insert_data(name='dither', value=self.dither_on)
        self._cycle_time_data_build.insert_data(name='mount_alt_begin', value=m_alt)
        self._cycle_time_data_build.insert_data(name='telescope', value=self.telescope.id)
        self._cycle_time_data_build.insert_data(name='id', value=self.id)
        self._cycle_time_data_build.insert_data(name='started', value=True)
        self._cycle_time_data_build.insert_data_dict(self.sequence_dict)
        self._cycle_time_data_build.insert_data(name='filter_pos', value=f)
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

        await self.journal.info(f'{self.id} {self.name} done.')
        logger.info(f'{self.id} done')
        return skip
