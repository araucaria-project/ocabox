from typing import List


class MultipartStructure:
    """
    This is a class that representing structure of messages sending between client and router
    """
    EMPTY_BIT_1 = 0
    CREATE_TIME = 1
    EMPTY_BIT_2 = 2
    ID_ = 3
    EMPTY_BIT_3 = 4
    DATA = 5

    _MIN_SIZE = 6

    def __init__(self, multipart: List[bytes], prefix_size: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.multipart: List[bytes] = multipart
        self.prefix_size: int = prefix_size

    @property
    def prefix_data(self) -> List[bytes]:
        return self.get_prefix_data(self.multipart, self.prefix_size)

    @property
    def create_time(self):
        return self.get_create_time(self.multipart, self.prefix_size)

    @property
    def id_(self):
        return self.get_id(self.multipart, self.prefix_size)

    @property
    def data(self):
        return self.get_data(self.multipart, self.prefix_size)

    @staticmethod
    def get_prefix_data(multipart, prefix_size: int = 0) -> List[bytes]:
        return multipart[:prefix_size]

    @staticmethod
    def get_create_time(multipart, prefix_size: int = 0):
        return multipart[(MultipartStructure.CREATE_TIME + prefix_size)]

    @staticmethod
    def get_id(multipart, prefix_size: int = 0):
        return multipart[(MultipartStructure.ID_ + prefix_size)]

    @staticmethod
    def get_data(multipart, prefix_size: int = 0):
        return multipart[(MultipartStructure.DATA + prefix_size):]

    @staticmethod
    def create_multipart(create_time: bytes, id_: bytes, data: List[bytes], prefix_data: List[bytes] = None):
        prefix_data = [] if prefix_data is None else prefix_data
        return [*prefix_data, b'', create_time, b'', id_, b'', *data]

    @staticmethod
    def validate_multipart(multipart, ps: int = 0):
        """
        This method validate multipart.

        :param multipart: multipart
        :param ps: prefix size
        :raise ValueError: when is something wrong witch multipart
        :return: True if ok
        """
        MS = MultipartStructure
        if len(multipart) < MultipartStructure._MIN_SIZE+ps:
            raise ValueError(f'Wrong multipart because is shorter than {MS._MIN_SIZE+ps}')
        if multipart[MS.EMPTY_BIT_1+ps] or multipart[MS.EMPTY_BIT_2+ps] or multipart[MS.EMPTY_BIT_3+ps]:
            raise ValueError(f'Empty byte in multipart is not empty')
        if not multipart[MS.CREATE_TIME+ps]:
            raise ValueError(f'Request has not message create date')
        if not multipart[MS.ID_+ps]:
            raise ValueError(f'Request has not message id')
        if not multipart[MS.DATA+ps]:
            raise ValueError(f'No data in multipart')
        return True

    def validate(self):
        """
        This method validate multipart storage in class.

        :raise ValueError: when is something wrong witch multipart
        :return: True if ok
        """
        self.validate_multipart(self.multipart, self.prefix_size)
