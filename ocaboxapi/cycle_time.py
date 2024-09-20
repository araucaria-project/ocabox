import logging
from ctc import CycleTimeCalc
from ctc import CycleTimeDataClean
from ctc import CycleTimeTrain

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CycleTime(CycleTimeCalc):

    def __init__(self, telescope: 'Telescope' = None, telescope_id: str = None, base_folder: str = None) -> None:
        self.t_id, self.bf =  self._provide_telescope_id_base_folder(telescope, telescope_id, base_folder)
        super().__init__(telescope=self.t_id, base_folder=self.bf)

    def _provide_telescope_id_base_folder(self, telescope, telescope_id, base_folder):
        if telescope is not None and telescope_id == None and base_folder == None:
            return telescope.id, '/data/misc/cycle_time_calc' #telescope.observatory.get_app_cfg(key='base_cycle_time_calc_dir')
        elif telescope is None and telescope_id is not None and base_folder is not None:
            return telescope_id, base_folder
        if telescope is None and telescope_id == None or \
                self.telescope is None and self.base_folder == None:
            logger.error(f'Put Telescope [Telescope] or telescope_id [str] and base_folder [str]')
            raise RuntimeError

    def clean_and_train_on_exit(self):
        CycleTimeDataClean.data_clean_all(base_folder=self.bf)
        CycleTimeTrain.train_all_telesc_all_commands(base_folder=self.bf)
