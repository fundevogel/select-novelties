#! /usr/bin/python

import argparse
import sys
import subprocess
import pandas as pd
import glob
from operator import itemgetter
from lxml import etree as et

parser = argparse.ArgumentParser(description="Find ISBNs in SLA files")

parser.add_argument(
    "--input", help="File being processed for ISBNs"
)

args = parser.parse_args()


# Scribus
tree = et.parse(args.input)
root = tree.getroot()
data = root.findall('.//PAGEOBJECT/StoryText/ITEXT')



csv_files = glob.glob('../csv/*.csv')

csv_list = []

for csv_file in csv_files:
    csv_data = pd.read_csv(csv_file, index_col=None, header=0)
    csv_list.append(csv_data)

books_data = pd.concat(csv_list, axis=0, ignore_index=True)
data_frame = pd.DataFrame(books_data, columns= ['Verlag', 'AutorIn', 'Titel', 'ISBN'])
books_list = data_frame.values.tolist()

books_list = list(sorted(books_list, key=itemgetter(0,1)))


def get_page_number(data, isbn):
    for element in data:
        if element.attrib['CH'][0:17] == isbn:
            parent = element.xpath('./../..')
            page = int(parent[0].attrib['OwnPage'])

            return page + 1

def _swap_name(name):
    # Split
    name_list = name.split(', ')

    # Reverse
    name_list_reversed = list(reversed(name_list))

    # Join
    new_name = ' '.join(name_list_reversed)

    return new_name


def swap_name(name):
    # Two or more names
    if ';' in name:
        new_name_list = []
        name_list = name.split('; ')

        for name in name_list:
            # Swap
            new_name = _swap_name(name)

            # Append
            new_name_list.append(new_name)

        # Join two or more names
        new_name = ' & '.join(new_name_list)

        return new_name

    # Swap
    new_name = _swap_name(name)

    return new_name


if __name__ == "__main__":
    csv_rows = subprocess.check_output('cat ../csv/*.csv | wc -l', shell=True)
    csv_headers = subprocess.check_output('ls ../csv/ | wc -l', shell=True)
    total_books_csv = int(csv_rows) - int(csv_headers)

    total_books_sla = len(books_list)


    if total_books_sla == total_books_csv:
        print 'Total books (from CSV): ' + str(total_books_csv)
        print 'Total books (from SLA): ' + str(total_books_sla)
        print 'Numbers match, you may pass!\n'
    else:
        print('Something\'s wrong - total book count doesn\'t match:')
        print 'Total books (from CSV): ' + str(total_books_csv)
        print 'Total books (from SLA): ' + str(total_books_sla)
        print('You shall not pass!\n')

        sys.exit()

    for book in books_list:
        publisher = book[0]
        author = swap_name(book[1])
        title = book[2]
        isbn = book[3]

        page_number = get_page_number(data, isbn)

        print(publisher + ': ' + author + ' - "' + title + '" auf Seite ' + str(page_number))
