import asyncio
import logging
import time

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
from ocaboxapi.exceptions import OcaboxError
from ocaboxapi.cycle_time import CycleTime
from ocaboxapi.guiding_controller import GuidingController
from typing import Dict, Optional
from obcom.comunication.comunication_error import CommunicationTimeoutError, CommunicationRuntimeError

from ocaboxapi.tertiary import Tertiary
from ocaboxapi.mirrorcell import MirrorCell
from ocaboxapi.optics import OpticalDetector, OpticsState

logger = logging.getLogger("telescope")


class Telescope(AbstractTelescope):
    """The Telescope maintains components of signgle telescope"""

    MIRROR_COVER_TIMEOUT = 180
    DOME_SHUTTER_TIMEOUT = 180

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
        self.mirrorcells = {}
        self.optical_detectors = {}
        self._optics = None
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

    def get_mirrorcell(self, id='mirrorcell') -> MirrorCell:
        try:
            return self.mirrorcells[id]
        except LookupError:
            dev = MirrorCell(id=id, telescope=self)
            self.mirrorcells[id] = dev
            return dev

    def get_optical_detector(self, detector: str) -> OpticalDetector:
        """The light path of ``detector`` (a component name, e.g. ``camera``), served by the optics service."""
        try:
            return self.optical_detectors[detector]
        except LookupError:
            dev = OpticalDetector(id=f'optics.{detector}', telescope=self)
            self.optical_detectors[detector] = dev
            return dev

    def get_optics(self) -> OpticsState:
        """The telescope-wide state of the optics service: selectors, busy detectors, last operation."""
        if self._optics is None:
            self._optics = OpticsState(id='optics.self', telescope=self)
        return self._optics

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
        except (CommunicationTimeoutError, CommunicationRuntimeError, OcaboxError):
            return {'alpaca': False}

    async def shutdown(self, dome_park_az: Optional[float] = None) -> None:
        logger.info(f'Starting shutdown')
        mount = self.get_mount()
        dome = self.get_dome()
        cover = self.get_covercalibrator()
        access = self.get_access_grantor()
        await access.aput_break_control()
        await access.aput_take_control(84000)
        if await mount.aget_slewing():
            await mount.aput_abortslew()
        if await dome.aget_slewing():
            await dome.aput_abortslew()
        await mount.aput_tracking(False)
        await cover.aput_closecover()
        t_stamp_m = time.time()
        while True:
            if time.time() > t_stamp_m + self.MIRROR_COVER_TIMEOUT:
                logger.error(f'Mirror cover close get timeout')
            coverstate = await cover.aget_coverstate()
            if coverstate == 1:
                break
            await asyncio.sleep(0.1)
        await dome.aput_closeshutter()
        t_stamp_d = time.time()
        while True:
            if time.time() > t_stamp_d + self.DOME_SHUTTER_TIMEOUT:
                logger.error(f'Dome shutter close get timeout')
            shutterstatus = await dome.aget_shutterstatus()
            if shutterstatus == 1:
                break
            await asyncio.sleep(0.1)
        await mount.aput_park()
        if dome_park_az:
            await dome.aput_slewtoazimuth(az=dome_park_az)
        else:
            await dome.aput_park()
        logger.info(f'Shutdown done')

    async def weather_stop(self, dome_park_az: Optional[float] = None) -> None:
        logger.info(f'Starting weather stop')
        mount = self.get_mount()
        dome = self.get_dome()
        cover = self.get_covercalibrator()
        access = self.get_access_grantor()
        await access.aput_break_control()
        await access.aput_take_control(84000)
        if await mount.aget_slewing():
            await mount.aput_abortslew()
        if await dome.aget_slewing():
            await dome.aput_abortslew()
        await mount.aput_tracking(False)
        await mount.aput_park()
        await cover.aput_closecover()
        t_stamp_m = time.time()
        while True:
            if time.time() > t_stamp_m + self.MIRROR_COVER_TIMEOUT:
                logger.error(f'Mirror cover close get timeout')
            coverstate = await cover.aget_coverstate()
            if coverstate == 1:
                break
            await asyncio.sleep(0.1)
        await dome.aput_closeshutter()
        t_stamp_d = time.time()
        while True:
            if time.time() > t_stamp_d + self.DOME_SHUTTER_TIMEOUT:
                logger.error(f'Dome shutter close get timeout')
            shutterstatus = await dome.aget_shutterstatus()
            if shutterstatus == 1:
                break
            await asyncio.sleep(0.1)
        if dome_park_az:
            await dome.aput_slewtoazimuth(az=dome_park_az)
        else:
            await dome.aput_park()
        logger.info(f'Weather stop done')

    async def emergency_stop(self) -> None:
        logger.info(f'Starting emergency stop')
        mount = self.get_mount()
        dome = self.get_dome()
        access = self.get_access_grantor()
        await access.aput_break_control()
        await access.aput_take_control(84000)
        await mount.aput_tracking(False)
        if await mount.aget_slewing():
            await mount.aput_abortslew()
        await mount.aput_motoroff()
        if await dome.aget_slewing():
            await dome.aput_abortslew()
        logger.info(f'Emergency stop done')

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
        for comp in self.mirrorcells.values():
            comp.unsubscribe_all()
        for comp in self.optical_detectors.values():
            comp.unsubscribe_all()
        if self._optics:
            self._optics.unsubscribe_all()
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
            comp.unwatch_all()
            comp.reset_params_values()
        for comp in self.mirrorcells.values():
            comp.unwatch_all()
            comp.reset_params_values()
        for comp in self.optical_detectors.values():
            comp.unwatch_all()
            comp.reset_params_values()
        if self._optics:
            self._optics.unwatch_all()
            self._optics.reset_params_values()
        if self._access_grantor:
            self._access_grantor.unwatch_all()
            self._access_grantor.reset_params_values()
        if self._guiding_controller:
            self._guiding_controller.unwatch_all()
            self._guiding_controller.reset_params_values()
