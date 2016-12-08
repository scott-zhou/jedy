#!/usr/bin/python3

import argparse
import logging
import sys
from lib import class_loader
from lib import run_time_data
from lib import thread


def parse_argument():
    parser = argparse.ArgumentParser(description='JVM impmentation in Python.')
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Output debug informations.'
    )
    parser.add_argument('--classfile', help='Java class file path name')
    parser.add_argument('classname', help='Java class name')
    return parser.parse_args()


def init_logging(debug):
    fmt = '%(levelname)s: %(message)s'
    formatter = logging.Formatter(fmt)
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(formatter)

    logger = logging.getLogger()
    if debug:
        logger.setLevel(logging.DEBUG)
        stdout.setLevel(logging.DEBUG)

    logger.addHandler(stdout)


if __name__ == "__main__":
    args = parse_argument()
    init_logging(args.debug)
    class_struct = class_loader.parse(args.classfile)
    class_struct.debug_info()
    run_time_data.method_area[class_struct.name()] = class_struct
    main_thread = thread.Thread()
    run_time_data.thread_pool.append(main_thread)
    main_thread.run(args.classname)
