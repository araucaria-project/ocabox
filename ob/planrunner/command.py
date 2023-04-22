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
        super().__init__(self.id, self.command_name, self.info_callback)
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
        logger.info(f'Command {self.id} {self.command_name} is written')

    def _write_subcommands(self) -> None:
        self._create_command_string()

        if self.command_name == 'OBJECT':
            self._write_object_skyflat('object')

        elif self.command_name == 'DOMEFLAT':
            self._write_domeflat()

        elif self.command_name == 'FOCUS':
            self._write_focus()

        elif self.command_name == 'DARK':
            self._write_zero_dark('dark')

        elif self.command_name == 'ZERO':
            self._write_zero_dark('zero')

        elif self.command_name == 'SKYFLAT':
            self._write_object_skyflat('skyflat')

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
        dome_flat_alt = 15.0

        sub = DomeSlew(f'{self.id}_{self.numb(id_next)}', self, az=dome_az)
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        id_next += 1

        sub = MountSlew(f'{self.id}_{self.numb(id_next)}',
                        self,
                        obj_name='domeflat',
                        alt=dome_flat_alt,
                        az=dome_az+180,
                        tracking=False,
                        epoch='2000'
                        )
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        id_next += 1

        sub = DomeScreenLight(f'{self.id}_{self.numb(id_next)}', self, light=True)
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        id_next += 1

        # sub = MirrorCover(f'{self.id}_{self.numb(id_next)}', self, open=True)
        # self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        # id_next += 1

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
                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
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

        sub = DomeScreenLight(f'{self.id}_{self.numb(id_next)}', self, light=False)
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        id_next += 1

        # sub = MirrorCover(f'{self.id}_{self.numb(id_next)}', self, open=False)
        # self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub


    def _write_focus(self):
        # faster readmode, fits not saved on Perun
        id_next = 0
        if 'pos' in self.kwargs:
            sub = Focusing(f'{self.id}_{self.numb(id_next)}', self, pos=self.kwargs['pos'])
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

                sub = DomeSlew(f'{self.id}_{self.numb(id_next)}', self, follow_tol=3.0)
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
                                     exp_time=float(par[2]),
                                     exp_no=int(par[0]),
                                     type='focusing',
                                     light=True,
                                     obj_name='focus',
                                     req_ra='',
                                     req_dec='',
                                     epoch='2000',
                                     filter=par[1]
                                     )
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

    def _write_zero_dark(self, subcommand_name: str) -> None:

        id_next = 0

        # sub = MirrorCover(f'{self.id}_{self.numb(id_next)}', self, open=False)
        # self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        # id_next += 1

        # Camera exposure
        if 'seq' in self.kwargs:
            seq_list = self._split_seq(self.kwargs['seq'])
            for n in seq_list:
                par = list(n.split('/'))
                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
                                     exp_time=float(par[2]),
                                     exp_no=int(par[0]),
                                     type=subcommand_name,
                                     light=False,
                                     obj_name=subcommand_name,
                                     req_ra='',
                                     req_dec='',
                                     epoch='2000',
                                     filter=''
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
        await self._arun(self.subcomponents, step_id=step_id)
        self.info_callback['stream_5'](f'{self.id}')
        return 0

    async def stop(self):
        await self.parent.stop()

    def _write_object_skyflat(self, subcommand_name: str) -> None:

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

            sub = MountSlew(f'{self.id}_{self.numb(id_next)}',
                            self,
                            obj_name=obj_name,
                            ra=req_ra,
                            dec=req_dec,
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

        # sub = MirrorCover(f'{self.id}_{self.numb(id_next)}', self, open=True)
        # self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        # id_next += 1

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

                sub = DomeSlew(f'{self.id}_{self.numb(id_next)}', self, follow_tol=3.0)
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

                if subcommand_name == 'skyflat':
                    type = 'skyflat'
                else:
                    type = 'science'

                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
                                     exp_time=float(par[2]),
                                     exp_no=int(par[0]),
                                     type=type,
                                     light=True,
                                     obj_name=obj_name,
                                     req_ra=req_ra,
                                     req_dec=req_dec,
                                     epoch='2000',
                                     filter=par[1]
                                     )
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

        # sub = MirrorCover(f'{self.id}_{self.numb(id_next)}', self, open=False)
        # self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
