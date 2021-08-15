#! /usr/bin/python
# ~*~ coding=utf-8 ~*~

from doit import get_var
from doit.tools import run_once

# TODO: Import only what is needed
import os  # path
import re  # sub
import sys  # stdout.write
import json
import datetime  # datetime.now
import fileinput  # input

from pandas import read_csv
from slugify import slugify

from scripts.python.hermes import create_mail
from scripts.python.thoth import get_booklist, get_publishers, get_book_count


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
config = {'issue': get_var('issue', '123')}
issue = config['issue']

# Directories
home = 'issues/' + issue
src = home + '/src'
dist = home + '/dist'
meta = home + '/meta'
conf = home + '/config'
shared = 'assets'

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

# (1) CSV files
csv_files = [category + '.csv' for category in categories]
csv_src = [src + '/csv/' + file for file in csv_files if os.path.isfile(src + '/csv/' + file)]
csv_dist = [path.replace(src, dist) for path in csv_src]

# (2) JSON files
json_files = [category + '.json' for category in categories]
json_src = [src + '/json/' + file for file in json_files if os.path.isfile(src + '/json/' + file)]
json_dist = [path.replace(src, dist) for path in json_src]

# Report files
duplicates_file = conf + '/duplicates.json'
age_rating_file = conf + '/age-ratings.json'
duplicates_report = meta + '/duplicates.txt'
age_rating_report = meta + '/age-ratings.txt'

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
            'csv2json',
            'fetch_api',
            'find_duplicates',
            'check_age_ratings',
        ]
    }


