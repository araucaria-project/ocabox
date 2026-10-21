# Changelog
All notable changes to this project will be documented in this file.

## [Unreleased]
....

## [2.11.0]
### Changed
- Optics subscriptions (`asubscribe_sees`, `_functions`, `_selectors`, `_declared`, `_busy`,
  `_operation`) hand the callback the value itself — `callback(value)`, a coroutine function too —
  as TIC delivers it, `None` when TIC has no truthful one (past `max_data_age`, the Staleness
  Contract); no more param events to read the value back from the component. They stay the
  component's own subscriptions, so `Telescope.unsubscribe_all_component` ends them.

## [2.10.1]
### Changed
- One T1: a GET or subscription without `time_of_data_tolerance` in the call or in the client's
  NATS config now carries the observatory's own T1 (`Observatory(time_of_data_tolerance=)`, default
  `timing.DEFAULT_REFRESH_AFTER` 0.5 s) on the wire instead of `None` — which obcom used to read as
  60 s, so a bare client refreshed its cache every 0.5 s and could be served values up to a minute
  old. Requires ocabox-common >= 1.11.0 (import guard), where T0 `delay` also defaults to T1.

## [2.10.0]
### Added
- Optics: `OpticsState.declared` and `aput_declare(key, position)` — vouch for a selector no reading
  proves (the dome while its shutter sensor reports an error); `None` withdraws (optics service ≥ 1.5).
### Changed
- `OpticsState.selectors` carries every selector axis with `origin`, `cause` (why it is unknown) and
  `label` (what people call it).

## [2.9.0]
### Added
- Optics: `Telescope.get_optical_detector(name)` (`sees`, `functions`, `aput_setpath(function)`) and
  `Telescope.get_optics()` (`selectors`, `busy`, `operation`) — the optics service of ocabox-tcs as
  TIC serves it (`<tel>.optics.<detector>.<item>`, ocabox-server ≥ 2.10). `aput_setpath` returns
  once the switch is accepted; follow `operation` for its outcome. Refusals arrive as server errors
  with the service's code (4007/4008/4009).
### Fixed
- `Telescope.unwatch_all_component` unwatches the tertiary (M3) instead of unsubscribing it.


## [2.8.6]
### Added
- Dome: introduced dome follower
- Nats bus: introduced Nats bus

## [2.8.2]
### Fixed
- Client: the first request after the receiver task is (re)started no longer fails with "The receive task was stopped" — the alive flag is set when the task is created, not on its first step (regression of 2.8.0).

## [2.8.1]
### Changed
- `ocabox-common` dependency follows git master again (no tag pin); the import guard requires >= 1.5.0.

## [2.8.0]
### Changed
- Python floor 3.11; `wait_for_psce()` retired, all waits use
  `asyncio.timeout()` (no orphaned middle task, correct `CancelledError`
  on cancel).
- `ocabox_bases.__version__` read from package metadata; `pyproject.toml`
  is the only place the version is edited.

## [2.7.6]
### Fixed
- `OcaboxStaleValueError` names the missing freshness witness — not subscribed
  / subscription stopped / subscription lost contact — instead of advising an
  `aget_…()` refresh that would not have helped.

## [2.7.5]
### Fixed
- A reply that arrived while the consumer's event loop was blocked is
  delivered instead of reported as a router timeout (false `4002`).

## [2.7.4]
### Changed
- ocabox-common pinned to the 1.4.0 release (git tag/rev) and checked at import
  time (ImportError names the found version).

## [2.7.3]
### Fixed
- Sync property reads: a subscription is a freshness witness, not a veto. A
  value refreshed within T2 is served even if its subscription is stopped or
  has lost contact; only when neither the subscription nor the local refresh
  age vouches does the value policy apply

## [2.7.2]
### Changed
- Default T2 (`Observatory(max_data_age=)` unset, per-call `aget_*` with only
  a tolerance) comes from the shared `ValueRequest.default_max_age` rule
  (2*T1 floored at 5 s; requires ocabox-common >= 1.4.0). Explicit T2 unchanged

## [2.7.1]
### Fixed
- Sync property reads of a subscribed param are judged by the cycle query's
  contact clock (`is_contact_fresh()`, obcom >= 1.3.4), not by the local
  change-stamp, which a stationary value never moves (undeclared clients
  raised `OcaboxStaleValueError` on such params after T2). Stopped
  subscriptions do not vouch; older obcom keeps the historical exemption

