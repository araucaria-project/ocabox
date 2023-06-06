import asyncio
import logging
from abc import ABC
from typing import Callable, Optional, List, Tuple

from pyaraucaria.coordinates import deg_str_to_deg, ra_dec_epoch, ra_dec_2_az_alt, dec_to_decimal, ra_to_decimal, \
    ra_to_sexagesimal

from ob.comunication.comunication_error import CommunicationRuntimeError
from ob.comunication.internal_client_api import InternalClientAPI
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
        def __init__(self, address, t=None, s=None, c=None, timeout=None):
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
            # ------ optional -------
            self.bounds: Tuple[Optional[float], Optional[float]] = (None, None)

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

        def _check_finish(self):
            """
            Method check current value is achieved target.

            :raise ValueError
            :return: bool
            """
            if self.custom_end_condition is not None and callable(self.custom_end_condition):
                return self.custom_end_condition(self.start, self.current, self.target)
            print(self.start, self.current, self.target)
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
                return
            bound_btm = self.bounds[0]
            bound_top = self.bounds[1]
            if self.target-bound_btm < self.current < self.target+bound_top:
                return True
            else:
                return False

        def done(self):
            return self._finish_fut.done()

        @property
        def progress(self) -> float:
            """
            Method count progress changing value

            :return: progress in float format from 0 to 1
            """
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

    class Move:
        def __init__(self, api):
            self.error = False
            self.error_content = None
            self.is_slewing = False
            self.positions = []
            self._api = api

        async def watch(self):
            self.is_slewing = True
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
            self.positions.append(position)


class DomeAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.DOME

    def __init__(self, source_name: str, resource_name: str, nr: int, target_request, properties: dict = None,
                 address_path: str = "", **kwargs) -> None:
        super().__init__(source_name=source_name, resource_name=resource_name, nr=nr, target_request=target_request,
                         properties=properties, address_path=address_path, **kwargs)

    async def go_to_position(self, alt, az, ra, dec, api: InternalClientAPI = None, **kwargs):
        """

        :param alt: altitude
        :param az: azimuth
        :param ra: ractescention
        :param dec: declination
        :param api:
        :param kwargs:
        :raise ResourceCommandError:
        :return:
        """
        if api is None:
            api = InternalClientAPI(request_solver=self._target, user_name=f"Default_{self.__class__.__name__}")
        # from alt az
        alt_ = None
        az_ = None
        if az is not None:
            az_ = az
        # from ra dec
        elif ra is not None and dec is not None:
            # todo tu obliczyć alt z ra dec
            az_ = None
            raise ResourceCommandError("Not implemented - go position by ra dec")
        else:
            raise ResourceCommandError("Can not find one of ra/dec or alt/az in action")

        result = await api.put_async(address=f"{self._tree_address_path.__str__()}.slewtoazimuth",
                                     parameters_dict={"Azimuth": az_}, no_wait=False)
        if result.status:
            return True
        else:
            raise ResourceCommandError("Action has error status in response")


class MountAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.MOUNT

    def __init__(self, source_name: str, resource_name: str, nr: int, target_request, properties: dict = None,
                 address_path: str = "", **kwargs) -> None:
        super().__init__(source_name=source_name, resource_name=resource_name, nr=nr, target_request=target_request,
                         properties=properties, address_path=address_path, **kwargs)
        self._latitude = self._properties.get("lat", 0)
        self._longitude = self._properties.get("lon", 0)  # todo wpisać te wartośći z symulatora do configa
        self._elevation = self._properties.get("elev", 0)
        self._epoch = self._properties.get("epoch", 2000)  # todo dodac do config albo z kwarksów
        self._min_alt = self._properties.get("min_alt", 15)  # todo dodac do settings
        # -----------------------------
        self._slewing = None

    async def go_to_position(self, ra, dec, epoch, api):
        return await self._go_to_position_ra_dec(ra, dec, epoch, api)

    async def _go_to_position_ra_dec(self, ra, dec, epoch, api):
        ra_f = ra_to_decimal(ra)
        dec_f = dec_to_decimal(dec)

        ra_now, dec_now = ra_dec_epoch(ra=ra_f,
                                       dec=dec_f,
                                       epoch=str(self._epoch))  # todo ma byc string zawsze to zapewnić gdzieś wyżej
        az, alt = ra_dec_2_az_alt(ra=ra_now,
                                  dec=dec_now,
                                  latitude=self._latitude,
                                  longitude=self._longitude,
                                  elevation=self._elevation,
                                  epoch=self._epoch)

        # ----------------- check min altitude -----------------
        if alt <= self._min_alt:
            raise ResourceCommandError(f"Altitude is lover then min altitude")

        m = self.Move(api)
        # todo dokończyć podmiane metod na tą z wartościami
        m.add_position(self.Position(f"{self._tree_address_path.__str__()}.rightascension", t=ra_now))
        m.add_position(self.Position(f"{self._tree_address_path.__str__()}.declination", t=dec_now))
        m.add_position(self.Position(f"{self._tree_address_path.__str__()}.tracking", t=True))

        try:
            # ----------------- set tracking -----------------
            result = await api.put_async(address=f"{self._tree_address_path.__str__()}.tracking",
                                         parameters_dict={"Tracking": True}, no_wait=False)
            if not result.status:
                raise ResourceCommandError(f"Action has error status in response {result.error}")
            # ----------------- move mount -----------------
            result = await api.put_async(address=f"{self._tree_address_path.__str__()}.slewtocoordinatesasync",
                                         parameters_dict={"RightAscension": ra_now,
                                                          "Declination": dec_now},
                                         no_wait=False)
            if not result.status:
                raise ResourceCommandError("Action has error status in response")
        except ResourceCommandError:
            m.is_slewing = False
            # jeśli coś poszło nie tak, to nie ma sensu czekać na ruch, coś może się wykonać, ale raczej źle
            raise
        finally:
            self._slewing = m
        await m.watch()
        return True

    def get_slew_progres(self):
        if self._slewing is None:
            return 0
        return self._slewing.progress

    async def wait_for_slew(self):
        if self._slewing is None:
            return
        await self._slewing.wait()


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
