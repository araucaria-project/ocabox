"""M1 mirror-cell FITS cards (M1-POS1..3 [µm], M1-ATSET) — ocabox#277.

Pins the two contracts of ``CameraExposure._m1_header_values``:
metres → µm conversion (the API stays in metres, scaling belongs to the
consumer), and graceful absence — a telescope without the subsystem, a
faulted motor or a communication problem yields empty cards (``''``), never
an exception that could fail or delay the exposure. Error → ``None`` mapping
itself is ``value_proof_get``'s job and is exercised through its stub here.
"""
import unittest
from unittest.mock import MagicMock

import ocaboxapi  # noqa: F401 — must precede ob.planrunner imports (breaks the ob↔ocaboxapi import cycle)
from ob.planrunner.subcommands.sub_camera_exposure import CameraExposure


def _harness(positions, atsetpoint):
    """Bare stand-in carrying only what _m1_header_values touches."""
    harness = MagicMock()

    async def value_proof_get(name, awaitab, expect_type, n_times=5, wait=3.0, log=False):
        return {'fitsh_m1_positions': positions,
                'fitsh_m1_atsetpoint': atsetpoint}[name]

    harness.value_proof_get = value_proof_get
    return harness


class M1HeaderValuesTest(unittest.IsolatedAsyncioTestCase):

    async def test_positions_converted_metres_to_um(self):
        harness = _harness([-9.63e-05, 0.0002158, 4.7e-06], True)
        self.assertEqual(await CameraExposure._m1_header_values(harness),
                         (-96.3, 215.8, 4.7, True))

    async def test_absent_subsystem_gives_empty_cards(self):
        """wk06-style absence (2002) or any fault: value_proof_get yields None."""
        harness = _harness(None, None)
        self.assertEqual(await CameraExposure._m1_header_values(harness),
                         ('', '', '', ''))

    async def test_malformed_positions_do_not_leak_partial_values(self):
        harness = _harness([1e-06, 2e-06], False)
        self.assertEqual(await CameraExposure._m1_header_values(harness),
                         ('', '', '', False))


if __name__ == '__main__':
    unittest.main()


# ---------------------------------------------------------------------------
# value_proof_get best-effort semantics (PR #282 review)
# ---------------------------------------------------------------------------
import asyncio
import time as _time
import unittest as _unittest
from types import SimpleNamespace as _SNS

from obcom.comunication.comunication_error import CommunicationRuntimeError as _CRE

from ob.planrunner.abstract_base import AbstractBase as _AB


class ValueProofGetSemanticsTest(_unittest.IsolatedAsyncioTestCase):

    async def test_communication_runtime_error_is_an_absent_value(self):
        async def blow_up():
            raise _CRE(message='router gone')
        self.assertIsNone(await _AB._value_proof_get('x', blow_up, float))

    async def test_single_attempt_failure_does_not_sleep(self):
        async def nothing():
            return None
        dummy = _SNS(journal=None, _value_proof_get=_AB._value_proof_get)
        t0 = _time.monotonic()
        res = await _AB.value_proof_get(dummy, 'x', nothing, float, n_times=1, wait=3.0)
        elapsed = _time.monotonic() - t0
        self.assertIsNone(res)
        self.assertLess(elapsed, 1.0, f'final failed attempt slept the full wait ({elapsed:.1f}s)')
