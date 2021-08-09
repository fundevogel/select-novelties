#! /usr/bin/python
# ~*~ coding=utf-8 ~*~

##
# Deletes page from an `.sla` file
#
# For more information,
# see https://wiki.scribus.net/canvas/Automatic_Scripter_Commands_list
#
# Usage:
# scribus -g -py delete-page.py base_file.sla --page INT
#
# License: MIT
# (c) Martin Folkers
##

import os
import scribus
import argparse

parser = argparse.ArgumentParser(
    description="Deletes page from an `.sla` file"
)

parser.add_argument(
    "file",
    default=None,
    help="SLA file to be processed",
)

parser.add_argument(
    "--page",
    type=int,
    help="Number of pages being deleted",
)


if __name__ == "__main__":
    args = parser.parse_args()

    # Open document
    scribus.openDoc(os.path.abspath(args.file))

    # Delete page
    scribus.deletePage(args.page)

    # Save & close document
    scribus.saveDoc()
    scribus.closeDoc()
