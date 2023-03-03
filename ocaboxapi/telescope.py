import logging

from ocaboxapi.abstelescope import AbstractTelescope
from ocaboxapi.access import AccessGrantor
from ocaboxapi.dome import Dome
from ocaboxapi.mount import Mount
from ocaboxapi.camera import Camera

logger = logging.getLogger("telescope")

class Telescope(AbstractTelescope):
    """The Telescope maintains components of signgle telescope"""

    def __init__(self, id: str, observatory: "Observatory") -> None:
        super().__init__(id=id, observatory=observatory)
        self.mounts = {}
        self.domes = {}
        self.rotators = {}
        self.focusers = {}
        self.filterweels = {}
        self.cameras = {}
        self._access_grantor = None

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
            return self.domes[id]
        except LookupError:
            dev = Camera(id=id, telescope=self)
            self.cameras[id] = dev
            return dev


    def get_access_grantor(self) -> AccessGrantor:
        if self._access_grantor is None:
            self._access_grantor = AccessGrantor(id='access_grantor', telescope=self)
        return self._access_grantor

    async def take_control(self, telescope: str):
        logger.info(f'Take control')
        await self.observatory.put_async(f'{self.tel_addr}.access_grantor.take_control')

