# Error Handling Reference — ocabox / ocabox-server (TIC)

Reference for developers using the ocabox API and writing ocabox clients. Covers
the full path of an error: where it is raised in the **ocabox-server** daemon
("TIC"), how it is mapped and logged, how it crosses the wire, and how the
**ocabox** client handles it by default and under configuration.

---

## Quick navigation

- [TL;DR](#tldr) — the 60-second model
- [1. Server side](#1-server-side-ocabox-server--tic) — severity, codes, mappings, logging, propagation
- [2. Client side](#2-client-side-ocabox) — exceptions, defaults, `error_policy`, queries/subscriptions/commands, logging, retry/timeout
- [3. Changing the severity of a specific error](#3-changing-the-severity-of-a-specific-error-maintainers) — maintainer how-to
- [4. Improvement proposals](#4-improvement-proposals)

---

## TL;DR

- Every request resolves to a **`ValueResponse`**. `status == True` → `value` is valid.
  `status == False` → `error` holds a **`ResponseError`** (`code`, `message`,
  `component_name`, `severity`, `kwargs`).
- **Severity** is one of `TEMPORARY` / `NORMAL` / `CRITICAL` — a *retryability*
  axis (would a retry in ~30 s plausibly succeed?), **not** an internal-vs-external axis.
- **Severity is hardcoded at the raise site** in the server. There is no config
  table — changing it is a code edit (see §3).
- **Client reaction depends on the access mode:**

  | Mode | Retry? | Configurable? |
  |---|---|---|
  | Subscription (`subscribe` / `subscribe_async`) | Yes — via `ErrorPolicy` (default: the observatory-wide `policy`) | **Yes** (`policy=` / deprecated `error_policy=`) |
  | Simple query (`aget_value`) | No retry, but a failed refresh is masked while the cache satisfies T2, then judged by `value_policy` (§2.7) | **Yes** (`value_policy=`, `max_data_age=`) |
  | Simple put (`aput_value`) | No | No (one shot, `request_timeout` only) |
  | Command (planrunner) | Yes — hardcoded `n_times=5, wait=3s` | No (own ad-hoc retry) |

---

## 1. Server side (ocabox-server / TIC)

### 1.1 Severity levels

Defined as **string constants** on `ErrorSeverity` (ABC) in
`obcom/data_colection/coded_error.py:8-21`. Not an `Enum`.

| Severity | Meaning (retryability) | Default client reaction (subscription) |
|---|---|---|
| `TEMPORARY` | Transient blip (timeout, momentary I/O). | Silent retry; user callback **never fires**. |
| `NORMAL` | **Default.** Sustained external-state failure. | `INTERACTIVE`→STOP; `SERVICE`→retry w/ backoff. |
| `CRITICAL` | Permanent (tree misconfig, bad address). | Always STOP. |

- Ordering for "worst-of" comparison: `TEMPORARY < NORMAL < CRITICAL`
  (`compare_severity()`, `coded_error.py:23-40`). A retry-exhausting freezer
  inherits the worst severity seen across attempts
  (`tree_conditional_freezer.py:125-132`).
- **Default when unspecified is `NORMAL`** (`coded_error.py:68`, `response_error.py:14`).
- **Convention history:** severity used to mean "inside TIC vs external state"
  (April 2026); since 2026-05-03 it means **retryability** (`doc/errors.md:46-79`).
  Some older raise sites still reflect the old convention — see §4.

### 1.2 Error code registry

Codes = `local_code + CODE_GROUP`. Source: `coded_error.py`, `address.py`, `value.py`.

| Group | Class | Codes |
|---|---|---|
| 1000 | `AddressError` | 1001 wrong format · 1002 non-existent · 1003 wrong params · **1004 access denied** |
| 2000 | `TreeValueError` | 2001 default · 2002 creation failed · 2003 too many retries |
| 3000 | `TreeStructureError` | 3001 wrong architecture / unexpected end of branch · **3002 method not implemented** |
| 4000 | `TreeOtherError` | 4001 wrong request · 4002 app not answering · 4003 not subscribable · **4004 subscription expired/heartbeat** · 4005 cannot connect to external service · 4006 bad timeout · 4007 wrong arg · **4008 device busy** |

- **4004** is overloaded: canonical "value generation timed out", but on a
  subscription it is the benign "expired, renew" heartbeat — auto-renewed client-side
  (`cycle_query.py:477`), never surfaced.
- **4008** (device busy, e.g. Andor `DRV_ACQUIRING`) added so clients map to
  `CameraBusy` instead of string-matching messages (CHANGELOG 2.3.13).

### 1.3 Error mappings (hardware → coded error)

The central exception→response conversion is `TreeBaseProvider.get_response()`
(`obsrv/tree_components/base_components/tree_base_provider.py:61-120`), which calls
`ResponseError.from_coded_error()` (preserves code/message/severity/kwargs).

**ALPACA** — `AlpacaConnector.raise_tree_exeption()` (`alpaca_connector.py:313-360`):

| Raw error | Mapped to | Severity |
|---|---|---|
| HTTP 400/500, content-type, generic HTTP | `TreeValueError(2002)` | NORMAL |
| `AlpacaError` errno 20072 (`DRV_ACQUIRING`) | `TreeOtherError(4008)` | TEMPORARY |
| `AlpacaError` other numeric | `TreeValueError(2002)` | NORMAL |
| `RequestConnectionError`, `asyncio.TimeoutError` | `TreeOtherError(4005)` | TEMPORARY |
| `TypeError` / `ValueError` | `AddressError(1003)` | NORMAL |
| `ServerConnectionError` | `TreeValueError(2002)` | TEMPORARY |

**Pilar / IRIS-CCD** — follow the documented retryability convention:

| Condition | Mapped to | Severity |
|---|---|---|
| Connectivity loss (`ConnectionError`, `OSError`, timeout) | `TreeOtherError(4005)` | NORMAL |
| Device replied with error (`RuntimeError`) | `TreeValueError(2002)` | NORMAL |
| Unknown method (`KeyError` in command map) | `TreeStructureError(3002)` | CRITICAL |

> ⚠️ **Inconsistency:** ALPACA still uses `TEMPORARY` for 4005/4008 (pre-2026-05
> convention); Pilar/IRIS were migrated to `NORMAL`. See §4 #3. Tests cover only
> Pilar/IRIS (`test_connector_transient_errors.py`).

### 1.4 Logging in the daemon

- Per-module loggers: `logging.getLogger(__name__.rsplit('.')[-1])` (module basename).
- **No severity↔log-level coupling** — a `CRITICAL` response is not logged louder
  than a `NORMAL` one.
- Levels observed:
  - `WARNING` — every ALPACA mapping logs at its raise site (`alpaca_connector.py:320-360`).
  - `ERROR` — `__check_error` raw HTTP/content failures; "CRITICAL …" in request solvers
    (`request_solver.py:32,39`; `base_request_solver.py:95,101`).
  - `INFO`/`DEBUG` — normal request lifecycle, freezer refresh.
- **Logging and propagation are independent.** A single ALPACA failure is typically
  logged **twice** (ERROR in `__check_error`, WARNING in `raise_tree_exeption`).
- **No server-side throttling.** A device-offline storm logs every poll. The
  "loud-then-throttled" UX is a client-side `ErrorPolicy` feature only.

### 1.5 What is propagated vs swallowed

- **Propagated:** all coded errors (`AddressError`, `TreeValueError`, `TreeOtherError`)
  become a `ResponseError` on a `status=False` `ValueResponse`.
- **Never swallow transient I/O into `None`/`{}`** — the freezer cannot distinguish
  that from a valid null read and polls forever (CHANGELOG 2.3.15, issue #20).
- **Last-resort wrappers** guarantee a response always comes back: unexpected
  escapes → `4002 CRITICAL` (`base_request_solver.py:118-135`); unparseable request →
  `4001 CRITICAL` (`request_solver.py:55`).
- **Router exception:** on overall request timeout the router logs and **sends
  nothing** (`router.py:158-159`) — the client only sees its own timeout.

### 1.6 Wire format

```
ValueResponse:
  address: str | Address
  value:   Value | None
  status:  bool            # False ⇒ error
  error:   ResponseError | None
            ├ code: int
            ├ message: str
            ├ component_name: str
            ├ severity: str   # TEMPORARY | NORMAL | CRITICAL
            └ kwargs: dict
```

Serialized as msgpack inside a ZMQ `MultipartStructure`. On receipt the client
rehydrates `error` into a typed `ResponseError` (`value_call.py:177-178`) — **client
code should use the typed object, never the dict form.**

JSON-ish debugging shape:
```json
{"address": ["iris","camera","ccdtemperature"], "status": false, "value": null,
 "error": {"code": 3002, "message": "Method not implemented",
           "component_name": "TreeIrisObservatory", "severity": "CRITICAL"}}
```

---

## 2. Client side (ocabox)

### 2.1 Exceptions the client exposes

All ocabox errors derive from `OcaboxError` and carry the server's structured
metadata (`.code`, `.component_name`, `.device_errno`, `.severity`, `.address`,
`.operation`) so callers never parse message strings or read server logs.

```
Exception
├── OcaboxError                    ocaboxapi/exceptions.py   (base; structured metadata)
│   ├── OcaboxServerError              TIC itself failed (internal / tree / value-build)
│   ├── OcaboxAccessDenied             server denied access (code 1004)
│   └── OcaboxDeviceError              server OK; instrument/driver reported a fault (code 4009)
│       └── CameraBusy                 device busy with another operation (code 4008)
└── BaseCommunicationError         obcom (re-exported via ob/__init__.py)
    ├── CommunicationTimeoutError       response didn't arrive before deadline
    └── CommunicationRuntimeError       transport / loop failure; also raised when policy says STOP
```

**Code → exception mapping** — single source of truth in
`OcaboxError.from_response(operation, address, error)`, used by **both**
`get_async` and `put_async` (no GET/PUT asymmetry):

| Server `ResponseError.code` | Client exception | Carries |
|---|---|---|
| 1004 | `OcaboxAccessDenied` | |
| 4008 | `CameraBusy` | `.device_errno` |
| 4009 | `OcaboxDeviceError` | `.device_errno` (e.g. ASCOM 1035), `.component_name` |
| anything else (`status=False`) | `OcaboxServerError` | |

### 2.2 Default handling by layer

| Layer | On error |
|---|---|
| `Client` (ZMQ, `client.py`) | Raises `CommunicationTimeoutError`/`CommunicationRuntimeError`; does not swallow. |
| `Observatory.get_async/put_async` | Re-raises comm errors; translates `status=False` to ocaboxapi exceptions. |
| `Component.aget_value` | Failed refresh: serves the cached value while it satisfies `max_data_age` (T2); past T2 applies `value_policy` — RAISE (default) / NONE / LAST_GOOD (§2.7). No timestamp cheat: every read re-asks, the server negative cache absorbs the hammering. |
| `Component.aput_value` (`:58-64`) | Logs INFO, then **re-raises** `OcaboxError` (any subclass). |
| `Component.subscribe` callback (`:105-129`) | On `status=False` logs `ERROR`; no watcher fires. |
| `Observatory.get` (sync) | **Not implemented** — logs error, returns `'n/a'`. |

### 2.3 Configuring error handling — `ErrorPolicy`

Introduced PR #268 (`feat/error-policy`, ocabox 2.5.0 / ocabox-common 1.1.0).
Defined in `obcom/comunication/error_policy.py`, re-exported from `ob/__init__.py`.

Since ocabox 2.7 the policy is the client's identity, set once:
`Observatory(policy='interactive'|'service'|'display'|ErrorPolicy)` — every
subscription inherits it; per-call override via
`subscribe_async(..., policy=...)` (`error_policy=` is a deprecated alias).

**Model:** `ErrorPolicy{temporary, normal, critical, value_policy}` — three
per-severity `SeverityRule(action, backoff, budget, log)` (the *transport*
axis) plus `value_policy ∈ {RAISE, NONE, LAST_GOOD}` (the *truth* axis, §2.7;
`None` = undeclared → pre-contract behaviour, nothing extra on the wire).

| `SeverityAction` | Behavior |
|---|---|
| `RETRY` | Library suppresses error, sleeps backoff, rebuilds subscription. Callback never sees it. |
| `NOTIFY` | Callback fires with the error **and** library keeps retrying. |
| `STOP` | Callback fires once with `status=False`; subscription terminates (historical behavior). |

- **`Backoff`**: `immediate()`, `fixed(s)`, `exponential(initial, ceiling, factor)`, `staged([(delay, attempts), …])` (final `attempts=None` = forever).
- **`Budget(max_attempts, max_seconds)`** — exhaustion downgrades to STOP.
- **`LogPolicy(first_n=1, then_every_seconds=3600)`** — throttles WARNING volume.

**Presets:**

| Preset | TEMPORARY | NORMAL | CRITICAL | value_policy | Use for |
|---|---|---|---|---|---|
| `INTERACTIVE` *(default)* | RETRY (exp 0.1→5 s) | **STOP** | STOP | — (RAISE locally) | scripts, CLI — caller reacts |
| `SERVICE` | RETRY (exp) | **RETRY** (staged 2s×3→10s×6→60s∞, log 3+hourly) | STOP | — (RAISE locally) | daemons that self-heal |
| `DISPLAY` | RETRY (exp) | RETRY (staged) | **NOTIFY** (staged) | **NONE** | GUIs/walls — render '—' + `value_tags()` |
| `FAIL_FAST` | RETRY fixed 0.1 s, budget 3 | STOP | STOP | — (RAISE locally) | CLI / tests |

**Deprecation:** `ignore_errors=` is deprecated in favor of `error_policy=`
(emits `DeprecationWarning`, honored one more release).

> `Component.subscribe` inherits the observatory-wide policy (set it once in
> the constructor); it forwards `max_data_age=` but not a per-call policy —
> for that call `Observatory.subscribe_async` directly.

### 2.4 The three modes

**(a) Subscriptions** — `Component.subscribe` → `Observatory.subscribe_async` →
`client.subscribe_with_callback`. The **only** path with `ErrorPolicy`. Per-error
severity drives RETRY/NOTIFY/STOP inside the cycle-query loop. Default `INTERACTIVE`.
Code 4004 is silently renewed regardless of policy. `status=False` with `error=None`
→ raises `CommunicationRuntimeError`.

**(b) Simple queries** — `aget_value` / `aput_value`. **No transport retry.**
GET applies the truth axis (§2.7): failed refresh → cached value while within
`max_data_age`, then `value_policy` decides (RAISE default). PUT re-raises,
always — deliberately outside the value policy. One shot, governed by
`request_timeout` (absolute deadline = `time() + delta`).

**(c) Commands (planrunner)** — own application-level retry, predating `ErrorPolicy`
(`ob/planrunner/abstract_base.py`). Retry only what a retry can fix:
- **Retried** (`n_times=5`, `wait=3.0s`): `OcaboxServerError`, `CommunicationTimeoutError`.
- **Fail fast, no retry**: `OcaboxDeviceError` (incl. `CameraBusy`) and
  `OcaboxAccessDenied` — a latched device state or a denied request won't clear by
  repeating; the planner logs to the journal and returns `False` immediately. This
  is what stops a `slewtocoordinatesasync` storm against a TCU in error state.
- `proof_put_startexposure`: still special-cases `CameraBusy` first — attempt #1 busy
  = foreign acquisition → fail fast; attempt #N>1 busy after a first-attempt timeout =
  our own put armed the camera → treat as success. Other device faults fail fast.
- `value_proof_get`: device/server/comm errors → `None` then retry (reads are
  low-harm; not yet aligned to fail-fast — see §4.0 follow-ups).
- Operator-facing errors go to **NATS journal** + a `status_error` subject
  (`base_subcommand.py:33-54`, levels `minor`/`major`/`critical`), not exceptions.

### 2.5 Client-side logging

Per-module loggers (`observatory`, `component`, `client`, planrunner subcommands).

| Level | Examples |
|---|---|
| DEBUG | every request/response round-trip; ZMQ send/receive lifecycle |
| INFO | access-denied note; put-error note; connection string; planrunner progress |
| WARNING | stale-data fallback; corrupted server data; **every planrunner retry attempt** |
| ERROR | subscription error responses; callback exceptions; missing return value; receive-task death |

Planrunner additionally publishes to the **NATS journal** and `status_error` subject —
operator-facing errors are independent of Python logging.

### 2.6 Retry & timeout (branch `fix/startexposure-retry-and-timeout`, 2.5.1)

- `request_timeout` is an **absolute deadline** (`time() + delta`), enforced in
  `Client._send_to_server` (`client.py:132-136`). Base default ~2.0 s.
- **Bug fixed:** the small default could raise `CommunicationTimeoutError` on a
  `startexposure` put *while the camera was actually armed*, then the planner
  retried and collided with `DRV_ACQUIRING`.
- **Fixes:** `Camera.STARTEXPOSURE_REQUEST_TIMEOUT = 30.0` (`camera.py:348`); new
  code 4008 → `CameraBusy`; `proof_put_startexposure` uses `CameraBusy` +
  attempt-number + first-attempt-was-timeout to decide inherit-vs-fail. Degrades
  gracefully against servers that don't emit 4008.

---

### 2.7 Staleness Contract — the temporal model and the truth axis (2.7.0)

Full design: vault `Architecture/Staleness Contract (unified read policy)`.
Three thresholds govern every read:

| | Meaning | Parameter | Default |
|---|---|---|---|
| **T0** | "don't call me more often than this" (push rate cap) | `delay` | 5 s |
| **T1** | preferred freshness — "fresher: serve; older: refresh" | `time_of_data_tolerance` | 60 s (wire) / 0.5 s (`Observatory`) |
| **T2** | truth bound — "older than this must not be presented" | `max_data_age` | `2 * T1` |

`(T1, T2]` is the repair window: refresh problems are masked and retried
there; only past T2 does `value_policy` decide what you get:

| `value_policy` | Past T2 you get |
|---|---|
| `RAISE` *(default)* | the underlying exception (`OcaboxStaleValueError` for sync property reads) |
| `NONE` | a **rich None**: subscriptions deliver `Value(None, ts=now, tags={reason: <error code>, last_good: <v>, last_good_ts: <ts>})`; `aget_value` returns bare `None`. The `last_good*` tags appear only when a last good value is known — read them with `.get()`, a startup outage carries `reason` alone |
| `LAST_GOOD` | the aging value, forever (bare-`.v` clients that prefer old data over no data) |

Usage:

```python
obs = Observatory(client_name='my-gui', policy='display')          # identity, once
await comp.subscribe('azimuth', cb, time_of_data_tolerance=5,      # T1
                     max_data_age=30)                              # T2 (else 2*T1)
# cb receives v=None when truth expires; comp.value_tags('azimuth')
# then holds {reason, last_good, last_good_ts} for grey-out rendering.

v = await comp.aget_value('azimuth', time_of_data_tolerance=5,     # pull path
                          value_policy='none', max_data_age=30)    # per-call override
```

Wire/deployment notes: a *declaring* policy (e.g. `DISPLAY`) puts
`value_policy` into request_data — requires **ocabox-server ≥ 2.5.2** on the
way to devices (≥ 2.6 for server-side enforcement); `max_data_age` is a plain
`ValueRequest` field, safe against any server. Legacy
`Observatory(on_read_error=…)` still works (deprecated) and maps onto the
truth axis locally without declaring anything on the wire. Params with a live
subscription are exempt from the sync-property age judgment — the
subscription owns the contract.

## 3. Changing the severity of a specific error (maintainers)

**There is no config file, mapping table, or registry for severity.** Severity is
**hardcoded at each raise site** in Python. To change the severity of a specific
error (e.g. on a user/admin request):

1. **Locate the raise site:**
   - Hardware/instrument errors → the connector
     (`obsrv/protocols/<alpaca|pilar|iris_ccd>/*_connector.py`).
   - Structural/tree errors → the tree component
     (`obsrv/tree_components/...`).
2. **Edit the `severity=` argument** on the `Tree*Error(...)` call (or add one —
   the default is `NORMAL`). Use `ResponseError.SEVERITY_CRITICAL` /
   `_NORMAL` / `_TEMPORARY`.
3. **Decision rubric** (`doc/errors.md:46-75`): *"if a daemon retried this in 30 s,
   would it succeed?"* yes → `TEMPORARY`/`NORMAL`; no → `CRITICAL`.
4. **Update the assertions** — `doc/errors.md` tables and
   `test/data_collection/specialistic_components/test_connector_transient_errors.py`
   assert exact `(code, severity)` pairs.

The change ships in an ocabox-server release; **no client change is needed** — the
client reacts to whatever severity arrives, per the active `ErrorPolicy`.

---

## 4. Improvement proposals

Ordered by impact. Bugs first, then design.

### 4.0 Device-error category — distinguish "device faulted" from "TIC failed" *(implemented)*

> **Status:** implemented across three coordinated branches —
> `ocabox-common feat/device-error-code-4009` (2.6.0… see PR),
> `ocabox-server feat/device-error-4009`, `ocabox feat/device-error-type` (2.6.0).
> Merge order: common → server → client. ALPACA + IRIS-CCD emit 4009; resolves
> items **#4** and **#5** below.
>
> **Follow-ups not in these PRs:** Pilar's device-reply path (raw `RuntimeError`
> on `get`, `{"status":"failed"}` dict on `put`) still needs aligning to 4009;
> `value_proof_get` (reads) does not yet fail-fast on device faults; and the
> ocabox `uv.lock` pins an obcom predating `error_policy` (item #5-adjacent
> dependency skew) — the lock must be refreshed for the branch to import.

**Problem.** When an instrument driver reports a fault (e.g. ALPACA
`InvalidOperationException` errno 1035, *"Telescope is not ready, please clear
Error"*), the server wraps it as `TreeValueError(2002)` and the client surfaces a
generic `OcaboxServerError`. That conflates two unrelated things — *TIC itself
failed* vs *TIC worked and faithfully relayed a device fault* — and the device's
`error_number` is dropped (only the text survives, buried in the exception string).
Operators must log-dive on the servers to learn what the device actually said.
A latched device state ("clear Error") is also **not retryable**, yet the planrunner
blindly retries the command every 3 s (observed: a `slewtocoordinatesasync` storm).

**Design (3 coordinated, loosely-coupled changes — merge order common → server → client):**

| # | Repo | Change |
|---|---|---|
| 1 | ocabox-common | New code **`4009` "Device reported an error"** in `TreeOtherError` (same 4xxx device/external-state family as 4005/4008). |
| 2 | ocabox-server | Device-replied faults (ALPACA numeric `AlpacaError`; Pilar/IRIS `RuntimeError`) → `TreeOtherError(4009, severity=NORMAL, device_errno=<errno>)` instead of `TreeValueError(2002)`. The device `error_number` + message ride in `kwargs` (already wire-supported by `from_coded_error`). |
| 3 | ocabox | `OcaboxError` base + `OcaboxDeviceError` (carries `.code`, `.component_name`, `.device_errno`, `.severity`, `.message`); single centralized `OcaboxError.from_response()` mapper used by **both** `get_async` and `put_async`; planrunner `proof_put`/`value_proof_get` **do not auto-retry** `OcaboxDeviceError`/`OcaboxAccessDenied` (fail fast — needs operator action). |

**Principle:** keep the mapping logic in **one** place (the `from_response` factory);
the client stays "dumb" but every exception carries the full structured metadata, so
no consumer ever has to parse strings or read server logs. Resolves items **#4**
(flat hierarchy) and **#5** (GET/PUT asymmetry) below.

---

1. **BUG — `TreeStructureError` silently drops `severity`** (`coded_error.py:129-130`):
   it accepts `severity` but never forwards it to `super().__init__()`, so it always
   defaults to `NORMAL`. Every `TreeStructureError(3002, severity=CRITICAL)` from the
   Pilar/IRIS connectors is demoted. One-line fix (`severity=severity`) in
   ocabox-common.

2. **BUG — connector `TreeStructureError(3002)` never reaches the client as 3002.**
   `get_response` treats `TreeStructureError` as the "delegate downward" signal; for a
   leaf connector (no subcontractor) it returns a hardcoded `ResponseError(3001,
   CRITICAL)`, discarding the connector's code and message. Root cause: overloading
   `TreeStructureError` for both control-flow and real errors.

3. **ALPACA severities contradict the retryability convention.** 4005/4008 are raised
   `TEMPORARY` → client retries silently forever, operator gets no signal for a
   sustained ALPACA outage. Align with Pilar/IRIS (`4005 NORMAL`) and add an
   ALPACA-severity test.

4. ~~**Client exception hierarchy is flat.**~~ **RESOLVED in §4.0** — `OcaboxError`
   base introduced; `OcaboxAccessDenied`/`OcaboxServerError`/`OcaboxDeviceError`
   all derive from it.

5. ~~**GET vs PUT asymmetry.**~~ **RESOLVED in §4.0** — both `get_async` and
   `put_async` now route through the shared `OcaboxError.from_response()` mapper.

6. **`error_policy` covers only subscriptions.** Queries and commands have no unified
   policy; planrunner reimplements ad-hoc fixed-interval retry. → reuse the
   `Backoff`/`Budget`/`LogPolicy` primitives for `proof_put`/`value_proof_get`, and
   forward `error_policy` through `Component.subscribe`.

7. **`aget_value` masks all errors** (bare `except Exception`) and fakes the
   timestamp, prolonging stale reads beyond the data-tolerance window. → narrow the
   catch and don't bump the timestamp on failure.

8. **No severity↔log-level coupling, no server-side throttling.** Operators can't
   grep by severity; an offline device logs every poll (twice for ALPACA). → map
   severity to log level and add rate-limited logging server-side.

9. **Stringly-typed severity & overloaded code 4004.** `ErrorSeverity` is string
   constants, not an `Enum` (typos silently fall back to NORMAL); 4004 means both
   "value timed out" and "subscription heartbeat". → `Enum` + a dedicated heartbeat
   signal.


