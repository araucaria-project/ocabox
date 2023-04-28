import asyncio
import logging
from abc import ABC
from typing import List, Tuple
from ob.data_colection.alpaca_api.standard_telescope_components import StandardTelescopeComponents
from ob.data_colection.resource_manager.resource import DomeAlpaca, Resource, CovercalibratorAlpaca, \
    SafetymonitorAlpaca, SwitchAlpaca, FocuserAlpaca, RotatorAlpaca, FilterwheelAlpaca, CameraAlpaca, MountAlpaca

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ResourceManager(StandardTelescopeComponents, ABC):
    """
    This is the resource manager for the telescope api support modules. The alpaca api class structure has been
    adopted as the resource standard.
    """
    RESOURCES_MAP = {}

    def __init__(self):
        self._resources: List[Resource] = []

    def get_resource(self, name, nr: int = 0):
        """
        This method returns for sub from resource manager. Resources are searched by alpaca resource type name
        and number, names may be repeated.

        :param name: name type of resource, one of provided types by manager
        :param nr: nr resource default 0
        :return: resource
        """
        out = None
        for res in self._resources:
            if res.name == name and res.nr == nr:
                out = res
                break
        return out


class ResourceManagerAlpaca(ResourceManager):
    """
    This is the resource manager for the alpaca module.
    """
    RESOURCES_MAP = {
        StandardTelescopeComponents.DOME: DomeAlpaca,
        StandardTelescopeComponents.MOUNT: MountAlpaca,
        StandardTelescopeComponents.CAMERA: CameraAlpaca,
        StandardTelescopeComponents.FILTERWHEEL: FilterwheelAlpaca,
        StandardTelescopeComponents.FOCUSER: FocuserAlpaca,
        StandardTelescopeComponents.ROTATOR: RotatorAlpaca,
        StandardTelescopeComponents.SWITCH: SwitchAlpaca,
        StandardTelescopeComponents.SAFETYMONITOR: SafetymonitorAlpaca,
        StandardTelescopeComponents.COVERCALIBRATOR: CovercalibratorAlpaca,
    }

    async def _create_resource_object_map(self, resource_map):
        self._resources = []
        for name, adr, typ, nr, prop in resource_map:
            c = self.RESOURCES_MAP.get(typ, None)
            if c is None:
                logger.error(f"{self.__class__.__name__} can not create resource. Unrecognised resource type {typ}")
                continue
            r = c(source_name=adr, resource_name=name, nr=nr, properties=prop)
            self._resources.append(r)

    async def initiate_resource_manager(self, resource_map: List[Tuple[str, str, str, int, dict]]):
        await self._create_resource_object_map(resource_map=resource_map)
