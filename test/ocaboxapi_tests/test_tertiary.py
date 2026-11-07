"""Tertiary (M3) client API.

Getters/subscriptions map 1:1 onto the server-side tertiary attribute names
(ocabox-server ``tertiary`` interface): ``nasmythport``, ``tertiarystatus`` and its
decomposed fields. The wire contract is the *param_name* passed to
``aget_value``/``subscribe`` — these tests pin it so a rename on either side
fails loudly here instead of 400-ing against production.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock

from ocaboxapi import Observatory


def _make_tertiary():
    observatory = Observatory(client_name='test-tertiary')
    tertiary = observatory.get_telescope('jk15').get_tertiary()
    tertiary.aget_value = AsyncMock()
    tertiary.aput_value = AsyncMock()
    tertiary.subscribe = AsyncMock()
    return tertiary


class TertiaryClientApiTest(unittest.IsolatedAsyncioTestCase):

    async def test_getters_use_server_attribute_names(self):
        tertiary = _make_tertiary()
        for method, param in [('aget_nasmythport', 'nasmythport'),
                              ('aget_tertiarystatus', 'tertiarystatus'),
                              ('aget_angle', 'angle'),
                              ('aget_moving', 'moving'),
                              ('aget_motoron', 'motoron'),
                              ('aget_portname', 'portname')]:
            with self.subTest(method=method):
                tertiary.aget_value.reset_mock()
                await getattr(tertiary, method)()
                tertiary.aget_value.assert_awaited_once_with(param, time_of_data_tolerance=None)

    async def test_getters_forward_freshness_tolerance(self):
        """TIC's cache default is 60 s — movement polling must be able to demand fresh data."""
        tertiary = _make_tertiary()
        await tertiary.aget_moving(time_of_data_tolerance=0.4)
        tertiary.aget_value.assert_awaited_once_with('moving', time_of_data_tolerance=0.4)

    async def test_subscriptions_use_server_attribute_names(self):
        tertiary = _make_tertiary()
        callback = MagicMock()
        for method, param in [('asubscribe_nasmythport', 'nasmythport'),
                              ('asubscribe_tertiarystatus', 'tertiarystatus'),
                              ('asubscribe_angle', 'angle'),
                              ('asubscribe_moving', 'moving'),
                              ('asubscribe_motoron', 'motoron'),
                              ('asubscribe_portname', 'portname')]:
            with self.subTest(method=method):
                tertiary.subscribe.reset_mock()
                await getattr(tertiary, method)(callback=callback)
                tertiary.subscribe.assert_awaited_once_with(
                    param, callback=callback, time_of_data_tolerance=None)

    async def test_selectnasmythport_sends_position(self):
        tertiary = _make_tertiary()
        await tertiary.aput_selectnasmythport(2)
        tertiary.aput_value.assert_awaited_once_with('selectnasmythport', Position=2)

    async def test_getters_return_server_value(self):
        tertiary = _make_tertiary()
        status = {"Moving": False, "MotorOn": True, "ErrorRaised": False,
                  "Angle": 134.785, "NasmythPort": 2, "PortName": "ADR10"}
        tertiary.aget_value.return_value = status
        self.assertEqual(await tertiary.aget_tertiarystatus(), status)


if __name__ == '__main__':
    unittest.main()
