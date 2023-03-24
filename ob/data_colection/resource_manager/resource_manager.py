import asyncio
import logging
from abc import ABC
from typing import List, Tuple

from ob.data_colection.alpaca_api.standard_telescope_components import StandardTelescopeComponents

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ResourceManager(StandardTelescopeComponents, ABC):
    """
    This is the resource manager for the telescope api support modules. The alpaca api class structure has been
    adopted as the resource standard.
    """
    def __init__(self):
        self._resources: List[ResourceManager.Resource] = []

    class Resource(asyncio.Lock):

        def __init__(self, name: str, source_name: str, resource_name: str, nr: int, **kwargs):
            self.name: str = name  # name in alpaca standard, can repeat for example if telescope has two filter well
            self.source_name: str = source_name  # tree address
            self.resource_name: str = resource_name  # custom name, is unique
            self.nr: int = nr  # number resource
            super().__init__(**kwargs)

    def get_resource(self, name, nr: int = 0):
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

    async def _create_resource_object_map(self, resource_map):
        self._resources = []
        for name, adr, typ, nr in resource_map:
            r = self.Resource(name=typ, source_name=adr, resource_name=name, nr=nr)
            self._resources.append(r)

    async def initiate_resource_manager(self, resource_map: List[Tuple[str, str, str, int]]):
        await self._create_resource_object_map(resource_map=resource_map)