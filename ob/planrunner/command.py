import logging
from typing import Dict, Any
from ob.planrunner.abstract_sequence import AbstractSequence
from ob.planrunner.subcommands.sub_mount_slew_coo import MountSlewCoo
from ob.planrunner.subcommands.sub_mount_slew_to_alt_az import MountSlewToAltAz
from ob.planrunner.subcommands.sub_dome_slave_telescope import DomeSlaveTelescope
from ob.planrunner.subcommands.sub_change_filter import ChangeFilter
from ob.planrunner.subcommands.sub_camera_exposure import CameraExposure


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
        super().__init__()
        self._write_subcommands()

    def _create_command_string(self):
        kw = ''
        for n in self.args:
            kw = f'{kw} {n}'
        for n in self.kwargs.keys():
            kw = f'{kw} {n}={self.kwargs[n]}'
        for n in self.parent_kwargs.keys():
            kw = f'{kw} {n}={self.parent_kwargs[n]}'
        self.info_callback['c_commands'](f'{self.id} {self.command_name}{kw}')
        logger.info(f'Command {self.id} {self.command_name} is written')

    def _write_subcommands(self) -> None:
        self._create_command_string()

        if self.command_name == 'OBJECT':
            self._write_object()

        elif self.command_name == 'DOMEFLAT':
            self._write_domeflat()

        elif self.command_name == 'FOCUS':
            self._write_focus()

        elif self.command_name == 'DARK':
            self._write_dark()

        elif self.command_name == 'ZERO':
            self._write_zero()

        elif self.command_name == 'SKYFLAT':
            self._write_skyflat()

        elif self.command_name == 'MARKER':
            self._write_marker()

        else:
            # TODO write some syntax error
            pass


    def _write_object(self):
        id_next = 0

        # Slew to coo
        if len(self.args) == 2:
            obj_name = ''
            ra = self.args[0]
            dec = self.args[1]
        else:
            obj_name = self.args[0]
            ra = self.args[1]
            dec = self.args[2]
        sub = MountSlewCoo(f'{self.id}_{self.numb(id_next)}', self,
                           obj_name=obj_name, ra=ra, dec=dec)
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub

        # Slave dome
        id_next += 1
        sub = DomeSlaveTelescope(f'{self.id}_{self.numb(id_next)}', self)
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub

        # Camera exposure
        id_next += 1
        if 'seq' in self.kwargs:
            if str(self.kwargs['seq']).find(','):
                seq_list = list(self.kwargs['seq'].split(','))
            else:
                seq_list = list(self.kwargs['seq'])
            for n in seq_list:
                par = list(n.split('/'))
                sub = ChangeFilter(f'{self.id}_{self.numb(id_next)}', self, filter=par[1])
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1
                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
                                     exposure_no=int(par[0]),
                                     exposure_time=float(par[2]))
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

    def _write_domeflat(self):
        id_next = 0

        # TODO turn on domeflat lamp, set brightness (value also from some config? or kwarg?)

        # Slew to alt az
        # TODO get Alt Az domeflat position from some config
        az = 90
        alt = 10
        # TODO add tracking on/off option
        sub = MountSlewToAltAz(f'{self.id}_{self.numb(id_next)}', self,
                               alt=float(alt), az=float(az))
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub

        # Camera exposure
        id_next += 1
        if 'seq' in self.kwargs:
            if str(self.kwargs['seq']).find(','):
                seq_list = list(self.kwargs['seq'].split(','))
            else:
                seq_list = list(self.kwargs['seq'])
            for n in seq_list:
                par = list(n.split('/'))
                sub = ChangeFilter(f'{self.id}_{self.numb(id_next)}', self, filter=par[1])
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1
                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
                                     exposure_no=int(par[0]),
                                     exposure_time=float(par[2]))
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

        # TODO turn off domeflat lamp

    def _write_focus(self):
        pass

    def _write_dark(self):
        pass

    def _write_zero(self):
        pass

    def _write_skyflat(self):
        pass

    def _write_marker(self):
        pass


    async def arun(self, step_id: str or None = None) -> None:
        self.info_callback['stream_1'](f'Command {self.id} {self.command_name} started')
        await self._arun(self.subcomponents, step_id=step_id)
        self.info_callback['stream_1'](f'Command {self.id} {self.command_name} done')
        self.info_callback['stream_5'](f'{self.id}')