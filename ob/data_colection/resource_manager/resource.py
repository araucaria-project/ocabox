import asyncio
import logging
from abc import ABC
from typing import Callable, Optional, Tuple

from pyaraucaria.coordinates import deg_str_to_deg, ra_dec_epoch, ra_dec_2_az_alt, dec_to_decimal, ra_to_decimal

from ob.comunication.comunication_error import CommunicationRuntimeError
from ob.data_colection.address import Address
from ob.data_colection.alpaca_api.standard_telescope_components import StandardTelescopeComponents
from ob.util_functions.asyncio_util_functions import wait_for_psce

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Resource(ABC):
    RESOURCE_NAME = ""

    def __init__(self, source_name: str, resource_name: str, nr: int, target_request, properties: dict = None,
                 address_path: str = "", **kwargs):
        if properties is None:
            properties = {}
        self._source_name: str = source_name
        self._resource_name: str = resource_name
        self._nr: int = nr
        self._properties: dict = properties  # properties, from settings and more
        self._lock = asyncio.Lock()
        if address_path:
            a = ".".join([address_path, self.source_name])
        else:
            a = ".".join([self.source_name])
        self._tree_address_path = Address.as_address(a)
        self._target = target_request
        super().__init__(**kwargs)

    @property
    def nr(self) -> int:
        """number resource, used in alpaca request"""
        return self._nr

    @property
    def name(self) -> str:
        """Name in alpaca standard, can repeat for example if telescope has two filter well"""
        return self.RESOURCE_NAME

    @property
    def adr(self) -> str:
        """tree full path address"""
        return self._tree_address_path.__str__()

    @property
    def source_name(self) -> str:
        """tree address name"""
        return self._source_name

    @property
    def id_name(self) -> str:
        """Custom name, is unique"""
        return self._resource_name

    @property
    def properties(self) -> dict:
        return self._properties

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    async def __aenter__(self):
        await self._lock.acquire()
        return None

    async def __aexit__(self, exc_type, exc, tb):
        self._lock.release()

    def __enter__(self):
        raise RuntimeError(
            '"yield from" should be used as context manager expression')

    def __exit__(self, *args):
        pass

    @staticmethod
    def _read_alt_az_coord(alt, az):
        """
        Method return alt, az after converting.

        :param alt: altitude
        :param az: azimuth
        :raise ValueError: if it can not convert values
        :return: alt az after converting
        """
        alt_ = None
        az_ = None
        if alt is not None and az is not None:
            try:
                az_ = float(az)
                alt_ = float(alt)
            except ValueError:
                try:
                    az_ = deg_str_to_deg(az)
                    alt_ = deg_str_to_deg(alt)
                except ValueError:
                    raise ValueError
        return alt_, az_


class Position:
    def __init__(self, address, t=None, s=None, c=None, timeout=None,
                 bounds: Tuple[Optional[float], Optional[float]] = (None, None), level: int = 1, name: str = ""):
        self._target = t
        self._start = s
        self._current = c
        self.custom_end_condition: Optional[Callable] = None
        self.error = False
        self.error_content = None
        self.task = None
        self._address = address
        self._finish_fut = None
        self.timeout = timeout if timeout is not None else 20
        self.level = level
        # ------ optional -------
        self.bounds: Tuple[Optional[float], Optional[float]] = bounds
        self._wait_for_others: list = []
        self._name: str = name

    def get_name(self) -> str:
        return self._name

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, s):
        self._start = s

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, c):
        self._current = c

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, t):
        self._target = t

    def get_finish_future(self):
        return self._finish_fut

    def _check_finish(self):
        """
            Method check current value is achieved target.

            :raise ValueError
            :return: bool
            """
        if self.custom_end_condition is not None and callable(self.custom_end_condition):
            return self.custom_end_condition(self.start, self.current, self.target)
        elif self.bounds[0] is not None and self.bounds[1] is not None:
            return self._check_finish_bounded()
        if self.current == self.target:
            return True
        else:
            return False

    def _check_finish_bounded(self):
        """
            Method check current value is achieved target witch bounds.

            :raise ValueError
            :return: bool
            """
        try:
            t = float(self.target)
            c = float(self.current)
        except ValueError:
            raise
        bound_btm = self.bounds[0]
        bound_top = self.bounds[1]
        if t - bound_btm < c < t + bound_top:
            return True
        else:
            return False

    def done(self):
        if self._finish_fut is None:
            return False  # false because position even wasn't start so not done
        return self._finish_fut.done()

    @property
    def progress(self) -> float:
        """
            Method count progress changing value

            :return: progress in float format from 0 to 1
            """
        if self.done():
            return float(1)
        # one of values not loaded
        if self.current is None or self.start is None or self.target is None:
            return float(0)
        # count progress percent if values can cast to float
        try:
            s = float(self.start)
            t = float(self.target)
            c = float(self.current)
            if abs(t - s) == 0:
                return float(1)
            return float(abs(c - s) / abs(t - s))
        except ValueError:
            pass
        # count progress in other situation
        if self.target == self.current:
            return float(1)
        else:
            return float(0)

    async def _coro(self, api):
        # wait for your turn
        for o in self._wait_for_others:
            await o.get_finish_future()
        # todo dodać jeszcze timeouty
        CQ = await api.subscribe(address=self._address,
                                 time_of_data_tolerance=0.3, delay=0.1)
        CQ.start()
        try:
            while True:
                await asyncio.sleep(0)
                try:
                    result = await CQ.get_response()
                except CommunicationRuntimeError:
                    self.error = True
                    self._finish_fut.set_result(False)
                    return

                single_result = result[0]
                if not single_result.status:
                    self.error = True
                    self._finish_fut.set_result(False)
                    return
                if single_result.value:
                    if self.start is None:
                        self.start = single_result.value.v
                    self.current = single_result.value.v
                    try:
                        res = self._check_finish()
                    except Exception as e:
                        self.error = True
                        self.error_content = str(e)
                        self._finish_fut.set_result(False)
                        return
                    if res:
                        self._finish_fut.set_result(True)
                        return
                else:
                    self.error = True
                    self._finish_fut.set_result(False)
                    return
        finally:
            if not self._finish_fut.done():
                self._finish_fut.set_result(False)
            await CQ.stop_and_wait()

    async def wait(self):
        if self._finish_fut is not None:
            await self._finish_fut

    async def run(self, api):
        if self.task:
            self.task.cancel()
        self._finish_fut = asyncio.get_running_loop().create_future()
        self.task = asyncio.create_task(wait_for_psce(self._coro(api=api), timeout=self.timeout))

    def add_more_important_position(self, position):
        self._wait_for_others.append(position)


