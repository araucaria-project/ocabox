import logging
import time
from typing import Optional
from ob.data_colection.coded_error import TreeOtherError
from ob.comunication.internal_client_api import InternalClientAPI
from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.specialistic_components.tree_alpaca import TreeAlpacaObservatory
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest
from typing import Callable, Dict, List
from serverish.messenger import Messenger, request
import asyncio
import numpy as np
import math

logger = logging.getLogger(__name__.rsplit('.')[-1])

class GuiderHandler:

    STATUSES = ['idle', 'dark', 'calibration', 'guiding', 'preview', 'error']
    DIRECTIONS = [0, 1, 2, 3]

    def __init__(self, rs) -> None:
        self.rs = rs
        self.status: str = 'idle'
        self.exposure: float = 3.0 # in seconds
        self.period: float = 6.0 # in seconds
        self.calib_step: float = 1000.0 # in milliseconds
        self.calib_no_of_steps: int = 6
        self.calib_data: Dict | None = None
        self.preview_single: bool = False
        self.sequence_id: str = ''
        self.loop_dark: int = 0
        self.nloops_dark: int = 0
        self.star_select: Dict | None = None
        self.mount_follow: bool = True
        self.darks: Dict = {}

    async def _exec_exposure(self, ):
        #TODO how to operate camera and telescope from here?
        await asyncio.sleep(self.exposure)
        # if after wait we get imageready true
        return

    async def _mount_pulseguide(self, direction: int, duration: float) -> None:
        # TODO put some maximum pulseguide value
        pass

    @staticmethod
    def get_vector_angle_to_x(vector: np.ndarray) -> float:
        x_axis = np.array([10, 0])
        cos_alfa = np.dot(x_axis, vector) / (np.linalg.norm(x_axis) * np.linalg.norm(vector))
        if vector[1] < 0:
            a = -1
        else:
            a = 1
        return math.degrees(math.acos(cos_alfa)) * a

    @staticmethod
    def vector_lenght(vector: np.ndarray) -> float:
        return float(np.linalg.norm(vector))

    async def _calib_final_calc(self):
        # Calculate angles
        for n in self.DIRECTIONS:
            self.calib_data[n]['angle_to_x'] = self.get_vector_angle_to_x(self.calib_data[n]['guid_corr'].sum())
            vect_lenght = self.vector_lenght(self.calib_data[n]['guid_corr'].mean(axis=0))
            self.calib_data[n]['speed_px_per_millisec'] = vect_lenght / self.calib_step
            self.calib_data[n]['step_std'] = self.calib_data[n]['guid_corr'].std(axis=0)

        # self.calib_data['calib_status'] = 'ok'

    async def _build_calib_data(self, guid_corr) -> (bool, int):

        for n in self.DIRECTIONS:
            if n not in self.calib_data.keys():
                self.calib_data[n] = {'guid_corr': np.zeros((self.calib_no_of_steps, 2))}
                return True, n
            else:
                last_step = max(list(self.calib_data[n].keys()))
                if last_step != self.calib_no_of_steps:
                    step_no = last_step + 1
                    self.calib_data[n]['guid_corr'][step_no - 1] = guid_corr
                    if step_no == self.calib_no_of_steps:
                        return False, n
                    else:
                        return True, n
                else:
                    pass
        await self._calib_final_calc()
        # TODO TALK TO JOURNAL
        self.status = 'idle'


    async def _calib_corr(self, param: Dict,) -> None:
        try:
            guid_corr = param['guid_corr']
        except KeyError:
            # TODO TALK TO JOURNAL
            self.status = 'idle'
            return
        mount_pulse, direction = await self._build_calib_data(guid_corr=guid_corr)
        if mount_pulse:
            await self._mount_pulseguide(direction=direction, duration=self.calib_step)

    async def _guid_corr(self, param: Dict, t_start: float) -> None:
        try:
            guid_corr = param['guid_corr']
        except KeyError:
            # TODO TALK TO JOURNAL
            self.status = 'idle'
            return
        # TODO CALCULATE CORRECTION AND DIRECTION
        dec_dir = 0 # [0, 1]
        ra_dir = 2 # [2, 3]
        duration = 1
        await self._mount_pulseguide(direction=dec_dir, duration=duration)
        await self._mount_pulseguide(direction=ra_dir, duration=duration)
        # TODO here wait until the period ends, if time is longer just exit method

    def _get_seq_id(self):
        return f'{round((time.time())*10)}'[-7:]

    async def _send_rpc_request(self, req: str, loop: int, nloops: int):
        #TODO get host, port form ocabox or some nats handler?
        async with Messenger().context(host="192.168.8.140", port=4222):
            dat, met = await request(subject='tic.rpc.dev.guiding',
                                     data=self._rpc_data(req=req, loop=loop, nloops=nloops),
                                     meta=self._rpc_meta(),
                                     timeout=5)
        return dat, met

    def _rpc_data(self, req: str, loop: int, nloops: int) -> Dict:
        return {
                "telescope_id": "dev", #TODO get from ocabox
                "request": req,
                "star_select": [],
                "fits_id": f'{round((time.time())*10)}'[-7:],
                "sequence_id": self.sequence_id,
                "exp_time": self.exposure,
                "loop": loop,
                "nloops": nloops,
                #"tel_ra": 122.33, ?
                #"tel_dec": 60.0001, ?
                #"tel_alt": 44.5, ?
                #"tel_az": 22, ?
                "dtyp": "sideint16"
               }

    def _rpc_meta(self):
        return {
                "message_type": 'rpc',  # IMPORTANT type message, one of pre declared types
                "tags": [""],  # tags
                'sender': 'tic_guider',  # name who send message
                 }

    async def _preview(self):
        await self._exec_exposure()
        d, m = await self._send_rpc_request(req="preview", loop=1, nloops=1)
        if d is not None:
            try:
                resp = d['response']
                status = d['status']
            except KeyError:
                #TODO TALK TO JOURNAL
                self.status = 'idle'
                return
            if resp in ['preview_done'] and status == 'ok':
                #TODO TALK TO JOURNAL
                pass
            else:
                #TODO TALK TO JOURNAL
                pass
        else:
            #TODO TALK TO JOURNAL
            self.status = 'idle'
        if self.preview_single:
            self.status = 'idle'

    async def _dark(self):
        await self._exec_exposure()
        d, m = await self._send_rpc_request(req="dark", loop=self.loop_dark, nloops=self.nloops_dark)
        if d is not None:
            try:
                resp = d['response']
                status = d['status']
            except KeyError:
                #TODO TALK TO JOURNAL
                self.status = 'idle'
                return
            if resp in ['dark_saved', 'master_dark_saved'] and status == 'ok':
                #TODO TALK TO JOURNAL
                self.loop_dark += 1
                if self.nloops_dark == self.loop_dark:
                    #TODO TALK TO JOURNAL
                    self.status = 'idle'
            else:
                #TODO TALK TO JOURNAL
                self.status = 'idle'
        else:
            #TODO TALK TO JOURNAL
            self.status = 'idle'

    async def _calibration(self) -> None:
        await self._exec_exposure()
        d, m = await self._send_rpc_request(req="calib", loop=1, nloops=1)
        if d is not None:
            try:
                resp = d['response']
                status = d['status']
            except KeyError:
                # TODO TALK TO JOURNAL
                self.status = 'idle'
                return
            if resp in ['corr_calc'] and status == 'ok':
                # TODO TALK TO JOURNAL
                try:
                    param = d['param']
                except KeyError:
                    # TODO TALK TO JOURNAL
                    self.status = 'idle'
                    return
                await self._calib_corr(param=param)
            elif resp in ['star_selected'] and status == 'ok':
                # TODO TALK TO JOURNAL
                pass
            elif resp in ['star_lost'] and status == 'ok':
                # TODO TALK TO JOURNAL
                self.status = 'idle'
                pass
            else:
                pass
        else:
            # TODO TALK TO JOURNAL
            self.status = 'idle'

    async def _guiding(self) -> None:
        t_start = time.time()
        await self._exec_exposure()
        d, m = await self._send_rpc_request(req="guiding_simple", loop=1, nloops=1)
        if d is not None:
            try:
                resp = d['response']
                status = d['status']
            except KeyError:
                # TODO TALK TO JOURNAL
                self.status = 'idle'
                return
            if resp in ['corr_calc'] and status == 'ok':
                # TODO TALK TO JOURNAL
                try:
                    param = d['param']
                except KeyError:
                    # TODO TALK TO JOURNAL
                    self.status = 'idle'
                    return
                await self._guid_corr(param=param, t_start=t_start)
            elif resp in ['star_selected'] and status == 'ok':
                # TODO TALK TO JOURNAL
                pass
            else:
                # TODO TALK TO JOURNAL
                pass
        else:
            # TODO TALK TO JOURNAL
            self.status = 'idle'


    async def preview(self, single: bool = False):
        #TODO TALK TO JOURNAL
        self.sequence_id = self._get_seq_id()
        self.preview_single = single
        self.status = 'preview'

    async def calibration(self) -> None:
        # TODO TALK TO JOURNAL
        self.sequence_id = self._get_seq_id()
        self.calib_data = {}
        self.status = 'calibration'

    async def dark(self, sub_no: int = 20) -> None:
        self.sequence_id = self._get_seq_id()
        self.loop_dark: int = 0
        self.nloops_dark: int = sub_no
        self.status = 'dark'

    async def guiding(self, star_select: List | None = None, mount_follow: bool = True) -> None:
        # TODO TALK TO JOURNAL
        if self.calib_data is not None:
            try:
                calib_status = self.calib_data['calib_status']
            except KeyError:
                # TODO TALK TO JOURNAL
                return
            if calib_status == 'ok':
                self.sequence_id = self._get_seq_id()
                self.star_select = star_select
                self.mount_follow = mount_follow
                self.status = 'guiding'
            else:
                # TODO TALK TO JOURNAL
                pass
        else:
            # TODO TALK TO JOURNAL
            pass

    async def stop(self) -> None:
        #TODO stop waiting for exposure and exposure itself
        #TODO TALK TO JOURNAL
        self.status = 'idle'

    async def run_body(self):
        while True:
            if self.status == 'preview':
                await self._preview()
            if self.status == 'dark':
                await self._dark()
            #if self.status == 'calibration':
            #    await self._calibration()
            #if self.status == 'guiding':
            #    await self._guiding()
            await asyncio.sleep(0.1)


