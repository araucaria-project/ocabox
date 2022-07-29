import asyncio
import logging
import datetime
import confuse

from ob.data_colection.address import AddressError
from ob.data_colection.alpaca_api.connector import Connector, AlpacaConnector
from ob.data_colection.alpaca_api.exceptions import AlpacaHttp400Error, AlpacaHttp500Error, AlpacaContentTypeError, \
    AlpacaError, AlpacaHttpError, RequestConnectionError
from ob.data_colection.alpaca_api.observatory import Observatory
from ob.data_colection.base_components.tree_base_provider import TreeBaseProvider
from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.coded_error import TreeStructureError
from ob.data_colection.value import Value, TreeValueError
from ob.data_colection.value_call import ValueRequest
from ob.ob_config import SingletonConfig

logger = logging.getLogger(__name__)


class TreeAlpacaObservatory(TreeBaseProvider):
    DEFAULT_PROTOCOL = 'alpaca'

    def __init__(self, component_name: str, subcontractor: ProvidesResponseProtocol = None, observatory_name=None,
                 **kwargs):
        super().__init__(component_name=component_name, subcontractor=subcontractor, **kwargs)
        self.observatory_name = observatory_name if observatory_name else component_name
        self._observatory = Observatory()
        self._connector: Connector
        self._connect_to_observatory()

    def _connect_to_observatory(self):
        self._connector = AlpacaConnector()
        self._observatory.connect(self.observatory_name, connector=self._connector)

    async def run(self):
        result = await self._connector.create_http_session()
        if result:
            logger.info(f"Permanent http session was successfully create")
        else:
            logger.warning(f"Can not create permanent http session. A 'on-demand session' will be used")
        await super().run()

    async def stop(self):
        await self._connector.close()
        await super().stop()

    def _get_alpaca_method(self, alpaca_address: list):
        """
        Get method from alpaca connector if exsist

        :param alpaca_address: path to alpaca method
        :return: alpaca method
        """
        method = None
        for atr in alpaca_address:
            try:
                method = getattr(method if method else self._observatory, atr)
            except AttributeError:
                logger.info(f"Alpaca hasn't method {'.'.join(alpaca_address)}")
                raise
        return method

    async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
        address = request.address
        index = request.index
        alpaca_address = address[index:]

        try:
            method = self._get_alpaca_method(alpaca_address)
        except AttributeError:
            raise AddressError(address=address, code=1002, message="Alpaca driver does not have such a method")
        if not method or not callable(method):
            raise AddressError(address=address, code=1002, message="Can not call this alpaca method")

        result = None
        try:
            result = await method()
        except AlpacaHttp400Error as e:
            # if server alpaca return 400 error
            logger.warning(f"Alpaca throw error 400 for request {address}")
            raise TreeValueError(None, 2002, message=e.message)
        except AlpacaHttp500Error as e:
            # if server alpaca return 500 error
            logger.warning(f"Alpaca throw error 500 for request {address}")
            raise TreeValueError(None, 2002, message=e.message)
        except AlpacaContentTypeError as e:
            # if server alpaca return data in wrong format
            logger.warning(f"Alpaca throw error AlpacaContentTypeError for request {address}")
            raise TreeValueError(None, 2002, message=e.message)
        except AlpacaError as e:
            # when server alpaca throws an error with a numeric value
            logger.warning(f"Alpaca throw numeric error for request {address}")
            raise TreeValueError(None, 2002, message=e.message)
        except AlpacaHttpError as e:
            # if server alpaca return unresolved error
            logger.warning(f"Alpaca throw AlpacaHttpError for request {address}")
            raise TreeValueError(None, 2002, message=e.message)
        except RequestConnectionError as e:
            # when can not connect to alpaca
            logger.warning(f"Server alpaca is not responding")
            raise TreeValueError(None, 2002, message=f"Server alpaca is not responding")

        return Value(result, datetime.datetime.now())

    def _get_cfg(self, name_cfg: str, default=None):
        """
        The method looks for a value in the configuration file and returns it.

        :param name_cfg: name of config value
        :param default: default value if key not exist in config
        :return: config value or None if method can't find it
        """
        try:
            value = SingletonConfig.get_config()['tree'][self._component_name][name_cfg].get()  # local
        except confuse.exceptions.NotFoundError:
            try:
                value = SingletonConfig.get_config()['data_collection'][self._component_name][name_cfg].get()  # global
            except confuse.exceptions.NotFoundError:
                value = default  # default
        return value

    def __del__(self):
        self._connector.__del__()
