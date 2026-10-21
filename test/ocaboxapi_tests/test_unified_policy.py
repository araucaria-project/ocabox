"""Unified read policy (Staleness Contract phase 3, ocabox#281).

`Observatory(policy=…)` drives both axes: subscriptions inherit it as their
ErrorPolicy (including the wire-declared value_policy) and GET / sync
property reads enforce its value axis locally.
"""
import time
import unittest
from unittest.mock import AsyncMock

from obcom.comunication.error_policy import ErrorPolicy, ValuePolicy
from obcom.data_colection.value_call import ValueRequest

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
        # T1=0.1 → refresh due and failing; the default T2 (floored) covers age 0.15
        self.assertIs(await tertiary.aget_value('moving', time_of_data_tolerance=0.1), True)

    async def test_failed_refresh_past_max_age_raises(self):
        tertiary = _tertiary(policy='interactive')
        _cache_stale(tertiary, 'moving', True,
                     age=ValueRequest.default_max_age(0.1) + 0.5)
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

    def test_live_subscription_with_fresh_contact_vouches_for_any_policy(self):
        """A stationary value never moves its change-stamp; a live query with
        healthy contact vouches for it regardless of declared value_policy."""
        from types import SimpleNamespace
        from obcom.comunication.error_policy import ErrorPolicy as EP
        for policy in (EP.SERVICE, EP.INTERACTIVE, EP.DISPLAY):
            observatory = Observatory(client_name='t', policy='interactive',
                                      time_of_data_tolerance=0.5)
            tertiary = observatory.get_telescope('jk15').get_tertiary()
            _cache_stale(tertiary, 'moving', True)
            live = SimpleNamespace(is_stopped=lambda: False,
                                   is_contact_fresh=lambda max_age=None: True,
                                   _error_policy=policy)
            tertiary.subscribed.append(tertiary.CQHolder(cq=live, id='moving'))
            try:
                self.assertIs(tertiary.moving, True, policy)
            finally:
                tertiary.subscribed.clear()

    def test_lost_contact_does_not_veto_a_fresh_local_refresh(self):
        """The subscription is a witness, not a veto: a value the client just
        refreshed itself is fresh even if its subscription lost contact."""
        from types import SimpleNamespace
        from obcom.comunication.error_policy import ErrorPolicy as EP
        lost = SimpleNamespace(is_stopped=lambda: False,
                               is_contact_fresh=lambda max_age=None: False,
                               _error_policy=EP.INTERACTIVE)
        observatory = Observatory(client_name='t', policy='interactive',
                                  time_of_data_tolerance=0.5)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True, age=0.0)
        tertiary.subscribed.append(tertiary.CQHolder(cq=lost, id='moving'))
        try:
            self.assertIs(tertiary.moving, True)
        finally:
            tertiary.subscribed.clear()

    def test_lost_contact_and_old_stamp_applies_policy(self):
        from types import SimpleNamespace
        from obcom.comunication.error_policy import ErrorPolicy as EP
        lost = SimpleNamespace(is_stopped=lambda: False,
                               is_contact_fresh=lambda max_age=None: False,
                               _error_policy=EP.SERVICE)
        for policy, expect in (('interactive', OcaboxStaleValueError), ('display', None)):
            observatory = Observatory(client_name='t', policy=policy,
                                      time_of_data_tolerance=0.5)
            tertiary = observatory.get_telescope('jk15').get_tertiary()
            _cache_stale(tertiary, 'moving', True)  # stamp far past T2
            tertiary.subscribed.append(tertiary.CQHolder(cq=lost, id='moving'))
            try:
                if expect is None:
                    self.assertIsNone(tertiary.moving)
                else:
                    with self.assertRaises(expect):
                        _ = tertiary.moving
            finally:
                tertiary.subscribed.clear()

    def test_stopped_subscription_does_not_veto_a_fresh_local_refresh(self):
        from types import SimpleNamespace
        from obcom.comunication.error_policy import ErrorPolicy as EP
        dead = SimpleNamespace(is_stopped=lambda: True,
                               is_contact_fresh=lambda max_age=None: True,
                               _error_policy=EP.DISPLAY)
        observatory = Observatory(client_name='t', policy='interactive',
                                  time_of_data_tolerance=0.5)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True, age=0.0)
        tertiary.subscribed.append(tertiary.CQHolder(cq=dead, id='moving'))
        try:
            self.assertIs(tertiary.moving, True)
        finally:
            tertiary.subscribed.clear()

    def test_stopped_subscription_does_not_vouch(self):
        from types import SimpleNamespace
        from obcom.comunication.error_policy import ErrorPolicy as EP
        observatory = Observatory(client_name='t', policy='interactive',
                                  time_of_data_tolerance=0.5)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True)  # stamp far past T2
        dead = SimpleNamespace(is_stopped=lambda: True,
                               is_contact_fresh=lambda max_age=None: True,
                               _error_policy=EP.DISPLAY)
        tertiary.subscribed.append(tertiary.CQHolder(cq=dead, id='moving'))
        try:
            with self.assertRaises(OcaboxStaleValueError):
                _ = tertiary.moving
        finally:
            tertiary.subscribed.clear()

    def _raise_message(self, cq):
        observatory = Observatory(client_name='t', policy='interactive',
                                  time_of_data_tolerance=0.5)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True, age=1000.0)
        if cq is not None:
            tertiary.subscribed.append(tertiary.CQHolder(cq=cq, id='moving'))
        try:
            with self.assertRaises(OcaboxStaleValueError) as ctx:
                _ = tertiary.moving
        finally:
            tertiary.subscribed.clear()
        return str(ctx.exception)

    def test_stale_message_names_missing_subscription(self):
        message = self._raise_message(None)
        self.assertIn('not subscribed', message)
        self.assertIn('aget_moving()', message)
        self.assertNotIn('stopped', message)

    def test_stale_message_names_stopped_subscription(self):
        from types import SimpleNamespace
        from obcom.comunication.error_policy import ErrorPolicy as EP
        dead = SimpleNamespace(is_stopped=lambda: True,
                               is_contact_fresh=lambda max_age=None: True,
                               _error_policy=EP.DISPLAY)
        message = self._raise_message(dead)
        self.assertIn('subscription stopped', message)
        self.assertIn('last change 1000.', message)
        self.assertNotIn('aget_moving()', message)

    def test_stale_message_names_lost_contact_with_ages(self):
        from types import SimpleNamespace
        from obcom.comunication.error_policy import ErrorPolicy as EP
        lost = SimpleNamespace(is_stopped=lambda: False,
                               is_contact_fresh=lambda max_age=None: False,
                               last_healthy_contact_age=42.0, truth_bound=30.0,
                               _error_policy=EP.DISPLAY)
        message = self._raise_message(lost)
        self.assertIn('lost contact 42.0s ago', message)
        self.assertIn('bound 30.0s', message)
        self.assertNotIn('aget_moving()', message)

    def test_old_obcom_without_contact_clock_keeps_historical_exemption(self):
        from types import SimpleNamespace
        from obcom.comunication.error_policy import ErrorPolicy as EP
        observatory = Observatory(client_name='t', policy='interactive',
                                  time_of_data_tolerance=0.5)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True)
        legacy = SimpleNamespace(is_stopped=lambda: False, _error_policy=EP.INTERACTIVE)
        tertiary.subscribed.append(tertiary.CQHolder(cq=legacy, id='moving'))
        try:
            self.assertIs(tertiary.moving, True)
        finally:
            tertiary.subscribed.clear()

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