class Move:
    def __init__(self, api):
        self.error = False
        self.error_content = None
        self.positions = []
        self._api = api
        self._actn = None

    async def watch(self):
        for p in self.positions:
            await p.run(api=self._api)

    @property
    def progress(self):
        """
        Property representing summ progress of all positions

        :raise ValueError
        :return:
        """
        suma = 0
        for p in self.positions:
            suma += p.progress  # can raise ValueError
        return suma / len(self.positions)

    def done(self):
        for p in self.positions:
            if not p.done():
                return False
        return True

    async def wait(self):
        for p in self.positions:
            await p.wait()

    def add_position(self, position):
        # this should be before add given position to list
        self._set_in_level(position=position)
        self.positions.append(position)

    def _set_in_level(self, position):
        """This should be before add given position to list"""
        for p in self.positions:
            if p.level < position.level:
                position.add_more_important_position(p)
            elif p.level > position.level:
                p.add_more_important_position(position)

    def set_action(self, action):
        self._actn = action

    async def make(self):
        try:
            if self._actn is not None:
                await self._actn
            else:
                await self._action()
        except NotImplementedError:
            raise ResourceCommandError(f"Method action is not implemented")
        except ResourceCommandError:
            raise

    async def _action(self):
        raise NotImplementedError


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


class DomeAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.DOME

    def __init__(self, source_name: str, resource_name: str, nr: int, target_request, properties: dict = None,
                 address_path: str = "", **kwargs) -> None:
        super().__init__(source_name=source_name, resource_name=resource_name, nr=nr, target_request=target_request,
                         properties=properties, address_path=address_path, **kwargs)


class MountAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.MOUNT

    def __init__(self, source_name: str, resource_name: str, nr: int, target_request, properties: dict = None,
                 address_path: str = "", **kwargs) -> None:
        super().__init__(source_name=source_name, resource_name=resource_name, nr=nr, target_request=target_request,
                         properties=properties, address_path=address_path, **kwargs)
        self.latitude = self._properties.get("lat", 0)
        self.longitude = self._properties.get("lon", 0)
        self.elevation = self._properties.get("elev", 0)
        self.epoch = self._properties.get("epoch", 2000)  # todo dodac do config albo z kwarksów
        self.min_alt = self._properties.get("min_alt", 15)  # todo dodac do settings
        # -----------------------------
        self._slewing = None

    def build_go_to_position(self, ra, dec, api) -> Move:
        return self._build_ra_dec_slew(ra, dec, api)

    def _build_ra_dec_slew(self, ra, dec, api) -> Move:
        m = MountSlewRaDec(api, resource=self, ra_dec=(ra, dec))
        return m


class CameraAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.CAMERA


class FilterwheelAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.FILTERWHEEL


class FocuserAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.FOCUSER


class RotatorAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.ROTATOR


class SwitchAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.SWITCH


class SafetymonitorAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.SAFETYMONITOR


class CovercalibratorAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.COVERCALIBRATOR


class ResourceCommandError(Exception):

    def __init__(self, msg=""):
        self.msg = msg
