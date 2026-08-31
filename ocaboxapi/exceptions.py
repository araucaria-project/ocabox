"""Client-facing ocabox exceptions.

All ocabox errors derive from :class:`OcaboxError` and carry the structured
metadata of the server's ``ResponseError`` (code, component, device errno,
severity) so callers never have to parse a message string or read server logs
to know what happened. The mapping from a server error *code* to the right
exception *type* lives in one place — :meth:`OcaboxError.from_response` — so the
client stays "dumb but well-informed": both GET and PUT use the same factory and
the same metadata.

Hierarchy::

    OcaboxError                     # base — any ocabox error
    ├── OcaboxServerError           # TIC itself failed (internal/tree/value-build)
    ├── OcaboxAccessDenied          # server denied access (code 1004)
    └── OcaboxDeviceError           # server OK; instrument/driver reported a fault (4009)
        └── CameraBusy              # device busy with another operation (4008)
"""


class OcaboxError(Exception):
    """Base for all ocabox client errors.

    :ivar code: server ``ResponseError`` code (e.g. 1004, 4008, 4009), or ``None``.
    :ivar component_name: reporting tree component (e.g. ``"TreeAlpacaObservatory"``).
    :ivar device_errno: numeric driver/instrument code when the device reported a
        fault (e.g. ASCOM ``1035``); ``None`` otherwise.
    :ivar severity: server severity string (``TEMPORARY`` / ``NORMAL`` / ``CRITICAL``).
    :ivar address: the request address that failed.
    :ivar operation: ``"GET"`` or ``"PUT"``.
    """

    def __init__(self, message, *, code=None, component_name=None,
                 device_errno=None, severity=None, address=None, operation=None):
        super().__init__(message)
        self.code = code
        self.component_name = component_name
        self.device_errno = device_errno
        self.severity = severity
        self.address = address
        self.operation = operation

    @classmethod
    def from_response(cls, operation, address, error):
        """Build the right ocabox exception from a failed-response ``ResponseError``.

        Single source of truth for the code→type mapping, shared by GET and PUT.

        :param operation: ``"GET"`` or ``"PUT"``.
        :param address: the request address.
        :param error: the ``ResponseError`` from ``ValueResponse.error`` (may be ``None``).
        """
        code = getattr(error, 'code', None)
        kwargs = getattr(error, 'kwargs', None) or {}
        exc_cls = _CODE_MAP.get(code, OcaboxServerError)
        return exc_cls(
            f'{exc_cls.__name__} on {operation} {address}: {error}',
            code=code,
            component_name=getattr(error, 'component_name', None),
            device_errno=kwargs.get('device_errno'),
            severity=getattr(error, 'severity', None),
            address=address,
            operation=operation,
        )


class OcaboxStaleValueError(OcaboxError):
    """A sync property read found only a value older than the freshness bound
    (Staleness Contract, value_policy=RAISE). No I/O happened — refresh with
    the async getter, subscribe, or declare a LAST_GOOD/NONE policy."""
    pass


class OcaboxServerError(OcaboxError):
    """TIC itself failed to satisfy the request (internal / tree / value-build)."""


class OcaboxAccessDenied(OcaboxError):
    """Server denied access (code 1004) — a special permission is required."""


class OcaboxDeviceError(OcaboxError):
    """The server worked and is faithfully relaying a fault reported by the
    instrument/driver (code 4009), e.g. ASCOM ``InvalidOperationException`` 1035
    "Telescope is not ready, please clear Error".

    Inspect :attr:`device_errno`, :attr:`component_name` and the message. Such a
    state usually needs operator action, so the planrunner does **not** auto-retry
    it.
    """


class CameraBusy(OcaboxDeviceError):
    """Camera busy with another operation, e.g. an acquisition in progress (code 4008)."""


# Code → exception-type registry. Unmapped codes fall back to OcaboxServerError.
_CODE_MAP = {
    1004: OcaboxAccessDenied,
    4008: CameraBusy,
    4009: OcaboxDeviceError,
}