class ValueTagsTest(unittest.IsolatedAsyncioTestCase):

    def test_value_tags_default_empty(self):
        observatory = Observatory(client_name='t', policy='display')
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        self.assertEqual(tertiary.value_tags('moving'), {})

    async def test_subscription_callback_stores_rich_none_tags(self):
        """The sub_callback path must copy a rich None's tags so a widget can
        render reason/last_good while the param value is None."""
        from types import SimpleNamespace
        observatory = Observatory(client_name='t', policy='display')
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        captured = {}

        async def fake_subscribe_async(address, **kwargs):
            captured.update(kwargs)
            return object()

        observatory.subscribe_async = fake_subscribe_async
        await tertiary.subscribe('moving', callback=None)
        sub_callback = captured['callback_method']
        tags = {'reason': 4005, 'last_good': True, 'last_good_ts': 123.0, 'from_cf': True}
        resp = SimpleNamespace(status=True, address='jk15.tertiary.moving',
                               value=SimpleNamespace(v=None, ts=200.0, tags=tags))
        sub_callback([resp])
        self.assertEqual(tertiary.value_tags('moving'), tags)
        self.assertIsNone(getattr(tertiary, '_moving_value'))
        tertiary.subscribed.clear()  # __del__ must not unsubscribe the stub


class TimestampStampTest(unittest.IsolatedAsyncioTestCase):

    async def test_unchanged_successful_refresh_stamps_the_clock(self):
        """The param watcher fires only on change — a successful pull of the
        SAME value must still refresh the timestamp, or properties raise
        OcaboxStaleValueError right after a good read."""
        observatory = Observatory(client_name='t', policy='interactive',
                                  time_of_data_tolerance=0.5)
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        _cache_stale(tertiary, 'moving', True, age=1000.0)
        tertiary._get_async = AsyncMock(return_value=True)  # same value as cached
        got = await tertiary.aget_value('moving', time_of_data_tolerance=0.1)
        self.assertIs(got, True)
        age = time.time() - getattr(tertiary, '_moving_timestamp')
        self.assertLess(age, 1.0, 'timestamp not stamped on unchanged successful refresh')
        self.assertIs(tertiary.moving, True)  # sync property must NOT raise now


