#! /usr/bin/python
# ~*~ coding=utf-8 ~*~

from doit import get_var

# TODO: Import only what is needed
import os  # path
import re  # sub
import sys  # stdout.write
import json  # dump, load
import time  # mktime
import datetime  # datetime.now
import fileinput  # input
import mimetypes  # guess_type

from email import generator  # Generator
from email import encoders  # encode_base64
from email import utils  # formatdate
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from operator import itemgetter

from pandas import read_csv
from slugify import slugify
from lxml import etree


###
# CONFIG (START)
#

DOIT_CONFIG = {
    'action_string_formatting': 'old',
    'default_tasks': [
        'phase_one',
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
config = {'issue': get_var('issue', '2021_02')}
issue = config['issue']

# Directories
# (1) Base
assets = 'assets'
# (2) Per-issue
home_dir = 'issues/' + issue
meta_dir = home_dir + '/meta'
conf_dir = home_dir + '/config'
src_dir = home_dir + '/src'
dist_dir = home_dir + '/dist'

# Time
now = datetime.datetime.now()

# Get this & next year
year = str(now.year)
next_year = str(now.year + 1)

# Season
season = 'spring' if issue[-2:] == '01' else 'autumn'
season_de = 'Frühjahr' if season == 'spring' else 'Herbst'

slug_replacements = ([
    ['Ü', 'UE'],
    ['ü', 'ue'],
    ['Ö', 'OE'],
    ['ö', 'oe'],
    ['Ä', 'AE'],
    ['ä', 'ae'],
    ['ß', 'ss'],
])

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

# Headings
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

#
# VARIABLES (END)
###


###
# HELPERS (START)
#

def get_files(extension: str, mode: str) -> list:
    files = [category + '.' + extension for category in [section[0] for section in structure]]

    directory = {
        'src': src_dir,
        'dist': dist_dir,
    }

    if mode not in directory:
        return []

    return [directory[mode] + '/' + extension + '/' + file for file in files if os.path.isfile(directory[mode] + '/' + extension + '/' + file)]


def get_template(template: str) -> str:
    if template == 'base':
        return dist_dir + '/templates/base.sla'

    if template == 'edited':
        return dist_dir + '/templates/edited.sla'

    if template == 'document':
        return dist_dir + '/documents/pdf/final.pdf'

    if template == 'age-ratings':
        return conf_dir + '/age-ratings.json'

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
            'compose_mails',
            'extract_data',
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
        'actions': ['bash scripts/bash/new_issue.bash ' + issue],
    }


def task_csv2json():
    """
    Converts CSV source files to JSON

    ISSUE/src/csv/example.csv` >> `ISSUE/src/json/example.json`
    """
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


    def csv2json(dependencies, targets):
        # Convert CSV to JSON
        # (1) Load CSV data
        csv_data = read_csv(dependencies[0], encoding='iso-8859-1', sep=';', names=names)

        # (2) Store as JSON
        csv_data.to_json(targets[0], 'records', force_ascii=False, indent=4)


    for csv_file in get_files('csv', 'src'):
        json_file = src_dir + '/json/' + os.path.basename(csv_file)[:-4] + '.json'

        yield {
            'name': json_file,
            'file_dep': [csv_file],
            'actions': [csv2json],
            'targets': [json_file],
        }


def task_fetch_api():
    """
    Fetches bibliographic data & book covers

    >> `ISSUE/config/age-ratings.json`
    """
    json_files = get_files('json', 'src')
    age_rating_file = get_template('age-ratings')

    return {
        'file_dep': json_files,
        'actions': ['php scripts/php/pcbis.php fetching ' + issue],
        'targets': [age_rating_file],
    }


def task_find_duplicates():
    """
    Finds all duplicate ISBNs

    >> `ISSUE/config/duplicates.json`
    >> `ISSUE/meta/duplicates.txt`
    """
    json_files = get_files('json', 'src')

    duplicates_file = conf_dir + '/duplicates.json'
    duplicates_report = meta_dir + '/duplicates.txt'

    def find_duplicates():
        duplicates = {}

        # Extract all categories an ISBN appears in
        for json_file in json_files:
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
        dump_json(isbns, duplicates_file)

        # Provide message in case report is empty
        if not report:
            report = ['No duplicates found!']

        # Write report to file
        with open(duplicates_report, 'w') as file:
            file.writelines(line + '\n' for line in report)

    return {
        'file_dep': json_files,
        'actions': [find_duplicates],
        'targets': [
            duplicates_file,
            duplicates_report,
        ],
    }


def task_check_age_ratings():
    """
    Detects improper age ratings

    >> `ISSUE/meta/age-ratings.txt`
    """
    age_rating_file = get_template('age-ratings')
    age_rating_report = meta_dir + '/age-ratings.txt'

    def check_age_ratings():
        age_ratings = []

        for isbn, age_rating in load_json(age_rating_file).items():
            age_ratings.append('%s: %s' % (isbn, age_rating))

        if not age_ratings:
            # .. otherwise there isn't anything to report back, really
            age_ratings = ['No improper age ratings found!']

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
    for json_file in get_files('json', 'src'):
        target_file = json_file.replace('src', 'dist')
        category = os.path.basename(json_file)[:-5]

        yield {
            'name': json_file,
            'file_dep': [json_file],
            'task_dep': ['fetch_api'],
            'actions': ['php scripts/php/pcbis.php processing ' + issue + ' ' + category],
            'targets': [target_file, target_file.replace('json', 'csv')],
        }


def task_generate_partials():
    """
    Generates one template file per category

    Using `ISSUE/dist/csv/example.csv` with either
    a) `ISSUE/src/templates/example.sla`,
    b) `ISSUE/src/templates/dataList.sla` or
    c) `assets/templates/dataList.sla` as fallback

    >> `ISSUE/dist/templates/example.sla`
    """
    for data_file in get_files('csv', 'dist'):
        # Stripping path & extension
        category = os.path.basename(data_file)[:-4]

        # Build target directory & filename
        partials_dir = dist_dir + '/templates/partials'
        partial_file = partials_dir + '/' + category + '.sla'

        # Add template extension
        template_name = category + '.sla'

        # Add source path
        template_file = src_dir + '/templates/' + template_name

        # Check if per-issue template file for given category exists ..
        if os.path.isfile(template_file) is False:
            # .. if it doesn't, choose per-issue generic template file
            template_file = src_dir + '/templates/dataList.sla'

        # .. otherwise ..
        if os.path.isfile(template_file) is False:
            # .. use common template file for given category
            template_file = assets + '/templates/' + template_name

        # But if that doesn't exist either ..
        if os.path.isfile(template_file) is False:
            # .. ultimately resort to common generic template file
            template_file = assets + '/templates/dataList.sla'

        # TODO: Maybe python function may be imported + executed directly?
        command = [
            # (1) Virtual environment python executable
            # (2) Python script `ScribusGenerator` by @berteh
            # See https://github.com/berteh/ScribusGenerator
            '.env/bin/python',
            'vendor/berteh/scribusgenerator/ScribusGeneratorCLI.py',
            '--single',            # Single file output
            '-c ' + data_file,     # CSV file
            '-o ' + partials_dir,  # Output directory
            '-n ' + category,      # Output filename
            template_file,         # Template path
        ]

        yield {
            'name': partial_file,
            'file_dep': [data_file, template_file],
            'actions': [
                ' '.join(command),
                (replace, [partial_file, '%%CATEGORY%%', headings[category]]),
            ],
            'targets': [partial_file],
        }


def task_create_base():
    """
    Sets up base template before importing category partials
    """
    # Check if per-issue base template exists
    base_file = src_dir + '/templates/main.sla'
    base_template = get_template('base')

    if os.path.isfile(base_file) is False:
        # If it doesn't, choose common base template
        base_file = assets + '/templates/main.sla'

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
        # 'targets': [base_template],
        'clean': True,
    }


