#!/usr/bin/python3

import argparse
import logging
import sys
import class_file_parser


def parse_argument():
    parser = argparse.ArgumentParser(description='JVM impmentation in Python.')
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Output debug informations.'
    )
    parser.add_argument('class_file', help='Java class file path name')
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
    class_file = class_file_parser.parse(args.class_file)
    class_file.debug_info()
