#! /usr/bin/python
# ~*~ coding=utf-8 ~*~

##
# Replaces all instances in a file with the current year
#
# Usage:
# python file.txt --pattern %YEAR%
#
# License: MIT
# (c) Martin Folkers
##

import argparse
import datetime
import fileinput
import re
import sys


parser = argparse.ArgumentParser(
    description="Replaces all instances in a file with the current year"
)

parser.add_argument(
    "files", nargs="*", default=None, help="File(s) that should be processed",
)

parser.add_argument(
    "--pattern", help="Pattern to be replaced"
)


def replace(file_name, pattern, value=''):
    file = fileinput.input(file_name, inplace=True)
    for line in file:
        replacement = value
        line = re.sub(pattern, replacement, line)
        sys.stdout.write(line)
    file.close()


if __name__ == "__main__":
    args = parser.parse_args()

    if args.pattern is None:
        print('No pattern specified, exiting ..')
        sys.exit()

    now = datetime.datetime.now()

    for file in args.files:
        replace(file, args.pattern, str(now.year))
