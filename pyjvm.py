#!/usr/bin/python3

import sys
import class_file_parser

if __name__ == "__main__":
    with open(sys.argv[1], 'rb') as jvm_file:
        class_file = class_file_parser.ClassFile(jvm_file)
        class_file.debug_info()
