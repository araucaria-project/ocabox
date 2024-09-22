from typing import Dict, List, Any
import logging
import random
from ob.planrunner.coded_error import SequenceTreeError


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Seq:

    """
    Class representing camera single sequence
    """

    def __init__(self, seq: str, command_kwargs: Dict):
        self.seq: str = seq
        self._focus_id: int or None = None
        self.command_kwargs: Dict = command_kwargs
        self.focus_folder: str or None = None
        self.skip = False
        self.set_focus_id()

    @property
    def focus_id(self) -> int or None:
        return self._focus_id

    def set_focus_id(self):
        self._focus_id = random.randrange(0, 100000)

    @property
    def focus_list(self) -> List[str] or None:
        """
        Input format focus_target/focus_step
        :return: [focus_target/focus_step]
        """
        if 'pos' in self.command_kwargs.keys():
            return list(self.command_kwargs['pos'].split('/'))
        else:
            return None

    @property
    def focus_target(self) -> int or None:
        if self.focus_list:
            return int(self.focus_list[0])
        else:
            return None

    def focus_position(self, exp_no: int) -> float or None:
        if self.focus_values_list:
            return self.focus_values_list[exp_no - 1]
        else:
            return None

    @property
    def focus_min(self) -> int or None:
        if self.focus_list:
            return int(round(self.focus_target - (self.focus_step * ((self.exp_no - 1) / 2))))
        else:
            return None

    @property
    def focus_step(self) -> int or None:
        if self.focus_list:
            return int(self.focus_list[1])
        else:
            return None

    @property
    def focus_values_list(self) -> List[str] or None:
        if self.focus_list:
            f = []
            for n in range(0, self.exp_no):
                f.append(self.focus_min + (self.focus_step * n))
            return f
        else:
            return None

    @property
    def seq_list(self) -> List[str]:
        return list(self.seq.split('/'))

    @property
    def exp_no(self) -> int:
        try:
            ret = int(self.seq_list[0])
        except (ValueError, IndexError):
            logger.error(f'Plan syntax error in: {self.seq}')
            raise SequenceTreeError
        return ret

    @property
    def filter_(self) -> str or int:
        return self.seq_list[1]

    @property
    def exp_time(self) -> float or None:
        try:
            return float(self.seq_list[2])
        except ValueError:
            return None

    @property
    def auto_exposure(self) -> bool:
        if self.seq_list[2] == 'a':
            return True
        else:
            return False

    @property
    def dither_list(self) -> List[str] or None:
        # [dither_mode, dither_every_sub, dither_distance]
        if 'dither' in self.command_kwargs.keys():
            if self.command_kwargs['dither'] == 'off':
                return None
            else:
                return list(self.command_kwargs['dither'].split('/'))
        else:
            return None

    @property
    def dither_mode(self) -> str:
        if self.dither_list:
            return str(self.dither_list[0])
        else:
            # TODO get from settings
            return 'basic'

    @property
    def dither_every_sub(self) -> int:
        if self.dither_list:
            return int(self.dither_list[1])
        else:
            # TODO get from settings
            return 1

    @property
    def dither_distance(self) -> float:
        if self.dither_list:
            return float(self.dither_list[2])
        else:
            # TODO get from settings
            return 8.0

    def dither_this_exp(self, ex: int) -> bool:
        if ((ex % self.dither_every_sub) == 0):
            return True
        else:
            return False