class EffectiveMaxAgeTest(unittest.TestCase):

    def test_per_call_t2_clamped_to_t1(self):
        observatory = Observatory(client_name='t', policy='interactive')
        tertiary = observatory.get_telescope('jk15').get_tertiary()
        self.assertEqual(tertiary._effective_max_age(60.0, 5.0), 60.0,
                         'T2 below T1 would open an unchecked (T2, T1) age window')
        self.assertEqual(tertiary._effective_max_age(0.1, 5.0), 5.0)


class ObservatoryT2InheritanceTest(unittest.IsolatedAsyncioTestCase):

    async def test_explicit_observatory_t2_is_inherited(self):
        observatory = Observatory(client_name='t', policy='display', max_data_age=45.0)
        captured = {}

        async def fake(address, **kwargs):
            captured.update(kwargs)
            return object()

        class FakeClient:
            subscribe_with_callback = staticmethod(fake)

        observatory._client = FakeClient()
        await observatory.subscribe_async('jk15.tertiary.moving')
        self.assertEqual(captured['max_data_age'], 45.0)

    async def test_derived_default_t2_is_not_inherited(self):
        observatory = Observatory(client_name='t', policy='display')
        captured = {}

        async def fake(address, **kwargs):
            captured.update(kwargs)
            return object()

        class FakeClient:
            subscribe_with_callback = staticmethod(fake)

        observatory._client = FakeClient()
        await observatory.subscribe_async('jk15.tertiary.moving')
        self.assertIsNone(captured['max_data_age'],
                          'the 2*T1 property-read default must not override per-subscription defaults')


class ObservatoryT1Test(unittest.IsolatedAsyncioTestCase):
    """One T1: without a per-call tolerance or a client-config key, the wire gets the observatory's
    own T1 (never ``None``, which obcom once read as 60 s while the local cache refreshed at 0.5 s)."""

    @staticmethod
    def _fake_client(captured):
        from types import SimpleNamespace

        async def fake(address, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(status=True, error=None, value=SimpleNamespace(v=1, ts=0.0, tags={}))

        class FakeClient:
            subscribe_with_callback = staticmethod(fake)
            get_async = staticmethod(fake)
        return FakeClient()

    async def test_default_t1_rides_on_the_wire(self):
        from obcom.comunication import timing
        observatory = Observatory(client_name='t', policy='display')
        captured = {}
        observatory._client = self._fake_client(captured)
        await observatory.subscribe_async('jk15.tertiary.moving')
        self.assertEqual(captured['time_of_data_tolerance'], timing.DEFAULT_REFRESH_AFTER)
        self.assertEqual(observatory.time_of_data_tolerance, timing.DEFAULT_REFRESH_AFTER)

    async def test_observatory_t1_rides_on_the_wire_for_subscribe_and_get(self):
        observatory = Observatory(client_name='t', policy='interactive', time_of_data_tolerance=2.0)
        captured = {}
        observatory._client = self._fake_client(captured)
        await observatory.subscribe_async('jk15.tertiary.moving')
        self.assertEqual(captured['time_of_data_tolerance'], 2.0)
        captured.clear()
        await observatory.get_async('jk15.tertiary.moving')
        self.assertEqual(captured['time_of_data_tolerance'], 2.0)

    async def test_client_config_still_wins(self):
        observatory = Observatory(client_name='t', policy='interactive', time_of_data_tolerance=2.0)
        observatory._get_client_config = lambda: {'time_of_data_tolerance': 0.25}
        captured = {}
        observatory._client = self._fake_client(captured)
        await observatory.subscribe_async('jk15.tertiary.moving')
        self.assertEqual(captured['time_of_data_tolerance'], 0.25)


if __name__ == '__main__':
    unittest.main()
