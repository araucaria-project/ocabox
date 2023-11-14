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

logger = logging.getLogger(__name__.rsplit('.')[-1])

class GuiderHandler:

    STATUSES = ['idle', 'calibration', 'guiding', 'preview', 'error']

    def __init__(self, rs) -> None:
        self.rs = rs
        self.status: str = 'idle'
        self.exposure: float = 3.0
        self.period: float = 6.0
        self.calib_step: float = 1.0
        self.calib_data: Dict | None = None
        self.preview_single: bool = False
        self.sequence_id: str = ''
        self.darks: Dict = {}

    async def exec_exposure(self, ):
        await asyncio.sleep(self.exposure)
        # if after wait we get imageready true
        return

    def get_seq_id(self):
        return f'{round((time.time())*10)}'[-7:]

    async def run_body(self):
        while True:
            if self.status == 'preview':
                await self._preview()
            await asyncio.sleep(0.1)

    def rpc_data(self, request: str) -> Dict:
        return {
                "telescope_id": "dev", # get from ocabox
                "request": request,
                "star_select": [],
                "fits_id": f'{round((time.time())*10)}'[-7:],
                "sequence_id": self.sequence_id,
                "exp_time": self.exposure,
                "loop": 1,
                "nloops": 1,
                #"tel_ra": 122.33,
                #"tel_dec": 60.0001,
                #"tel_alt": 44.5,
                #"tel_az": 22,
                "dtyp": "sideint16"
               }
    def meta(self):
        return {
                "message_type": 'rpc',  # IMPORTANT type message, one of pre declared types
                "tags": [""],  # tags
                'sender': 'tic_guider',  # name who send message
                 }

    async def _preview(self):
        await self.exec_exposure()
        async with Messenger().context(host="192.168.8.140", port=4222):
            d, m = await request(subject='tic.rpc.dev.guiding',
                                 data=self.rpc_data(request="preview"),
                                 meta=self.meta(),
                                 timeout=5)
        if self.preview_single:
            self.status = 'idle'

    async def preview(self, single: bool = False):
        self.sequence_id = self.get_seq_id()
        self.preview_single = single
        self.status = 'preview'

    async def stop(self) -> None:
        # stop waiting for exposure and exposure itself
        self.status = 'idle'

    async def start_calib(self) -> None:
        pass

    async def prep_dark(self, sub_no: int = 3) -> None:
        pass

    async def start_guiding(self, star_select: List | None = None, mount_follow: bool = True) -> None:
        pass


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
            await self.gh.start_calib()
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
            await self.gh.start_guiding(star_select=star_select, mount_follow=mount_follow)
            return Value(v=True, ts=time.time())

        if command == 'prep_dark' and request_type == 'PUT':
            try:
                sub_no = request.request_data['sub_no']
            except KeyError:
                raise TreeOtherError(code=4007,
                                     message=f'{self.get_name()}: Missing "sub_no" parameter in {command} request.')
            await self.gh.prep_dark(sub_no=sub_no)
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
