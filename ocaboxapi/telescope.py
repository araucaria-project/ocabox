import logging

from ocaboxapi.abstelescope import AbstractTelescope
from ocaboxapi.dome import Dome
from ocaboxapi.mount import Mount

log = logging.getLogger("telescope")

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

    def get_mount(self, id='mount') -> Mount:
        try:
            return self.mounts[id]
        except LookupError:
            dev = Mount(id, self)
            self.mounts[id] = dev
            return dev

    def get_dome(self, id='dome') -> Dome:
        try:
            return self.domes[id]
        except LookupError:
            dev = Dome(id=id, telescope=self)
            self.domes[id] = dev
            return dev