def task_phase_two():
    """
    'Phase 2' tasks: prod-stage
    """
    return {
        'actions': None,
        'task_dep': [
            'process_data',
            'generate_partials',
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
            # 'compose_mails',
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
        'actions': ['bash scripts/bash/new_issue.bash ' + issue],
    }


def task_csv2json():
    """
    Converts CSV source files to JSON

    ISSUE/src/csv/example.csv` >> `ISSUE/src/json/example.json`
    """
    def csv2json():
        # Define header row
        names = [
            'AutorIn',
            'Titel',
            'Verlag',
            'ISBN',
            'Einband',
            'Preis',
            'Meldenummer',
            'SortRabatt',
            'Gewicht',
            'Informationen',
            'Zusatz',
            'Kommentar',
        ]

        for csv_file in csv_src:
            # Convert CSV to JSON
            # (1) Load CSV data
            csv_data = read_csv(csv_file, encoding='iso-8859-1', sep=';', names=names)

            # (2) Store as JSON
            json_file = src + '/json/' + os.path.basename(csv_file)[:-4] + '.json'
            csv_data.to_json(json_file, 'records', force_ascii=False, indent=4)

    return {
        'file_dep': csv_src,
        'actions': [csv2json],
        'targets': json_src,
    }


def task_fetch_api():
    """
    Fetches bibliographic data & book covers

    >> `ISSUE/config/age-ratings.json`
    """
    return {
        'file_dep': json_src,
        'actions': ['php scripts/php/pcbis.php ' + issue + ' fetching'],
        'targets': [age_rating_file],
    }


def task_find_duplicates():
    """
    Finds all duplicate ISBNs

    >> `ISSUE/config/duplicates.json`
    >> `ISSUE/meta/duplicates.txt`
    """
    def find_duplicates():
        duplicates = {}

        # Extract all categories an ISBN appears in
        for json_file in json_src:
            # Get category (= filename w/o extension)
            category = os.path.basename(json_file)[:-5]

            for data in load_json(json_file):
                isbn = data['ISBN']

                if isbn not in duplicates:
                    duplicates[isbn] = set()

                duplicates[isbn].add(category)

        # Setup ISBN allowlist & report
        isbns = {}
        report = []

        # Go through findings ..
        for isbn, categories in duplicates.items():
            # .. checking if each ISBN has more than one category, and if so ..
            if len(categories) > 1:
                # .. report duplicate for given categories
                # (1) Remove duplicate categories
                categories = list(dict.fromkeys(categories))

                # (2) Report duplicate ISBN & categories in question
                report.append('%s: %s' % (isbn, ' & '.join(categories)))

                # (3) Store duplicate categories per ISBN
                isbns[isbn] = categories

        # Store duplicate ISBNs
        if isbns:
            dump_json(isbns, duplicates_file)

        # Provide message in case report is empty
        if not report:
            report = ['No duplicates found!']

        # Write report to file
        with open(duplicates_report, 'w') as file:
            file.writelines(line + '\n' for line in report)

    return {
        'file_dep': json_src,
        'actions': [find_duplicates],
        'targets': [duplicates_file, duplicates_report],
    }


def task_check_age_ratings():
    """
    Detects improper age ratings

    >> `ISSUE/meta/age-ratings.txt`
    """
    def check_age_ratings():
        age_ratings = []

        for isbn, age_rating in load_json(age_rating_file).items():
            age_ratings.append('%s: %s' % (isbn, age_rating))

        if not age_ratings:
            # .. otherwise there isn't anything to report back, really
            age_ratings = ['No improper age ratings found!']

        print(age_ratings)
        # Save improper age ratings
        with open(age_rating_report, 'w') as file:
            # Write age ratings report to file
            file.writelines(age_rating + '\n' for age_rating in age_ratings)

    return {
        'file_dep': [age_rating_file],
        'actions': [check_age_ratings],
        'targets': [age_rating_report],
    }


def task_process_data():
    """
    Processes raw data

    ISSUE/src/json/example.json` >> `ISSUE/dist/json/example.json`
    """
    return {
        'file_dep': json_src,
        'actions': ['php scripts/php/pcbis.php ' + issue + ' processing'],
        'targets': json_dist,
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
            template_file = shared + '/templates/' + template_name

        # But if that doesn't exist either ..
        if os.path.isfile(template_file) is False:
            # .. ultimately resort to common generic template file
            template_file = shared + '/templates/dataList.sla'

        # TODO: Maybe python function may be imported + executed directly?
        command = [
            # (1) Virtual environment python executable
            # (2) Python script `ScribusGenerator` by @berteh
            # See https://github.com/berteh/ScribusGenerator
            '.env/bin/python',
            'vendor/berteh/scribusgenerator/ScribusGeneratorCLI.py',
            '--single',                            # Single file output
            '-c ' + data_file,                     # CSV file
            '-o ' + dist + '/templates/partials',  # Output directory
            '-n ' + category,                      # Output filename
            template_file,                         # Template path
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
        # 'flatpak run net.scribus.Scribus -g -ns -py',
        'scribus -g -ns -py',
        'scripts/python/delete_page.py',
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
            # 'flatpak run net.scribus.Scribus -g -ns -py',
            'scribus -g -ns -py',               # Scribus command
            'scripts/python/import_pages.py',   # Scribus script
            base_template,                      # Base template
            category_file,                      # Import file
            '--page ' + str(page_number),       # Page number
            '--masterpage category_' + season,  # Masterpage
        ]

        # Remove cover page if corresponding category partial doesn't exist
        if os.path.isfile(category_file) is False:
            command = [
                # 'flatpak run net.scribus.Scribus -g -ns -py',
                'scribus -g -ns -py',             # Scribus command
                'scripts/python/delete_page.py',  # Scribus script
                base_template,                    # Base template
                '--page ' + str(page_number),     # Page number
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
        # 'flatpak run net.scribus.Scribus',
        'scribus -g -py',               # Scribus command
        'scripts/python/build_pdf.py',  # Scribus script
        '--input ' + edited_template,   # Input file
        '--output %(targets)s',         # Output file
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
    # slug = slugify(season_de)
    slug = 'herbst'

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
def compose_mails():
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
                'season': season,
                'subject': subject,
                'text': text,
                'output_path': mail_file,
            })],
            'targets': [mail_file],
        }

#
# TASKS (END)
###


###
# HELPERS (START)
#

def create_path(path):
    # Determine if (future) target is appropriate data file
    if os.path.splitext(path)[1].lower() in ['.csv', '.json']:
        path = os.path.dirname(path)

    if not os.path.exists(path):
        try:
            os.makedirs(path)

        # Guard against race condition
        except OSError:
            pass


def load_json(json_file):
    try:
        with open(json_file, 'r') as file:
            return json.load(file)

    except json.decoder.JSONDecodeError:
        raise Exception

    return {}


def dump_json(data, json_file):
    create_path(json_file)

    with open(json_file, 'w') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

#
# HELPERS (END)
###
