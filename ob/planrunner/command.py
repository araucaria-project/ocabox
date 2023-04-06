import logging
from typing import Dict, Any
from ob.planrunner.abstract_sequence import AbstractSequence
from ob.planrunner.subcommands.sub_mount_slew_coo import MountSlewCoo
from ob.planrunner.subcommands.sub_mount_slew_to_alt_az import MountSlewToAltAz
from ob.planrunner.subcommands.sub_dome_slew import DomeSlew
from ob.planrunner.subcommands.sub_change_filter import ChangeFilter
from ob.planrunner.subcommands.sub_camera_exposure import CameraExposure
from pyaraucaria.coordinates import ra_dec_2_az_alt, deg_str_to_deg

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
            # TODO add info, that parsed plan have errors
            self.info_callback['stream_1'](f'Command {self.command_name} not recognized, check plan syntax' )

    def _write_object(self):
        id_next = 0
        obj_name = ''
        req_ra = ''
        req_dec = ''
        # Slew to coo
        if len(self.args) > 1:
            if len(self.args) == 2:
                req_ra = self.args[0]
                req_dec = self.args[1]
                sub = MountSlewCoo(f'{self.id}_{self.numb(id_next)}',
                                   self,
                                   obj_name=obj_name,
                                   ra=req_ra,
                                   dec=req_dec,
                                   epoch='2000')
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
            elif len(self.args) == 3:
                obj_name = self.args[0]
                req_ra = self.args[1]
                req_dec = self.args[2]
                sub = MountSlewCoo(f'{self.id}_{self.numb(id_next)}',
                                   self,
                                   obj_name=obj_name,
                                   ra=req_ra,
                                   dec=req_dec,
                                   epoch='2000')
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub

            # Slave dome
            id_next += 1
            OCA = {'latitude': '-24:35:53', 'longitude': '-70:11:47', 'elevation': '2817'}
            dome_az, _ = ra_dec_2_az_alt(ra=req_ra,
                                       dec=req_dec,
                                       latitude=OCA['latitude'],
                                       longitude=OCA['longitude'],
                                       elevation=OCA['elevation'],
                                       epoch='2000')
            sub = DomeSlew(f'{self.id}_{self.numb(id_next)}',
                           self)
            self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
            id_next += 1
        else:
            pass

        # Camera exposure
        if 'seq' in self.kwargs:
            # TODO move to abstract sequence
            if str(self.kwargs['seq']).find(','):
                seq_list = list(self.kwargs['seq'].split(','))
            else:
                seq_list = list(self.kwargs['seq'])
            for n in seq_list:
                par = list(n.split('/'))
                sub = ChangeFilter(f'{self.id}_{self.numb(id_next)}',
                                   self,
                                   filter=par[1])
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
                                     type='science',
                                     light=True,
                                     exp_no=int(par[0]),
                                     exp_time=float(par[2]),
                                     obj_name=obj_name,
                                     req_ra=req_ra,
                                     req_dec=req_dec,
                                     epoch='2000')
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

    def _write_domeflat(self):
        id_next = 0

        # Slew to altaz
        # TODO turn on domeflat lamp, set brightness (value also from some config? or kwarg?)
        # TODO get Alt Az domeflat position from some config
        dome_az = 0.0
        dome_flat_az = dome_az + 180.0
        dome_flat_alt = 15.0
        sub = DomeSlew(f'{self.id}_{self.numb(id_next)}',
                       self,
                       az=dome_az)
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
        id_next += 1

        sub = MountSlewToAltAz(f'{self.id}_{self.numb(id_next)}',
                               self,
                               alt=dome_flat_alt,
                               az=dome_az+180,
                               tracking=False,
                               epoch='2000')
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
                sub = ChangeFilter(f'{self.id}_{self.numb(id_next)}',
                                   self,
                                   filter=par[1])
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1
                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
                                     type='flat',
                                     light=True,
                                     domeflatlight=True,
                                     exp_no=int(par[0]),
                                     exp_time=float(par[2]),
                                     obj_name='',
                                     req_ra='',
                                     req_dec='',
                                     epoch='2000'
                                     )
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

        # TODO turn off domeflat lamp

    def _write_focus(self):
        # faster readmode, fits not saved on Perun
        pass

    def _write_dark(self):
        id_next = 0

        # Camera exposure
        id_next += 1
        if 'seq' in self.kwargs:

            if str(self.kwargs['seq']).find(','):
                seq_list = list(self.kwargs['seq'].split(','))
            else:
                seq_list = list(self.kwargs['seq'])
            for n in seq_list:
                par = list(n.split('/'))
                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
                                     type='dark',
                                     light=False,
                                     exp_no=int(par[0]),
                                     exp_time=float(par[2]),
                                     obj_name='',
                                     req_ra='',
                                     req_dec='',
                                     epoch='2000'
                                     )
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

    def _write_zero(self):
        id_next = 0

        # Camera exposure
        id_next += 1
        if 'seq' in self.kwargs:

            if str(self.kwargs['seq']).find(','):
                seq_list = list(self.kwargs['seq'].split(','))
            else:
                seq_list = list(self.kwargs['seq'])
            for n in seq_list:
                par = list(n.split('/'))
                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
                                     type='zero',
                                     light=False,
                                     exp_no=int(par[0]),
                                     exp_time=float(par[2]),
                                     obj_name='',
                                     req_ra='',
                                     req_dec='',
                                     epoch='2000'
                                     )
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1

    def _write_skyflat(self):
        id_next = 0

        sub = MountSlewToAltAz(f'{self.id}_{self.numb(id_next)}',
                               self,
                               alt=self.kwargs['alt'],
                               az=self.kwargs['az'],
                               tracking=True,
                               epoch='2000')
        self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub

        # Slave dome
        id_next += 1
        sub = DomeSlew(f'{self.id}_{self.numb(id_next)}',
                       self,
                       az=deg_str_to_deg(self.kwargs['az']))
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
                sub = ChangeFilter(f'{self.id}_{self.numb(id_next)}',
                                   self,
                                   filter=par[1])
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1
                sub = CameraExposure(f'{self.id}_{self.numb(id_next)}',
                                     self,
                                     type='flat',
                                     light=True,
                                     exp_no=int(par[0]),
                                     exp_time=float(par[2]),
                                     obj_name='',
                                     req_ra='',
                                     req_dec='',
                                     epoch='2000'
                                     )
                self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
                id_next += 1


    def _write_marker(self):
        pass

    async def arun(self, step_id: str or None = None) -> int:
        self.info_callback['stream_1'](f'Command {self.id} {self.command_name} started')
        await self._arun(self.subcomponents, step_id=step_id)
        self.info_callback['stream_5'](f'{self.id}')
        return 0

    async def stop(self):
        await self.parent.stop()
