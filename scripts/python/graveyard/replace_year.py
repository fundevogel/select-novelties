#! /usr/bin/python
# ~*~ coding=utf-8 ~*~

##
# Replaces all instances in a file with the current year
#
# Usage:
# python document.sla --pattern %%YEAR%%
#
# License: MIT
# (c) Martin Folkers
##

import os
import re
import sys
import argparse
import datetime
import fileinput

parser = argparse.ArgumentParser(
    description="Replaces all instances in a file with the current year"
)

parser.add_argument(
    "files", nargs="*", default=None, help="File(s) that should be processed",
)

parser.add_argument(
    "--pattern", default=None,
    help="Pattern to be replaced"
)


def replace(file_name, pattern):
    path = os.path.abspath(file_name)
    file = fileinput.input(path, inplace=True)

    now = datetime.datetime.now()

    for line in file:
        line = re.sub(pattern, str(now.year), line)
        sys.stdout.write(line)
    file.close()


if __name__ == "__main__":
    args = parser.parse_args()

    if args.pattern is None:
        print('No pattern specified, exiting ..')
        sys.exit()

    for file in args.files:
        replace(file, args.pattern)
