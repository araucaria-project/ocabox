import asyncio
import logging

from ocaboxapi.abstelescope import AbstractTelescope
from ocaboxapi.access import AccessGrantor
from ocaboxapi.cctv import CCTV
from ocaboxapi.dome import Dome
from ocaboxapi.mount import Mount
from ocaboxapi.camera import Camera
from ocaboxapi.focuser import Focuser
from ocaboxapi.filterwheel import FilterWheel
from ocaboxapi.covercalibrator import CoverCalibrator
from ocaboxapi.rotator import Rotator
from ocaboxapi.plan import ObservationPlan
from ocaboxapi.exceptions import OcaboxServerError
from ocaboxapi.cycle_time import CycleTime
from ocaboxapi.guiding_controller import GuidingController
from typing import Dict
from obcom.comunication.comunication_error import CommunicationTimeoutError, CommunicationRuntimeError

from ocaboxapi.tertiary import Tertiary

logger = logging.getLogger("telescope")


class Telescope(AbstractTelescope):
    """The Telescope maintains components of signgle telescope"""

    def __init__(self, id: str, observatory: "Observatory") -> None:
        super().__init__(id=id, observatory=observatory)
        self.id = id
        self.mounts = {}
        self.domes = {}
        self.rotators = {}
        self.focusers = {}
        self.filterwheels = {}
        self.cameras = {}
        self.cctvs = {}
        self.covercalibrators = {}
        self.tertiarys = {}
        self._access_grantor = None
        self._observation_plan = None
        self._cycle_time_calculator = None
        self._guiding_controller = None
        # !!! po dodaniu nowego komponentu który dziedziczy po TelescopeComponent lub Component należy uzupełnić
        # metody unwatch_all_component() i unsubscribe_all_component()

    def get_mount(self, id='mount') -> Mount:
        try:
            return self.mounts[id]
        except LookupError:
            dev = Mount(id=id, telescope=self)
            self.mounts[id] = dev
            return dev

    def get_dome(self, id='dome') -> Dome:
        try:
            return self.domes[id]
        except LookupError:
            dev = Dome(id=id, telescope=self)
            self.domes[id] = dev
            return dev

    def get_camera(self, id='camera') -> Camera:
        try:
            return self.cameras[id]
        except LookupError:
            dev = Camera(id=id, telescope=self)
            self.cameras[id] = dev
            return dev

    def get_tertiary(self, id='tertiary') -> Tertiary:
        try:
            return self.tertiarys[id]
        except LookupError:
            dev = Tertiary(id=id, telescope=self)
            self.tertiarys[id] = dev
            return dev

    def get_cctv(self, id='cctv') -> CCTV:
        try:
            return self.cctvs[id]
        except LookupError:
            dev = CCTV(id=id, telescope=self)
            self.cctvs[id] = dev
            return dev

    def get_filterwheel(self, id='filterwheel') -> FilterWheel:
        try:
            return self.filterwheels[id]
        except LookupError:
            dev = FilterWheel(id=id, telescope=self)
            self.filterwheels[id] = dev
            return dev

    def get_focuser(self, id='focuser') -> Focuser:
        try:
            return self.focusers[id]
        except LookupError:
            dev = Focuser(id=id, telescope=self)
            self.focusers[id] = dev
            return dev

    def get_covercalibrator(self, id='covercalibrator') -> CoverCalibrator:
        try:
            return self.covercalibrators[id]
        except LookupError:
            dev = CoverCalibrator(id=id, telescope=self)
            self.covercalibrators[id] = dev
            return dev

    def get_access_grantor(self) -> AccessGrantor:
        if self._access_grantor is None:
            self._access_grantor = AccessGrantor(id='access_grantor', telescope=self)
        return self._access_grantor

    def get_observation_plan(self) -> ObservationPlan:
        if self._observation_plan is None:
            self._observation_plan = ObservationPlan(id='observation_plan', telescope=self)
        return self._observation_plan

    def get_rotator(self, id='derotator') -> Rotator:
        try:
            return self.rotators[id]
        except LookupError:
            dev = Rotator(id=id, telescope=self)
            self.rotators[id] = dev
            return dev

    def get_cycle_time_calculator(self, base_folder: str = None, client_config_dict: Dict or None = None) -> CycleTime:
        if self._cycle_time_calculator is None:
            self._cycle_time_calculator = CycleTime(
                telescope=self, base_folder=base_folder, client_config_dict=client_config_dict
            )
        return self._cycle_time_calculator

    def get_guiding_controller(self) -> GuidingController:
        if self._guiding_controller is None:
            self._guiding_controller = GuidingController(id='custom_guider', telescope=self)
        return self._guiding_controller

    async def is_telescope_alpaca_server_available(self, request_timeout: float = None) -> Dict[str, bool]:
        """
        The method checks if the telescope alpaca server responds
        :param request_timeout: waiting for answer timeout
        :return: True if server responds
        """
        try:
            va = await self.observatory.get_async(f'{self.tel_addr}.mount.connected',
                                                  request_timeout=request_timeout)
            if va == True or va == False:
                return {'alpaca': True}
        except (CommunicationTimeoutError, CommunicationRuntimeError, OcaboxServerError):
            return {'alpaca': False}

    async def shutdown(self):
        m = self.get_mount()
        d = self.get_dome()
        c = self.get_covercalibrator()
        a = self.get_access_grantor()
        await a.aput_break_control()
        await a.aput_take_control(600)
        if await m.aget_slewing():
            await m.aput_abortslew()
        if await d.aget_slewing():
            await d.aput_abortslew()
        await m.aput_tracking(False)
        await c.aput_closecover()
        while True:
            current = await c.aget_coverstate()
            if current == 1:
                await d.aput_closeshutter()
                break
            await asyncio.sleep(0.1)
        await m.aput_park()
        await d.aput_park()
        await asyncio.sleep(30)
        await m.aput_motoroff()

    async def weather_stop(self):
        m = self.get_mount()
        d = self.get_dome()
        c = self.get_covercalibrator()
        a = self.get_access_grantor()
        await a.aput_break_control()
        await a.aput_take_control(600)
        if await m.aget_slewing():
            await m.aput_abortslew()
        if await d.aget_slewing():
            await d.aput_abortslew()
        await m.aput_tracking(False)
        await m.aput_park()
        await c.aput_closecover()
        while True:
            current = await c.aget_coverstate()
            if current == 1:
                await d.aput_closeshutter()
                break
            await asyncio.sleep(0.1)
        await d.aput_park()

    async def emergency_stop(self):
        m = self.get_mount()
        d = self.get_dome()
        a = self.get_access_grantor()
        await a.aput_break_control()
        await a.aput_take_control(600)
        await m.aput_tracking(False)
        if await m.aget_slewing():
            await m.aput_abortslew()
        await m.aput_motoroff()
        if await d.aget_slewing():
            await d.aput_abortslew()

    def unsubscribe_all_component(self):
        for comp in self.mounts.values():
            comp.unsubscribe_all()
        for comp in self.domes.values():
            comp.unsubscribe_all()
        for comp in self.rotators.values():
            comp.unsubscribe_all()
        for comp in self.focusers.values():
            comp.unsubscribe_all()
        for comp in self.filterwheels.values():
            comp.unsubscribe_all()
        for comp in self.cameras.values():
            comp.unsubscribe_all()
        for comp in self.cctvs.values():
            comp.unsubscribe_all()
        for comp in self.covercalibrators.values():
            comp.unsubscribe_all()
        for comp in self.tertiarys.values():
            comp.unsubscribe_all()
        if self._access_grantor:
            self._access_grantor.unsubscribe_all()
        if self._guiding_controller:
            self._guiding_controller.unsubscribe_all()

    def unwatch_all_component(self):
        for comp in self.mounts.values():
            comp.unwatch_all()
            comp.reset_params_values()
        for comp in self.domes.values():
            comp.unwatch_all()
            comp.reset_params_values()
        for comp in self.rotators.values():
            comp.unwatch_all()
            comp.reset_params_values()
        for comp in self.focusers.values():
            comp.unwatch_all()
            comp.reset_params_values()
        for comp in self.filterwheels.values():
            comp.unwatch_all()
            comp.reset_params_values()
        for comp in self.cameras.values():
            comp.unwatch_all()
            comp.reset_params_values()
        for comp in self.cctvs.values():
            comp.unwatch_all()
            comp.reset_params_values()
        for comp in self.covercalibrators.values():
            comp.unwatch_all()
            comp.reset_params_values()
        for comp in self.tertiarys.values():
            comp.unsubscribe_all()
            comp.reset_params_values()
        if self._access_grantor:
            self._access_grantor.unwatch_all()
            self._access_grantor.reset_params_values()
        if self._guiding_controller:
            self._guiding_controller.unwatch_all()
            self._guiding_controller.reset_params_values()
