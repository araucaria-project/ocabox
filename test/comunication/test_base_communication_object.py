import time
import unittest

from ob.comunication.base_communication_object import BaseCommunicationObject
from ob.comunication.comunication_error import CommunicationTimeoutError
from ob.comunication.message_serializer import MessageSerializer
from ob.comunication.multipart_structure import MultipartStructure


class BaseCommunicationObjectTest(unittest.TestCase):
    class SampleBaseCommunicationObject(BaseCommunicationObject):
        DEFAULT_NAME = 'SampleBaseCommunicationObject'
        TYPE = 'client'

    def test__get_time_to_expire(self):
        bco = self.SampleBaseCommunicationObject(name='SampleTestClient')
        now = time.time()
        delta = 1
        # fresh message
        ms = MultipartStructure(
            [b'', MessageSerializer.pack_b(now), b'0', MessageSerializer.pack_b(now + delta), b'\xc2', b'',
             b'sample_data'])
        time_to_expire = bco._get_time_to_expire(ms=ms)
        self.assertTrue(0 < time_to_expire < delta)
        # expire message
        ms = MultipartStructure(
            [b'', MessageSerializer.pack_b(now), b'0', MessageSerializer.pack_b(now - delta), b'\xc2', b'', b'sample_data'])
        with self.assertRaises(CommunicationTimeoutError):
            bco._get_time_to_expire(ms=ms)
        # message hasn't timeout value
        ms = MultipartStructure(
            [b'', MessageSerializer.pack_b(now), b'0', b'', b'\xc2', b'', b'sample_data'])
        with self.assertRaises(CommunicationTimeoutError):
            bco._get_time_to_expire(ms=ms)
        # message hasn't timeout value and try to get default value
        time_to_expire = bco._get_time_to_expire(ms=ms, use_default=True)
        self.assertTrue(time_to_expire == bco.default_timeout)


if __name__ == '__main__':
    unittest.main()
