from typing import Dict, List
from pyaraucaria.coordinates import az_alt_2_ra_dec, ra_to_decimal, dec_to_decimal, deg_to_decimal_deg
import random

from ob.planrunner.ern.errors import PlanBuildError


class SequenceData:
    """
    Class representing camera single sequence parameters
    """
    _SEQUENCE_LEN = 3

    def __init__(self, seq: str):
        self._seq = seq.split('/') if seq else []

    def validate(self):
        """

        raise PlanBuildError
        :return:
        """

        if len(self._seq) != self._SEQUENCE_LEN:
            raise PlanBuildError(f"The length of the sequence is wrong, should "
                                 f"be {self._SEQUENCE_LEN}")

        try:
            int(self._seq[0])
        except ValueError:
            raise PlanBuildError(f"Wrong first value in sequence, can't cast to int")

        if self._seq[2] != 'a':
            try:
                float(self._seq[2])
            except ValueError:
                raise PlanBuildError(f"Wrong third value in sequence, can't cast to float")

    @property
    def exp_quantity(self) -> int:
        return int(self._seq[0])

    @property
    def filter(self) -> str or int:
        return self._seq[1]

    @property
    def exp_time(self) -> float:
        if self._seq[2] == 'a':
            return 0.0
        return float(self._seq[2])

    @property
    def auto_exposure(self) -> bool:
        if self._seq[2] == 'a':
            return True
        else:
            return False
