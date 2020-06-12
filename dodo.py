#! /usr/bin/python
# ~*~ coding=utf-8 ~*~

from doit import get_var
from doit.tools import run_once

# TODO: Import only what is needed
import os  # path
import re  # sub
import sys  # stdout.write
import datetime  # datetime.now
import fileinput  # input

from slugify import slugify

from scripts.hermes import create_mail
from scripts.thoth import get_booklist, get_publishers, get_book_count


###
# CONFIG (START)
#

DOIT_CONFIG = {
    'action_string_formatting': 'old',
    'default_tasks': [
        'phase_one',
        'phase_two',
    ],
    'verbosity': 2,
}

#
# CONFIG (END)
###


###
# VARIABLES (START)
#

# CLI
config = {'issue': get_var('issue', '2020_02')}
issue = config['issue']

# Directories
home = 'issues/' + issue
src = home + '/src'
dist = home + '/dist'
meta = home + '/meta'
shared = 'shared'

# Files
base_unprocessed = dist + '/templates/unprocessed.sla'
base_processed = dist + '/templates/processed.sla'
edited_template = dist + '/templates/edited.sla'
document_file = dist + '/documents/pdf/final.pdf'

# Time
now = datetime.datetime.now()
year = str(now.year)

# Seasonal
season = 'spring' if issue[-2:] == '01' else 'autumn'

general = [
    ['hoerbuch', 15],
    ['besonderes', 14],
    ['sachbuch', 13],
    ['ab14', 12],
    ['ab12', 11],
    ['ab10', 10],
    ['ab8', 9],
    ['ab6', 8],
    ['vorlesebuch', 7],
    ['bilderbuch', 6],
    ['toddler', 5],
]

specials = [['ostern', 16]] if season == 'spring' else [
    ['kalender', 17], ['weihnachten', 16]]

categories = specials + general

# Category files
csv_files = [file[0] + '.csv' for file in categories]
csv_files_src = [src + '/csv/' + file_name for file_name in csv_files]
csv_files_dist = [dist + '/csv/' + file_name for file_name in csv_files]

#
# VARIABLES (END)
###


###
# GROUPS (START)
#

def task_phase_one():
    """
    'Phase 1' tasks: pre-stage
    """
    return {
        'actions': None,
        'task_dep': [
            'new_issue',
            'find_duplicates',
            'fetch_api',
            'detect_age_ratings',
        ]
    }


def task_phase_two():
    """
    'Phase 2' tasks: prod-stage
    """
    return {
        'actions': None,
        'task_dep': [
            'generate_partials',
            'copy_base_template',
            'import_pages',
            'replace_year',
            'prepare_editing',
        ]
    }


def task_phase_three():
    """
    'Phase 3' tasks: post-stage
    """
    return {
        'actions': None,
        'task_dep': [
            'build_pdf',
            'optimize_document',
            # 'compose_mails',
            'write_summary',
        ]
    }

#
# GROUPS (END)
###


###
# TASKS (START)
#

def task_new_issue():
    """
    Sets up new issue
    """
    return {
        'actions': ['bash scripts/new_issue.bash ' + issue],
        'targets': csv_files_src,
        'uptodate': [run_once],
    }


def task_find_duplicates():
    """
    Finds all duplicate ISBNs

    >> `ISSUE/meta/duplicates.txt`
    """
    # TODO: Run always (for the `echo`)
    # TODO: Clean
    return {
        # 'file_dep': csv_files_src,
        'actions': ['bash scripts/find_duplicates.bash ' + issue],
        'targets': [meta + '/duplicates.txt'],
        'verbosity': 2,
    }


def task_fetch_api():
    """
    Fetches bibliographic data & book covers

    ISSUE/dist/csv/example.csv` >> `ISSUE/dist/csv/example.csv`
    """
    return {
        'file_dep': csv_files_src,
        'actions': ['php scripts/fetch_api.php ' + issue],
        'targets': csv_files_dist,
    }


def task_generate_partials():
    """
    Generates template file for each category

    Using `ISSUE/dist/csv/example.csv` with either
    a) `ISSUE/src/templates/example.sla`,
    b) `ISSUE/src/templates/dataList.sla` or
    c) `shared/templates/dataList.sla` as fallback

    >> `ISSUE/dist/templates/example.sla`
    """
    for data_file in csv_files_dist:
        # Stripping path & extension
        category = os.path.basename(data_file)[:-4]

        # Add template extension
        template_name = category + '.sla'

        # Add source path
        template_file = src + '/templates/' + template_name

        # Check if per-issue template file for given category exists ..
        if os.path.isfile(template_file) is False:
            # .. if it doesn't, choose per-issue generic template file
            template_file = src + '/templates/dataList.sla'

        # Otherwise ..
        if os.path.isfile(template_file) is False:
            # .. common template file for given category
            template_file = shared + '/templates/partials/' + template_name

        # But if that doesn't exist either ..
        if os.path.isfile(template_file) is False:
            # .. ultimately resort to common generic template file
            template_file = shared + '/templates/partials/dataList.sla'

        # TODO: Maybe python function may be imported + executed directly?
        command = [
            # (1) Virtual environment python executable
            # (2) Python script `ScribusGenerator` by @berteh
            # See https:#github.com/berteh/ScribusGenerator
            '.env/bin/python',
            'scripts/vendor/berteh/scribusgenerator/ScribusGeneratorCLI.py',
            '--single',  # Single file output
            '-c ' + data_file,  # CSV file
            '-o ' + dist + '/templates/partials',  # Output directory
            '-n ' + category,  # Output filename (without extension)
            template_file,  # Template path
        ]

        yield {
            'name': data_file,
            'file_dep': [data_file, template_file],
            'actions': [' '.join(command)],
            'targets': [dist + '/templates/partials/' + category + '.sla'],
        }


