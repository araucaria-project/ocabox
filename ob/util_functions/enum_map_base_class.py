class BaseArgsMap:

    @classmethod
    def has_item(cls, item):
        return item in [v for i, v in cls.__dict__.items() if i[:1] != '_']

    @classmethod
    def get_item(cls, item):
        r = None
        for i, v in cls.__dict__.items():
            if i[:1] != '_' and item == v:
                r = v
        return r


class StrVal(str, BaseArgsMap):
    _VAL_ = None

    def __new__(cls, string, v):
        instance = super().__new__(cls, string)
        instance._VAL_ = v
        return instance

    def val(self):
        return self._VAL_


