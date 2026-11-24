"""Optics client API — the optics service as TIC serves it (ocabox-server ``TreeNatsService``).

The wire contract is the address: ``<tel>.optics.<detector>.<item>`` and ``<tel>.optics.self.<item>``
(subjects ``status.optics.<tel>.<detector>.<item>`` / ``rpc.optics.<tel>.<detector>.setpath`` on the
service side). These tests pin it, and the parameter name of ``setpath``.
"""
import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock

from obcom.data_colection.response_error import ResponseError
from obcom.data_colection.value import Value
from obcom.data_colection.value_call import ValueResponse
from ocaboxapi import Camera, Observatory
from ocaboxapi.optics import OpticalDetector, OpticsState


def _telescope():
    return Observatory(client_name='test-optics').get_telescope('jk15')


def _mocked(component):
    component.aget_value = AsyncMock()
    component.aput_value = AsyncMock(return_value={'accepted': True, 'moves': {'tertiary': 'andor'}})
    component.observatory.subscribe_async = AsyncMock(side_effect=lambda address, **kw: f'cq:{address}')
    component.observatory.unsubscribe = MagicMock()
    return component


def _answer(component, response: ValueResponse):
    """Run the last subscription's callback on ``response`` as the cycle query does: the sync one is
    called, the async one awaited (the caller awaits what this returns)."""
    kwargs = component.observatory.subscribe_async.await_args.kwargs
    if 'async_callback_method' in kwargs:
        return kwargs['async_callback_method']([response])
    kwargs['callback_method']([response])


