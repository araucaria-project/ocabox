"""Mirror-cell (M1 active collimation) client API.

Getters/subscriptions map 1:1 onto the server-side mirror-cell attribute
names (the ocabox-server ``mirrorcell`` interface, ≥ 2.4.0): the aggregates plus the
per-motor scalars ``motor<N>{position,status,statustext}``. The wire contract
is the *param_name* passed to ``aget_value``/``subscribe`` and the PUT
parameter names — these tests pin them so a rename on either side fails
loudly here instead of 400-ing against production.

⚠️ The movement/stop paths have never been commanded on real hardware
(supervised test pending) — these tests cover the wire contract only.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock

from ocaboxapi import Observatory


def _make_mirrorcell():
    observatory = Observatory(client_name='test-mirrorcell')
    cell = observatory.get_telescope('jk15').get_mirrorcell()
    cell.aget_value = AsyncMock()
    cell.aput_value = AsyncMock()
    cell.subscribe = AsyncMock()
    return cell


class MirrorCellClientApiTest(unittest.IsolatedAsyncioTestCase):

    async def test_getters_use_server_attribute_names(self):
        cell = _make_mirrorcell()
        for method, param in [('aget_available', 'available'),
                              ('aget_mirrorcellstatus', 'mirrorcellstatus'),
                              ('aget_positions', 'positions'),
                              ('aget_motorstatuses', 'motorstatuses'),
                              ('aget_motorstatustexts', 'motorstatustexts'),
                              ('aget_atsetpoint', 'atsetpoint'),
                              ('aget_moving', 'moving')]:
            with self.subTest(method=method):
                cell.aget_value.reset_mock()
                await getattr(cell, method)()
                cell.aget_value.assert_awaited_once_with(param, time_of_data_tolerance=None)

    async def test_per_motor_getters_use_server_attribute_names(self):
        cell = _make_mirrorcell()
        for method, field in [('aget_motor_position', 'position'),
                              ('aget_motor_status', 'status'),
                              ('aget_motor_statustext', 'statustext')]:
            for index in range(cell.MOTOR_COUNT):
                with self.subTest(method=method, index=index):
                    cell.aget_value.reset_mock()
                    await getattr(cell, method)(index)
                    cell.aget_value.assert_awaited_once_with(
                        f'motor{index}{field}', time_of_data_tolerance=None)

    async def test_getters_forward_freshness_tolerance(self):
        """TIC's cache default is 60 s — movement polling must be able to demand fresh data."""
        cell = _make_mirrorcell()
        await cell.aget_moving(time_of_data_tolerance=0.4)
        cell.aget_value.assert_awaited_once_with('moving', time_of_data_tolerance=0.4)
        cell.aget_value.reset_mock()
        await cell.aget_motor_position(1, time_of_data_tolerance=0.4)
        cell.aget_value.assert_awaited_once_with('motor1position', time_of_data_tolerance=0.4)

    async def test_subscriptions_use_server_attribute_names(self):
        cell = _make_mirrorcell()
        callback = MagicMock()
        for method, param in [('asubscribe_available', 'available'),
                              ('asubscribe_mirrorcellstatus', 'mirrorcellstatus'),
                              ('asubscribe_positions', 'positions'),
                              ('asubscribe_motorstatuses', 'motorstatuses'),
                              ('asubscribe_motorstatustexts', 'motorstatustexts'),
                              ('asubscribe_atsetpoint', 'atsetpoint'),
                              ('asubscribe_moving', 'moving')]:
            with self.subTest(method=method):
                cell.subscribe.reset_mock()
                await getattr(cell, method)(callback=callback)
                cell.subscribe.assert_awaited_once_with(
                    param, callback=callback, time_of_data_tolerance=None)

    async def test_per_motor_subscriptions_use_server_attribute_names(self):
        cell = _make_mirrorcell()
        callback = MagicMock()
        await cell.asubscribe_motor_position(2, callback=callback)
        cell.subscribe.assert_awaited_once_with(
            'motor2position', callback=callback, time_of_data_tolerance=None)

    async def test_bad_motor_index_is_client_side_valueerror(self):
        """motor3/… do not exist in the server address space — fail before the wire."""
        cell = _make_mirrorcell()
        for bad in (-1, 3, 99, True, 1.5, '1'):
            with self.subTest(index=bad):
                with self.assertRaises(ValueError):
                    await cell.aget_motor_position(bad)
        cell.aget_value.assert_not_awaited()

    async def test_commands_send_server_parameter_names(self):
        cell = _make_mirrorcell()
        await cell.amove_all_motors_to([1e-06, -2e-06, 3e-06])
        cell.aput_value.assert_awaited_once_with(
            'moveallmotorsto', Positions=[1e-06, -2e-06, 3e-06])
        cell.aput_value.reset_mock()
        await cell.amove_all_motors_offset([5e-06, 0.0, -5e-06])
        cell.aput_value.assert_awaited_once_with(
            'moveallmotorsoffset', Offsets=[5e-06, 0.0, -5e-06])
        cell.aput_value.reset_mock()
        await cell.amove_one_motor_offset(2, -5e-06)
        cell.aput_value.assert_awaited_once_with(
            'moveonemotoroffset', Index=2, Offset=-5e-06)
        cell.aput_value.reset_mock()
        await cell.astop_one_motor(1)
        cell.aput_value.assert_awaited_once_with('stoponemotor', Index=1)
        cell.aput_value.reset_mock()
        await cell.astop_all_motors()
        cell.aput_value.assert_awaited_once_with('stopallmotors')

    async def test_getters_return_server_value(self):
        cell = _make_mirrorcell()
        positions = [4.6999998092651369e-06, -1.4e-05, 1.2199999809265136e-05]
        cell.aget_value.return_value = positions
        self.assertEqual(await cell.aget_positions(), positions)

    def test_registered_on_telescope(self):
        observatory = Observatory(client_name='test-mirrorcell')
        telescope = observatory.get_telescope('jk15')
        cell = telescope.get_mirrorcell()
        self.assertIs(telescope.get_mirrorcell(), cell)  # cached, one instance per id
        self.assertEqual(cell.my_address(), telescope.tel_addr + '.mirrorcell')


if __name__ == '__main__':
    unittest.main()
