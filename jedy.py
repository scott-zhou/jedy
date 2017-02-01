#!/usr/bin/python3

import argparse
import logging
import sys
import os
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
    parser.add_argument('--classpath', help='Java class file path name')
    parser.add_argument('--java-home', help='Java home path')
    parser.add_argument('--java-library-path', help='Java libraqry path')
    parser.add_argument('classname', help='Java class name')
    return parser.parse_args()


def init_logging(debug: bool):
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
    logging.debug(args)
    if args.classpath:
        class_loader.classpath = args.classpath
    else:
        class_loader.classpath = os.path.dirname(os.path.realpath(__file__))
    class_loader.java_home = args.java_home
    class_loader.java_library_path = args.java_library_path
    class_struct = class_loader.load_class(args.classname)
    class_struct.debug_info()
    main_thread = thread.Thread(args.classname, 'main', '([Ljava/lang/String;)V', [''])
    run_time_data.thread_pool.append(main_thread)
    main_thread.run()