def _delivered(component, value, tags=None):
    """What TIC delivers: ``value``, or the Staleness Contract's rich None when ``value`` is None."""
    address = component.observatory.subscribe_async.await_args.args[0]
    tags = tags if tags is not None else ({} if value is not None else {'reason': 2003})
    return _answer(component, ValueResponse(address, value=Value(value, time.time(), tags=tags)))


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
                cq = await getattr(detector, f'asubscribe_{item}')(callback, time_of_data_tolerance=0.5)
                address, kwargs = detector.observatory.subscribe_async.await_args.args[0], detector.observatory.subscribe_async.await_args.kwargs
                self.assertEqual((address, kwargs['time_of_data_tolerance'], kwargs['max_data_age']), (f'jk15.optics.camera.{item}', 0.5, None))
                self.assertEqual(cq, f'cq:jk15.optics.camera.{item}')
                self.assertEqual(detector.subscribed[-1].cq, cq)  # the component's own: unsubscribe_all ends it

    async def test_a_subscription_hands_over_the_value(self):
        detector = _mocked(_telescope().get_optical_detector('camera'))
        callback = MagicMock()
        await detector.asubscribe_sees(callback)
        _delivered(detector, [{'class': 'sky.science', 'terminal': 'sky', 'via': []}])
        self.assertEqual(callback.call_args.args[0].v, [{'class': 'sky.science', 'terminal': 'sky', 'via': []}])

    async def test_none_says_why(self):
        """A rich None keeps its reason and last good value: the panel can say why it went blank."""
        detector = _mocked(_telescope().get_optical_detector('camera'))
        callback = MagicMock()
        await detector.asubscribe_sees(callback)
        _delivered(detector, None, tags={'reason': 4005, 'last_good': [], 'last_good_ts': 1.0})
        value = callback.call_args.args[0]
        self.assertIsNone(value.v)
        self.assertEqual(value.tags, {'reason': 4005, 'last_good': [], 'last_good_ts': 1.0})

    async def test_an_error_answer_is_a_none_with_its_code(self):
        state = _mocked(_telescope().get_optics())
        callback = MagicMock()
        await state.asubscribe_selectors(callback)
        _delivered(state, {'dome': {'position': 'open'}})
        error = ResponseError(code=4002, message='TIC unreachable', component_name='jk15.optics.self')
        _answer(state, ValueResponse('jk15.optics.self.selectors', value=None, status=False, error=error))
        value = callback.call_args.args[0]
        self.assertIsNone(value.v)
        self.assertEqual(value.tags, {'reason': 4002, 'message': 'TIC unreachable'})
        self.assertEqual(state.selectors, {'dome': {'position': 'open'}})  # an error leaves the cache alone

    async def test_the_cache_follows_the_deliveries(self):
        """The subscription is the cache's freshness witness, so it feeds it: a sync read and
        ``value_tags`` agree with what the callback saw, not with an older ``aget``."""
        detector = _mocked(_telescope().get_optical_detector('camera'))
        detector.param.update(_sees_value=[{'class': 'dark', 'terminal': 'covercalibrator', 'via': []}])
        await detector.asubscribe_sees(MagicMock())
        _delivered(detector, [{'class': 'sky.science', 'terminal': 'sky', 'via': []}])
        self.assertEqual(detector.sees, [{'class': 'sky.science', 'terminal': 'sky', 'via': []}])
        _delivered(detector, None, tags={'reason': 2003})
        self.assertIsNone(detector.sees)
        self.assertEqual(detector.value_tags('sees'), {'reason': 2003})

    async def test_a_coroutine_callback_is_awaited_by_the_subscription(self):
        """Registered as the cycle query's async callback: awaited in delivery order inside its
        containment, never a task of our own that nobody awaits."""
        state = _mocked(_telescope().get_optics())
        received = []

        async def callback(value):
            await asyncio.sleep(0)
            received.append(value.v)

        await state.asubscribe_operation(callback)
        self.assertNotIn('callback_method', state.observatory.subscribe_async.await_args.kwargs)
        await _delivered(state, {'state': 'moving'})
        await _delivered(state, {'state': 'done'})
        self.assertEqual(received, [{'state': 'moving'}, {'state': 'done'}])

    async def test_setpath_sends_the_function(self):
        detector = _mocked(_telescope().get_optical_detector('camera'))
        answer = await detector.aput_setpath('object')
        detector.aput_value.assert_awaited_once_with('setpath', function='object')
        self.assertEqual(answer['moves'], {'tertiary': 'andor'})

    async def test_state_reads_and_subscriptions(self):
        state = _mocked(_telescope().get_optics())
        callback = MagicMock()
        for item in ('selectors', 'declared', 'busy', 'operation'):
            with self.subTest(item=item):
                await getattr(state, f'aget_{item}')()
                state.aget_value.assert_awaited_with(item, time_of_data_tolerance=None)
                await getattr(state, f'asubscribe_{item}')(callback, time_of_data_tolerance=1.0, max_data_age=4.0)
                kwargs = state.observatory.subscribe_async.await_args.kwargs
                self.assertEqual((state.observatory.subscribe_async.await_args.args[0], kwargs['max_data_age']), (f'jk15.optics.self.{item}', 4.0))

    async def test_confirm_reject_abort_name_the_operation(self):
        state = _mocked(_telescope().get_optics())
        await state.aput_confirm('a1b2c3')
        state.aput_value.assert_awaited_with('confirm', operation='a1b2c3')
        await state.aput_reject('a1b2c3', reason='people in the dome')
        state.aput_value.assert_awaited_with('reject', operation='a1b2c3', reason='people in the dome')
        await state.aput_abort('a1b2c3')
        state.aput_value.assert_awaited_with('abort', operation='a1b2c3')

    async def test_declare_sends_key_and_position(self):
        state = _mocked(_telescope().get_optics())
        await state.aput_declare('dome', 'open')
        state.aput_value.assert_awaited_once_with('declare', key='dome', position='open')
        await state.aput_declare('dome', None)
        state.aput_value.assert_awaited_with('declare', key='dome', position=None)

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


