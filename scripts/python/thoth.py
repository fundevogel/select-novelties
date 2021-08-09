#! /usr/bin/python
# ~*~ coding=utf-8 ~*~

import os
import glob
import pandas

from lxml import etree
from operator import itemgetter


def _swap_name(name):
    # Split
    name_list = str(name).split(', ')

    # Reverse
    name_list_reversed = list(reversed(name_list))

    # Join
    new_name = ' '.join(name_list_reversed)

    return new_name


def swap_name(name):
    # Two or more names
    if ';' in str(name):
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


def get_page_number(data, isbn):
    for element in data:
        if element.attrib['CH'][0:17] == isbn:
            parent = element.xpath('./../..')
            page = int(parent[0].attrib['OwnPage'])

            return page + 1


def get_booklist(input_file):
    # Parsing Scribus template file
    tree = etree.parse(input_file)
    root = tree.getroot()
    data = root.findall('.//PAGEOBJECT/StoryText/ITEXT')

    # Parsing CSV data files
    file_path = os.path.dirname(os.path.dirname(input_file))
    csv_path = file_path + '/csv/*.csv'
    csv_files = glob.glob(csv_path)

    csv_list = []

    for csv_file in csv_files:
        csv_data = pandas.read_csv(csv_file, index_col=None, header=0)
        csv_list.append(csv_data)

    books_data = pandas.concat(csv_list, axis=0, ignore_index=True, sort=True)
    data_frame = pandas.DataFrame(
        books_data, columns=['ISBN', 'Verlag', 'AutorIn', 'Titel']
    )
    book_list = data_frame.values.tolist()

    # Processing books
    new_book_list = []

    # Adding page number
    for book in book_list:
        new_book_list.append(list([
            book[0],
            book[1],
            swap_name(book[2]),
            book[3],
            get_page_number(data, book[0])
        ]))

    # Sorting lists: (1) publisher, (4) page number, (2) author
    sorted_book_list = list(sorted(new_book_list, key=itemgetter(1, 4, 2)))

    return sorted_book_list


def get_publishers(books):
    # Build sorted list of publishers
    publishers = [book[1] for book in books]

    # Remove duplicates
    publishers = [publisher for index, publisher in enumerate(
        publishers) if index == publishers.index(publisher)]

    # Sort case-insensitive (python2 version)
    # For future releases supporting python3, see
    # https://docs.python.org/3/library/stdtypes.html#str.casefold
    return sorted(publishers, key=lambda s: s.lower())


def count_lines(file_path):
    with open(file_path) as file:
        for index, line in enumerate(file):
            pass

    return index + 1


def total_lines(files):
    numbers = []

    for file in files:
        numbers.append(count_lines(file) - 1)

    return sum(numbers)


def get_book_count(input_file):
    dist_dir = os.path.dirname(os.path.dirname(input_file))

    # Getting total number of books
    # (1) .. from CSV by extracting books from existing `csv` files
    csv_files = glob.glob(dist_dir + '/csv/*.csv')
    total_csv_books = total_lines(csv_files)

    # (2) .. from SLA by extracting books from template
    books = get_booklist(input_file)
    total_sla_books = len(books)

    return [total_csv_books, total_sla_books]