def task_extend_base():
    """
    Imports category partials into base template

    `ISSUE/dist/templates/unprocessed.sla` +
    `ISSUE/dist/templates/partials/*.sla` >> `ISSUE/dist/processed.sla`
    """
    base_template = get_template('base')

    # Create import for each category partial after its designated page number
    for category, page_number in structure:
        # Define category partial
        category_file = dist_dir + '/templates/partials/' + category + '.sla'

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

    `ISSUE/dist/templates/base.sla` >> `ISSUE/dist/templates/edited.sla`
    """
    base_template = get_template('base')
    edited_template = get_template('edited')

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
                replace(base_template,
                    'MNAM="' + template,
                    'MNAM="' + template.replace('spring', 'autumn')
                )

    return {
        'file_dep': [base_template],
        # 'task_dep': ['extend_base'],
        'actions': [
            (apply_season),
            (replace, [base_template, '%%SEASON%%', season_de]),
            (replace, [base_template, '%%YEAR%%', year]),
            (replace, [base_template, '%%NEXT_YEAR%%', next_year]),
            'cp %(dependencies)s %(targets)s',
        ],
        'targets': [edited_template],
    }


def task_build_pdf():
    """
    Builds document from base template

    `ISSUE/dist/templates/edited.sla` >> `ISSUE/dist/documents/final.pdf`
    """
    edited_template = get_template('edited')
    document_file = get_template('document')

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
    document_file = get_template('document')

    # Season slug
    slug = slugify(season_de, replacements=slug_replacements)

    # Image resolutions
    resolutions = [
        '50',   # XXS
        '75',  # XS
        '100',  # S
        '175',  # M
        '200',  # L
        '225',  # XL
        '250',  # XXL
    ]

    for resolution in resolutions:
        # Build output filepath
        optimized_file = home_dir + '/' + str(now.year) + '-' + slug + '-buchempfehlungen_' + resolution + '.pdf'

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
    edited_template = get_template('edited')
    summary_file = meta_dir + '/summary.txt'

    def summarize():
        # Extract books from template
        books = extract_books(edited_template)

        publishers = {book['Verlag'] for book in books}

        with open(summary_file, 'w') as file:
            for publisher in sorted(publishers, key=str.casefold):
                file.write(publisher + ':\n')

                for book in books:
                    if book['Verlag'] == publisher:
                        author = book['AutorIn']
                        title = book['Titel']
                        page_number = book['Seitenzahl']

                        file.write(
                            author + ' - "' + title + '" auf Seite ' +
                            str(page_number) + '\n'
                        )

                file.write('\n')

    return {
        'actions': [(summarize)],
        'targets': [summary_file],
    }


def task_compose_mails():
    """
    Drafts mail files for publishers

    >> `ISSUE/dist/documents/mails/publisher.eml`
    """
    edited_template = get_template('edited')

    # Extract books from template
    books = extract_books(edited_template)

    # Grab publishers
    publishers = {book['Verlag'] for book in books}

    # Build text block for each of them
    for publisher in sorted(publishers, key=str.casefold):
        text_block = []

        for book in books:
            if book['Verlag'] == publisher:
                author = book['AutorIn']
                title = book['Titel']
                page_number = book['Seitenzahl']

                text_block.append(
                    author + ' - "' + title + '" auf Seite ' +
                    str(page_number) + '\n'
                )

        # Build output filepath
        mail_file = dist_dir + '/documents/mails/'  # Add path
        mail_file += slugify(publisher, replacements=slug_replacements) + '.eml'

        subject = 'Empfehlungsliste ' + season_de + ' ' + year

        # Load text parts
        text_block = '<br>'.join(text_block)

        # (1) Grab season text
        with open(assets + '/mails/' + season + '.html', 'r') as file:
            season_text = ''.join(file.readlines())

        # (2) Grab email signature
        with open(assets + '/mails/signature.html', 'r') as file:
            signature = ''.join(file.readlines())

        text = (
            '<html><head></head><body>'
            + season_text + '<p>' + text_block + '</p>' + signature +
            '</body></html>'
        )

        yield {
            'name': mail_file,
            'actions': [(create_mail, [], {
                'is_from': 'info@fundevogel.de',
                'subject': subject,
                'text': text,
                'output_path': mail_file,
            })],
            'targets': [mail_file],
        }


def task_extract_data():
    """
    Grab data from the redacted template

    >> `ISSUE/config/data.json`
    """
    edited_template = get_template('edited')
    data_contents_file = conf_dir + '/data.json'
    json_files = get_files('json', 'dist')

    def extract_data():
        # Parsing Scribus template file
        text_elements = etree.parse(edited_template).getroot().findall('.//PAGEOBJECT/StoryText/ITEXT')

        books = {}

        # Parsing JSON data files
        for json_file in json_files:
            # Extract books from template
            for data in load_json(json_file):
                book = []

                for element in text_elements:
                    if data['ISBN'] in element.attrib['CH']:
                        # Determine page number
                        parent = element.getparent()

                        for child in parent:
                            if (child.tag == 'ITEXT'):
                                book.append(child.attrib['CH'])

                books[data['ISBN']] = book[:-1]

        # Store results
        dump_json(books, data_contents_file)

    return {
        'file_dep': json_files,
        'actions': [(extract_data)],
        'targets': [data_contents_file],
    }

#
# TASKS (END)
###


###
# UTILITIES (START)
#

def replace(path, pattern, replacement):
    # Replace pattern inside a given file
    file = fileinput.input(path, inplace=True)

    for line in file:
        line = re.sub(pattern, replacement, line)
        sys.stdout.write(line)

    file.close()


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


def extract_books(input_file: str):
    json_files = get_files('json', 'dist')

    # Parsing Scribus template file
    text_elements = etree.parse(input_file).getroot().findall('.//PAGEOBJECT/StoryText/ITEXT')

    books = []

    # Parsing JSON data files
    for json_file in json_files:
        # Determine category
        category = headings[os.path.basename(json_file)[:-5]]

        for data in load_json(json_file):
            book = {
                'AutorIn': data['AutorInnen'],
                'Titel': data['Titel'],
                'Verlag': data['Verlag'],
                'Seitenzahl': 0,
                'Kategorie': category,
            }

            for element in text_elements:
                if data['ISBN'] in element.attrib['CH']:
                    # Determine page number
                    parent = element.xpath('./../..')
                    page = int(parent[0].attrib['OwnPage'])

                    # Store data
                    book['Seitenzahl'] = page + 1

            books.append(book)

    # Sort by (1) page number, (2) publisher, (3) author & (4) book title
    return sorted(books, key=itemgetter('Seitenzahl', 'Verlag', 'AutorIn', 'Titel'))


def create_mail(
    is_from='',
    goes_to='',
    cc='',
    bcc='',
    subject='',
    text='',
    attachments=[],
    output_path='mail.eml',
):
    # Create `eml` file
    # (1) Add message header
    mail = MIMEMultipart()
    mail['Subject'] = subject
    mail['To'] = goes_to
    mail['From'] = is_from
    mail['Cc'] = cc
    mail['Bcc'] = bcc
    mail['Date'] = get_rfc2822_date()

    # (2) Add message body
    body = MIMEText(text, 'html', 'utf-8')
    mail.attach(body)

    # (3) Add attachments
    if attachments:
        for attachment in attachments:
            attachment = add_attachment(attachment)

            if attachment:
                mail.attach(attachment)

    # (4) Write contents
    with open(output_path, 'w') as file:
        output_path = generator.Generator(file)
        output_path.flatten(mail)


def get_rfc2822_date():
    # See https://tools.ietf.org/html/rfc2822
    now = datetime.datetime.now()
    time_tuple = now.timetuple()
    timestamp = time.mktime(time_tuple)

    return utils.formatdate(timestamp)


def add_attachment(file_path: str):
    # Checking if attachment file exists
    if os.path.isfile(file_path):

        # Detecting filetype
        file_type, encoding = mimetypes.guess_type(file_path)

        if file_type is None or encoding is not None:
            file_type = 'application/octet-stream'

        type_primary, type_secondary = file_type.split('/', 1)

        if type_primary == 'text':
            with open(file_path) as file:
                data = MIMEText(file.read(), type_secondary)

        elif type_primary == 'image':
            with open(file_path, 'rb') as file:
                data = MIMEImage(file.read(), type_secondary)

        elif type_primary == 'audio':
            with open(file_path, 'rb') as file:
                data = MIMEAudio(file.read(), type_secondary)

        else:
            with open(file_path, 'rb') as file:
                data = MIMEBase(type_primary, type_secondary)
                data.set_payload(file.read())

            encoders.encode_base64(data)

        # Build filename
        file_name = os.path.basename(file_path)

        # Add attachment header
        data.add_header('Content-Disposition', 'attachment', filename=file_name)

        return data

    return False

#
# UTILITIES (END)
###