## [2.7.0]
### Changed
- **Staleness Contract, phase 3**: unified read policy `Observatory(policy=
  'interactive'|'service'|'display'|ErrorPolicy)` + `max_data_age` (T2, default
  `2*T1`); subscriptions inherit both, `aget_*` per-call `value_policy=`/
  `max_data_age=` with (T1, T2] masking on failed refresh, sync properties
  judge age vs T2 (subscribed params exempt); `on_read_error`/`OnReadError`
  deprecated aliases; timestamp cheat removed; announced default flip
  STALE→RAISE. `value_tags()` exposes rich-None tags. Requires ocabox-server
  ≥ 2.6 for wire-declaring policies. (ocabox-common#8, #281)

## [2.6.5]
### Added
- Planrunner fills the **M1 mirror-cell FITS cards** `M1-POS1..3` [µm] and
  `M1-ATSET` in `prepare_header()` (raw frames get `OCASTD 1.1.3`). Positions
  are converted metres → µm at this consumer; absence (wk06), a motor fault
  or a communication problem yields empty cards and never fails or delays
  the exposure. Details in `CameraExposure._m1_header_values`.
### Dependencies
- Requires pyaraucaria ≥ 2.14 (M1 cards in the `fits_header()` template) —
  unpinned git dep, so deployments need `poetry update pyaraucaria`.

## [2.6.4]
### Added
- Per-observatory **read-error policy** —
  `Observatory(on_read_error=OnReadError.RAISE | STALE | NONE)`: what
  `aget_*` getters do when a refresh fails. `RAISE` propagates the exception
  (`OcaboxDeviceError` on 4009 etc.); `STALE` serves the last cached value
  (the historical behaviour); `NONE` returns `None`. The policy is the
  client's identity — set once, no per-call override; `aput_value` is
  untouched (commands always raise). Future modes reserved: `STALE_MARKED`
  (value + data timestamp — the native semantics of the planned direct-NATS
  reads), `REPEAT` (bounded retry).
### Deprecated
- Constructing `Observatory` **without an explicit `on_read_error`**: the
  implicit default stays `STALE` for now (bit-for-bit the old behaviour) and
  logs a once-per-observatory warning — **the ocabox 2.7 line flips the
  default to `RAISE`**. Under the old (and interim-default) behaviour a
  failed read serves stale data with a refreshed timestamp, so the server's
  error model (4009 device fault, 2002 absent subsystem) never reaches
  one-shot callers and stale values can masquerade as live telemetry. GUIs
  that must render through blips: pass `OnReadError.STALE` explicitly;
  CLIs/services: `OnReadError.RAISE`.

## [2.6.3]
### Added
- `MirrorCell` (M1 active collimation) client component —
  `telescope.get_mirrorcell()` with `aget_`/`asubscribe_` for `available`,
  `mirrorcellstatus`, `positions` (metres), `motorstatuses`,
  `motorstatustexts`, `atsetpoint`, `moving`, and per-motor accessors
  `aget_motor_{position,status,statustext}(index)` (+ subscriptions).
  Commands: `amove_all_motors_to/offset`, `amove_one_motor_offset`,
  `astop_one_motor`, `astop_all_motors` — ⚠️ never commanded on real
  hardware yet (supervised test pending). Requires ocabox-server ≥ 2.4.0.
  Error model and details in the class docstring.

## [2.6.2]
### Added
- `Component.aget_value` (and the `Tertiary` getters) accept
  `time_of_data_tolerance` — forwarded to the server so caches must refresh
  entries older than the tolerance. Without it TIC serves values up to its
  default 60 s tolerance, which made movement polling (`aget_moving`) and
  post-move status reads observe stale state on components that no service
  subscribes to (found live on jk15 M3: `set 1 --wait` returned instantly
  showing the old port).

## [2.6.1]
### Added
- `Tertiary` (M3) read-back — `aget_`/`asubscribe_` for `nasmythport`
  (current physical port, int), `tertiarystatus` (full dict) and its
  decomposed fields `angle`, `moving`, `motoron`, `portname`, matching
  ocabox-server ≥ 2.3.18 (`tertiaryOCA` kind). Port numbers are physical
  AutoSlew ports (jk15: 1=ADR6/beso, 2=ADR10/andor) — NOT 0-based.
  `aput_selectnasmythport` unchanged. A controller fault surfaces as
  `OcaboxDeviceError` (4009) on every decomposed read — the vendor error flag
  is deliberately NOT exposed as a value; `tertiarystatus` stays readable as
  the raw diagnostic view.

## [2.6.0]
### Added
- `OcaboxError` base exception and `OcaboxDeviceError` — the server now
  distinguishes a fault *reported by an instrument/driver* (code 4009, the
  server worked and relayed the device error) from a TIC-internal failure.
  `OcaboxDeviceError` carries structured metadata so callers never parse
  message strings or read server logs: `.code`, `.component_name`,
  `.device_errno` (e.g. ASCOM `1035` "Telescope is not ready, please clear
  Error"), `.severity`, `.address`, `.operation`.
- `OcaboxError.from_response(operation, address, error)` — single source of
  truth mapping a server error *code* to the right exception *type*. Used by
  **both** `get_async` and `put_async`, fixing the prior GET/PUT asymmetry
  (GET previously collapsed 1004/4008 into a generic error).
### Changed
- Exception hierarchy is now rooted at `OcaboxError`:
  `OcaboxServerError`, `OcaboxAccessDenied`, `OcaboxDeviceError` all derive
  from it, and `CameraBusy` moved under `OcaboxDeviceError` (a busy device is a
  device state, code 4008). `OcaboxAccessDenied` is no longer a bare `Exception`
  sibling. Catch `OcaboxError` for "any ocabox error"; `telescope.py` and
  `component.py` were widened accordingly.
- Planrunner `proof_put` / `proof_put_startexposure` **no longer auto-retry**
  `OcaboxDeviceError` (incl. `CameraBusy`) or `OcaboxAccessDenied` — a latched
  device state or a denied request won't clear by repeating, so they fail fast
  (logged to the journal) instead of hammering the device. This stops the
  observed `slewtocoordinatesasync` retry storm on a TCU in error state.
  Transient `OcaboxServerError` / `CommunicationTimeoutError` still retry.
### Dependencies
- Requires ocabox-common ≥ `1.2.1` (code 4009) and ocabox-server ≥ `2.3.16`
  (emits 4009). Degrades gracefully against older servers: a device fault
  without 4009 still surfaces as `OcaboxServerError`.

## [2.5.1]
### Added
- `CameraBusy(OcaboxServerError)` exception, raised by `Observatory.put_async` when the server returns `TreeOtherError(code=4008)`. Lets callers react to "device busy" cleanly instead of string-matching wrapped Alpaca errors.
- `Camera.STARTEXPOSURE_REQUEST_TIMEOUT` (default 30 s, configurable). `aput_startexposure` uses it as `request_timeout` to prevent the silent first-attempt comm-timeout that armed the camera while the planner thought the put failed and retried, colliding with `DRV_ACQUIRING`.
- `AbstractBase.proof_put_startexposure`: specialised retry that catches `CameraBusy` and disambiguates by attempt number, never inheriting a foreign acquisition. Used by `sub_camera_exposure.py` and `auto_flat.py`.
### Dependencies
- ocabox-common bumped to `1.0.3` (registers code 4008 description).
- Runtime: requires ocabox-server `2.3.13` to actually receive code `4008` (otherwise `CameraBusy` never fires; falls through to legacy `OcaboxServerError` path with no behavioural regression).


## [2.5.0]
### Added
- `Observatory.subscribe_async(... error_policy=ErrorPolicy.SERVICE)` —
  per-severity policy for subscription error handling. Re-exports
  `ErrorPolicy`, `SeverityAction`, `SeverityRule`, `Backoff`, `Budget`,
  and `LogPolicy` from `ob` for convenience. Default keeps the historical
  GUI-friendly behaviour (`ErrorPolicy.INTERACTIVE`); long-running
  daemons should opt into `ErrorPolicy.SERVICE` so the library handles
  recovery from transient `severity=NORMAL` errors instead of letting
  the subscription die. Requires ocabox-common 1.1.0
  (`obcom.comunication.error_policy`).
### Requires
- `ocabox-common` 1.1.0+ at runtime, for `obcom.comunication.error_policy`.
  The `pyproject.toml` dep entry tracks ocabox-common's default branch
  by URL, so a `poetry update` after ocabox-common 1.1.0 merges picks up
  the new module automatically.
### Deprecated
- `ignore_errors=` on `subscribe_async` — pass `error_policy=` instead.
  Still honoured for one release with a `DeprecationWarning`.

## [2.4.0]
### Added
- support for safety cut-off in `safety` module of `ocaboxapi`
- 
## [2.3.4]
### Changed
- `ocaboxapi.telescope.shutdown` added timeout on wait operations
- `ocaboxapi.telescope.weather_stop` added timeout on wait operations

## [2.3.3]
### Added
- `Observatory.dischard_cached_telescope` 
### Fixed
- auto-flat calculation

## [2.3.1]
### Changed
- minimum python version bumped to 3.10
- Dependencies versions bumped

## [2.3.0]
### Added
- `planrunner` set CCD temperature added to fits header

## [2.2.2]
### Fixed
- Removed `definitions.py` and references to it.

## [2.2.1]
### Fixed
- `params` deprecation warning in `component` no longer appears, stopped using deprecated method.

## [2.2.0]
### Added
- `planrunner` separate flat and domeflat flags, added filter offset kwarg
- `planrunner` added filter offset kwarg
- `planrunner` error subject works now
- `planrunner` add fits list to command log
- `ocaboxapi` add nasmyth port api and autoslew errors read api
### Changed
- `planrunner` better errors serve (access denied)
- `autoflat` now saves only reads higher than 0, 3-rd point is now linear

## [2.1.0]
### Added
- Served better proof_put and proof_get in `planrunner`, add access denied error serve
- add kwarg add mechanism `read_mod` to `planrunner`
### Changed
- `Wait` command arguments changed from wait to sec and from wait_sunrise to sunrise / sunset
- `Autoflat` now has 400 points of statistics
- for `planrunner` changed stream to tic.planrunner.* 

## [2.0.2]
### Changed
- Removed application configuration system using `confuse` and configuration files. From now on, creating a rare 
client will require providing appropriate configuration parameters in the constructor. 
- `Observatory` will search NATS for a predefined configuration. The existence of an open connection to nats is 
required before using the API

## [2.0.1]
- Added support for new server method `reload_config`.

## [2.0.0]
- The project was divided into `ocabox-server`, `ocabox-common` and `ocabox` (client part) parts

## [1.0.18]

### Added
- add new methods to alpaca dome driver: `domefansrunning`, `domefansrunning`, `domefansturnoff`
### Changed
- A site section has been added to the configuration, which contains the configuration of external applications. 
It will be sent to nats together with the alpacas configuration. From now on, alpaca configurations will be 
wrapped in `telescopes` sections. 
### Fixed

## [1.0.17]

### Added
- `cycle_time_calc` added sunrise and sunset
- `planrunner` added sunrise and sunset wait, seq is possible to write seq=12x(...) now
- `astroplan` add to poetry

### Changed
- `sub_camera_exposure` folders creation and symlinks moved to ofp
- `nightplan` add comment use
- `planrunner` numering is 000 instead of 00
- `cycle_time_calc` is training not only full nights, night id is jd now

### Fixed
- evening and morning autoflat canceling
- fixed `planrunner` wait ut

## [1.0.16]

### Added
- auto skyflat evening factor add
- cycle time api in `ocaboxapi`
- cycle time logging
- A mechanism has been added that will send alpaca configuration to nats at server startup
- NATS config for `TOI_Client`
- NATS rpc subject for all clients
- `ocaboxapi` dome ventilators
- `sub_camera_exposure` fits gather and saving by ofp downloader

### Changed
- skyflat dithering movement value to 8'
- `CameraExposure` changed to header beta3, fixed autoexposure skyflat no oper. skipping, get filter to header from pos
- `cycle_time_calc` telescope find changed, filter manage changed
- `ocaboxapi` - `FilterWheel` jk15 get proper filter names 

### Fixed
- `cycle_time_calc` fixed first filter pos

## [1.0.15] - 2023-08-14
### Added
- CCTV method asubscribe_ir
- `ocaboxapi.__init__` CCTV
- planrunner.command tracking=off or on or default
- Added custom `CoverCalibrator` alpaca module which has correctly working methods `opencover` and `closecover`
- Module `cycle_time_calc` added and implemented into `planrunner`
- `planrunner` get is running info
- `planrunner` added `get_value_proof`
- `planrunner` camera auto exposure info added

### Fixed
- Fixed getting values from config in method `get_app_cfg()` form `Observatory` object
- Fixed `WAIT` ut after midnight
- Fixed `ZERO` exposition time (extended to 1s)
- `planrunner` fixed altaz dithering
- `cycle_time` test, altaz distance fix
- `ocaboxapi/telescope`: `shutdown` ,`emergency_stop`, `whether_stop` fixed

## [1.0.14] - 2023-06-26
### Added
- added `Observatory.is_tic_server_available`
- added a new method GET to alpaca api `errorstring`
- added `Telescope.is_telescope_alpaca_server_available`
- Added methods to build a dictionary mapping the tree structure together with the configuration.
- added STOP, WAIT commands  to client plan runner
- ocaboxapi.Mount errorstring and cleanerror
- base_command, root class for sequences and subcommands
- night log added
- shutdown, wheather stop, emergency stop added in ocaboxapi.Telescope
- epoch option in planner
- dome_follow=off kwarg planner
- async plan runner run
- param dict in night plan dict, observer name to fits
- add SNAP command
- partly plan syntax verification

### Changed
- improved automatic skyflats time calculation (substracted bias level)
- ocaboxapi formatter cover status 4 updated
- refactor comm screen light, cover
- removed deg_str_to_deg pyaraucaria module
- new plan parsing construction - pyaraucaria issue #5

### Fixed
- Automatic skyflat time in fits header 
- Automatic skyflats time calculation (zero substract)
- Fixed internal api response type error
- Altaz dither fix
- Fixed internal api response type error
- 

## [1.0.13] - 2023-06-02
### Changed
- `Planrunner/sub_camera` exposure array delay, fix some folders creation options
- `Planrunner/sub_change_filter` changed timout
- `Planrunner/command` added mirror covers on option, domeflat light on option, dark and bias now changing filters and put
to  fits header, get rid of str coo and location

### Fixed
- Handled aioHTTP exceptions in `TreeAlpacaObservatory`

## [1.0.12] - 2023-05-22
### Changed
- planrunner command.py changed architecture for 3 methods: dark_bias, dome_flat, object_skyflat_focusing
, dithering added, focusing method changed
- planrunner sub_camera_exposure added folders creation for different commands, some minor changes
- After receiving from the server an error terminating the CycleQuery, the callbacks will be run one last time.

### Fixed
- Fixed bug with callback executor in CycleQuery when stoping 
- Fixed issues with `RequestSolver` not handling some error types.

## [1.0.11] - 2023-05-17
### Added
- An intermediary module between `Client` and `ClientAPI` and `Client` and cycle-query has been added
- Created an in-tree API based on the normal API.
- Initial support for Ubiquity CCTV camera (IR LED control)
- Reading config also from .secrets.yaml files

### Changed
- Cycle-query no longer have direct access to the `Client`. Instead, they use the new `BaseClientRequestSolver` module.
- Rebuild alpaca resource manager `ResourceManagerAlpaca`. From now on, he will also be able to perform operations 
on resources, not only to manage access to them.
- Python 3.9 is now minimal version - requirement of the `pyunifiprotect` library

## [1.0.10] - 2023-04-28
### Fixed
- Fixed the problem with waiting until the task timeout expires when the Alpaca server is not responding. From now on, 
before the task is canceled, the alpaca module will return an error saying that it cannot connect to the server.

## [1.0.9] - 2023-04-21
### Added
- Formatter for Celsius degrees and Kelvins

### Changed
- Added TIC IP to log timeout error  

## [1.0.8] - 2023-04-21
### Added
- Add to planrunner commands `DOMEFLAT`, `FOCUS`.
- Parameters dict info_callback.
- Add camera log.
- Add fits statistics.
- Add new methods to `ocaboxapi`

### Changed
- Add gain and readoutmode to fits header.
- Dome move subcommand changed.
- Saving int16 fits to side int16.
- Filter mapping.

## [1.0.7] - 2023-04-18
### Changed
- From now put response from alpaca wil be returned as single value, not dict witch all data response

## [1.0.6] - 2023-04-18
### Changed
- Upgrade version of `pyzmq` library
- method `is_access` from `access_grantor` from now will not be cachable

### Added
- added parameter in the configuration file that allows you to exclude addresses with the given regex from the 
cache memory

## [1.0.5] - 2023-04-11
### Added
- New custom command to alpaca driver

## [1.0.4] - 2023-03-31
### Added
- Added `ocaboxapi` rotator
- Added `planrunner` skip and abort in executor
- Added `planrunner` DARK, ZERO, FLAT, DOMEFLAT, SKYFLAT commands creation

### Changed
- Changed `planrunner` header and mount and camera executing

### Fixed
- Fixed `config_oca.yaml` longitude position

## [1.0.3] - 2023-03-29
### Added
- Resources in the resource manager have been extended with the `properties` parameter

## [1.0.2] - 2023-03-28
### Added
- add formatters for subframe and gain: `fmt_subframe` and `fmt_gain`


## [1.0.1] - 2023-03-27
### Added
- add new method to alpaca api `reportmaxalt`

## [1.0.0] - 2023-03-24
### Changed
- New methods in Camera `ocaboxapi`

## [0.2.4] - 2023-03-24
### Changed
- Rename class `TreeRequestAlpacaBlocker` to `TreeBaseRequestBlocker` and move it to file `tree_base_request_blocker.py`
- Minor changes in `ocaboxapi`

### Added
- Added mechanism for determining the resources available to blocks in the tree has been added. each value-providing 
block is seen as a resource, and it can be modified to be seen as multiple resources. In the future, resources can be 
used to recognize the target of the query, for example, in blocker.
- The `TreeAlpacaObservatory` block now provides a `ResourceManagerAlpaca` class to manage access to individual alpaca 
resources.
- Added a temporary mechanism to run observation plans on the client side. In the future it will be rebuilt and moved 
- to the server side.

## [0.2.3] - 2023-03-14
### Added
- Added new classes: `CoverCalibrator`, supporting alpaca components to ocaboxapi
- Added a new method to `ocaboxapi` class

### Changed
- Improved error severity handling
- changed the mechanism for closing subscriptions when the server cannot update the value due to an error. From now on, 
the subscription will be renewed when temporary errors occur.

### Fixed
- Fixed an issue with unsuccessful refreshes value counter in `TreeConditionalFreezer` resetting when a short timeout 
was set.
- Fixed bugs in module `TreeConditionalFreezer` logic

## [0.2.2] - 2023-03-07
### Added
- Added new classes: `Camera`, `FilterWheel`, `Focuser`, supporting alpaca components to ocaboxapi

### Changed
- Updated classes: `Mount`, `AccessGrantor`, `Observatory`, in ocaboxapi

## [0.2.1] - 2023-03-06
### Added
- Added a new command to `TreeBlockerAccessGrantor` that checks if the requesting user has access
### Changed
-`Client` class has been moved back to `ob` module

## [0.2.0] - 2023-03-03
### Added
- New module `ocaboxapi`. 
- Added first version of new high level client API: `Observatory`, `Telescope`, `Dome`, `AccessGrantor`, ...
- Added `ocaboxapi.formatter` module with formatters for sexadecimal values, and cover status
- The `MultipartStructure` template has been extended with a flag (`SERVICE_MSG`) redirecting messages to local 
service by the server. When the flag is set to true, messages will not go to the tree.
- Added the ability to ping the server by using internal queries to the server. That is, the ones with the 
`SERVICE_MSG` flag.
- Added methods `ping_server` to `Client` and `server_is_alive` to `ClientAPI`, which uses a new mechanism for sending 
messages to the server that allows to ping the server. Read more in the method documentation.

### Changed
- `ClientAPI` and `Client` class has been moved to new `ocaboxapi` module!

## [0.1.4] - 2023-02-25
### Added
- Added `get_cfg` methos to `ClientAPI` class. Easy access to client conf with possible default value.
- Configuration for `OcaClient`
- Configuration for the Ping-Task output interval
### Fixed
- Fixed an issue with bad error handling when incoming address is too short for `TreeAlpacaObservatory`
- Fixed issue with reporting timeout errors 4004 by `ConditionalCycleQuery`
### Changed
- `TreeBaseBrokerDefaultTarget` from now on will always forward the request to the default provider when there is a 
problem with finding the provider by address.
- Lots of logging improvements
- Change of default log-messages format (e.g. `2023-02-23 21:24:26 [INFO] [router] start main task`)

## [0.1.3] - 2023-02-13
### Added
- Added `__repr__` method to the `ValueResponse` class
### Fixed
- Fixed a problem with the request listener task in Client synchronization, where when the response from the server 
came quite quickly, the main task did not look for it in the list and waited for it until Timeout expired.

## [0.1.2] - 2023-02-10
### Added
- Added support for CoverCalibrator component to alpaca driver.
### Fixed
- Fixed an issue where tasks in the Client raced when starting and shutting down the request listener.
### Changed
- From now on, take and release user control requests must be the PUT type
- In the example server configuration, access_grantor module has been hidden behind the cache module. 
This allows you to subscribe to these values

## [0.1.1] - 2023-02-03
### Added
- Callback method to cycle query
### Fixed
- Fixed cmd_client console
### Changed
- path to test folder will be getting from project dir root instead current context

## 0.1.0 - 2023-01-05
### Added
- The first working version of the project

## 0.0.0 - 2022-04-20
### Added
- Project core files added and initialized.


[Unreleased]: https://github.com/araucaria-project/ocabox

[1.0.14]: https://github.com/araucaria-project/ocabox