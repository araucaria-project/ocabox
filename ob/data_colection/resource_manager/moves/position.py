import asyncio
import time
from typing import Tuple, Optional, Callable

from ob.comunication.comunication_error import CommunicationRuntimeError
from ob.util_functions.asyncio_util_functions import wait_for_psce


# todo Position do zmiany nazwy
class Position:
    def __init__(self, address, t=None, s=None, c=None, timeout=None,
                 bounds: Tuple[Optional[float], Optional[float]] = (None, None), order: int = 1, name: str = ""):
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
        self.order = order
        self._start_tmstp = 0
        self._finish_tmstp = 0
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

    @property
    def start_timestamp(self):
        return self._start_tmstp

    @start_timestamp.setter
    def start_timestamp(self, s):
        self._start_tmstp = s

    @property
    def finish_timestamp(self):
        return self._finish_tmstp

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
            self._finish_tmstp = time.time()
            if not self._finish_fut.done():
                self._finish_fut.set_result(False)
            await CQ.stop_and_wait()

    async def wait(self):
        # todo może powinien zwracać błąd gdy czekamy a nie zostało uruchomione
        if self._finish_fut is not None:
            await self._finish_fut

    async def run(self, api):
        if self.task:
            self.task.cancel()
        self._finish_fut = asyncio.get_running_loop().create_future()
        self.task = asyncio.create_task(wait_for_psce(self._coro(api=api), timeout=self.timeout))

    def add_more_important_position(self, position):
        self._wait_for_others.append(position)
