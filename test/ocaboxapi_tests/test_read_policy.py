"""Per-observatory read-error policy (``OnReadError``).

``Component.aget_value`` historically caught every refresh failure and served
the stale cached value with a refreshed timestamp — so the error model built
through the whole stack (server severity codes → ``OcaboxError`` hierarchy)
never reached one-shot callers, and stale positions could masquerade as live
telemetry. The policy makes the behaviour an explicit, per-client choice.
Since 2.7 ``OnReadError`` is a deprecated alias of the unified policy's
value axis and the implicit default is RAISE (the announced flip).
"""
import unittest
from unittest.mock import AsyncMock

from ocaboxapi import Observatory, OnReadError
from ocaboxapi.exceptions import OcaboxDeviceError


def _tertiary(**observatory_kwargs):
    observatory = Observatory(client_name='test-read-policy', **observatory_kwargs)
    tertiary = observatory.get_telescope('jk15').get_tertiary()
    tertiary._get_async = AsyncMock(
        side_effect=OcaboxDeviceError('controller reports ErrorRaised',
                                      code=4009, device_errno=5, operation='GET'))
    return tertiary


def _cache_stale(component, param_name, value):
    """Plant a cached value that is stale — writing the value fires the param
    watcher which stamps it fresh, so the timestamp must be reset afterwards."""
    setattr(component, f'_{param_name}_value', value)
    setattr(component, f'_{param_name}_timestamp', 0.0)


class OnReadErrorPolicyTest(unittest.IsolatedAsyncioTestCase):

    async def test_implicit_default_flipped_to_raise(self):
        """The flip announced through the 2.6 line: no policy → RAISE, loudly."""
        with self.assertLogs('observatory', level='WARNING') as logs:
            observatory = Observatory(client_name='test-read-policy')
        self.assertIn('RAISE', '\n'.join(logs.output))
        self.assertIs(observatory.on_read_error, OnReadError.RAISE)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        tertiary._get_async = AsyncMock(side_effect=OcaboxDeviceError('fault', code=4009))
        _cache_stale(tertiary, 'moving', True)
        with self.assertRaises(OcaboxDeviceError):
            await tertiary.aget_moving(time_of_data_tolerance=1.0)

    async def test_explicit_policy_is_silent(self):
        with self.assertNoLogs('observatory', level='WARNING'):
            Observatory(client_name='test-read-policy', on_read_error=OnReadError.RAISE)

    async def test_raise_policy_propagates(self):
        """The error model reaches the caller — the whole point of the policy."""
        tertiary = _tertiary(on_read_error=OnReadError.RAISE)
        with self.assertRaises(OcaboxDeviceError):
            await tertiary.aget_moving(time_of_data_tolerance=1.0)

    async def test_stale_policy_serves_last_value(self):
        tertiary = _tertiary(on_read_error=OnReadError.STALE)
        _cache_stale(tertiary, 'moving', True)
        self.assertIs(await tertiary.aget_moving(time_of_data_tolerance=1.0), True)

    async def test_stale_policy_first_read_returns_none(self):
        """No cached value yet — the historical behaviour, kept bit-for-bit."""
        tertiary = _tertiary(on_read_error=OnReadError.STALE)
        self.assertIsNone(await tertiary.aget_moving(time_of_data_tolerance=1.0))

    async def test_none_policy_returns_none_despite_cache(self):
        tertiary = _tertiary(on_read_error=OnReadError.NONE)
        _cache_stale(tertiary, 'moving', True)
        self.assertIsNone(await tertiary.aget_moving(time_of_data_tolerance=1.0))

    async def test_string_policy_accepted(self):
        tertiary = _tertiary(on_read_error='stale')
        _cache_stale(tertiary, 'moving', True)
        self.assertIs(await tertiary.aget_moving(time_of_data_tolerance=1.0), True)

    async def test_invalid_policy_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            Observatory(client_name='test-read-policy', on_read_error='explode')

    async def test_policy_is_read_only(self):
        """Set-once invariant enforced — a later (possibly unvalidated string)
        assignment must fail loudly, not silently degrade to STALE."""
        observatory = Observatory(client_name='test-read-policy',
                                  on_read_error=OnReadError.RAISE)
        with self.assertRaises(AttributeError):
            observatory.on_read_error = 'stale'
        self.assertIs(observatory.on_read_error, OnReadError.RAISE)

    async def test_successful_read_ignores_policy(self):
        tertiary = _tertiary(on_read_error=OnReadError.NONE)
        tertiary._get_async = AsyncMock(return_value=True)
        self.assertIs(await tertiary.aget_moving(time_of_data_tolerance=1.0), True)


if __name__ == '__main__':
    unittest.main()
