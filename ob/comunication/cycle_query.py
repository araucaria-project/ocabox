"""Extended CycleQuery classes with optional error-callbacks and clearer terminal-stop logging.

This module wraps the upstream :mod:`obcom.comunication.cycle_query` classes and adds:

* :meth:`BaseCycleQuery.add_error_callback_method` – register a **sync** error handler
* :meth:`BaseCycleQuery.add_async_error_callback_method` – register an **async** error handler

Error handlers receive the :class:`~obcom.comunication.comunication_error.CommunicationRuntimeError`
that caused the subscription to terminate permanently.

Additionally, when a :class:`ConditionalCycleQuery` subscription terminates permanently, an
``ERROR``-level log line is emitted that makes it unambiguous that the subscription is dead::

    CycleQuery terminated for <repr>: <error>. No further callbacks will fire.
"""

import asyncio
import logging

from obcom.comunication.comunication_error import CommunicationRuntimeError
from obcom.comunication.cycle_query import (
    BaseCycleQuery as _BaseCycleQuery,
    ConditionalCycleQuery as _ConditionalCycleQuery,
    PeriodicCycleQuery as _PeriodicCycleQuery,
)

logger = logging.getLogger(__name__.rsplit('.')[-1])

__all__ = ["BaseCycleQuery", "ConditionalCycleQuery", "PeriodicCycleQuery"]


