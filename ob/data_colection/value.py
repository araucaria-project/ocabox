from datetime import datetime


class Value:

    def __init__(self, v, ts: datetime, value_type=None, **kwargs):
        self.v = v
        self.ts: datetime = ts
        self.type = value_type

    def __eq__(self, other):
        return self.v == other.v

    def __gt__(self, other):
        return self.v > other.v

    def __lt__(self, other):
        return self.v < other.v
