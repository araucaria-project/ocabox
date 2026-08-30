"""Unified read policy (Staleness Contract phase 3, ocabox#281).

`Observatory(policy=…)` drives both axes: subscriptions inherit it as their
ErrorPolicy (including the wire-declared value_policy) and GET / sync
property reads enforce its value axis locally.
"""
import time
import unittest
from unittest.mock import AsyncMock

from obcom.comunication.error_policy import ErrorPolicy, ValuePolicy

from ocaboxapi import Observatory
from ocaboxapi.exceptions import OcaboxDeviceError, OcaboxStaleValueError


def _tertiary(**kw):
    observatory = Observatory(client_name='test-unified-policy', **kw)
    tertiary = observatory.get_telescope('jk15').get_tertiary()
    tertiary._get_async = AsyncMock(
        side_effect=OcaboxDeviceError('controller reports ErrorRaised', code=4009))
    return tertiary


def _cache_stale(component, param_name, value, age=1000.0):
    setattr(component, f'_{param_name}_value', value)
    setattr(component, f'_{param_name}_timestamp', time.time() - age)


class PolicyConstructionTest(unittest.TestCase):

    def test_presets_by_name(self):
        for name, preset in (('interactive', ErrorPolicy.INTERACTIVE),
                             ('service', ErrorPolicy.SERVICE),
                             ('display', ErrorPolicy.DISPLAY)):
            observatory = Observatory(client_name='t', policy=name)
            self.assertIs(observatory.policy, preset)

    def test_display_declares_none_locally_and_on_wire(self):
        observatory = Observatory(client_name='t', policy='display')
        self.assertIs(observatory.value_policy, ValuePolicy.NONE)
        self.assertIs(observatory.policy.value_policy, ValuePolicy.NONE)

    def test_undeclared_presets_enforce_raise_locally(self):
        observatory = Observatory(client_name='t', policy='interactive')
        self.assertIsNone(observatory.policy.value_policy)  # wire-inert
        self.assertIs(observatory.value_policy, ValuePolicy.RAISE)

    def test_policy_and_on_read_error_are_exclusive(self):
        with self.assertRaises(ValueError):
            Observatory(client_name='t', policy='display', on_read_error='stale')

    def test_unknown_preset_rejected(self):
        with self.assertRaises(ValueError):
            Observatory(client_name='t', policy='heroic')

    def test_legacy_on_read_error_maps_locally_but_stays_wire_inert(self):
        """STALE→LAST_GOOD locally; the wire policy must stay undeclared so a
        legacy client is safe against pre-2.5.2 servers."""
        with self.assertWarns(DeprecationWarning):
            observatory = Observatory(client_name='t', on_read_error='stale')
        self.assertIs(observatory.value_policy, ValuePolicy.LAST_GOOD)
        self.assertIsNone(observatory.policy.value_policy)


class AgetMaxAgeTest(unittest.IsolatedAsyncioTestCase):
    """T2 masking in aget: a failed refresh with a cached value younger than
    max_data_age serves the cache regardless of policy; past T2 the truth
    axis decides."""

    async def test_failed_refresh_inside_repair_window_serves_cache_even_for_raise(self):
        tertiary = _tertiary(policy='interactive')  # RAISE
        _cache_stale(tertiary, 'moving', True, age=0.15)
        # T1=0.1 → refresh due and failing; T2 default 2*T1=0.2 ≥ age 0.15
        self.assertIs(await tertiary.aget_value('moving', time_of_data_tolerance=0.1), True)

    async def test_failed_refresh_past_max_age_raises(self):
        tertiary = _tertiary(policy='interactive')
        _cache_stale(tertiary, 'moving', True, age=0.5)
        with self.assertRaises(OcaboxDeviceError):
            await tertiary.aget_value('moving', time_of_data_tolerance=0.1)

    async def test_per_call_max_data_age_overrides_default(self):
        tertiary = _tertiary(policy='interactive')
        _cache_stale(tertiary, 'moving', True, age=0.5)
        self.assertIs(await tertiary.aget_value('moving', time_of_data_tolerance=0.1,
                                                max_data_age=1.0), True)


class AgetValuePolicyTest(unittest.IsolatedAsyncioTestCase):

    async def test_per_call_override_beats_observatory_policy(self):
        tertiary = _tertiary(policy='interactive')  # RAISE
        _cache_stale(tertiary, 'moving', True)
        self.assertIsNone(await tertiary.aget_value(
            'moving', time_of_data_tolerance=1.0, value_policy='none'))
        self.assertIs(await tertiary.aget_value(
            'moving', time_of_data_tolerance=1.0, value_policy=ValuePolicy.LAST_GOOD), True)

    async def test_last_good_no_longer_cheats_the_timestamp(self):
        """Every read re-asks the server (its negative cache paces the I/O)."""
        tertiary = _tertiary(policy=ErrorPolicy.INTERACTIVE.with_overrides(
            value_policy=ValuePolicy.LAST_GOOD))
        _cache_stale(tertiary, 'moving', True)
        await tertiary.aget_value('moving', time_of_data_tolerance=1.0)
        await tertiary.aget_value('moving', time_of_data_tolerance=1.0)
        self.assertEqual(tertiary._get_async.await_count, 2)


class SyncPropertyAgeTest(unittest.TestCase):

    def test_stale_property_raises_for_raise_clients(self):
        observatory = Observatory(client_name='t', policy='interactive',
                                  time_of_data_tolerance=0.5)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True)
        with self.assertRaises(OcaboxStaleValueError):
            _ = tertiary.moving

    def test_fresh_property_is_served(self):
        observatory = Observatory(client_name='t', policy='interactive',
                                  time_of_data_tolerance=5.0)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True, age=0.0)
        self.assertIs(tertiary.moving, True)

    def test_stale_property_none_for_display_clients(self):
        observatory = Observatory(client_name='t', policy='display',
                                  time_of_data_tolerance=0.5)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True)
        self.assertIsNone(tertiary.moving)

    def test_stale_property_served_for_last_good_clients(self):
        with self.assertWarns(DeprecationWarning):
            observatory = Observatory(client_name='t', on_read_error='stale')
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True)
        self.assertIs(tertiary.moving, True)

    def test_subscribed_param_is_exempt_from_age_judgment(self):
        """A live subscription owns the contract — the pushed value is the
        contract-compliant view even when its change-ts is old."""
        observatory = Observatory(client_name='t', policy='interactive',
                                  time_of_data_tolerance=0.5)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True)
        tertiary.subscribed.append(tertiary.CQHolder(cq=None, id='moving'))
        try:
            self.assertIs(tertiary.moving, True)
        finally:
            tertiary.subscribed.clear()  # __del__ must not try to unsubscribe the stub


class ValueTagsTest(unittest.TestCase):

    def test_value_tags_default_empty(self):
        observatory = Observatory(client_name='t', policy='display')
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        self.assertEqual(tertiary.value_tags('moving'), {})


if __name__ == '__main__':
    unittest.main()
