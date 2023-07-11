import logging
import time
from datetime import datetime

from ob.comunication.comunication_error import CommunicationTimeoutError, CommunicationRuntimeError
from ob.data_colection.resource_manager.errors import ResourceCommandError
from ob.data_colection.resource_manager.resource_manager import ResourceManager
from ob.planrunner.ern.moves.move import Move
from ob.planrunner.ern.moves.position import Position

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CameraExposure(Move):
    _USED_RESOURCE = ResourceManager.CAMERA

    def __init__(self, exposure_time: float, light: bool, plan_data, resource_nr=0):
        super().__init__(plan_data=plan_data)
        self._resource_nr = resource_nr
        self._resource_content = self.res_mngr.get_resource(self._USED_RESOURCE, nr=self._resource_nr)

        self._exposure_time: float = exposure_time
        self._light: bool = light

        self.exp_time_start = None
        self.readout_time_start = None

        self._build()

    def _build(self):
        # here position has random value in target, it will be updated in a_init() method
        self.add_position(
            Position(f"{self._resource_content.adr}.imageready", t=True))

    async def _action(self):

        self.exp_time_start = datetime.utcnow()
        self.readout_time_start = time.time()
        # ----------------- exposure -----------------
        try:
            result = await self.api.put_async(address=f"{self._resource_content.adr}.startexposure",
                                              parameters_dict={'Duration': self._exposure_time, 'Light': self._light},
                                              no_wait=False)
        except (CommunicationRuntimeError, CommunicationTimeoutError) as e:
            raise ResourceCommandError(f"Action has error {str(e)}")
        if not result.status:
            raise ResourceCommandError(f"Action has error status in response {result.error}")
        await self.watch()
