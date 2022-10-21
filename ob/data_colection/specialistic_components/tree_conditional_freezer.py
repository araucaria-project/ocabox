import asyncio
import contextlib
import time
import logging
from typing import Protocol, runtime_checkable
from ob.data_colection.base_components.tree_base_provider import TreeBaseProvider
from ob.data_colection.coded_error import TreeStructureError, TreeOtherError
from ob.data_colection.specialistic_components.tree_cache_observatory_protocols import TreeCacheProtocol, \
    KnownValueProtocol
from ob.data_colection.value import Value, TreeValueError
from ob.data_colection.value_call import ValueRequest

logger = logging.getLogger(__name__)


# todo zapytać  o podwojne zapytania do rutera, jedna wartość może się zmienić szybciej nisz druga i co wtedy?
#  Zdajemy się na inteligęcje urzytkownika? może niech będzie taka opcja ale w client_API się to uniemożliwi?


class TreeConditionalFreezer(TreeBaseProvider):
    COMPONENT_DEFAULT_NAME: str = 'TreeConditionalFreezer'

    def __init__(self, component_name: str, subcontractor: TreeCacheProtocol = None, **kwargs):
        super().__init__(component_name=component_name, subcontractor=subcontractor, **kwargs)
        self._subcontractor: TreeCacheProtocol = subcontractor
        self._event_change_data_in_cache: asyncio.Event or None = None
        self._event_change_data: asyncio.Event or None = None
        self._sink_task: asyncio.Task or None = None
        self._max_unsuccessful_refreshes: int = self._get_cfg('max_unsuccessful_refreshes')

    def set_max_refreshes(self, max_: int):
        self._max_unsuccessful_refreshes = max_

    async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
        if not request.cycle_query:
            raise TreeStructureError  # this is no subscribe request so push is forward

        if not self._subcontractor:
            raise TreeStructureError

        time_of_known_change = request.request_data.get('time_of_known_change', None)
        current_time = time.time()
        t_tolerance = request.time_of_data_tolerance

        # wait some before doing anything, no send message to fast
        wait_to = request.request_data.get('no_send_before', 0)
        if current_time < wait_to:
            await asyncio.sleep(wait_to - current_time)

        wait_offset_error: float = 0
        nr_of_unsuccessful_refreshes: int = 0
        # todo co jeśli zapyta o nieistniejacy adres? nigdy nie zaktualizuje ale zawsze będzie w cache - sądze że
        #  powinien ponowić próbę kilka razy i zwrocić błąd taki sam jak zwraca dostawca bo nie znamy powodu - czy to
        #  będzie niepodłączona alpaka czy nieistniejący adres czy cos innego

        # get instance object representing known value stored in cache - is not necessity tyo refresh this in loop
        k_value: KnownValueProtocol or None = self._subcontractor.get_k_val(request.address)
        if k_value is None:
            print('okook')
            # create k_value in cache list because no one request about it yet
            await self._update_value(request)
            k_value = self._subcontractor.get_k_val(request.address)  # init value if not exist yet
        if k_value is None:  # is steel None that mean value is not cachable
            logger.info(f'Retrieve a cycle query for a non-cacheable value {request.address}')
            raise TreeOtherError(code=4003)
        # todo musimy sprawdzać czy jest cachable przez wywołanie metody nie tak jak wyzej bo jest sytuacja gdy
        #  pierwsze zapytanie pujdzie GET a potem na ten sam adres PUT wyjdzie ze jest cachable a nie prawdz !!!
        #  TU SKONCZYLEM
        #  teraz nie działa bo tutaj przechodzi i potem prubuje aktualizowac wartośc zapytaniem PUT które zwraca
        #  status OK ale nie aktualizuje wartości a na dodatek pyta za szybko bo interwały są wyliczane z wartości
        while True:
            print('ok')
            if k_value.get_value() is None:
                pass

            elif time_of_known_change is None or time_of_known_change < k_value.get_change_time():
                # todo przemyśleć czy jednak nie zwracać tej wartości skoro już jest pobrana zamiast oddelegowywać
                #  do cache bo tam może ugrząznąć na jakiś minimalny czas
                raise TreeStructureError

            # wait
            result_waiter = await self._waiter(k_value=k_value,
                                               t_tolerance=t_tolerance,
                                               min_wait=wait_offset_error)  # can raise TreeValueError
            if result_waiter:
                continue  # continue because event was call so is not necessary to update value again

            # update value
            status_update = await self._update_value(request)
            if status_update:
                wait_offset_error = 0
                nr_of_unsuccessful_refreshes = 0
            else:
                logger.info(f'Can not update value in cache: {request.address}')
                wait_offset_error = t_tolerance
                nr_of_unsuccessful_refreshes += 1
            if nr_of_unsuccessful_refreshes > self._max_unsuccessful_refreshes:
                logger.info(f'Too many failed attempts to refresh a value {request.address}')
                raise TreeValueError(code=2003)

        # # Unexpected end
        # logger.error(f'Unexpected end method before create any value')
        # raise TreeValueError(code=2001, message='Unexpected end program')

    async def _waiter(self, k_value: KnownValueProtocol, t_tolerance: float, min_wait: float = 0) -> bool:
        """
        This method is used to wait for the value in the cache or time to change before the specified expiration
        date will expire

        :param k_value: Object of known value from cache block
        :param t_tolerance: the allowable difference between the present moment and timestamp of the value
        :param min_wait: minimum wait time
        :raise TreeValueError: When can not find _event_change_data
        :return: True if waiter finish by event call
        """
        while True:
            current_time = time.time()
            if k_value.get_timestamp() is None:
                waiting_time = 0
            else:
                waiting_time = k_value.get_timestamp() + t_tolerance - current_time
            # check and set min waiting time
            if min_wait != 0:
                if waiting_time < min_wait:
                    waiting_time = min_wait
                min_wait = 0  # Restore 0 because the minimum expectation can only be the first time the loop passes
            if waiting_time <= 0:
                return False  # it's time to update value - return False because it is not event call
            if self._event_change_data is None:
                raise TreeValueError(code=2002)
            is_event = await self._event_wait(self._event_change_data, waiting_time)
            if is_event:  # event call
                return True  # value was changed

    async def _update_value(self, request: ValueRequest) -> bool:
        """
        This method call subcontractor to get response and update cache module.

        :param request: request object
        :return: status response, if false that mean is some errors
        """
        request.time_of_data = time.time()
        result = await self._subcontractor.get_response(request=request.copy())
        return result.status

    async def _sink(self):
        try:
            if self._event_change_data_in_cache is None:
                self._event_change_data_in_cache = asyncio.Event()
            if self._event_change_data is None:
                self._event_change_data = asyncio.Event()
            while True:
                await self._event_change_data_in_cache.wait()
                self._event_change_data_in_cache.clear()
                self._event_change_data.set()
                await asyncio.sleep(0)
                self._event_change_data.clear()
        finally:
            # clear events because sink not working no del because some task can wait and should have some time to
            # close self before delete event
            if self._event_change_data_in_cache is not None:
                self._event_change_data_in_cache = None
            if self._event_change_data is not None:
                self._event_change_data = None

    @staticmethod
    async def _event_wait(evt, timeout):
        # suppress TimeoutError because we'll return False in case of timeout
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(evt.wait(), timeout)
        return evt.is_set()

    def set_change_event(self):
        """Method set the event"""
        if self._event_change_data is not None:
            self._event_change_data_in_cache.set()

    def clear_change_event(self):
        """Method unset the event"""
        if self._event_change_data is not None:
            self._event_change_data_in_cache.clear()

    async def run(self):
        # todo pomyslec nad czyms sprytniejszym niz odpalanie go na zawsze
        self._sink_task = asyncio.create_task(self._sink())
        await asyncio.sleep(0)  # let the sink task run
        await super().run()

    async def stop(self):
        if self._sink_task is not None:
            self._sink_task.cancel()
            try:
                await self._sink_task
            except asyncio.CancelledError:
                pass  # todo tu skonczylem - tu jest jakis blad niewiadomo skad !
        await super().stop()


@runtime_checkable
class TreeConditionalFreezerProtocol(Protocol):

    def set_change_event(self):
        pass

    def clear_change_event(self):
        pass
