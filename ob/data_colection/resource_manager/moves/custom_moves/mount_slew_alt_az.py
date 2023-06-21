from pyaraucaria.coordinates import deg_to_decimal_deg

from ob.data_colection.resource_manager.errors import ResourceCommandError
from ob.data_colection.resource_manager.moves.move import Move
from ob.data_colection.resource_manager.moves.position import Position


class MountSlewAltAz(Move):
    def __init__(self, api, resource, alt_az):
        super().__init__(api=api)
        self._resource_content = resource
        self._alt = alt_az[0]
        self._az = alt_az[1]
        self._position_alt_name = "alt"
        self._position_az_name = "az"
        self._build()

    def _build(self):
        # positions ra and dec have to have a name because it will be used in updating targets
        self.add_position(
            Position(f"{self._resource_content.adr}.altitude", t=self._alt, bounds=(0.5, 0.5),
                     name=self._position_alt_name))
        self.add_position(
            Position(f"{self._resource_content.adr}.azimuth", t=self._az, bounds=(0.5, 0.5),
                     name=self._position_az_name))
        self.add_position(Position(f"{self._resource_content.adr}.tracking", t=False))
        self.add_position(Position(f"{self._resource_content.adr}.slewing", t=False, level=2))

    async def _action(self):
        try:
            alt = deg_to_decimal_deg(self._alt)
            az = deg_to_decimal_deg(self._az)
        except ValueError:
            raise ResourceCommandError(f"Wrong az alt format")
        # check min alt
        if alt <= self._resource_content.min_alt:
            raise ResourceCommandError(f"Altitude is lover then min altitude")

        # update alt az in positions targets
        for p in self.positions:
            if p.get_name() == self._position_alt_name:
                p.target = alt
            if p.get_name() == self._position_az_name:
                p.target = az

        # ----------------- set tracking -----------------
        result = await self._api.put_async(address=f"{self._resource_content.adr}.tracking",
                                           parameters_dict={"Tracking": False}, no_wait=False)
        if not result.status:
            raise ResourceCommandError(f"Action has error status in response {result.error}")
        # ----------------- move mount -----------------
        result = await self._api.put_async(address=f"{self._resource_content.adr}.slewtoaltazasync",
                                           parameters_dict={"Azimuth": az,
                                                            "Altitude": alt},
                                           no_wait=False)
        if not result.status:
            raise ResourceCommandError("Action has error status in response")
        await self.watch()

