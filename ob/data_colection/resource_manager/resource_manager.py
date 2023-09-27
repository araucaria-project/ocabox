import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Tuple

from ob.comunication.internal_client_api import InternalClientAPI
from ob.data_colection.alpaca_api.standard_telescope_components import StandardTelescopeComponents
from ob.data_colection.resource_manager.resource import DomeAlpaca, Resource, CovercalibratorAlpaca, \
    SafetymonitorAlpaca, SwitchAlpaca, FocuserAlpaca, RotatorAlpaca, FilterwheelAlpaca, CameraAlpaca, MountAlpaca

logger = logging.getLogger(__name__.rsplit('.')[-1])


class TelescopeComponentManager(StandardTelescopeComponents, ABC):
    """
    This is the resource manager for the telescope api support modules. The alpaca api class structure has been
    adopted as the resource standard.
    """
    RESOURCES_MAP = {}

    def __init__(self, target, path):
        self._resources: List[Resource] = []
        self._target = target
        self._path = path
        # ----- api ------
        # self._obs_api = Observatory(client_name="resource_manager_init_client", software_id="")
        self._rare_api = InternalClientAPI(request_solver=self._target, user_name=f"resource_manager_init_client")
        # self._obs_api.connect(self._rare_api)

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

    @abstractmethod
    async def initiate_resource_manager(self, resource_map: List[Tuple[str, str, str, int, dict]]):
        raise NotImplementedError


class TelescopeComponentManagerAlpaca(TelescopeComponentManager):
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
            r = c(source_name=adr, resource_name=name, nr=nr, target_request=self._target, properties=prop,
                  address_path=self._path)
            await r.a_init()
            self._resources.append(r)

    async def initiate_resource_manager(self, resource_map: List[Tuple[str, str, str, int, dict]]):
        await self._create_resource_object_map(resource_map=resource_map)
