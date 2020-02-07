#!/usr/bin/env python

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

import argparse
import os
import scribus

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


args = parser.parse_args()


# Generating PDF
scribus.openDoc(args.input)
pdf = scribus.PDFfile()

file_name = os.path.splitext(scribus.getDocName())[0] + ".pdf"

if args.output is not None:
    file_name = args.output

pdf.file = file_name
pdf.save()
scribus.closeDoc()
