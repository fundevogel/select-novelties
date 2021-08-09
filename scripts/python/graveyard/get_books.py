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
import glob
import os
import sys

from slugify import slugify

from lib.hermes import create_mail
from lib.thoth import get_booklist


def count_lines(file_path):
    with open(file_path) as file:
        for index, line in enumerate(file):
            pass

    return index + 1


def total_lines(files):
    number_list = []

    for file in files:
        number_list.append(count_lines(file) - 1)

    return sum(number_list)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="List all books and their page numbers from our SLA files"
    )

    parser.add_argument(
        "--input", help="SLA file being processed for ISBNs"
    )

    parser.add_argument(
        "--subject", default="",
        help="Subject"
    )

    args = parser.parse_args()

    dist_dir = os.path.dirname(os.path.dirname(args.input))
    mail_dir = dist_dir + '/documents/mails/'

    # Getting total number of books
    # (1) .. from CSV
    csv_files = glob.glob(dist_dir + '/csv/*.csv')
    total_csv_books = total_lines(csv_files)

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

    # Extract publishers
    publishers = sorted([book[1] for book in book_list])

    for publisher in publishers:
        print(publisher)

    # Remove duplicates
    publishers = [publisher for index, publisher in enumerate(
        publishers) if index == publishers.index(publisher)]

    for publisher in publishers:
        print(publisher)

    with open(os.path.abspath(dist_dir + '/../meta/summary.txt'), 'w') as file:
        for publisher in publishers:
            publisher_books = []

            file.write(publisher + ':\n')

            for book in book_list:
                if book[1] == publisher:
                    author = book[2]
                    title = book[3]
                    page_number = book[4]

                    publisher_books.append(
                        author + ' - "' + title + '" auf Seite ' +
                        str(page_number) + '<br>'
                    )

                    file.write(
                        author + ' - "' + title + '" auf Seite ' +
                        str(page_number) + '\n'
                    )

            file.write('\n')

            create_mail(
                output_file=mail_dir + slugify(publisher) + '.eml',
                subject=args.subject,
                text='\n'.join(publisher_books)
            )
