#!/usr/bin/python3

import sys
import class_file_parser

if __name__ == "__main__":
    class_file = class_file_parser.parse(sys.argv[1])
    class_file.debug_info()
