# Changelog
All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- CCTV method asubscribe_ir
- ocaboxapi.__init__ CCTV


## [1.0.14] - 2023-06-26
### Added
- added `Observatory.is_tic_server_available`
- added a new method GET to alpaca api `errorstring`
- added `Telescope.is_telescope_alpaca_server_available`
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

[1.0.8]: https://github.com/araucaria-project/ocabox