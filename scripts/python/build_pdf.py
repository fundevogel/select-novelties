#! /usr/bin/python
# ~*~ coding=utf-8 ~*~

##
# Generates PDF file from a given SLA file - quick & dirty
#
# For more information,
# see https://wiki.scribus.net/canvas/Automatic_Scripter_Commands_list
#
# Usage:
# scribus -g -py pdf-gen.py --input input_file.sla --output output_file.pdf
#
# License: MIT
# (c) Martin Folkers
##

import scribus
import argparse

parser = argparse.ArgumentParser(
    description="Generates PDF file from a given SLA file - quick & dirty"
)

parser.add_argument(
    "--input",
    help="Takes SLA file under specified path",
)

parser.add_argument(
    "--output",
    help="Creates PDF file under specified path",
)

if __name__ == "__main__":
    args = parser.parse_args()

    # Generating PDF
    scribus.openDoc(args.input)
    pdf = scribus.PDFfile()

    file_name = scribus.getDocName()[:-3] + 'pdf'

    if args.output is not None:
        file_name = args.output

    pdf.thumbnails = 1
    pdf.file = file_name
    pdf.save()
    scribus.closeDoc()
