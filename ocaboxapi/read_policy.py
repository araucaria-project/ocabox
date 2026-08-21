from __future__ import annotations

from enum import Enum


class OnReadError(Enum):
    """Per-observatory policy for a failed component read refresh.

    Applies to ``Component.aget_value`` (hence every ``aget_*`` getter) when
    pulling a fresh value fails — a device fault (server 4009), an absent
    subsystem (2002), or a communication error. Set once at the client
    boundary: ``Observatory(on_read_error=OnReadError.STALE)`` — the policy is
    the client's identity (a GUI, a CLI, a service), deliberately not a
    per-call choice.

    Members:

    * ``RAISE`` (default since the 2.7 line) — propagate the exception
      (e.g. ``OcaboxDeviceError``). The honest contract for CLIs, scripts and
      services: a read either yields data satisfying the requested freshness
      or fails loudly. This is also the semantics that maps onto the planned
      direct-NATS reads (serverish): last published message older than the
      tolerance ⇒ error. An Observatory constructed without an explicit
      policy still logs a warning — declare your client's identity.
    * ``STALE`` — serve the last cached value and log a warning; the
      historical GUI-friendly behaviour (the implicit default before 2.7).
      For displays that must keep rendering through blips.
    * ``NONE`` — return ``None``. For callers that render "no data" themselves
      and want neither exceptions nor stale values.

    Reserved for future extension (not implemented yet — see the read-policy
    roadmap issue): ``STALE_MARKED`` (return value together with its data
    timestamp so the consumer can judge freshness — the native semantics of
    NATS ``last_per_subject`` reads and what staleness-aware GUIs actually
    want) and ``REPEAT`` (bounded retry with backoff before giving up, a
    per-severity policy like the subscription ``ErrorPolicy``).
    """

    RAISE = 'raise'
    STALE = 'stale'
    NONE = 'none'
