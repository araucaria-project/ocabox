# Changelog
All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.2.2] - 2023-03-07
## Added
- Added new classes: `Camera`, `FilterWheel`, `Focuser`, supporting alpaca components to ocaboxapi

## Changed
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

[0.2.2]: https://github.com/araucaria-project/ocabox