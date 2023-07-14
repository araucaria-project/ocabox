import logging
from abc import abstractmethod, ABC

logger = logging.getLogger(__name__.rsplit('.')[-1])


class PartMove(ABC):
    def __init__(self, address: str, timeout=None, order: int = 1, name: str = ""):
        self._target = 1
        self._start = 0
        self._current = 0
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

    def done(self):
        if self._finish_fut is None:
            return False  # false because position even wasn't start so not done
        return self._finish_fut.done()

    async def wait(self):
        # todo może powinien zwracać błąd gdy czekamy a nie zostało uruchomione
        if self._finish_fut is not None:
            await self._finish_fut

    @abstractmethod
    async def run(self, api):
        raise NotImplementedError

    def add_more_important_position(self, position):
        self._wait_for_others.append(position)

    @property
    @abstractmethod
    def progress(self) -> float:
        """
        Method count progress changing value

        :return: progress in float format from 0 to 1
        """
        raise NotImplementedError
