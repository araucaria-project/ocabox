from pyaraucaria.coordinates import deg_to_decimal_deg

from ob.data_colection.resource_manager.errors import ResourceCommandError
from ob.data_colection.resource_manager.resource_manager import ResourceManager
from ob.planrunner.ern.errors import PlanBuildError
from ob.planrunner.ern.moves.move import Move
from ob.planrunner.ern.moves.position import Position


class MountSlewAltAz(Move):
    _USED_RESOURCE = ResourceManager.MOUNT

    def __init__(self, api, alt_az, plan_data, resource_nr=0):
        super().__init__(api=api, plan_data=plan_data)
        self._resource_nr = resource_nr
        self._resource_content = self.res_mngr.get_resource(self._USED_RESOURCE, nr=self._resource_nr)
        self._alt = alt_az[0]
        self._az = alt_az[1]
        self._position_alt_name = "alt"
        self._position_az_name = "az"
        self._real_alt = None
        self._real_az = None
        self._build()

    def _build(self):
        try:
            self._real_alt = deg_to_decimal_deg(self._alt)
            self._real_az = deg_to_decimal_deg(self._az)
        except ValueError:
            raise PlanBuildError(f"Wrong az alt format")

        self.add_position(
            Position(f"{self._resource_content.adr}.altitude", t=self._real_alt, bounds=(0.5, 0.5),
                     name=self._position_alt_name))
        self.add_position(
            Position(f"{self._resource_content.adr}.azimuth", t=self._real_az, bounds=(0.5, 0.5),
                     name=self._position_az_name))
        self.add_position(Position(f"{self._resource_content.adr}.tracking", t=False))
        self.add_position(Position(f"{self._resource_content.adr}.slewing", t=False, order=2))

    async def _action(self):
        # check min alt
        if self._real_alt <= self._resource_content.min_alt:
            raise ResourceCommandError(f"Altitude is lover then min altitude")

        # todo zacząć uzywać głównego API a nie RARE API
        # ----------------- set tracking -----------------
        result = await self._api.put_async(address=f"{self._resource_content.adr}.tracking",
                                           parameters_dict={"Tracking": False}, no_wait=False)
        if not result.status:
            raise ResourceCommandError(f"Action has error status in response {result.error}")
        # ----------------- move mount -----------------
        result = await self._api.put_async(address=f"{self._resource_content.adr}.slewtoaltazasync",
                                           parameters_dict={"Azimuth": self._real_az,
                                                            "Altitude": self._real_alt},
                                           no_wait=False)
        if not result.status:
            raise ResourceCommandError("Action has error status in response")
        await self.watch()