class InstrumentsTest(unittest.TestCase):
    """The telescope's detectors and the parts in front of them, from the published configuration."""

    def setUp(self):
        import copy
        from obcom.optics.conformance import JK15_WITH_MOUNT
        components = copy.deepcopy(JK15_WITH_MOUNT)
        components['camera']['flags'] = ['scientific']
        components['camera']['camera_model'] = 'Andor iKon-XL 231'
        components['camera'].update({
            'dir': 'jk15',
            'fits_prefix': 'c',
            'resolution': [4096, 4112],
            'fov': [23.5, 23.5],
            'dither_distance': 8.0,
            'operation_temperature': -70,
            'readout_modes': {'0': {'val_mhz': 1.0}},
        })
        self.tel = _telescope()
        self.tel.observatory.get_telescopes_configuration = lambda: {'jk15': {'observatory': {'components': components}}}
        self.components = components

    def test_every_detector_with_its_configuration(self):
        detectors = self.tel.get_detectors()
        self.assertEqual([d.name for d in detectors], list(self.tel.optical_graph.detectors))
        camera = self.tel.get_optical_detector('camera')
        self.assertEqual((camera.kind, camera.flags, camera.config['camera_model']), ('camera', ('scientific',), 'Andor iKon-XL 231'))
        self.assertIn('object', camera.function_names)
        self.assertEqual(self.tel.get_optical_detector('guider').function_names, ())
        self.assertEqual([d.name for d in self.tel.get_detectors(flag='scientific')], ['camera'])

    def test_detector_configuration_properties(self):
        detector = self.tel.get_optical_detector('camera')
        self.assertEqual(
            (detector.dir, detector.fits_prefix, detector.resolution, detector.fov,
             detector.dither_distance, detector.operation_temperature, detector.readout_modes),
            ('jk15', 'c', (4096, 4112), (23.5, 23.5), 8.0, -70, {'0': {'val_mhz': 1.0}})
        )
        self.assertEqual(self.tel.get_component('camera').dir, 'jk15')
        self.assertEqual(self.tel.get_camera().readout_modes, detector.readout_modes)

    def test_missing_detector_configuration_is_safe(self):
        detector = self.tel.get_optical_detector('guider')
        self.assertIsNone(detector.dir)
        self.assertIsNone(detector.fits_prefix)
        self.assertIsNone(detector.resolution)
        self.assertIsNone(detector.fov)
        self.assertIsNone(detector.dither_distance)
        self.assertIsNone(detector.operation_temperature)
        self.assertEqual(detector.readout_modes, {})

    def test_the_device_and_the_parts_in_front(self):
        camera = self.tel.get_optical_detector('camera')
        self.assertIsInstance(camera.device, Camera)
        self.assertEqual([(type(p).__name__, p.id) for p in camera.upstream('filterwheel')], [('FilterWheel', 'filterwheel')])
        self.assertEqual([(type(p).__name__, p.id) for p in camera.upstream('rotator')], [('Rotator', 'derotator')])
        self.assertEqual(self.tel.get_optical_detector('guider_beso').upstream('rotator'), [])
        self.assertEqual(self.tel.get_filterwheel('filterwheel').kind, 'filterwheel')  # every component knows its config

    def test_station_and_default(self):
        camera = self.tel.get_optical_detector('camera')
        self.assertEqual(sorted(d.name for d in camera.station), ['camera', 'guider'])
        self.assertIs(self.tel.default_detector({'tertiary': {'position': 'andor'}}), camera)
        self.assertEqual(self.tel.default_detector({'tertiary': {'position': 'beso'}}).name, 'guider_beso')
        self.assertIsNone(self.tel.default_detector({'tertiary': {'position': None}}))

    def test_unknown_names_and_kinds_without_a_device(self):
        with self.assertRaisesRegex(LookupError, 'no component'):
            self.tel.get_component('nosuch')
        with self.assertRaisesRegex(LookupError, "kind 'splitter' has no device"):
            self.tel.get_component('pickoff')

    def test_the_graph_follows_the_configuration(self):
        first = self.tel.optical_graph
        self.assertIs(self.tel.optical_graph, first)  # parsed once
        self.components['camera']['flags'] = []
        self.assertIsNot(self.tel.optical_graph, first)  # republished: parsed again
