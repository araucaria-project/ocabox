import asyncio
import logging
from abc import ABC
from typing import Callable, Optional, List

from pyaraucaria.coordinates import deg_str_to_deg, ra_dec_epoch, ra_dec_2_az_alt

from ob.comunication.comunication_error import CommunicationRuntimeError
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

    async def _subscription_pack(self, api, condi, command: str):

        fut = asyncio.get_running_loop().create_future()

        CQ = await api.subscribe(address=f"{self._tree_address_path.__str__()}.{command}",
                                 time_of_data_tolerance=0.3)

        async def coro(result):
            try:
                if fut.done():
                    return
                single_result = result[0]
                if single_result.value and single_result.value.v:
                    r = await condi(single_result.value.v)
                    if r is True:
                        fut.set_result(True)
                else:
                    fut.set_result(False)
            finally:
                CQ.stop()

        # TODO Wymyślić jakiś lepszy mechanizm zamykania subskrypcji, teraz callback robi stop ale nie czeka a CQ musi
        #  być przekazywane dalej i oczekiwane ręcznie

        CQ.add_callback_async_method(coro)
        CQ.start()
        return fut, CQ

    class Position:
        def __init__(self, address, t=None, s=None, c=None):
            self.target = t
            self.start = s
            self.current = c
            self.custom_end_condition: Optional[Callable] = None
            self.is_slewing = False
            self.error = False
            self.error_content = None
            self.task = None
            self._address = address

        def check_finish(self):
            if self.custom_end_condition is not None and callable(self.custom_end_condition):
                return self.custom_end_condition()
            if self.current == self.target:
                return True
            else:
                return False

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
                return float(abs(c - s) / abs(t - s))
            except ValueError:
                pass
            # count progress in other situation
            if self.target == self.current:
                return float(1)
            else:
                return float(0)

        async def coro(self, api):
            CQ = await api.subscribe(address=self._address,
                                     time_of_data_tolerance=0.3)
            CQ.start()
            while True:
                await asyncio.sleep(0)
                try:
                    result = await CQ.get_response()
                except CommunicationRuntimeError:
                    self.is_slewing = False
                    self.error = True
                    return

                single_result = result[0]
                if not single_result.status:
                    self.error = True
                if single_result.value:
                    if self.start is None:
                        self.start = single_result.value.v
                    self.current = single_result.value.v
                    self.check_finish()
                else:
                    self.error = True

    class Move:
        def __init__(self, api):
            self.error = False
            self.error_content = None
            self.is_slewing = False
            self.positions = []
            self._api = api

        # async def coro(self, p, address, api):
        #     CQ = await api.subscribe(address=address,
        #                              time_of_data_tolerance=0.3)
        #     CQ.start()
        #     while True:
        #         await asyncio.sleep(0)
        #         try:
        #             result = await CQ.get_response()
        #         except CommunicationRuntimeError:
        #             self.is_slewing = False
        #             self.error = True
        #             return
        #
        #         single_result = result[0]
        #         if not single_result.status:
        #             self.error = True
        #         if single_result.value:
        #             if p.start is None:
        #                 p.start = single_result.value.v
        #             p.current = single_result.value.v
        #             self.check_finish()
        #         else:
        #             self.error = True

        async def move(self):
            for p in self.positions:
                p.task = asyncio.create_task(p.coro(api=self._api))

        @property
        def progress(self):
            suma = 0
            for p in self.positions:
                suma += p.progress
            return suma / len(self.positions)

        def check_finish(self):
            for p in self.positions:
                if not p.check_finish():
                    return False
            return True


