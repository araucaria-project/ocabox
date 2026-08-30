from __future__ import annotations

from enum import Enum


class OnReadError(Enum):
    """DEPRECATED alias — use ``Observatory(policy=…)`` and the unified
    ``obcom.comunication.error_policy.ValuePolicy`` axis instead.

    Mapping: ``RAISE``→``ValuePolicy.RAISE``, ``STALE``→``ValuePolicy.LAST_GOOD``,
    ``NONE``→``ValuePolicy.NONE``. Constructing an ``Observatory`` with
    ``on_read_error=`` still works (one deprecation warning) but never
    declares a policy on the wire. The 2.7 default flip announced below has
    happened. The ``STALE_MARKED``/``REPEAT`` placeholders are subsumed by
    the Staleness Contract (rich ``Value(None)`` tags and per-severity
    ``ErrorPolicy`` rules respectively).

    Historical documentation of the per-observatory policy:

    Applies to ``Component.aget_value`` (hence every ``aget_*`` getter) when
    pulling a fresh value fails — a device fault (server 4009), an absent
    subsystem (2002), or a communication error. Set once at the client
    boundary: ``Observatory(on_read_error=OnReadError.STALE)`` — the policy is
    the client's identity (a GUI, a CLI, a service), deliberately not a
    per-call choice.

    Members:

    * ``RAISE`` — propagate the exception (e.g. ``OcaboxDeviceError``).
      The honest contract for CLIs, scripts and services: a read either yields
      data satisfying the requested freshness or fails loudly. This is also
      the semantics that maps onto the planned direct-NATS reads (serverish):
      last published message older than the tolerance ⇒ error. **Becomes the
      default in the ocabox 2.7 line** — an Observatory constructed without
      an explicit policy logs a warning until then.
    * ``STALE`` — serve the last cached value and log a warning; the
      historical GUI-friendly behaviour (pre-policy ``aget_value`` did this
      unconditionally) and the implicit default until the 2.7 flip. For
      displays that must keep rendering through blips.
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
