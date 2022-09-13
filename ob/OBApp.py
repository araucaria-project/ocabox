import logging
import argparse
import threading
from functools import cached_property

from ob.ob_config import SingletonConfig
from ocabox_bases import __version__


class OBApp(object):
    """OBApp class - common services for all scripts

    OBApp provides:

    - common command line arguments and arguments handling
    - logger configuration
    """

    def __init__(self, description=None) -> None:
        super().__init__()

        self.logger = logging.getLogger('app')
        self._args = None
        self._machine = None
        self.description = description

    def parse_args(self, argv=()):
        """Parses program args, sets up logger level according to --verbose"""
        self._args = self.parser.parse_args(argv)
        if self._args.verbose == 1:
            logging.basicConfig(level=logging.INFO)
            logging.getLogger().setLevel(logging.INFO)
            self.logger.setLevel(logging.INFO)
        if self._args.verbose > 1:
            logging.basicConfig(level=logging.DEBUG)
            logging.getLogger().setLevel(logging.DEBUG)
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug('Loglevel set to DEBUG')
        return self._args

    @property
    def args(self):
        if self._args is None:
            with threading.Lock():
                if self._args is None:
                    self.parse_args()
        return self._args

    @cached_property
    def parser(self) -> argparse.ArgumentParser:
        return self.create_commandline_parser()

    def create_commandline_parser(self, description=None, epilog=None, add_help=False):
        if epilog is None:
            epilog = ("configuration files order: \n  " +
                      "\n  ".join(SingletonConfig.get_config_files()) +
                      "\n\nOB: ocabox {} by Araucaria Project, AkondLab, CAMK (mkalusz@camk.edu.pl)"
                      .format(__version__)
                      )
        elif not epilog:
            epilog = None  # epilog == False  => do not present any
        if not description:
            description = self.description if self.description else 'FITS warehouse tool'

        # noinspection PyTypeChecker
        return argparse.ArgumentParser(description=description,
                                       epilog=epilog,
                                       formatter_class=argparse.RawDescriptionHelpFormatter,
                                       add_help=add_help)

    def add_commandline_misc_group(self, parser: argparse.ArgumentParser = None,
                                   verbose=True, addhelp=True):
        """Adds --help, --verbose options, common to all scripts"""
        if not parser:
            parser = self.parser

        group_misc = parser.add_argument_group('misc arguments')

        # Optional verbosity counter (eg. -v, -vv, -vvv, etc.)
        if addhelp:
            group_misc.add_argument(
                "-h", "--help",
                action="help",
                help="show this help message and exit")
        if verbose:
            group_misc.add_argument(
                "-v", "--verbose",
                action="count",
                default=0,
                help="log level (-v for INFO, -vv for DEBUG)")
        group_misc.add_argument(
            "--version",
            action="version",
            version="%(prog)s (version {version})".format(version=__version__))

    def add_help_section(self, title: str, content: str):
        self.parser.epilog = '{}\n{}\n\n{}'.format(title, content.strip('\n'), self.parser.epilog)
