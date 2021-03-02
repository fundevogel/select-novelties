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
config = {'issue': get_var('issue', '2021_01')}
issue = config['issue']

# Directories
home = 'issues/' + issue
src = home + '/src'
dist = home + '/dist'
meta = home + '/meta'
shared = 'shared'

# Files
base_template = dist + '/templates/base.sla'
edited_template = dist + '/templates/edited.sla'
document_file = dist + '/documents/pdf/final.pdf'

# Time
now = datetime.datetime.now()

# Get this & next year
year = str(now.year)
next_year = str(now.year + 1)

# Season
season = 'spring' if issue[-2:] == '01' else 'autumn'
season_de = 'Frühjahr' if season == 'spring' else 'Herbst'

# Document structure
structure = [
    ['kalender', 20],
    ['weihnachten', 19],
    ['ostern', 18],
    ['hoerbuch', 17],
    ['besonderes', 16],
    ['kreatives', 15],
    ['sachbuch', 14],
    ['comic', 13],
    ['ab14', 12],
    ['ab12', 11],
    ['ab10', 10],
    ['ab8', 9],
    ['ab6', 8],
    ['vorlesebuch', 7],
    ['bilderbuch', 6],
    ['toddler', 5],
]

# Data files
categories = [section[0] for section in structure]
csv_files = [category + '.csv' for category in categories]
csv_src = [src + '/csv/' + file for file in csv_files if os.path.isfile(src + '/csv/' + file)]
csv_dist = [path.replace(src, dist) for path in csv_src]

#
# VARIABLES (END)
###


###
# HELPERS (START)
#

# Replaces pattern inside a given file
def replace(path, pattern, replacement):
    file = fileinput.input(path, inplace=True)

    for line in file:
        line = re.sub(pattern, replacement, line)
        sys.stdout.write(line)

    file.close()

#
# HELPERS (END)
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
            'fetch_api',
            'find_duplicates',
            'detect_age_ratings',
            'generate_partials',
        ]
    }


