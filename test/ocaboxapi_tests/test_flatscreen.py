"""Flat screen client API.

Getters, subscriptions and commands map 1:1 onto the server-side flat screen attribute names (ocabox-server
``FlatScreen``): ``lamp``, ``commanded``, ``lampon``, ``lampoff``. These tests pin that wire contract, the
``flatscreen`` kind of the configuration, and the deprecated mount lamp methods.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock

from ocaboxapi import FlatScreen, Observatory


def _make_flatscreen():
    observatory = Observatory(client_name='test-flatscreen')
    flatscreen = observatory.get_telescope('jk15').get_flatscreen()
    flatscreen.aget_value = AsyncMock()
    flatscreen.aput_value = AsyncMock()
    flatscreen.subscribe = AsyncMock()
    return flatscreen


class FlatScreenClientApiTest(unittest.IsolatedAsyncioTestCase):

    async def test_getters_use_server_attribute_names(self):
        flatscreen = _make_flatscreen()
        for method, param in [('aget_lamp', 'lamp'), ('aget_commanded', 'commanded')]:
            with self.subTest(method=method):
                flatscreen.aget_value.reset_mock()
                await getattr(flatscreen, method)(time_of_data_tolerance=2.0)
                flatscreen.aget_value.assert_awaited_once_with(param, time_of_data_tolerance=2.0)

    async def test_subscriptions_use_server_attribute_names(self):
        flatscreen = _make_flatscreen()
        callback = MagicMock()
        for method, param in [('asubscribe_lamp', 'lamp'), ('asubscribe_commanded', 'commanded')]:
            with self.subTest(method=method):
                flatscreen.subscribe.reset_mock()
                await getattr(flatscreen, method)(callback=callback)
                flatscreen.subscribe.assert_awaited_once_with(param, callback=callback, time_of_data_tolerance=None)

    async def test_commands_use_server_attribute_names(self):
        flatscreen = _make_flatscreen()
        await flatscreen.aput_lampon()
        flatscreen.aput_value.assert_awaited_once_with('lampon')
        flatscreen.aput_value.reset_mock()
        await flatscreen.aput_lampoff()
        flatscreen.aput_value.assert_awaited_once_with('lampoff')

    async def test_commanded_returns_the_server_record(self):
        flatscreen = _make_flatscreen()
        flatscreen.aget_value.return_value = {'lamp': 'on', 'at': '2026-11-06T15:41:24+00:00'}
        self.assertEqual((await flatscreen.aget_commanded())['lamp'], 'on')


class FlatScreenTelescopeTest(unittest.TestCase):

    def test_one_flatscreen_per_id(self):
        telescope = Observatory(client_name='test-flatscreen').get_telescope('jk15')
        self.assertIs(telescope.get_flatscreen(), telescope.get_flatscreen('flatscreen'))
        self.assertIsInstance(telescope.get_flatscreen(), FlatScreen)

    def test_flatscreen_kind_has_the_flatscreen_client(self):
        telescope = Observatory(client_name='test-flatscreen').get_telescope('jk15')
        telescope.component_config = MagicMock(return_value={'kind': 'flatscreen', 'driver': 'asa-autoslew'})
        self.assertIsInstance(telescope.get_component('flatscreen'), FlatScreen)


class MountDomeLampDeprecationTest(unittest.IsolatedAsyncioTestCase):

    async def test_mount_lamp_methods_warn_and_still_switch(self):
        mount = Observatory(client_name='test-flatscreen').get_telescope('jk15').get_mount()
        mount.aput_value = AsyncMock()
        for method, attribute in [('aput_domelamp_on', 'domeflatlampon'), ('aput_domelamp_off', 'domeflatlampoff')]:
            with self.subTest(method=method), self.assertWarns(DeprecationWarning):
                await getattr(mount, method)()
            mount.aput_value.assert_awaited_with(attribute)


if __name__ == '__main__':
    unittest.main()