def task_copy_base_template():
    """
    Sets up base template before importing category partials
    """
    # Check if per-issue base template exists
    base_template = src + '/templates/main.sla'

    if os.path.isfile(base_template) is False:
        # If it doesn't, choose common base template
        base_template = shared + '/templates/' + season + '.sla'

    return {
        'actions': [
            'cp ' + base_template + ' ' + base_unprocessed,
            'cp ' + base_template + ' ' + base_processed,
        ]
    }


def task_import_pages():
    """
    Imports category partials into base template

    `ISSUE/dist/templates/unprocessed.sla` +
    `ISSUE/dist/templates/partials/*.sla` >> `ISSUE/dist/processed.sla`
    """
    # Create import for each category partial after its designated page number
    for category, page_number in categories:
        # Define category partial
        category_file = dist + '/templates/partials/' + category + '.sla'

        # Build command
        command = [
            # (1) Python script, executed via Scribus (Flatpak)
            # (2) Uses `processed` base template version
            'flatpak run net.scribus.Scribus -g -ns -py scripts/import_pages.py',
            base_processed,
            category_file,  # Import file
            '--page ' + str(page_number),  # Page number
            '--masterpage category_' + season + '_' + category,  # Masterpage
        ]

        yield {
            'name': category_file,
            'actions': [' '.join(command)],
        }


def task_replace_year():
    """
    Inserts current year into base template

    `ISSUE/dist/templates/placeholder.sla` >> `ISSUE/dist/templates/year.sla`

    """
    def replace(path, pattern):
        file = fileinput.input(path, inplace=True)

        for line in file:
            line = re.sub(pattern, year, line)
            sys.stdout.write(line)

        file.close()

    return {
        'file_dep': [base_processed],
        'actions': [(replace, [base_processed, '%%YEAR%%'])],
    }


def task_prepare_editing():
    """
    Ensures that base template is ready for manual editing

    `ISSUE/dist/templates/processed.sla` >> `ISSUE/dist/templates/edited.sla`
    """
    # Performs nominal-actual comparison of total books
    def compare(template_file):
        # Count books - [0] = CSV, [1] = SLA
        total_csv, total_sla = get_book_count(template_file)

        # Check if they match - if not, exit
        if total_csv == total_sla:
            print 'Total books (from CSV): ' + str(total_csv)
            print 'Total books (from SLA): ' + str(total_sla)
            print 'Numbers match, you may pass!\n'
        else:
            print('Something\'s wrong - total book count doesn\'t match:')
            print 'Total books (from CSV): ' + str(total_csv)
            print 'Total books (from SLA): ' + str(total_sla)
            print('You shall not pass!\n')

            sys.exit()

    return {
        'file_dep': [base_processed],
        'actions': [
            'cp %(dependencies)s %(targets)s',
            (compare, [edited_template])
        ],
        'targets': [edited_template]
    }


def task_detect_age_ratings():
    """
    Detects improper age ratings

    >> `ISSUE/meta/age-ratings.txt`
    """
    age_ratings_file = meta + '/age-ratings.txt'

    return {
        'file_dep': csv_files_dist,
        'actions': ['bash scripts/detect_age_ratings.bash ' + issue],
        'targets': [age_ratings_file],
    }


def task_build_pdf():
    """
    Builds document from base template

    `ISSUE/dist/templates/edited.sla` >> `ISSUE/dist/documents/final.pdf`
    """
    # Build command
    command = [
        # Python script, executed via Scribus (Flatpak)
        'flatpak run net.scribus.Scribus -g -py scripts/build_pdf.py',
        '--input %(dependencies)s',  # Input file
        '--output %(targets)s',  # Output file
    ]

    return {
        'file_dep': [edited_template],
        'actions': [' '.join(command)],
        'targets': [document_file]
    }


