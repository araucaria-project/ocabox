"""Optics client API — the optics service as TIC serves it (ocabox-server ``TreeNatsService``).

The wire contract is the address: ``<tel>.optics.<detector>.<item>`` and ``<tel>.optics.self.<item>``
(subjects ``status.optics.<tel>.<detector>.<item>`` / ``rpc.optics.<tel>.<detector>.setpath`` on the
service side). These tests pin it, and the parameter name of ``setpath``.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock

from ocaboxapi import Observatory
from ocaboxapi.optics import OpticalDetector, OpticsState


def _telescope():
    return Observatory(client_name='test-optics').get_telescope('jk15')


def _mocked(component):
    component.aget_value = AsyncMock()
    component.aput_value = AsyncMock(return_value={'accepted': True, 'moves': {'tertiary': 'andor'}})
    component.subscribe = AsyncMock()
    return component


class OpticsClientApiTest(unittest.IsolatedAsyncioTestCase):

    def test_addresses(self):
        tel = _telescope()
        self.assertEqual(tel.get_optical_detector('camera').my_address(), 'jk15.optics.camera')
        self.assertEqual(tel.get_optics().my_address(), 'jk15.optics.self')

    def test_components_are_cached_per_detector(self):
        tel = _telescope()
        self.assertIs(tel.get_optical_detector('camera'), tel.get_optical_detector('camera'))
        self.assertIsNot(tel.get_optical_detector('camera'), tel.get_optical_detector('beso'))
        self.assertIs(tel.get_optics(), tel.get_optics())
        self.assertIsInstance(tel.get_optics(), OpticsState)

    async def test_detector_reads_and_subscriptions(self):
        detector = _mocked(_telescope().get_optical_detector('camera'))
        callback = MagicMock()
        for item in ('sees', 'functions'):
            with self.subTest(item=item):
                await getattr(detector, f'aget_{item}')(time_of_data_tolerance=0.5)
                detector.aget_value.assert_awaited_with(item, time_of_data_tolerance=0.5)
                await getattr(detector, f'asubscribe_{item}')(callback=callback)
                detector.subscribe.assert_awaited_with(item, callback=callback, time_of_data_tolerance=None)

    async def test_setpath_sends_the_function(self):
        detector = _mocked(_telescope().get_optical_detector('camera'))
        answer = await detector.aput_setpath('object')
        detector.aput_value.assert_awaited_once_with('setpath', function='object')
        self.assertEqual(answer['moves'], {'tertiary': 'andor'})

    async def test_state_reads_and_subscriptions(self):
        state = _mocked(_telescope().get_optics())
        callback = MagicMock()
        for item in ('selectors', 'busy', 'operation'):
            with self.subTest(item=item):
                await getattr(state, f'aget_{item}')()
                state.aget_value.assert_awaited_with(item, time_of_data_tolerance=None)
                await getattr(state, f'asubscribe_{item}')(callback=callback, time_of_data_tolerance=1.0)
                state.subscribe.assert_awaited_with(item, callback=callback, time_of_data_tolerance=1.0)

    def test_setpath_is_a_human_command(self):
        """The permission is the human's, checked by TIC's blocker — no service bypass by default."""
        self.assertFalse(_telescope().get_optical_detector('camera').request_special_permission)

    def test_cleanup_covers_optics(self):
        tel = _telescope()
        detector, state = tel.get_optical_detector('camera'), tel.get_optics()
        for component in (detector, state):
            component.unsubscribe_all = MagicMock()
            component.unwatch_all = MagicMock()
            component.reset_params_values = MagicMock()
        tel.unsubscribe_all_component()
        tel.unwatch_all_component()
        for component in (detector, state):
            component.unsubscribe_all.assert_called_once()
            component.unwatch_all.assert_called_once()


class TelescopeCleanupTest(unittest.TestCase):

    def test_unwatch_all_component_unwatches_m3_and_keeps_its_subscriptions(self):
        """unwatch_all_component removes local watchers only; it used to unsubscribe M3 instead."""
        tertiary = _telescope().get_tertiary()
        tel = tertiary.telescope
        tertiary.unsubscribe_all = MagicMock()
        tertiary.unwatch_all = MagicMock()
        tertiary.reset_params_values = MagicMock()
        tel.unwatch_all_component()
        tertiary.unwatch_all.assert_called_once()
        tertiary.unsubscribe_all.assert_not_called()


if __name__ == '__main__':
    unittest.main()
