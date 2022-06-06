import logging

from ob.data_colection.coded_error import AddressError

logger = logging.getLogger(__name__)


class Address:

    def __init__(self, adr: str, **kwargs):
        super().__init__(**kwargs)
        if not isinstance(adr, str):
            raise AddressError(adr, code=1001, message='wrong type address.')
        self.adr = adr.split('.') if adr else []

    @classmethod
    def as_address(cls, a):
        """
        This method convert given value to Address object.

        :param a: value in anny type
        :return: Address
        """
        if isinstance(a, Address):
            return a
        if isinstance(a, str):
            return Address(a)
        raise ValueError(a)

    def __eq__(self, other):
        return self.adr == other.adr

    def __hash__(self):
        return hash(self.adr)

    def __str__(self):
        return '.'.join(self.adr)

    def __iter__(self):
        return iter(self.adr)

    def __getitem__(self, item):
        return self.adr[item]

    def __len__(self):
        return len(self.adr)

    def get_last_index(self):
        return len(self.adr) - 1

    def __copy__(self):
        return Address(self.__str__())

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if k == 'adr':
                v = '.'.join(self.adr)
            d[k] = v
        return d
