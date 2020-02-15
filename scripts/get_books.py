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

import argparse
import os
import sys
import subprocess
from slugify import slugify

from lib.hermes import create_mail
from lib.thoth import get_booklist

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="List all books and their page numbers from our SLA files"
    )

    parser.add_argument(
        "--input", help="File being processed for ISBNs"
    )

    parser.add_argument(
        "--subject", help="Subject"
    )

    args = parser.parse_args()

    # Getting total number of books
    # (1) .. from CSV
    here = os.path.dirname(os.path.realpath(__file__))
    csv_path = os.path.dirname(args.input)
    total_csv_books = int(subprocess.check_output(
        'bash ' + here + '/count_books.bash ' + csv_path, shell=True
    ))

    # (2) .. from SLA
    book_list = get_booklist(args.input)
    total_sla_books = len(book_list)

    # (3) Checking if they match - if not, exit
    if total_sla_books == total_csv_books:
        print 'Total books (from CSV): ' + str(total_csv_books)
        print 'Total books (from SLA): ' + str(total_sla_books)
        print 'Numbers match, you may pass!\n'
    else:
        print('Something\'s wrong - total book count doesn\'t match:')
        print 'Total books (from CSV): ' + str(total_csv_books)
        print 'Total books (from SLA): ' + str(total_sla_books)
        print('You shall not pass!\n')

        sys.exit()

    # Extract
    publishers = [book[1] for book in book_list]
    publishers = [publisher for index, publisher in enumerate(
        publishers) if index == publishers.index(publisher)]

    for publisher in publishers:
        print publisher + ':'

        for book in book_list:
            if book[1] == publisher:
                author = book[2]
                title = book[3]
                page_number = book[4]

                print(
                    author + ' - "' + title + '" auf Seite ' + str(page_number)
                )

        print('\n')

    file_dir = os.path.dirname(os.path.dirname(args.input))
    mail_dir = file_dir + '/mails/'

    for publisher in publishers:
        publisher_books = []

        for book in book_list:
            if book[1] == publisher:
                author = book[2]
                title = book[3]
                page_number = book[4]

                publisher_books.append(
                    author + ' - "' + title + '" auf Seite ' +
                    str(page_number) + '<br>'
                )

        create_mail(
            output_file=mail_dir + slugify(publisher) + '.eml',
            subject=args.subject,
            text='\n'.join(publisher_books)
        )
