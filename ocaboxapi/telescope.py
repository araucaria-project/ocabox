import asyncio
import json
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
from obcom.optics import GraphInvalid, OpticalGraph, default_detector, parse_graph, positions_of

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
        self._graph: tuple[str, OpticalGraph | None] | None = None  #: (the configuration it was parsed from, the graph)
        # !!! po dodaniu nowego komponentu który dziedziczy po TelescopeComponent lub Component należy uzupełnić
        # metody unwatch_all_component() i unsubscribe_all_component()

    # ------------------------------------------------------------------ components by configuration

    #: the getter of each configured ``kind`` that has a client class
    KIND_GETTERS = {'telescope': 'get_mount', 'dome': 'get_dome', 'camera': 'get_camera', 'tertiaryOCA': 'get_tertiary',
                    'tertiary': 'get_tertiary', 'mirrorcellACC': 'get_mirrorcell', 'filterwheel': 'get_filterwheel',
                    'focuser': 'get_focuser', 'covercalibrator': 'get_covercalibrator', 'rotator': 'get_rotator'}

    def get_component(self, name: str):
        """Component ``name`` of the configuration, with the client class of its ``kind``:
        ``get_component('derotator')`` is a :class:`Rotator`. ``LookupError`` for a name the
        configuration does not have, or a kind TIC serves no device for (a splitter, BESO)."""
        kind = self.component_config(name).get('kind')
        if kind is None:
            raise LookupError(f'{self.id}: no component {name!r} in the configuration')
        getter = self.KIND_GETTERS.get(kind)
        if getter is None:
            raise LookupError(f'{self.id}.{name}: kind {kind!r} has no device in TIC')
        return getattr(self, getter)(name)

    @property
    def optical_graph(self) -> OpticalGraph | None:
        """The optical graph of this telescope from the published configuration — what light reaches
        which detector through what; ``None`` without one (no detector declares ``paths:``) or when
        it is invalid (logged). Parsed again only when the configuration changes."""
        components = (self.get_config().get('observatory') or {}).get('components') or {}
        authored = json.dumps(components, sort_keys=True, default=str)
        if self._graph is None or self._graph[0] != authored:
            graph = None
            if any(isinstance(spec, dict) and spec.get('paths') for spec in components.values()):
                try:
                    graph = parse_graph(components, telescope=self.id)
                except GraphInvalid as e:
                    logger.error(f'{self.id}: optical graph invalid: {"; ".join(err.message for err in e.errors)}')
            self._graph = (authored, graph)
        return self._graph[1]

    def get_detectors(self, flag: str | None = None) -> list[OpticalDetector]:
        """Every detector of the optical graph — cameras, guiders, spectrographs — in configuration
        order; with ``flag`` only those whose configuration lists it (``flag='scientific'``)."""
        graph = self.optical_graph
        if graph is None:
            return []
        detectors = [self.get_optical_detector(name) for name in graph.detectors]
        return [d for d in detectors if flag is None or flag in d.flags]

    def default_detector(self, selectors: dict | None) -> OpticalDetector | None:
        """The detector to show first, from what the optics service publishes as ``selectors``: the
        one the routing selectors (M3) are set up for, an instrument before its guider; ``None``
        while that is not known. Pure — call it from a ``selectors`` subscription."""
        graph = self.optical_graph
        if graph is None:
            return None
        name = default_detector(graph, positions_of(selectors))
        return None if name is None else self.get_optical_detector(name)

    async def adefault_detector(self, time_of_data_tolerance: float | None = None) -> OpticalDetector | None:
        """:meth:`default_detector` from the optics service's current ``selectors``."""
        return self.default_detector(await self.get_optics().aget_selectors(time_of_data_tolerance=time_of_data_tolerance))

    # ------------------------------------------------------------------ components

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
            dev = OpticalDetector(id=f'optics.{detector}', name=detector, telescope=self)
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
