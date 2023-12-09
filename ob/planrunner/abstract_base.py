import logging
from abc import ABC
from typing import Dict, List, Any, Callable
import pwd
import os
from pyaraucaria.date import datetime_to_julian
from datetime import datetime
import math
from serverish.messenger import get_journalpublisher
from serverish.messenger.msg_journal_pub import MsgJournalPublisher

logger = logging.getLogger(__name__.rsplit('.')[-1])


class AbstractBase(ABC):

    COMMAND_NAMES = ['SKYFLAT', 'FOCUS', 'DOMEFLAT', 'DARK', 'ZERO', 'OBJECT', 'WAIT', 'STOP', 'SNAP', 'SEQUENCE']
    KWARGS = ['uobi', 'dome_follow', 'epoch', 'mirror_cover', 'observer', 'screen_light', 'az', 'alt', 'seq',
              'pos', 'dither', 'wait', 'ut', 'tracking']

    def __init__(self, id: str, name: str, telescope: 'Telescope',
                 info_callback: Dict[str, Callable], c_type: str) -> None:
        self.id = id
        self.telescope = telescope
        self.info_callback = info_callback
        self.name = name
        self.c_type: str = c_type
        self.started: bool = False
        self.done: bool = False
        self.skipped: bool = False
        self.journal: MsgJournalPublisher | None = None
        super().__init__()

    def journal_subject(self) -> str:
        c = self.telescope.observatory.get_app_cfg('nats_subject')
        r = f'{c["journal_root"]}.{self.telescope.id}.{c["tic_comp"]["planner"]}'
        return r

    def get_journal(self, tel_id) -> None:
        self.journal = get_journalpublisher(subject=self.journal_subject())

    @property
    def user(self):
        return pwd.getpwuid(os.getuid())[0]

    async def _value_proof_get(self, name: str, awaitab: Callable, expect_type) -> Any:
        try:
            res = await awaitab()
            if expect_type==float and isinstance(res, int):
                try:
                    res = float(res)
                except ValueError:
                    pass
            if isinstance(res, expect_type):
                logger.debug(f"Get {name} value done: {res}")
                return res
            else:
                logger.warning(f"Can't get {name} value, result is {res}")
                return None
        except Exception as e:
            logger.warning(f"Can't get {name} value: {e}")
            return None

    async def value_proof_get(self, name: str, awaitab: Callable, expect_type: type, n_times: int = 5) -> Any:
        for n in range(1, n_times+1):
            res = await self._value_proof_get(name=name, awaitab=awaitab, expect_type=expect_type)
            if res is not None:
                return res
            else:
                logger.warning(f"Can't get {name}, (is None)")
            if n == n_times:
                return None

    @staticmethod
    def _mk_folder(folder: str):
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
                logger.info(f'Creating folder {folder}')
            except Exception as e:
                logger.warning(
                    f'Folder creation failed, please create folder {folder} manually '
                    f'or adjust config key "app.base_fits_dir". Error: {e}'
                )

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

    def _add_to_log_night(self, log_line: Dict[str, Any], filter: Dict[str, Any] = None) -> None:
        put = True
        if filter and len(filter) > 0:
            for n, k in filter.items():
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


        # if self.kwargs:
        #     if len(self.kwargs) > 0:
        #         for n in self.kwargs.keys():
        #             if n != 'seq_data':
        #                 ex_js[n] = self.kwargs[n]

        ex_js['id'] = self.id
        ex_js['name'] = self.name
        ex_js['started'] = self.started
        ex_js['done'] = self.done
        ex_js['skipped'] = self.skipped
        ex_js['timestamp_utc'] = str(datetime.utcnow())
        ex_js['c_type'] = self.c_type
        self._add_to_log_night(ex_js, {'c_type': 'command'})
        return ex_js
