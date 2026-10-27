#!/usr/bin/python3

import argparse
import logging
import os
import sys
from lib import class_loader
from lib import jvm
from lib import run_time_data
from lib import thread


def parse_argument():
    parser = argparse.ArgumentParser(description='JVM impmentation in Python.')
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Output debug informations.'
    )
    parser.add_argument(
        '--trace',
        action='store_true',
        help='Output every executed instruction, implies --debug.'
    )
    parser.add_argument(
        '--printclass',
        action='store_true',
        help='Output class detail informations.'
    )
    parser.add_argument('--classpath', help='Java class file path name')
    parser.add_argument('--java-home', help='Java home path')
    parser.add_argument('--java-library-path', help='Java libraqry path')
    parser.add_argument('classname', help='Java class name')
    parser.add_argument(
        'args', nargs=argparse.REMAINDER, help='Arguments of main method')
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
    init_logging(args.debug or args.trace)
    thread.trace = args.trace
    class_loader.printclass = args.printclass
    logging.debug(args)
    jedy_home = os.path.dirname(os.path.realpath(__file__))
    if args.classpath:
        class_loader.classpath = args.classpath
    else:
        class_loader.classpath = os.getcwd()
    if args.java_home:
        class_loader.jrelibpath = os.path.join(args.java_home, 'lib')
    else:
        class_loader.jrelibpath = os.path.join(jedy_home, 'openjdk_jre', 'lib')
    class_loader.java_home = args.java_home
    class_loader.java_library_path = args.java_library_path
    classname = args.classname.replace('.', '/')
    logging.debug(
        f'Loading class {classname} from path {class_loader.classpath}')
    class_struct = class_loader.load_class(classname)
    if not class_struct:
        print(f'Error: Could not find or load main class {args.classname}',
              file=sys.stderr)
        sys.exit(1)
    main_thread = thread.Thread(
        classname, 'main', '([Ljava/lang/String;)V', args.args)
    run_time_data.thread_pool.append(main_thread)
    try:
        jvm.boot(main_thread)
        main_thread.run()
    except thread.JavaException:
        sys.exit(1)
    finally:
        sys.stdout.flush()
