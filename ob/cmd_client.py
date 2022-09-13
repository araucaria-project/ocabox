#!/usr/bin/env python
import asyncio
import sys
from ob.OBApp import OBApp
from ob.comunication.client_api import ClientAPI
from ob.comunication.comunication_error import CommunicationRuntimeError, CommunicationTimeoutError
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueResponse


def add_client_arguments(app: OBApp):
    app.parser.add_argument('address')
    options = app.parser.add_argument_group('request options')
    options.add_argument('-w', '--no_wait',
                         action='store_true',
                         help='This flag when is set request is sent to the server and no wait for response.')
    options.add_argument('-T', '--type',
                         type=str,
                         default='GET',
                         help='Possible type request. Default it is GET type. Possible type: GET, PUT, EXECUTE')
    options.add_argument('-t', '--timeout',
                         type=float,
                         default=None,
                         help='Absolute timestamp after which it will stop expecting a response')

    options.add_argument('-O', '--time_of_data',
                         type=float,
                         default=None,
                         help='Absolute timestamp which the data are to come. It is used to download archive data')
    options.add_argument('-o', '--time_of_data_tolerance',
                         type=float,
                         default=None,
                         help='time tolerance of the data. Part of the data is stored in the cache and sent to clients '
                              'if it is within this tolerance.')
    options.add_argument('-p', '--parameter',
                         metavar=('KEY', 'VALUE'),
                         nargs=2, action='append',
                         help='Request parameters')

    app.add_commandline_misc_group()
    app.add_help_section('examples:', '''
        Slew dome to azimuth:
            sample_telescope.dibi.dome.slewtoazimuth -T PUT -p Azimuth 56
        Get dome name:
            sample_telescope.dibi.dome.name

        to "Learn by Example" visit:
        https://github.com/araucaria-project/ocabox
            ''')


class CMD_Client(OBApp):
    BREAK_COMMANDS = ['end', 'quit', 'escape', 'exit']

    def __init__(self):
        super().__init__(description='This is a command line simple client for ocabox application.\n'
                                     'Use -v to see additional info')
        add_client_arguments(self)
        self.c_api = ClientAPI(name='CMD_client', user_name='CMD_client', user_description='CMD client command line '
                                                                                           'service')
        self._cursor = '<CMD_Client>>:'

    def run_CMD(self):

        try:
            while True:
                input_command = self._read_input()
                if len(input_command) <= 0:
                    continue
                elif self.is_break_command(input_command[0]):
                    break
                # TODO complete a regular referral client when needed. At this time, the program ends after giving
                #  incorrect parameters. Perhaps the argparse should be changed
                self.parse_args(input_command)
                self._solve_command()
        except KeyboardInterrupt:
            pass
        return 0

    @classmethod
    def is_break_command(cls, val: str) -> bool:
        for bc in cls.BREAK_COMMANDS:
            if bc == val:
                return True
        return False

    def _read_input(self):
        print(self._cursor, end='')
        f = input()
        return f.split()

    def main_method(self, argv):
        self.parse_args(argv)
        return self._solve_command()

    def _solve_command(self):
        # address
        address = self.args.address
        if not address:
            self.logger.error('address can not be empty')
            return 0

        # time_of_data
        time_of_data = self.args.time_of_data

        # time_of_data_tolerance
        time_of_data_tolerance = self.args.time_of_data_tolerance

        # request_timeout
        request_timeout = self.args.timeout

        # parameters
        parameters = {}
        if self.args.parameter:
            for k, v in self.args.parameter:
                parameters[k] = v

        # no_wait
        no_wait = self.args.no_wait

        request_type = self.args.type
        if request_type == 'GET':
            method = self.c_api.get_async(address=address,
                                          time_of_data=time_of_data,
                                          time_of_data_tolerance=time_of_data_tolerance,
                                          request_timeout=request_timeout,
                                          parameters_dict=parameters)
        elif request_type == 'PUT':
            method = self.c_api.put_async(address=address,
                                          time_of_data=time_of_data,
                                          time_of_data_tolerance=time_of_data_tolerance,
                                          request_timeout=request_timeout,
                                          parameters_dict=parameters,
                                          no_wait=no_wait)
        else:
            self.logger.error('Unrecognized type request, use --help to read about possible type requests.')
            return 0

        try:
            result = asyncio.run(method)
            if isinstance(result, ValueResponse):
                print(f"Value: {result.value.v if isinstance(result.value, Value) else result.value}",
                      '\n',
                      f"Error: {result.error if not result.status else None}")
            else:
                self.logger.error('Unrecognized type response.')
        except CommunicationRuntimeError as e:
            self.logger.error(e)
            return 0
        except CommunicationTimeoutError as e:
            self.logger.error(e)
            return 0
        except Exception as e:
            self.logger.error(e)
            return 0
        except KeyboardInterrupt as e:
            self.logger.error(f'Request was stop by KeyboardInterrupt')
            return 0
        finally:
            del self.c_api
        return 1


if __name__ == "__main__":
    client = CMD_Client()
    retcode = client.run_CMD()
    sys.exit(retcode)
