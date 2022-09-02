import logging
import time
from ob.data_colection.address import AddressError
from ob.data_colection.alpaca_api.connector import Connector, AlpacaConnector
from ob.data_colection.alpaca_api.exceptions import AlpacaHttp400Error, AlpacaHttp500Error, AlpacaContentTypeError, \
    AlpacaError, AlpacaHttpError, RequestConnectionError
from ob.data_colection.alpaca_api.observatory import Observatory
from ob.data_colection.base_components.tree_base_provider import TreeBaseProvider
from ob.data_colection.value import Value, TreeValueError
from ob.data_colection.value_call import ValueRequest

logger = logging.getLogger(__name__)


class TreeAlpacaObservatory(TreeBaseProvider):
    """
    This object represents an alpaca module in a tree structure. Responsible for redirecting queries to the alpaca
    server with the api device. The object hasn't an address in the tree structure.

    :param component_name: this is name of tree component, used for debug
    :param observatory_name: This is observatory name, it is used to get configuration from config file.
    """
    DEFAULT_PROTOCOL = 'alpaca'
    COMPONENT_DEFAULT_NAME: str = 'TreeAlpacaObservatory'

    def __init__(self, component_name: str, observatory_name=None, **kwargs):
        super().__init__(component_name=component_name, subcontractor=None, **kwargs)
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
        Get method or attribute from alpaca connector if exists

        :param alpaca_address: path to alpaca method
        :return: alpaca method or attribute
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
        alpaca_address = address[index:].copy()
        request_type = request.request_type
        request_arguments = request.request_data

        alpaca_method_name = alpaca_address[len(alpaca_address) - 1]
        alpaca_address[len(alpaca_address) - 1] = 'put' if request_type == 'PUT' else 'get'
        try:
            method = self._get_alpaca_method(alpaca_address)
        except AttributeError:
            raise AddressError(address=address, code=1002, message="Alpaca driver does not have such a method")

        if not method or not callable(method):
            raise AddressError(address=address, code=1002, message="Can not call this alpaca method in driver")

        try:
            result = await method(alpaca_method_name, **request_arguments)
        except AlpacaHttp400Error as e:
            # if server alpaca return 400 error
            logger.warning(f"Alpaca throw error 400 for request {address}")
            raise TreeValueError(address=None, code=2002, message=e.message)
        except AlpacaHttp500Error as e:
            # if server alpaca return 500 error
            logger.warning(f"Alpaca throw error 500 for request {address}")
            raise TreeValueError(address=None, code=2002, message=e.message)
        except AlpacaContentTypeError as e:
            # if server alpaca return data in wrong format
            logger.warning(f"Alpaca throw error AlpacaContentTypeError for request {address}")
            raise TreeValueError(address=None, code=2002, message=e.message)
        except AlpacaError as e:
            # when server alpaca throws an error with a numeric value
            logger.warning(f"Alpaca throw numeric error for request {address}")
            raise TreeValueError(address=None, code=2002, message=e.message)
        except AlpacaHttpError as e:
            # if server alpaca return unresolved error
            logger.warning(f"Alpaca throw AlpacaHttpError for request {address}")
            raise TreeValueError(address=None, code=2002, message=e.message)
        except RequestConnectionError:
            # when can not connect to alpaca
            logger.warning(f"Server alpaca is not responding")
            raise TreeValueError(address=None, code=2002, message=f"Server alpaca is not responding")
        except TypeError:
            # when given arguments is wrong
            logger.warning(f"Alpaca driver get wrong arguments to run function")
            raise AddressError(address=address, code=1003, message=f"Wrong arguments for method")
        # TODO gdy jest PUT to zwraca cały blok odpowiedzi a przy GET tylko result.get("Value", None) to jest w api do alpaki ale tutaj można to naprawić bo narazie jest zwracany słownik
        return Value(result, time.time())

    def __del__(self):
        self._connector.__del__()
