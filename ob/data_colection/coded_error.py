import logging
from abc import ABC
from typing import List, Tuple

logger = logging.getLogger(__name__)


class BaseCodedError(Exception, ABC):
    """
    This is a base exception with code.

    :ivar message: Error message
    :ivar code: Error code
    :cvar CODE_GROUP: Number of error group, must be the number of whole thousands
    :cvar _KNOWN_LOCAL_CODES: List of known errors with local codes (codes without number of group can be number
        between 1 and 999)
    :cvar ERROR_CODE: This is list of pair (code, description)

    :param code: Error code
    :param message: Error message
    """
    CODE_GROUP: int = 0
    # This is list of pair (code, description) code can be number between 1 and 999
    _KNOWN_LOCAL_CODES: List[Tuple[int, str]] = []
    ERROR_CODE: List[Tuple[int, str]] = [(c + CODE_GROUP, d) for c, d in _KNOWN_LOCAL_CODES]

    def __init__(self, code: int = CODE_GROUP, message: str = "", **kwargs):
        if message:
            message = message
        elif code != self.CODE_GROUP:
            message = f'Error code {str(code)} - {self.get_code_description(code)}'
        else:
            message = "Default error."
        self.message = message
        self.code = code
        super().__init__(self.message)

    @classmethod
    def is_code_known(cls, code: int) -> bool:
        """
        Method returns true if given code is known
        :param code: code to check
        :return: true if code is known and false if not
        """
        for c, m in cls.ERROR_CODE:
            if code == c:
                return True
        return False

    @classmethod
    def get_code_description(cls, code) -> str:
        """
        Method returns description for given code if code is known or empty string if not.
        :param code: code
        :return: description for given code or empty string
        """
        for c, m in cls.ERROR_CODE:
            if code == c:
                return m
        return ''


class TreeStructureError(BaseCodedError):
    """
    This is a base exception with code for project structure errors.

    :ivar message: Error message
    :ivar code: Error code
    :cvar CODE_GROUP: Number of error group, must be the number of whole thousands
    :cvar _KNOWN_LOCAL_CODES: List of known errors with local codes (codes without number of group can be number
        between 1 and 999)
    :cvar ERROR_CODE: This is list of pair (code, description)

    :param code: Error code
    :param message: Error message
    """
    CODE_GROUP: int = 3000
    _KNOWN_LOCAL_CODES = [(1, 'Wrong tree architecture, unexpected end of the branch, no next component'),
                          (2, 'Component has not implemented method or method work incorrect')]

    def __init__(self, code: int = CODE_GROUP, message="", **kwargs):
        super().__init__(message=message, code=code, **kwargs)


class TreeOtherError(BaseCodedError):
    CODE_GROUP = 4000
    _KNOWN_LOCAL_CODES = [(1, 'Wrong request'),
                          (2, 'Application do not answer')]

    def __init__(self, code: int = CODE_GROUP, message="", **kwargs):
        super().__init__(message=message, code=code, **kwargs)
