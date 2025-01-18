import asyncio
import logging
from abc import ABC
from typing import Dict, List, Any, Callable
import pwd
import os
from pyaraucaria.date import datetime_to_julian
from datetime import datetime
import math
from serverish.messenger import get_journalpublisher, get_publisher
from serverish.messenger.msg_journal_pub import MsgJournalPublisher
from serverish.messenger.msg_publisher import MsgPublisher

from ob.planrunner.iter_async import AsyncRangeIter
from ocaboxapi.exceptions import OcaboxServerError, OcaboxAccessDenied
from obcom.comunication.comunication_error import CommunicationTimeoutError


logger = logging.getLogger(__name__.rsplit('.')[-1])


class AbstractBase(ABC):

    COMMAND_NAMES = ['SKYFLAT', 'FOCUS', 'DOMEFLAT', 'DARK', 'ZERO', 'OBJECT', 'WAIT', 'STOP', 'SNAP', 'SEQUENCE']
    KWARGS = ['uobi', 'dome_follow', 'epoch', 'mirror_cover', 'observer', 'screen_light', 'az', 'alt', 'seq',
              'pos', 'dither', 'sec', 'ut', 'tracking', 'comment', 'sunrise', 'sunset', 'auto_focus', 'read_mod',
              'test']

    def __init__(self, id: str, name: str, telescope: 'Telescope',
                 info_callback: Dict[str, Callable], c_type: str, param: Dict[str, Any] or None = None) -> None:
        self.id = id
        self.telescope = telescope
        self.info_callback = info_callback
        self.name = name
        self.c_type: str = c_type
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        self.param = param if param is not None else {}
        self.journal: MsgJournalPublisher | None = None
        self.get_journal()
        self.build_plan_status()
        self.command_log_pub = self.get_publish(stream='status', field='planner_command_log')
        super().__init__()

    @property
    def journal_subject(self) -> str:
        r = self.param['cfg_gen'].get_value(
            seq=['site', 'global', 'nats', 'subjects', 'journal', 'planner'], source='nats'
        )
        logger.debug(f'Journal subject {r}')
        return r

    def get_subject(self, stream: str, field: str) -> str:
        r = self.param['cfg_gen'].get_value(seq=['site', 'global', 'nats', 'subjects', stream, field], source='nats')
        logger.debug(f'Status subject {r}')
        return r

    def get_journal(self) -> None:
        self.journal = get_journalpublisher(subject=self.journal_subject)

    def get_publish(self, stream: str, field: str) -> MsgPublisher or None:
        subj = self.get_subject(stream=stream, field=field)
        if subj is None:
            logger.error(f'Wrong subject for field {field}')
            return None
        return get_publisher(subject=subj)

    def build_plan_status(self):
        self.param['plan_status'].build(id=self.id, name=self.name, ctype=self.c_type)

    @property
    def user(self):
        return pwd.getpwuid(os.getuid())[0]

    @staticmethod
    async def _value_proof_get(name: str, awaitab: Callable, expect_type) -> Any:
        try:
            res = await awaitab()
        except OcaboxServerError:
            logger.warning(f'Tic OcaboxServerError.')
            return None
        except CommunicationTimeoutError:
            logger.warning(f'Tic CommunicationTimeoutError')
            return None
        except OcaboxAccessDenied:
            logger.warning(f'Tic OcaboxAccessDenied')
            return None
        if expect_type == float and isinstance(res, int):
            try:
                res = float(res)
            except ValueError:
                pass
        if isinstance(res, expect_type):
            # logger.info(f"Get {name} value done: {res}")
            return res
        else:
            logger.warning(f"Can't get {name} value, result is {res}")
            return None

    async def value_proof_get(self, name: str, awaitab: Callable, expect_type: type, n_times: int = 5,
                              wait: float = 3.0, log: bool = False) -> Any:
        async for n in AsyncRangeIter(start=1, end=n_times):
            if log:
                logger.info(f'Proof get {name} start.')
            res = await self._value_proof_get(name=name, awaitab=awaitab, expect_type=expect_type)
            if log:
                logger.info(f'Proof get {name} got {res}.')
            if res is not None:
                return res
            else:
                logger.warning(f"Can't get {name}, (is None)")
                await asyncio.sleep(wait)
            if n == n_times:
                return None

    @staticmethod
    async def proof_put(awaitab: Callable, name: str = '', n_times: int = 5, wait: float = 3.0, **kwargs) -> bool:
        async for n in AsyncRangeIter(start=1, end=n_times):
            try:
                logger.info(f'Proof put {name} start.')
                await awaitab(**kwargs)
                # logger.info(f'Sending proof put request {name} req no. {n}/{n_times}')
                return True
            except OcaboxServerError:
                logger.warning(f'Tic OcaboxServerError')
                await asyncio.sleep(wait)
                continue
            except CommunicationTimeoutError:
                logger.warning(f'Tic CommunicationTimeoutError')
                await asyncio.sleep(wait)
                continue
            except OcaboxAccessDenied:
                logger.warning(f'Tic OcaboxAccessDenied')
                await asyncio.sleep(wait)
                continue
        logger.error(f'Sending {name} failed')
        return False

    @staticmethod
    def _mk_folder(folder: str):
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            logger.info(f'Creating folder {folder}')

    @staticmethod
    def get_julian_date(date: str or datetime) -> float:
        return datetime_to_julian(date)

    @property
    def log_night_folder(self):
        return os.path.expanduser(self.telescope.observatory.get_app_cfg('base_log_night_dir'))

    @staticmethod
    def get_jd_now() -> float:
        return AbstractBase.get_julian_date(datetime.utcnow())

    @property
    def log_file_name(self) -> str:
        return f'log_night_{math.floor(AbstractBase.get_jd_now())}.txt'

    def _add_to_log_night(self, log_line: Dict[str, Any], filter_rules: Dict[str, Any] = None) -> None:
        put = True
        if filter_rules and len(filter_rules) > 0:
            for n, k in filter_rules.items():
                if n in log_line.keys():
                    if log_line[n] == k:
                        put = put * True
                    elif log_line[n] is not k:
                        put = put * False
                else:
                    put = put * False

        if put == 1 or put == True:
            f = open(os.path.join(self.log_night_folder, self.log_file_name), "a")
            f.write(f'{log_line}')
            f.write('\n')
            f.close()

    def exec_json(self, **kw) -> Dict[str, Any]:
        ex_js = {}
        if kw:
            for n in kw.keys():
                if n != 'seq_data':
                    ex_js[n] = kw[n]
        ex_js['id'] = self.id
        ex_js['name'] = self.name
        ex_js['started'] = self.started
        ex_js['done'] = self.done
        ex_js['skipped'] = self.skipped
        ex_js['timestamp_utc'] = str(datetime.utcnow())
        ex_js['c_type'] = self.c_type
        self._add_to_log_night(ex_js, {'c_type': 'command'})
        return ex_js

    async def get_filters_dict(self) -> Dict[str, int] or None:
        filers = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'filterwheel', 'filters'
        ], source='nats')
        try:
            return {f['name']: f['position'] for f in filers}
        except (LookupError, TypeError):
            inf = f'Can not take filters from cfg general'
            logger.error(inf)
            await self.journal.info(inf)
            return None
