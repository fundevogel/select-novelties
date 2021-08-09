#! /usr/bin/python
# ~*~ coding=utf-8 ~*~

##
# Imports all pages of an `.sla` file into another one
#
# For more information,
# see https://wiki.scribus.net/canvas/Automatic_Scripter_Commands_list
#
# Usage:
# scribus -g -py import-pages.py base_file.sla import_pages.sla
#
# License: MIT
# (c) Martin Folkers
##

import os
import scribus
import argparse

parser = argparse.ArgumentParser(
    description="Imports all pages of an `.sla` file into another one"
)

parser.add_argument(
    "files", nargs="*",
    default=None,
    help="SLA files to be processed",
)

parser.add_argument(
    "--page",
    type=int,
    help="Pages are imported before / after this page",
)

parser.add_argument(
    "--before",
    action="store_true",
    help="Imports pages before instead of after",
)

parser.add_argument(
    "--masterpage",
    help="Applies given master page to imported pages"
)

parser.add_argument(
    "--output", default=None,
    help="Creates new SLA file under specified path",
)


def get_pages_range(sla_file):
    scribus.openDoc(sla_file)
    page_count = range(1, scribus.pageCount() + 1)
    scribus.closeDoc()

    return tuple(page_count)


if __name__ == "__main__":
    args = parser.parse_args()

    # Variables
    base_file = os.path.abspath(args.files[0])
    import_file = os.path.abspath(args.files[1])
    page_number = args.page - 1
    insert_position = 0 if args.before is True else 1  # 0 = before; 1 = after
    master_page = args.masterpage
    total_pages = get_pages_range(import_file)

    # Output path
    output_file = args.output

    if output_file is not None:
        output_file = os.path.abspath(args.output)

    # Importing `import_file`
    scribus.openDoc(base_file)
    scribus.importPage(
        import_file, total_pages, 1, insert_position, page_number
    )

    # Applying masterpage(s)
    if master_page is not None:
        for number in range(page_number + 2, page_number + len(total_pages) + 2):
            scribus.applyMasterPage(master_page, number)

    # Either overwriting `base_file` ..
    if output_file is None:
        scribus.saveDoc()
    # .. or creating new `output` file (requires `--output`)
    else:
        scribus.saveDocAs(output_file)

    scribus.closeDoc()
