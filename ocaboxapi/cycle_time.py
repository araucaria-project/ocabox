import logging
from typing import Dict, Tuple, List
from ctc.cycle_time_calc import CycleTimeCalc
from ctc.cycle_time_data_clean import CycleTimeDataClean
from ctc import CycleTimeTrain

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTime(CycleTimeCalc):

    _DEFAULT_BASE_FOLDER = '/data/misc/cycle_time_calc'

    def __init__(
            self, telescope: 'Telescope' = None, telescope_id: str = None, base_folder: str = None,
            client_config_dict: Dict or None = None) -> None:
        self._cli_conf_dict = client_config_dict
        self._rm_modes: Dict[str, List[float]] or None = None
        self._observ_loc: Dict[str, float] or None = None
        self._tel_id, self._base_fold =  self._provide_inputs(
            telescope=telescope, telescope_id=telescope_id, base_folder=base_folder
        )
        super().__init__(telescope=self._tel_id, base_folder=self._base_fold)
        if self._rm_modes is not None:
            super().set_rm_modes(rm_modes=self._rm_modes)
        if self._observ_loc is not None:
            super().set_observatory_location(location=self._observ_loc)

    def provide_rm_modes(
            self, telescope_id: str = None, client_config_dict: Dict or None = None) -> None:
        try:
            _rm_mod = \
                client_config_dict['telescopes'][telescope_id]['observatory']['components']['camera']['readout_modes']
            if self._rm_modes is None:
                self._rm_modes = {}
            self._rm_modes[telescope_id] = [mod['val_mhz'] for _, mod in _rm_mod.items()]
        except (LookupError, TypeError):
            pass

    @staticmethod
    def get_telescopes_list(client_config_dict: Dict or None = None) -> List[str] or None:
        try:
            return list(client_config_dict['telescopes'].keys())
        except (LookupError, TypeError):
            return None

    def _provide_inputs(self, telescope, telescope_id, base_folder) -> Tuple[str, str]:
        if telescope_id is not None:
            _tel_id = telescope_id
        elif telescope is not None:
            _tel_id = telescope.id
        else:
            logger.warning(f'Warning: Put Telescope [Telescope] or telescope_id [str], now putting default')
            _tel_id = 'default'

        if base_folder is not None:
            _base_fold = base_folder
        elif self._cli_conf_dict is not None:
            try:
                _base_fold = self._cli_conf_dict['site']['global']['paths']['base_cycle_time_calc_dir']
            except (LookupError, TypeError):
                _base_fold = self._DEFAULT_BASE_FOLDER
        else:
            _base_fold = self._DEFAULT_BASE_FOLDER

        if self._cli_conf_dict is not None:
            self.provide_rm_modes(telescope_id=_tel_id, client_config_dict=self._cli_conf_dict)

            try:
                _loc = self._cli_conf_dict['site']['global']['geo_location']
                self._observ_loc = {
                    'latitude': _loc['lat'],
                    'longitude': _loc['lon'],
                    'elevation': _loc['elev']
                }
            except (LookupError, TypeError):
                pass

        return _tel_id, _base_fold

    def clean_and_train_on_exit(self, client_config_dict: Dict or None = None):
        if client_config_dict is not None:
            tel_list = self.get_telescopes_list(client_config_dict=client_config_dict)
            if tel_list is not None:
                for t in tel_list:
                    self.provide_rm_modes(telescope_id=t, client_config_dict=client_config_dict)
        CycleTimeDataClean.data_clean_all(base_folder=self._base_fold, rm_modes=self._rm_modes)
        CycleTimeTrain.train_all_telesc_all_commands(base_folder=self._base_fold)
