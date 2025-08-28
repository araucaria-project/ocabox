import asyncio
import logging
from abc import ABC
from typing import Dict, List, Any, Callable, Optional
import pwd
import os

import nats.errors
from pyaraucaria.date import datetime_to_julian
from datetime import datetime
import math
from serverish.messenger import get_journalpublisher, get_publisher, get_reader, get_singlereader
from serverish.messenger.msg_journal_pub import MsgJournalPublisher
from serverish.messenger.msg_publisher import MsgPublisher
from serverish.messenger.msg_reader import MsgReader
from serverish.messenger.msg_single_read import MsgSingleReader

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
                 info_callback: Dict[str, Callable], c_type: str, param: Optional[Dict[str, Any]] = None) -> None:
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
        self.reader_weather_davies: MsgSingleReader | None = None
        self.get_journal()
        self.get_reader_weather_davies()
        self.build_plan_status()
        self.command_log_pub = self.get_publish(stream='status', field='planner_command_log')
        self.status_error_pub = self.get_publish(stream='planner', field='status_error')
        super().__init__()

    def get_subject(self, stream: str, field: Optional[str]) -> Optional[str]:
        if field is None:
            r = self.param['cfg_gen'].get_value(
                seq=['site', 'global', 'nats', 'subjects', stream], source='nats'
            )
        else:
            r = self.param['cfg_gen'].get_value(
                seq=['site', 'global', 'nats', 'subjects', stream, field], source='nats'
            )
        logger.debug(f'Status subject {r}')
        return r

    def get_journal(self) -> None:
        self.journal = get_journalpublisher(subject=self.get_subject(stream='journal', field='planner'))

    def get_reader_weather_davies(self) -> None:
        self.reader_weather_davies = get_singlereader(
            subject=self.get_subject(stream='weather', field=None), deliver_policy='last'
        )

    async def weather_davies_read(self) -> Optional[Dict]:
        data, meta = await self.reader_weather_davies.read()
        try:
            return data
        except (TimeoutError, LookupError, ValueError, TypeError, nats.errors.TimeoutError):
            return None

    def get_publish(self, stream: str, field: str) -> Optional[MsgPublisher]:
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
                inf = f'Proof get {name} start.'
                logger.info(inf)
                await self.journal.debug(f'msg: {inf}, uid: {pwd.getpwuid(os.getuid())[0]}.')
            res = await self._value_proof_get(name=name, awaitab=awaitab, expect_type=expect_type)
            if log:
                inf = f'Proof get {name} got response: {res}.'
                logger.info(inf)
                await self.journal.debug(f'msg: {inf}, uid: {pwd.getpwuid(os.getuid())[0]}.')
            if res is not None:
                return res
            else:
                inf = f"Can't get {name}, (is None)"
                logger.warning(inf)
                if log:
                    await self.journal.warning(f'msg: {inf}, uid: {pwd.getpwuid(os.getuid())[0]}.')
                await asyncio.sleep(wait)
            if n == n_times:
                return None

    async def proof_put(self, awaitab: Callable, name: str = '', n_times: int = 5, wait: float = 3.0, **kwargs) -> bool:
        async for n in AsyncRangeIter(start=1, end=n_times):
            try:
                logger.info(f'Proof put {name} start.')
                await awaitab(**kwargs)
                # logger.info(f'Sending proof put request {name} req no. {n}/{n_times}')
                return True
            except OcaboxServerError:
                inf = f'Tic OcaboxServerError'
                logger.warning(inf)
                await self.journal.warning(f'msg: {inf}, uid: {pwd.getpwuid(os.getuid())[0]}.')
                await asyncio.sleep(wait)
                continue
            except CommunicationTimeoutError:
                inf = f'Tic CommunicationTimeoutError'
                logger.warning(inf)
                await self.journal.warning(f'msg: {inf}, uid: {pwd.getpwuid(os.getuid())[0]}.')
                await asyncio.sleep(wait)
                continue
            except OcaboxAccessDenied:
                inf = f'Tic OcaboxAccessDenied'
                logger.warning(inf)
                await self.journal.warning(f'msg: {inf}, uid: {pwd.getpwuid(os.getuid())[0]}.')
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
    def get_julian_date(date: str | datetime) -> float:
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

    async def get_filters_dict(self) -> Optional[Dict[str, int]]:
        filters = self.param['cfg_gen'].get_value(seq=[
            'telescopes', self.telescope.id, 'observatory', 'components', 'filterwheel', 'filters'
        ], source='nats')
        try:
            return {f['name']: f['position'] for f in filters}
        except (LookupError, TypeError):
            inf = f'Can not take filters from cfg general'
            logger.error(inf)
            await self.journal.error(inf)
            return None
