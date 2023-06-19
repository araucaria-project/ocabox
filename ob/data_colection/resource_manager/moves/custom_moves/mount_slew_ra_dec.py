from pyaraucaria.coordinates import ra_to_decimal, dec_to_decimal, ra_dec_epoch, ra_dec_2_az_alt

from ob.data_colection.resource_manager.moves.move import Move
from ob.data_colection.resource_manager.moves.position import Position
from ob.data_colection.resource_manager.errors import ResourceCommandError


class MountSlewRaDec(Move):
    def __init__(self, api, resource, ra_dec):
        super().__init__(api=api)
        self._resource_content = resource
        self._ra_f = ra_to_decimal(ra_dec[0])
        self._dec_f = dec_to_decimal(ra_dec[1])
        self._position_ra_name = "ra"
        self._position_dec_name = "dec"
        self._build()

    def _build(self):
        # positions ra and dec have to have a name because it will be used in updating targets
        self.add_position(
            Position(f"{self._resource_content.adr}.rightascension", t=self._ra_f, bounds=(0.5, 0.5),
                     name=self._position_ra_name))
        self.add_position(
            Position(f"{self._resource_content.adr}.declination", t=self._dec_f, bounds=(0.5, 0.5),
                     name=self._position_dec_name))
        self.add_position(Position(f"{self._resource_content.adr}.tracking", t=True))
        self.add_position(Position(f"{self._resource_content.adr}.slewing", t=False, level=2))

    async def _action(self):
        ra_now, dec_now = ra_dec_epoch(ra=self._ra_f,
                                       dec=self._dec_f,
                                       epoch=str(self._resource_content.epoch))
        az, alt = ra_dec_2_az_alt(ra=ra_now,
                                  dec=dec_now,
                                  latitude=self._resource_content.latitude,
                                  longitude=self._resource_content.longitude,
                                  elevation=self._resource_content.elevation,
                                  epoch=self._resource_content.epoch)
        if alt <= self._resource_content.min_alt:
            raise ResourceCommandError(f"Altitude is lover then min altitude")

        # update ra dec in positions targets
        for p in self.positions:
            if p.get_name() == self._position_ra_name:
                p.target = ra_now
            if p.get_name() == self._position_dec_name:
                p.target = dec_now

        # ----------------- set tracking -----------------
        result = await self._api.put_async(address=f"{self._resource_content.adr}.tracking",
                                           parameters_dict={"Tracking": True}, no_wait=False)
        if not result.status:
            raise ResourceCommandError(f"Action has error status in response {result.error}")
        # ----------------- move mount -----------------
        result = await self._api.put_async(address=f"{self._resource_content.adr}.slewtocoordinatesasync",
                                           parameters_dict={"RightAscension": ra_now,
                                                            "Declination": dec_now},
                                           no_wait=False)
        if not result.status:
            raise ResourceCommandError("Action has error status in response")
        await self.watch()
