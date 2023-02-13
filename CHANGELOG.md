# Changelog
All notable changes to this project will be documented in this file.


## [Unreleased]

## [0.1.3] - 2023-02-13
### Added
- Added support for CoverCalibrator component to alpaca driver.
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

[0.1.3]: https://github.com/araucaria-project/ocabox