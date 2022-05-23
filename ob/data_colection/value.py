from datetime import datetime, timedelta


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
        return self.ts < dt  # id this date is older then date with is need then value is expired

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if k == 'ts':
                v = datetime.timestamp(v)
            d[k] = v
        return d
