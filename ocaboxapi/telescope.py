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
        self.rotators = {}
        self._access_grantor = None
        self._observation_plan = None

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
