"""Unit tests for the ocabox exception hierarchy and the centralized
``OcaboxError.from_response`` code->type mapping (the single source of truth
shared by ``Observatory.get_async`` and ``put_async``)."""
import unittest

from ocaboxapi.exceptions import (
    OcaboxError, OcaboxServerError, OcaboxAccessDenied, OcaboxDeviceError, CameraBusy,
)


class _FakeResponseError:
    """Stand-in for obcom ResponseError as seen client-side after rehydration."""

    def __init__(self, code, device_errno=None, severity='NORMAL',
                 component_name='TreeAlpacaObservatory', message='boom'):
        self.code = code
        self.message = message
        self.component_name = component_name
        self.severity = severity
        self.kwargs = {'device_errno': device_errno} if device_errno is not None else {}

    def __str__(self):
        return f'ResponseError code {self.code}'


class ExceptionHierarchyTest(unittest.TestCase):
    def test_all_derive_from_base(self):
        for cls in (OcaboxServerError, OcaboxAccessDenied, OcaboxDeviceError, CameraBusy):
            self.assertTrue(issubclass(cls, OcaboxError))

    def test_camerabusy_is_a_device_error_not_a_server_error(self):
        self.assertTrue(issubclass(CameraBusy, OcaboxDeviceError))
        self.assertFalse(issubclass(CameraBusy, OcaboxServerError))


class FromResponseMappingTest(unittest.TestCase):
    def test_code_to_type_mapping(self):
        cases = [
            (1004, None, OcaboxAccessDenied),
            (4008, 20072, CameraBusy),
            (4009, 1035, OcaboxDeviceError),
            (2002, None, OcaboxServerError),   # TIC value-build failure
            (3001, None, OcaboxServerError),   # tree structure
            (None, None, OcaboxServerError),   # unmapped fallback
        ]
        for code, errno, expected in cases:
            exc = OcaboxError.from_response('PUT', 'tel.mount.slew',
                                            _FakeResponseError(code, device_errno=errno))
            self.assertIs(type(exc), expected, msg=f'code={code}')
            self.assertIsInstance(exc, OcaboxError)

    def test_metadata_is_carried(self):
        exc = OcaboxError.from_response(
            'PUT', 'tel.mount.slewtocoordinatesasync',
            _FakeResponseError(4009, device_errno=1035, component_name='TreeAlpacaObservatory',
                               message='Telescope is not ready, please clear Error'))
        self.assertEqual(exc.code, 4009)
        self.assertEqual(exc.device_errno, 1035)
        self.assertEqual(exc.component_name, 'TreeAlpacaObservatory')
        self.assertEqual(exc.severity, 'NORMAL')
        self.assertEqual(exc.operation, 'PUT')
        self.assertEqual(exc.address, 'tel.mount.slewtocoordinatesasync')

    def test_none_error_does_not_crash(self):
        """status=False with error=None must still produce a typed exception."""
        exc = OcaboxError.from_response('GET', 'a.b', None)
        self.assertIs(type(exc), OcaboxServerError)
        self.assertIsNone(exc.code)
        self.assertIsNone(exc.device_errno)


if __name__ == '__main__':
    unittest.main()
