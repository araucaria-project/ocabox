# Ocabox

The project is a client of the `octabox-server`. It contains an API and the necessary elements for communication.

## Installation

### Install with poetry

First, make sure you have poetry installed. For this, use the command:
```bash
poetry --version
```
If the poetry version is displayed, you can proceed to the next step. Otherwise, install poetry first.
In the next step, download and go to the main directory of the project:
```bash
  git clone https://github.com/araucaria-project/ocabox.git
  cd ocabox/
```
Next install requirements
```bash
  poetry install
```
If you also want to run examples of using the program then instead of the above command you have to use.
```bash
  poetry install --extras "examples"  
```

## Usage/Examples

If you installed the project correctly, you can run one of the available scripts. To do this, execute the command:
```bash
  poetry run <script_name> <params>
```
available scripts

| Script name       | Description                                                                                      | Params                              |
|-------------------|--------------------------------------------------------------------------------------------------|-------------------------------------|
| tests             | Run all unit test. Read [Running Tests](#running-tests) for mor <br/>information                 |                                     |
| cmd_client        | Run CMD client console                                                                           |                                     |
| cmd_simple_client | Run CMD client single command                                                                    | Type '--help' to see all parameters |

## Configuration

The default configuration is stored in the `ob/config.yaml` file. It can be overwritten by other configuration files in 
the `ob/configuration/` directory. There are also scripts that build the application in this directory. By default, 
the `ob/configuration/config.yaml` and `/etc/ocabox/config.yaml` files (if exist) is imported and overwrites the default configuration. Files with different 
names must be explicitly added in the build script or client application. It is recommended to keep the configuration 
in the `ob/configuration/config.yaml` file, the file must be created during the first installation.

The configuration file is divided into sections. They can be overwritten in full or in parts. 

### Client

#### client
In the `client` section, network socket parameters and general request parameters for clients are configured.

For example, to configure client class that has name `MySampleClientName`:

```yaml
client:
  MySampleClientName:
    port: 5559
    url: 192.168.0.0
    protocol: tcp
    timeout: 30
```
* `port` - port where requests will be sent
* `url` - url address
* `protocol` - used protocol
* `timeout` - timeout after which the query expires and is canceled

#### comunication
In this model, the configuration of various types of queries is included. Among others, recurring queries (subscription).
The configuration is the same as in the other sections.

## Running Tests

If you installed the project correctly, you can run all tests by execute the command:
```bash
  poetry run tests
```

## License
The [MIT](LICENSE) License
