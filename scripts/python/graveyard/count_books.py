#! /usr/bin/python
# ~*~ coding=utf-8 ~*~

import os
import glob


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
    books = extract_books(input_file)
    total_sla_books = len(books)

    return [total_csv_books, total_sla_books]
