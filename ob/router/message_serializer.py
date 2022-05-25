import logging

import msgpack

logger = logging.getLogger(__name__)


# TODO chy chcem odziedziczyć go po słowiku?
class MessageSerializer:
    SERIALIZER_NAME = 'msgpack'

    def __init__(self, data: dict):
        self._data: dict = data

    @classmethod
    def from_bytes(cls, data_b: bytes):
        """
        Method create class MessageSerializer from give bytes.
        :param data_b: data in bytes
        :return: MessageSerializer
        """
        data = cls.unpack_b(data_b)
        return cls(data)

    def to_byte(self):
        """
        Convert data of this class to bytes
        :return: data of this class in bytes
        """
        return self.pack_b(self._data)

    @staticmethod
    def unpack_b(data_b: bytes):
        """
        This method convert bytes to dict using external serializer.
        :param data_b: data in bytes
        :return: data in dict
        """
        return msgpack.unpackb(data_b)

    @staticmethod
    def pack_b(data: dict):
        """
        This method convert dict to bytes using external serializer
        :param data: data in dict
        :return: data in bytes
        """
        return msgpack.packb(data)

    def get_all(self):
        """
        This method return dict with all data stored in this class
        :return: dict with data
        """
        return self._data

    def get(self, key):
        """
        This method return value for the given key from data stored in this class
        :param key: key
        :return: value for given key
        """
        return self._data.get(key)

    @staticmethod
    def is_correct(data: dict):
        """
        This method checks if the data is correct.
        :return: true if data is correct and false if not
        """
        if not isinstance(data, dict):
            return False
        return True