class TreeCustomGuiderHandler(TreeProvider):
    """
    This module is responsible for managing custom telescope guider.
    The module has several defined address commands:
        - method1 - cos ...
        - method2 - cos ...
    """

    COMPONENT_DEFAULT_NAME: str = 'TreeCustomGuiderHandler'

    def __init__(self, component_name: str, source_name: str, target_alpaca: TreeAlpacaObservatory, **kwargs):
        super().__init__(component_name=component_name, source_name=source_name, **kwargs)
        self._target_alpaca: TreeAlpacaObservatory = target_alpaca
        self.rs = None
        self.gh: GuiderHandler | None = None

    async def get_value(self, request: ValueRequest, **kwargs) -> Optional[Value]:

        # todo poniżej są dane wiadomości: user, request_type (PUT/GET), command (np. method1, method2)
        user = request.user
        request_type = request.request_type
        if user is None:
            raise TreeOtherError(code=4001, message='No user in request')
        try:
            command = request.address[request.index]
        except IndexError:
            raise AddressError(code=1001, message='The address does not contain a command.')

        # ------------------------------------------------------------------------------------

        # todo jak się robi zapytania :
        #  można sobie to obudoawać w jakąś metodę lokalnie jeśli będzie wygodniej
        #  pamiętajmy że uzywamy starego rare api które udostępnia masę opcji i zapytania idą przez cache więc
        #  jak chcemy ominąc to trzeba odpowiednio ustawić parametry
        #address_to_alpaca = f"{self.rs.get_resource(self.rs.MOUNT).adr}.azimuth"  # <--- tak bierzemy adres do Mounta i doklejamy do niebo polecenie np azimuth
        #address_to_alpaca_camera = f"{self.rs.get_resource(self.rs.CAMERA, nr=1).adr}.azimuth"  # <--- tak bierzemy adres do Mounta i doklejamy do niebo polecenie np azimuth
        # result = self.api.get_async(address=address_to_alpaca, ...) # <--- tak używamy api
        # todo ważana sprawa to żeby nie wbijać na stałe jakichś danych, jeśli jest coś konkretnego potrzebne to
        #  zapytac ernesta bo bardzo prawdopodobne że jest na to sposób np: jakąś nazwę teleskopu albo
        #  coś z konfiguracj wziąść ( działamy po stronie servera więc konfiguracja jest tutaj najświeższa ni niema
        #  sensu pytać NATS - szkoda wydajność marnować)

        # todo ---- poniżej ifologia z metodami jeśli jest skompplikowana logika to należy ją wyrzucić do osobnej metody
        #  żeby poniższy kod był czytelny ----  + wszystkie metody wpisać do domumętacji na góże

        if command == 'status' and request_type == 'GET':
            return Value(v=self.gh.status, ts=time.time())

        if command == 'exposure' and request_type == 'GET':
            return Value(v=self.gh.exposure, ts=time.time())

        if command == 'exposure' and request_type == 'PUT':
            try:
                self.gh.exposure = request.request_data['exp']
            except KeyError:
                raise TreeOtherError(code=4007,
                                     message=f'{self.get_name()}: Missing "exp" parameter in {command} request.')
            return Value(v=self.gh.status, ts=time.time())

        if command == 'period' and request_type == 'GET':
            return Value(v=self.gh.period, ts=time.time())

        if command == 'period' and request_type == 'PUT':
            try:
                self.period = request.request_data['period']
            except KeyError:
                raise TreeOtherError(code=4007,
                                     message=f'{self.get_name()}: Missing "period" parameter in {command} request.')
            return Value(v=True, ts=time.time())

        if command == 'calib_step' and request_type == 'GET':
            return Value(v=self.gh.calib_step, ts=time.time())

        if command == 'calib_step' and request_type == 'PUT':
            try:
                self.calib_step = request.request_data['step']
            except KeyError:
                raise TreeOtherError(code=4007,
                                     message=f'{self.get_name()}: Missing "step" parameter in {command} request.')
            return Value(v=True, ts=time.time())

        if command == 'preview' and request_type == 'PUT':
            try:
                single = request.request_data['single']
            except KeyError:
                raise TreeOtherError(code=4007,
                                     message=f'{self.get_name()}: Missing "single" parameter in {command} request.')
            await self.gh.preview(single=single)
            return Value(v=True, ts=time.time())

        if command == 'stop' and request_type == 'PUT':
            await self.gh.stop()
            return Value(v=True, ts=time.time())

        if command == 'start_calib' and request_type == 'PUT':
            await self.gh.calibration()
            return Value(v=True, ts=time.time())

        if command == 'start_guiding' and request_type == 'PUT':
            try:
                star_select = request.request_data['star_select']
            except KeyError:
                raise TreeOtherError(code=4007,
                                     message=f'{self.get_name()}: Missing "star_select" parameter in {command} request.')
            try:
                mount_follow = request.request_data['mount_follow']
            except KeyError:
                raise TreeOtherError(code=4007,
                                     message=f'{self.get_name()}: Missing "mount_follow" parameter in {command} request.')
            await self.gh.guiding(star_select=star_select, mount_follow=mount_follow)
            return Value(v=True, ts=time.time())

        if command == 'dark' and request_type == 'PUT':
            try:
                sub_no = request.request_data['sub_no']
            except KeyError:
                raise TreeOtherError(code=4007,
                                     message=f'{self.get_name()}: Missing "sub_no" parameter in {command} request.')
            await self.gh.dark(sub_no=sub_no)
            return Value(v=True, ts=time.time())

        if command == 'calib_data' and request_type == 'GET':
            return Value(v=self.gh.calib_data, ts=time.time())

        raise AddressError(code=1002, message=f'Unrecognised method for module {self.get_name()}')

    async def run(self):
        self.rs = await self._target_alpaca.get_res_manager()
        self.gh = GuiderHandler(rs=self.rs)
        self.task = asyncio.create_task(self.gh.run_body())
        await super().run()

    async def stop(self):
        self.task.cancel()
        await super().stop()
