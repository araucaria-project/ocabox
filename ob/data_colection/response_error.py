import logging

logger = logging.getLogger(__name__)


class ResponseError:

    SEVERITY_LEVELS = ['NORMAL', 'CRITICAL']

    ERROR_CODE = [(1001, 'Wrong address format'),
                  (1002, 'Non-existent address'),
                  (2001, 'Value error'),
                  (3001, 'Wrong tree architecture, unexpected end of the branch, no next component')]

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

    @staticmethod
    def is_code_known(code: int):
        for c, m in ResponseError.ERROR_CODE:
            if code == c:
                return True
        return False

    @staticmethod
    def get_code_description(code):
        for c, m in ResponseError.ERROR_CODE:
            if code == c:
                return m
        return ''