class DomeAlpaca(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.DOME

    def __init__(self, source_name: str, resource_name: str, nr: int, target_request, properties: dict = None,
                 address_path: str = "", **kwargs) -> None:
        super().__init__(source_name=source_name, resource_name=resource_name, nr=nr, target_request=target_request,
                         properties=properties, address_path=address_path, **kwargs)

    async def wait_to_slew(self, alt, az, ra, dec, api: InternalClientAPI = None, timeout: int = 20, **kwargs) -> bool:
        """

        :param alt:
        :param az:
        :param ra:
        :param dec:
        :param api:
        :param timeout:
        :param kwargs:
        :raise ResourceCommandError:
        :return:
        """
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
        try:
            await wait_for_psce(fut, timeout=timeout)
            if fut.done() and fut.result() is False:
                raise ResourceCommandError("Unexpected error when waiting for subscription")
            else:
                pass
        except asyncio.TimeoutError:
            raise ResourceCommandError("To long waiting for action")
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

    # todo dodać jakoś informację o tym ile procent wykonuje się dana czynność. Do pasków postępów  !!!!

    def __init__(self, source_name: str, resource_name: str, nr: int, target_request, properties: dict = None,
                 address_path: str = "", **kwargs) -> None:
        super().__init__(source_name=source_name, resource_name=resource_name, nr=nr, target_request=target_request,
                         properties=properties, address_path=address_path, **kwargs)

    async def _wait_for_ra(self, ra, api: InternalClientAPI = None, timeout: int = 20, **kwargs):
        if api is None:
            api = InternalClientAPI(request_solver=self._target, user_name=f"Default_{self.__class__.__name__}")

        command = "rightascension"

        async def condi(val):
            if val == ra:
                return True
            return False

        fut, cq = await self._subscription_pack(api, condi, command)
        try:
            await wait_for_psce(fut, timeout=timeout)
            if fut.done() and fut.result() is False:
                raise ResourceCommandError("Unexpected error when waiting for subscription")
            else:
                pass
        except asyncio.TimeoutError:
            raise ResourceCommandError("To long waiting for action")
        finally:
            await cq.stop_and_wait()
        return True

    async def _wait_for_dec(self, dec, api: InternalClientAPI = None, timeout: int = 20, **kwargs):
        if api is None:
            api = InternalClientAPI(request_solver=self._target, user_name=f"Default_{self.__class__.__name__}")

        command = "declination"

        async def condi(val):
            if val == dec:
                return True
            return False

        fut, cq = await self._subscription_pack(api, condi, command)
        try:
            await wait_for_psce(fut, timeout=timeout)
            if fut.done() and fut.result() is False:
                raise ResourceCommandError("Unexpected error when waiting for subscription")
            else:
                pass
        except asyncio.TimeoutError:
            raise ResourceCommandError("To long waiting for action")
        finally:
            await cq.stop_and_wait()
        return True

    async def wait_to_slew(self, alt, az, ra, dec, api: InternalClientAPI = None, timeout: int = 20, **kwargs) -> bool:
        """

        :param alt:
        :param az:
        :param ra:
        :param dec:
        :param api:
        :param timeout:
        :param kwargs:
        :raise ResourceCommandError:
        :return:
        """
        if api is None:
            api = InternalClientAPI(request_solver=self._target, user_name=f"Default_{self.__class__.__name__}")

        ra_ = ra
        dec_ = dec
        timeout = 60
        await asyncio.gather(self._wait_for_ra(ra=ra_, api=api, timeout=timeout),
                             self._wait_for_dec(dec=dec_, api=api, timeout=timeout))
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

        # TODO This should be taken from settings
        tel = {'latitude': '-24:35:53', 'longitude': '-70:11:47', 'elevation': '2817'}
        epoch = '2000'  # todo co to jest? Mikołaj

        # from alt az
        if alt is not None and az is not None:
            await self._go_to_position_alt_az(alt, az, api)
        elif ra is not None and dec is not None:
            await self._go_to_position_ra_dec(ra, dec, tel.get("latitude"), tel.get("longitude"), tel.get("elevation"),
                                              epoch,
                                              api)
        else:
            raise ResourceCommandError("Wrong parameters")

    async def _go_to_position_ra_dec(self, ra, dec, latitude, longitude, elevation, epoch, api):
        ra_now, dec_now = ra_dec_epoch(ra=ra,
                                       dec=dec,
                                       latitude=latitude,
                                       longitude=longitude,
                                       elevation=elevation,
                                       epoch=epoch)
        az, alt = ra_dec_2_az_alt(ra=ra_now,
                                  dec=dec_now,
                                  latitude=latitude,
                                  longitude=longitude,
                                  elevation=elevation,
                                  epoch=epoch)

        # ----------------- check min altitude -----------------
        mount_min_alt = 14.9  # todo wo wywalenia albo całkiem albo do settings
        if deg_str_to_deg(alt) <= mount_min_alt:  # todo w zależności co z mount_min_alt to może do wywalenia
            raise ResourceCommandError(f"Altitude is lover then min altitude")

        # ----------------- set tracking -----------------
        result = await api.put_async(address=f"{self._tree_address_path.__str__()}.tracking",
                                     parameters_dict={"Tracking": True}, no_wait=False)
        if not result.status:
            raise ResourceCommandError("Action has error status in response")

        # ----------------- move mount -----------------
        result = await api.put_async(address=f"{self._tree_address_path.__str__()}.slewtocoordinatesasync",
                                     parameters_dict={"RightAscension": ra_now, "Declination": dec_now}, no_wait=False)
        if not result.status:
            raise ResourceCommandError("Action has error status in response")
        return True

    async def _go_to_position_alt_az(self, alt, az, api):
        try:
            alt_, az_ = self._read_alt_az_coord(alt, az)
        except ValueError:
            raise ResourceCommandError(msg="given alt az is in wrong format")

        # ----------------- check min altitude -----------------
        mount_min_alt = 14.9  # todo wo wywalenia albo całkiem albo do settings
        if deg_str_to_deg(alt) <= mount_min_alt:  # todo w zależności co z mount_min_alt to może do wywalenia
            raise ResourceCommandError(f"Altitude is lover then min altitude")

        # ----------------- move mount -----------------
        result = await api.put_async(address=f"{self._tree_address_path.__str__()}.slewtoaltazasync",
                                     parameters_dict={"Azimuth": az_, "Altitude": alt_}, no_wait=False)
        if not result.status:
            raise ResourceCommandError("Action has error status in response")

        # todo traking zawsze będzie włączony w tym a jak ktoś będzie chciał inaczej to w komędach (np Object) sobie napiszę
        # # ----------------- set tracking -----------------
        # # todo sprawdzić co z tym trakingiem bo był ustawiany 3 razy w starej wersji
        # if "tracking" in self.kwargs.keys():
        #     await asyncio.sleep(5)
        #     await self.mount.aput_tracking(self.kwargs["tracking"])
        #     self.info_callback['stream_1'](
        #         f'{self.id} {self.subcommand_name} tracking={self.kwargs["tracking"]}')

        return True


class MountAlpaca_v2(Resource):
    RESOURCE_NAME = StandardTelescopeComponents.MOUNT

    def __init__(self, source_name: str, resource_name: str, nr: int, target_request, properties: dict = None,
                 address_path: str = "", **kwargs) -> None:
        super().__init__(source_name=source_name, resource_name=resource_name, nr=nr, target_request=target_request,
                         properties=properties, address_path=address_path, **kwargs)
        self._slewing = None

    # async def go_to_position(self, alt, az, ra, dec, api: InternalClientAPI = None, **kwargs):
    #     """
    #
    #     :param alt: altitude
    #     :param az: azimuth
    #     :param ra: ractescention
    #     :param dec: declination
    #     :param api:
    #     :param kwargs:
    #     :raise ResourceCommandError:
    #     :return:
    #     """
    #
    #     if api is None:
    #         api = InternalClientAPI(request_solver=self._target, user_name=f"Default_{self.__class__.__name__}")
    #
    #     # TODO This should be taken from settings
    #     tel = {'latitude': '-24:35:53', 'longitude': '-70:11:47', 'elevation': '2817'}
    #     epoch = '2000'  # todo co to jest? Mikołaj
    #
    #     self._slewing["target_ra"] = None
    #     self._slewing["target_dec"] = None
    #     self._slewing["target_alt"] = None
    #     self._slewing["target_az"] = None
    #
    #     # from alt az
    #     if alt is not None and az is not None:
    #         self._slewing["target_alt"] = alt
    #         self._slewing["target_az"] = az
    #         await self._go_to_position_alt_az(alt, az, api)
    #     elif ra is not None and dec is not None:
    #         await self._go_to_position_ra_dec(ra, dec, tel.get("latitude"), tel.get("longitude"), tel.get("elevation"),
    #                                           epoch, api)
    #     else:
    #         raise ResourceCommandError("Wrong parameters")

    async def _go_to_position_ra_dec(self, ra, dec, latitude, longitude, elevation, epoch, api):
        ra_now, dec_now = ra_dec_epoch(ra=ra,
                                       dec=dec,
                                       latitude=latitude,
                                       longitude=longitude,
                                       elevation=elevation,
                                       epoch=epoch)
        az, alt = ra_dec_2_az_alt(ra=ra_now,
                                  dec=dec_now,
                                  latitude=latitude,
                                  longitude=longitude,
                                  elevation=elevation,
                                  epoch=epoch)

        # ----------------- check min altitude -----------------
        mount_min_alt = 14.9  # todo wo wywalenia albo całkiem albo do settings
        if deg_str_to_deg(alt) <= mount_min_alt:  # todo w zależności co z mount_min_alt to może do wywalenia
            raise ResourceCommandError(f"Altitude is lover then min altitude")

        m = self.Move(api)
        m.positions[0] = self.Position("declination", t=ra_now)
        m.positions[1] = self.Position("declination", t=dec_now)

        try:
            # ----------------- set tracking -----------------
            result = await api.put_async(address=f"{self._tree_address_path.__str__()}.tracking",
                                         parameters_dict={"Tracking": True}, no_wait=False)
            if not result.status:
                raise ResourceCommandError("Action has error status in response")

            # ----------------- move mount -----------------
            result = await api.put_async(address=f"{self._tree_address_path.__str__()}.slewtocoordinatesasync",
                                         parameters_dict={"RightAscension": ra_now, "Declination": dec_now},
                                         no_wait=False)
            if not result.status:
                raise ResourceCommandError("Action has error status in response")
        except ResourceCommandError:
            m.is_slewing = False
            # jeśli coś poszło nie tak, to nie ma sensu czekać na ruch, coś może się wykonać, ale raczej źle
            raise
        m.is_slewing = True
        self._slewing = m
        return True

    async def _go_to_position_alt_az(self, alt, az, api):
        try:
            alt_, az_ = self._read_alt_az_coord(alt, az)
        except ValueError:
            raise ResourceCommandError(msg="given alt az is in wrong format")

        # ----------------- check min altitude -----------------
        mount_min_alt = 14.9  # todo wo wywalenia albo całkiem albo do settings
        if deg_str_to_deg(alt) <= mount_min_alt:  # todo w zależności co z mount_min_alt to może do wywalenia
            raise ResourceCommandError(f"Altitude is lover then min altitude")

        # ----------------- move mount -----------------
        result = await api.put_async(address=f"{self._tree_address_path.__str__()}.slewtoaltazasync",
                                     parameters_dict={"Azimuth": az_, "Altitude": alt_}, no_wait=False)
        if not result.status:
            raise ResourceCommandError("Action has error status in response")

        # todo traking zawsze będzie włączony w tym a jak ktoś będzie chciał inaczej to w komędach (np Object) sobie napiszę
        # # ----------------- set tracking -----------------
        # # todo sprawdzić co z tym trakingiem bo był ustawiany 3 razy w starej wersji
        # if "tracking" in self.kwargs.keys():
        #     await asyncio.sleep(5)
        #     await self.mount.aput_tracking(self.kwargs["tracking"])
        #     self.info_callback['stream_1'](
        #         f'{self.id} {self.subcommand_name} tracking={self.kwargs["tracking"]}')

        return True

    async def _slewing_subscribe_ra_dec(self, api: InternalClientAPI = None, timeout: int = 20, **kwargs):
        if api is None:
            api = InternalClientAPI(request_solver=self._target, user_name=f"Default_{self.__class__.__name__}")

        move = self._slewing

        command = "declination"


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
