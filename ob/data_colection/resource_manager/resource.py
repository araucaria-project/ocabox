import asyncio
import logging
from abc import ABC

from ob.comunication.internal_client_api import InternalClientAPI
from ob.data_colection.address import Address
from ob.data_colection.alpaca_api.standard_telescope_components import StandardTelescopeComponents
from ob.data_colection.tree_user import BaseTreeUser
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


class DomeAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.DOME

    def __init__(self, source_name: str, resource_name: str, nr: int, target_request, properties: dict = None,
                 address_path: str = "", **kwargs) -> None:
        super().__init__(source_name=source_name, resource_name=resource_name, nr=nr, target_request=target_request,
                         properties=properties, address_path=address_path, **kwargs)

    async def wait_to_slew(self, alt, az, ra, dec, api: InternalClientAPI = None, timeout: int = 20, **kwargs) -> bool:
        if api is None:
            api = InternalClientAPI(request_solver=self._target, user_name=f"Default_{self.__class__.__name__}")

        az_ = az
        fut = asyncio.get_running_loop().create_future()

        async def result_check(result):
            if fut.done():
                return
            single_result = result[0]
            if single_result.value and single_result.value.v:
                if single_result.value.v == az_:
                    fut.set_result(True)
            else:
                fut.set_result(False)

        CQ = await api.subscribe_with_callback(address=f"{self._tree_address_path.__str__()}.azimuth",
                                               time_of_data_tolerance=0.3, async_callback_method=result_check)

        # todo sprawdzić co jest nie tak z delay = 0.1 w wywołaniu wyżej, test nie przechodzi
        try:
            await wait_for_psce(fut, timeout=timeout)
            if fut.done() and fut.result() is False:
                raise ResourceCommandError
        except asyncio.TimeoutError:
            raise ResourceCommandError
        finally:
            await CQ.stop_and_wait()
        return True

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
        # todo Cz ustawiamy altitude? Mikołaj
        # from alt az
        alt_ = None
        az_ = None
        if az is not None:
            az_ = az
        # from ra dec
        elif ra is not None and dec is not None:
            # todo tu obliczyć alt z ra dec
            az_ = None
            raise ResourceCommandError
        else:
            raise ResourceCommandError

        result = await api.put_async(address=f"{self._tree_address_path.__str__()}.slewtoazimuth",
                                     parameters_dict={"Azimuth": az_}, no_wait=False)
        if result.status:
            return True
        else:
            raise ResourceCommandError


class MountAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.MOUNT


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
    pass