class BaseCycleQuery(_BaseCycleQuery):
    """Extended :class:`~obcom.comunication.cycle_query.BaseCycleQuery` with optional error callbacks.

    Adds two registration methods for *terminal-stop* handlers that are invoked exactly once
    when the subscription permanently stops due to a non-retryable error.  Regular callbacks
    (registered via :meth:`add_callback_method` / :meth:`add_callback_async_method`) continue to
    receive one final call with the last response just as before – this is purely additive.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._error_callback_methods: list = []
        self._error_callback_methods_a: list = []

    # ------------------------------------------------------------------
    # Public API – error-callback registration
    # ------------------------------------------------------------------

    def add_error_callback_method(self, method):
        """Register a *sync* error callback invoked on terminal stop.

        The *method* is called with a single positional argument, the
        :class:`~obcom.comunication.comunication_error.CommunicationRuntimeError` that caused the
        cycle query to stop permanently.  It is called **once**, immediately after the terminal
        stop is detected, before the final regular-callback invocation.

        This is the recommended way for clients to detect and act on permanent subscription
        failure (e.g. unsubscribe, mark a metric as unavailable, raise an alert) instead of
        relying on the "callback called once with status=False" convention.

        :param method: callable(CommunicationRuntimeError)
        """
        self._error_callback_methods.append(method)

    def add_async_error_callback_method(self, method):
        """Register an *async* error callback invoked on terminal stop.

        Like :meth:`add_error_callback_method` but *method* is expected to be a coroutine
        function.  It is awaited inside the callback runner task.

        :param method: async callable(CommunicationRuntimeError)
        """
        self._error_callback_methods_a.append(method)

    # ------------------------------------------------------------------
    # Internal – override callback runner to add error-callback support
    # ------------------------------------------------------------------

    async def _execute_callbacks(self):
        """Main callback-runner loop with error-callback support and clearer terminal-stop logging.

        Behaviour:

        * Normal operation: delegates to regular callbacks on every received response.
        * Terminal stop: emits an ``ERROR``-level log stating the subscription is permanently dead,
          calls all registered error callbacks (async first, then sync) with the error, then falls
          through to call regular callbacks one final time (if a last response exists).
        """
        run = True
        while run:
            await asyncio.sleep(0)
            try:
                result = await self.get_response()
            except CommunicationRuntimeError as exc:
                run = False
                result = self._last_response

                # ---- Clearer terminal-stop log ----------------------------------------
                logger.error(
                    f"{self}: CycleQuery terminated: {exc}. No further callbacks will fire."
                )

                # ---- Invoke error callbacks -------------------------------------------
                for a_method in self._error_callback_methods_a:
                    if callable(a_method):
                        try:
                            logger.debug(f"{self}: Execute async error callback {a_method.__name__}")
                            await a_method(exc)
                        except Exception as err:  # noqa: BLE001
                            logger.error(
                                f"Error in async error callback {a_method.__name__}. Error: {err}"
                            )

                for method in self._error_callback_methods:
                    if callable(method):
                        try:
                            logger.debug(f"{self}: Execute error callback {method.__name__}")
                            method(exc)
                        except Exception as err:  # noqa: BLE001
                            logger.error(
                                f"Error in error callback {method.__name__}. Error: {err}"
                            )

                # If there is no last response don't fire regular callbacks
                if not self._last_response:
                    return

            # ---- Regular callbacks (run on every response including the final one) ----
            for a_method in self._callback_methods_a:
                if callable(a_method):
                    try:
                        logger.debug(f"{self}: Execute callback {a_method.__name__}")
                        await a_method(result)
                    except TypeError as e:
                        logger.error(f"Error in callback method {a_method.__name__}. Error: {e}")

            for method in self._callback_methods:
                if callable(method):
                    try:
                        logger.debug(f"{self}: Execute callback {method.__name__}")
                        method(result)
                    except TypeError as e:
                        logger.error(f"Error in callback method {method.__name__}. Error: {e}")


class ConditionalCycleQuery(BaseCycleQuery, _ConditionalCycleQuery):
    """Conditional (subscription-style) cycle query with error-callback support.

    Extends :class:`~obcom.comunication.cycle_query.ConditionalCycleQuery` from *obcom* with the
    error-callback infrastructure provided by this package's :class:`BaseCycleQuery`.

    **Error handling summary**

    +---------------------------+------------------------------------------+
    | Condition                 | Behaviour                                |
    +===========================+==========================================+
    | Response code **4004**    | Silent retry – subscription expired,     |
    |                           | server just needs a keep-alive.          |
    +---------------------------+------------------------------------------+
    | ``severity == TEMPORARY`` | Silent retry – transient server error.   |
    +---------------------------+------------------------------------------+
    | Any other error           | **Terminal stop** – the subscription     |
    |                           | is permanently dead.  Sequence:          |
    |                           |                                          |
    |                           | 1. ERROR-level log: *"CycleQuery         |
    |                           |    terminated … No further callbacks     |
    |                           |    will fire."*                          |
    |                           | 2. Registered error callbacks are        |
    |                           |    called once with the               |
    |                           |    ``CommunicationRuntimeError``.        |
    |                           | 3. Regular callbacks receive one final   |
    |                           |    call with ``status=False`` (if a      |
    |                           |    last response exists), then never     |
    |                           |    fire again.                           |
    +---------------------------+------------------------------------------+

    **Registering an error callback**::

        cq = await observatory.subscribe_async(address, callback_method=my_callback)
        cq.add_error_callback_method(lambda err: logger.critical(f"Subscription dead: {err}"))

    :param crs: :class:`~obcom.comunication.base_client_request_solver.BaseClientRequestSolver`
    :param list_request: list of :class:`~obcom.data_colection.value_call.ValueRequest` objects
    :param delay: minimum interval between responses (seconds)
    :param loop: asyncio event loop (auto-detected when omitted)
    :param query_name: human-readable name used in log lines
    :param max_missed_msg: missed-message budget before terminal stop (-1 = unlimited)
    :param request_timeout: per-request timeout in seconds (default 30 s)
    :param ignore_errors: when ``True`` non-temporary errors are treated as failed
        attempts rather than causing a terminal stop
    :raises CommunicationRuntimeError: if no running event loop can be found
    """


class PeriodicCycleQuery(BaseCycleQuery, _PeriodicCycleQuery):
    """Periodic cycle query with error-callback support.

    Extends :class:`~obcom.comunication.cycle_query.PeriodicCycleQuery` from *obcom* with the
    error-callback infrastructure provided by this package's :class:`BaseCycleQuery`.
    """
