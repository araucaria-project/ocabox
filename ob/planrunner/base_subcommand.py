import logging
import os
from serverish.base import dt_utcnow_array
from ob.planrunner.abstract_base import AbstractBase
from datetime import datetime
from typing import Dict, List, Any, Callable

logger = logging.getLogger(__name__.rsplit('.')[-1])


class BaseSubCommand(AbstractBase):

    def __init__(self, id: str, name: str, telescope: 'Telescope',
                 info_callback: Dict[str, Callable], uobi: int, param: Dict[str, Any] or None = None) -> None:
        self.uobi = uobi
        super().__init__(id=id, name=name, info_callback=info_callback,
                         telescope=telescope, c_type='subcommand', param=param)
        self._mk_folder(self.log_night_folder)

    def create_sub_command_string(self, **kw):
        k = ''
        if kw:
            for n in kw.keys():
                if n != 'seq_data':
                    k = f'{k} {n}={kw[n]}'
                    self.param['plan_status'].upd_static_kwargs(id=self.id, field=n, value=kw[n])

        self.info_callback['c_subcommands'](f'{self.id};{self.name};;{k}')

    async def arun(self) -> int:
        raise NotImplementedError

    async def status_error_publish(
            self, level: str, description: str, plan_runner_quits: bool) -> bool:
        levels = ['minor', 'major', 'critical']

        data = {
            'id': self.id,
            'uobi': self.uobi,
            'telescope': self.telescope.id,
            'subcommand_name':  self.name,
            'error_level': level,
            'error_description': description,
            'plan_runner_quits': plan_runner_quits,
            'error_time': dt_utcnow_array
        }
        try:
            await self.status_error_pub.publish(data=data, timeout=30)
        except TimeoutError:
            logger.error(f'Nats status_error_publish get timeout error.')

    @property
    def fits_main_folder(self) -> str:
        base_fits_folder = os.path.expanduser(self.telescope.observatory.get_app_cfg('base_fits_dir'))
        return os.path.join(base_fits_folder, f'{self.telescope.id}')

    @property
    def fits_raw_folder_name(self) -> str:
        return 'raw'

    @property
    def fits_focus_folder(self) -> str:
        return os.path.join(self.fits_main_folder, f'focus')

    @property
    def fits_focus_folder_actual(self) -> str:
        return os.path.join(self.fits_focus_folder, f'actual')