def task_phase_two():
    """
    'Phase 2' tasks: prod-stage
    """
    return {
        'actions': None,
        'task_dep': [
            'create_base',
            'extend_base',
            'steady_base',
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
            'write_summary',
            'compose_mails',
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
        'uptodate': [run_once],
        'actions': ['bash scripts/new_issue.bash ' + issue],
    }


def task_fetch_api():
    """
    Fetches bibliographic data & book covers

    ISSUE/dist/csv/example.csv` >> `ISSUE/dist/csv/example.csv`
    """
    return {
        'file_dep': csv_src,
        'actions': ['php scripts/fetch_api.php ' + issue],
        'targets': csv_dist,
    }


def task_find_duplicates():
    """
    Finds all duplicate ISBNs

    >> `ISSUE/meta/duplicates.txt`
    """
    return {
        'file_dep': csv_dist,
        'actions': ['bash scripts/find_duplicates.bash ' + issue],
        'targets': [meta + '/duplicates.txt'],
    }


def task_detect_age_ratings():
    """
    Detects improper age ratings

    >> `ISSUE/meta/age-ratings.txt`
    """
    return {
        'file_dep': csv_dist,
        'actions': ['bash scripts/detect_age_ratings.bash ' + issue],
        'targets': [meta + '/age-ratings.txt'],
    }


def task_generate_partials():
    """
    Generates one template file per category

    Using `ISSUE/dist/csv/example.csv` with either
    a) `ISSUE/src/templates/example.sla`,
    b) `ISSUE/src/templates/dataList.sla` or
    c) `shared/templates/dataList.sla` as fallback

    >> `ISSUE/dist/templates/example.sla`
    """
    for data_file in csv_dist:
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

        # Prepare category substitution
        partial_file = dist + '/templates/partials/' + category + '.sla'

        headings = {
            'toddler': 'Für die Kleinsten',
            'bilderbuch': 'Bilderbuch',
            'vorlesebuch': 'Vorlesegeschichten',
            'ab6': 'Erstleser',
            'ab8': 'Bücher ab 8',
            'ab10': 'Bücher ab 10',
            'ab12': 'Bücher ab 12',
            'ab14': 'Junge Erwachsene',
            'comic': 'Graphic Novel',
            'sachbuch': 'Sachbuch',
            'kreatives': 'Kreatives Gestalten',
            'besonderes': 'Besonderes',
            'hoerbuch': 'Hörbuch Spezial',
            'ostern': 'Ostern Spezial',
            'weihnachten': 'Weihnachten Spezial',
            'kalender': 'Kalender für ' + next_year,
        }

        yield {
            'name': data_file,
            'file_dep': [data_file, template_file],
            'actions': [
                ' '.join(command),
                (replace, [partial_file, '%%CATEGORY%%', headings[category]]),
            ],
            'targets': [dist + '/templates/partials/' + category + '.sla'],
        }


def task_create_base():
    """
    Sets up base template before importing category partials
    """
    # Check if per-issue base template exists
    base_file = src + '/templates/main.sla'

    if os.path.isfile(base_file) is False:
        # If it doesn't, choose common base template
        base_file = shared + '/templates/main.sla'

    # Remove unsuitable intro page
    page_number = 4 if season == 'spring' else 3

    # Build command
    intro_cmd = [
        'flatpak run net.scribus.Scribus -g -ns -py',
        'scripts/delete_page.py',
        base_template,
        '--page ' + str(page_number),
    ]

    return {
        'actions': [
            'cp ' + base_file + ' ' + base_template,
            ' '.join(intro_cmd),
        ],
        'targets': [base_template],
        'clean': True,
    }


def task_extend_base():
    """
    Imports category partials into base template

    `ISSUE/dist/templates/unprocessed.sla` +
    `ISSUE/dist/templates/partials/*.sla` >> `ISSUE/dist/processed.sla`
    """
    # Create import for each category partial after its designated page number
    for category, page_number in structure:
        # Define category partial
        category_file = dist + '/templates/partials/' + category + '.sla'

        # Build command
        command = [
            # (1) Python script, executed via Scribus (Flatpak)
            # (2) Uses `processed` base template version
            'flatpak run net.scribus.Scribus -g -ns -py',
            'scripts/import_pages.py',
            base_template,
            category_file,  # Import file
            '--page ' + str(page_number),  # Page number
            '--masterpage category_' + season,  # Masterpage
        ]

        # Remove cover page if corresponding category partial doesn't exist
        if os.path.isfile(category_file) is False:
            command = [
                'flatpak run net.scribus.Scribus -g -ns -py',
                'scripts/delete_page.py',
                base_template,
                '--page ' + str(page_number),
            ]

        yield {
            'name': category_file,
            'file_dep': [base_template],
            'actions': [' '.join(command)],
        }


def task_steady_base():
    """
    Ensures that base template is ready for manual editing

    a) replacing variables
    b) copying base template
    c) comparing book count

    `ISSUE/dist/templates/base.sla` >> `ISSUE/dist/templates/edited.sla`
    """
    # Replace spring template names with autumn ones
    def apply_season():
        templates = [
            'cover_spring',
            'toc_spring',
            'section_spring',
            'category_spring',
        ]

        # Base template features spring colors ..
        if season == 'autumn':
            # .. therefore, we have to change in case of autumn edition
            for template in templates:
                # .. achieved with a simple substitution
                replace(
                    base_template,
                    'MNAM="' + template,
                    'MNAM="' + template.replace('spring', 'autumn')
                )

    # Performs nominal-actual comparison of total books
    def compare(template_file):
        # Count books - [0] = CSV, [1] = SLA
        total_csv, total_sla = get_book_count(edited_template)

        # Check if they match - if not, exit
        if total_csv != total_sla:
            sys.exit('You shall not pass!')

    return {
        'file_dep': [base_template],
        'task_dep': ['extend_base'],
        'actions': [
            (apply_season),
            (replace, [base_template, '%%SEASON%%', season_de]),
            (replace, [base_template, '%%YEAR%%', year]),
            (replace, [base_template, '%%NEXT_YEAR%%', next_year]),
            'cp %(dependencies)s %(targets)s',
            (compare, [edited_template])
        ],
        'targets': [edited_template],
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
        '--input ' + edited_template,  # Input file
        '--output %(targets)s',  # Output file
    ]

    return {
        'actions': [' '.join(command)],
        'targets': [document_file]
    }


def task_optimize_document():
    """
    Optimizes document for smaller file size

    `ISSUE/dist/documents/pdf/bloated.pdf` >> `ISSUE/dist/optimized.pdf`
    """
    # Season slug
    slug = slugify(season_de)

    # Image resolutions
    resolutions = [
        '50',   # XXS
        '100',  # XS
        '150',  # S
        '200',  # M
        '250',  # L
        '300',  # XL
    ]

    # TODO: Keep order
    for resolution in resolutions:
        # Craft output path
        optimized_file = home + '/'  # Add path
        optimized_file += 'buchempfehlungen-' + slug  # Add season
        optimized_file += '-' + str(now.year) + '_' + resolution + '.pdf'

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
    def summarize():
        # Extract books from template
        books = get_booklist(edited_template)

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
        'actions': [(summarize)],
        'targets': [meta + '/summary.txt'],
    }


# TODO: Improve mail + templates
def task_compose_mails():
    """
    Drafts mail files for publishers

    >> `ISSUE/dist/documents/mails/publisher.eml`
    """
    # Extract books from template
    books = get_booklist(edited_template)

    # Select publishers
    publishers = get_publishers(books)

    for publisher in publishers:
        text_block = []

        for book in books:
            if book[1] == publisher:
                author = book[2]
                title = book[3]
                page_number = book[4]

                text_block.append(
                    author + ' - "' + title + '" auf Seite ' +
                    str(page_number) + '<br>'
                )

        # Craft output path
        mail_file = dist + '/documents/mails/'  # Add path
        mail_file += publisher + '.eml'

        subject = 'Empfehlungsliste ' + season_de + ' ' + year
        # TODO: Variable text - autumn is quite different!
        text = '\n'.join(text_block)

        yield {
            'name': mail_file,
            'actions': [(create_mail, [], {
                'subject': subject,
                'text': text,
                'output_path': mail_file,
            })],
            'targets': [mail_file],
        }

#
# TASKS (END)
###
