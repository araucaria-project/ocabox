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

logger = logging.getLogger(__name__.rsplit('.')[-1])


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
        address_to_alpaca = f"{self.rs.get_resource(self.rs.MOUNT).adr}.azimuth"  # <--- tak bierzemy adres do Mounta i doklejamy do niebo polecenie np azimuth
        address_to_alpaca_camera = f"{self.rs.get_resource(self.rs.CAMERA, nr=1).adr}.azimuth"  # <--- tak bierzemy adres do Mounta i doklejamy do niebo polecenie np azimuth
        # result = self.api.get_async(address=address_to_alpaca, ...) # <--- tak używamy api
        # todo ważana sprawa to żeby nie wbijać na stałe jakichś danych, jeśli jest coś konkretnego potrzebne to
        #  zapytac ernesta bo bardzo prawdopodobne że jest na to sposób np: jakąś nazwę teleskopu albo
        #  coś z konfiguracj wziąść ( działamy po stronie servera więc konfiguracja jest tutaj najświeższa ni niema
        #  sensu pytać NATS - szkoda wydajność marnować)

        # todo ---- poniżej ifologia z metodami jeśli jest skompplikowana logika to należy ją wyrzucić do osobnej metody
        #  żeby poniższy kod był czytelny ----  + wszystkie metody wpisać do domumętacji na góże


        if command == 'status' and request_type == 'GET':
            status = "idle"
            return Value(v=status, ts=time.time())

        if command == 'start_guiding' and request_type == 'PUT':
            #timeout_control = "response string"
            return Value(v=True, ts=time.time())
        raise AddressError(code=1002, message=f'Unrecognised method for module {self.get_name()}')

    async def run(self):
        self.rs = await self._target_alpaca.get_res_manager()
        await super().run()

    async def stop(self):
        await super().stop()


