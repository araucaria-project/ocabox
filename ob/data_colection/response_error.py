import logging

from ob.data_colection.address import AddressError
from ob.data_colection.coded_error import OBStructureError
from ob.data_colection.value import OBValueError

logger = logging.getLogger(__name__)


class ResponseError:

    SEVERITY_LEVELS = ['NORMAL', 'CRITICAL']
    SUPPORTED_ERRORS = [OBValueError, OBStructureError, AddressError]

    def __init__(self, code: int, message: str, component_name: str, severity: str = 'NORMAL'):
        self.code: int = code
        self.message: str = message
        self.component_name: str = component_name
        self.severity: str = severity

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            d[k] = v
        return d

    def __copy__(self):
        return ResponseError(self.code, self.message, self.component_name, self.severity)

    def __str__(self):
        return f'ResponseError ({self.severity}) code: {str(self.code)} - ' \
               f'{self.message if self.message else self.get_code_description(self.code)}'

    @classmethod
    def is_code_known(cls, code: int):
        for e in cls.SUPPORTED_ERRORS:
            if e.is_code_known(code):
                return True
        return False

    @classmethod
    def get_code_description(cls, code):
        for e in cls.SUPPORTED_ERRORS:
            desc = e.get_code_description(code)
            if desc:
                return desc
        return ''

    @classmethod
    def get_code_error(cls, code):
        for e in cls.SUPPORTED_ERRORS:
            if e.is_code_known(code):
                return e
        return None