def task_optimize_document():
    """
    Optimizes document for smaller file size

    `ISSUE/dist/documents/pdf/bloated.pdf` >> `ISSUE/dist/optimized.pdf`
    """
    # Season identifier
    identifier = 'fruehjahr' if season == 'spring' else 'herbst'

    # Image resolutions
    resolutions = [
        '50',   # 3XS
        '75',   # XXS
        '100',  # XS
        '150',  # S
        '200',  # M
        '250',  # L
        '300',  # XL
        '400',  # XXL
        '500',  # 3XL
    ]

    # TODO: Keep order
    for resolution in resolutions:
        # Craft output path
        optimized_file = home + '/'  # Add path
        optimized_file += 'buchempfehlungen-' + identifier  # Add season
        optimized_file += '-' + year + '_' + resolution + '.pdf'

        # Build command
        command = [
            'gs',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dConvertCMYKImagesToRGB=true',
            '-dSubsetFonts=true',
            '-dCompressFonts=true',
            '-dPDFSETTINGS=/printer',
            '-dDownsampleColorImages=true',
            '-dDownsampleGrayImages=true',
            '-dDownsampleMonoImages=true',
            '-dColorImageResolution=' + resolution,
            '-dGrayImageResolution=' + resolution,
            '-dMonoImageResolution=' + resolution,
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            '-sOutputFile=%(targets)s',
            '-c .setpdfwrite',
            '-f %(dependencies)s',
        ]

        yield {
            'name': [optimized_file],
            'file_dep': [document_file],
            'actions': [' '.join(command)],
            'targets': [optimized_file],
        }


def task_write_summary():
    """
    Lists all books, sorted by publisher

    >> `ISSUE/meta/summary.txt`
    """
    def summarize(template_file):
        # Extract books from template
        books = get_booklist(template_file)

        # Select publishers
        publishers = get_publishers(books)

        with open(meta + '/summary.txt', 'w') as file:
            for publisher in publishers:
                file.write(publisher + ':\n')

                for book in books:
                    if book[1] == publisher:
                        author = book[2]
                        title = book[3]
                        page_number = book[4]

                        file.write(
                            author + ' - "' + title + '" auf Seite ' +
                            str(page_number) + '\n'
                        )

                file.write('\n')

    return {
        # 'file_dep': [edited_template],
        'actions': [(summarize, [edited_template])],
        'targets': [meta + '/summary.txt'],
    }


# def task_compose_mails():
#     """
#     Drafts mail files for publishers

#     >> `ISSUE/dist/documents/mails/publisher.eml`
#     """
#     # Extract books from template
#     books = get_booklist(edited_template)

#     # Season identifier
#     identifier = 'Frühling' if season == 'spring' else 'Herbst'

#     # Select publishers
#     publishers = get_publishers(books)

#     for publisher in publishers:
#         text_block = []

#         for book in books:
#             if book[1] == publisher:
#                 author = book[2]
#                 title = book[3]
#                 page_number = book[4]

#                 text_block.append(
#                     author + ' - "' + title + '" auf Seite ' +
#                     str(page_number) + '<br>'
#                 )

#         # Craft output path
#         mail_file = dist + '/documents/mails/'  # Add path
#         mail_file += slugify(publisher) + '.eml'

#         subject = 'Empfehlungsliste ' + identifier + ' ' + year
#         # TODO: Variable text - autumn is quite different!
#         text = '\n'.join(text_block)

#         yield {
#             'name': mail_file,
#             # 'file_dep': [edited_template],
#             'actions': [(create_mail, [], {
#                 'subject': subject,
#                 'text': text,
#                 'output_path': mail_file,
#             })],
#             'targets': [mail_file],
#         }

#
# TASKS (END)
###


###
# HELPERS (START)
#

def task_generate_single():
    """
    Generates single template file for custom category

    Behaves like `generate_partials`, but for a single category
    """
    # Stripping path & extension
    category = get_var('cat', '')

    # Define data file
    data_file = dist + '/csv/' + category + '.csv'

    # Add template extension
    template_name = category + '.sla'

    # Add source path
    template_file = src + '/templates/' + template_name

    # Check if per-issue template file for given category exists ..
    if os.path.isfile(template_file) is False:
        # .. if it doesn't, choose per-issue generic template file
        template_file = src + '/templates/dataList.sla'

    # Otherwise ..
    if os.path.isfile(template_file) is False:
        # .. common template file for given category
        template_file = shared + '/templates/partials/' + template_name

    # But if that doesn't exist either ..
    if os.path.isfile(template_file) is False:
        # .. ultimately resort to common generic template file
        template_file = shared + '/templates/partials/dataList.sla'

    # TODO: Maybe python function may be imported + executed directly?
    command = [
        # (1) Virtual environment python executable
        # (2) Python script `ScribusGenerator` by @berteh
        # See https:#github.com/berteh/ScribusGenerator
        '.env/bin/python',
        'scripts/vendor/berteh/scribusgenerator/ScribusGeneratorCLI.py',
        '--single',  # Single file output
        '-c ' + data_file,  # CSV file
        '-o ' + dist + '/templates/partials',  # Output directory
        '-n ' + category,  # Output filename (without extension)
        template_file,  # Template path
    ]

    return {
        # 'file_dep': [data_file, template_file],
        'actions': [' '.join(command)],
        'targets': [dist + '/templates/partials/' + category + '.sla'],
    }

#
# HELPERS (END)
###
