import logging
from pyaraucaria.coordinates import deg_to_decimal_deg
from ob.comunication.comunication_error import CommunicationRuntimeError, CommunicationTimeoutError
from ob.data_colection.resource_manager.errors import ResourceCommandError
from ob.data_colection.resource_manager.resource_manager import ResourceManager
from ob.planrunner.ern.errors import PlanBuildError
from ob.planrunner.ern.moves.move import Move
from ob.planrunner.ern.moves.position import Position

logger = logging.getLogger(__name__.rsplit('.')[-1])


class DomeSlew(Move):
    _USED_RESOURCE = ResourceManager.DOME

    def __init__(self, az: float or str or int, plan_data, resource_nr: int = 0):
        super().__init__(plan_data=plan_data)
        self._resource_nr = resource_nr
        self._resource_content = self.res_mngr.get_resource(self._USED_RESOURCE, nr=self._resource_nr)
        self._az = az
        self._position_az_name = "az"
        self._position_slewing_name = "slewing"
        self._real_az = None
        self._build()

    def _build(self):
        try:
            self._real_az = deg_to_decimal_deg(self._az)
        except (ValueError, TypeError):
            raise PlanBuildError(f"Wrong az format")

        self.add_position(
            Position(f"{self._resource_content.adr}.azimuth", t=self._real_az, bounds=(0.5, 0.5),
                     name=self._position_az_name))
        self.add_position(Position(f"{self._resource_content.adr}.slewing", t=False, order=2,
                                   name=self._position_slewing_name))

    async def _action(self):
        # ----------------- move dome -----------------
        try:
            result = await self.api.put_async(address=f"{self._resource_content.adr}.slewtoazimuth",
                                              parameters_dict={"Azimuth": self._real_az},
                                              no_wait=False)
        except (CommunicationRuntimeError, CommunicationTimeoutError) as e:  # probably newer happened
            raise ResourceCommandError(f"Action has error {str(e)}")
        if not result.status:
            raise ResourceCommandError("Action has error status in response")
        await self.watch()
