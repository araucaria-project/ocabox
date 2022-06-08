import logging
from datetime import datetime, timedelta

from ob.data_colection.coded_error import BaseCodedError

logger = logging.getLogger(__name__)


class Value:

    def __init__(self, v, ts: datetime or float, value_type=None, **kwargs):
        self.v = v
        if isinstance(ts, float):
            ts = datetime.fromtimestamp(ts)
        self.ts: datetime = ts
        self.type = value_type

    def __eq__(self, other):
        return self.v == other.v

    def __gt__(self, other):
        return self.v > other.v

    def __lt__(self, other):
        return self.v < other.v

    def is_expired(self, dt: datetime, tolerance: timedelta = None):
        """
        This method check if date of this value is older then give date minus tolerance.
        :param dt: date what is needed
        :param tolerance: allowable time delay
        :return: true if date of this value is older what is needed.
        """
        if tolerance:
            dt = dt - tolerance
        return self.ts < dt  # id this date is older than date with is need then value is expired

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if k == 'ts':
                v = datetime.timestamp(v)
            d[k] = v
        return d


class OBValueError(BaseCodedError):
    """
    This is a base exception with code for Value errors.

    :ivar message: Error message
    :ivar code: Error code
    :ivar value: value
    :cvar CODE_GROUP: Number of error group, must be the number of whole thousands
    :cvar _KNOWN_LOCAL_CODES: List of known errors with local codes (codes without number of group can be number
        between 1 and 999)
    :cvar ERROR_CODE: This is list of pair (code, description)

    :param value: value
    :param code: Error code
    :param message: Error message
    """
    CODE_GROUP: int = 2000
    _KNOWN_LOCAL_CODES = [(1, 'Default Value error'),
                          (2, 'Error creating value')]

    def __init__(self, value: Value or None = None, code: int = CODE_GROUP, message: str = "", **kwargs):
        self.value = value
        super().__init__(message=message, code=code, **kwargs)
