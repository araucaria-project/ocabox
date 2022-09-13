#!/usr/bin/env python
import sys
from ob.cmd_client import CMD_Client


def main(argv):
    """Command line entry point"""

    cmd_client = CMD_Client()
    cmd_client.main_method(argv[1:])


if __name__ == "__main__":
    retcode = main(sys.argv)
    sys.exit(retcode)
