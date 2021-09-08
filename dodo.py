import os
import re
import sys
import json
import fileinput

from datetime import datetime
from mimetypes import guess_type
from operator import itemgetter
from time import mktime

from email import generator  # Generator
from email import encoders  # encode_base64
from email import utils  # formatdate
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from doit import get_var
from lxml import etree
from pandas import read_csv
from slugify import slugify


###
# CONFIG (START)
#

VERSION = '2.2.1'

# CLI
DOIT_CONFIG = {
    'verbosity': 2,
    'action_string_formatting': 'old',
    'default_tasks': [
        'phase_one',
    ],
}

config = {'issue': get_var('issue', '2021_02')}
issue = config['issue']

# Season
season = 'spring' if issue[-2:] == '01' else 'autumn'
season_de = 'Frühjahr' if season == 'spring' else 'Herbst'

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
now = datetime.now()
year = str(now.year)
next_year = str(now.year + 1)
last_year = str(now.year - 1)

# Headings
headings = {
    'toddler': 'Für die Kleinsten',
    'bilderbuch': 'Bilderbücher',
    'vorlesebuch': 'Vorlesegeschichten',
    'ab6': 'Erstleser',
    'ab8': 'Bücher ab 8',
    'ab10': 'Bücher ab 10',
    'ab12': 'Bücher ab 12',
    'ab14': 'Junge Erwachsene',
    'comic': 'Graphic Novel',
    'sachbuch': 'Sachbücher',
    'kreatives': 'Kreatives Gestalten',
    'besonderes': 'Besonderes',
    'hoerbuch': 'Hörbuch Spezial',
    'ostern': 'Ostern Spezial',
    'weihnachten': 'Weihnachten Spezial',
    'kalender': 'Kalender für ' + next_year,
}

#
# CONFIG (END)
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
            'fetch_api',
            'check_data',
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
            'create_template',
            'generate_partials',
            'import_partials',
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
            'optimize_pdf',
            'finish_issue',
        ]
    }

#
# GROUPS (END)
###


###
# TASKS (START)
#

def task_fetch_api():
    """
    Fetches bibliographic data & book covers

    ISSUE/src/csv/example.csv` >> `ISSUE/src/json/example.json`
    """
    for csv_file in get_files('csv', 'src'):
        category = os.path.basename(csv_file)[:-4]
        json_file = src_dir + '/json/' + category + '.json'

        yield {
            'name': json_file,
            'file_dep': [csv_file],
            'actions': ['php scripts/php/pcbis.php fetching ' + issue + ' ' + category],
            'targets': [json_file],
        }


def task_check_data():
    """
    Finds all duplicate ISBNs & detects improper age ratings

    >> `ISSUE/config/duplicates.json`
    >> `ISSUE/meta/duplicates.txt`
    >> `ISSUE/config/age-ratings.json`
    >> `ISSUE/meta/age-ratings.txt`
    """
    def find_duplicates(dependencies, targets):
        duplicates = {}

        # Extract all categories an ISBN appears in
        for json_file in dependencies:
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
        dump_json(isbns, targets[0])

        # Provide message in case report is empty
        if not report:
            report = ['No duplicates found!']

        # Write report to file
        with open(targets[1], 'w') as file:
            file.writelines(line + '\n' for line in report)


    def check_age_ratings(dependencies, targets):
        src = {}

        for json_file in dependencies:
            category = os.path.basename(json_file)[:-5]

            for data in load_json(json_file):
                age_rating = data['Altersempfehlung']

                if 'angabe' in age_rating or 'bis' in age_rating:
                    src[data['ISBN']] = age_rating

        # Store age ratings data in JSON file
        dump_json(src, targets[2])

        age_ratings = []

        for isbn, age_rating in src.items():
            age_ratings.append('%s: %s' % (isbn, age_rating))

        if not age_ratings:
            # .. otherwise there isn't anything to report back, really
            age_ratings = ['No improper age ratings found!']

        # Save improper age ratings
        with open(targets[3], 'w') as file:
            # Write age ratings report to file
            file.writelines(age_rating + '\n' for age_rating in age_ratings)


    return {
        'task_dep': ['fetch_api'],
        'file_dep': get_files('json', 'src'),
        'actions': [
            find_duplicates,
            check_age_ratings,
        ],
        'targets': [
            get_template('duplicates'),
            meta_dir + '/duplicates.txt',
            get_template('age-ratings'),
            meta_dir + '/age-ratings.txt',
        ],
    }


def task_process_data():
    """
    Processes raw data, respecting duplicates & proper age ratings

    ISSUE/src/json/example.json` >> `ISSUE/dist/json/example.json`
    """
    for json_file in get_files('json', 'src'):
        category = os.path.basename(json_file)[:-5]

        yield {
            'name': json_file,
            'file_dep': [json_file, get_template('age-ratings'), get_template('duplicates')],
            'task_dep': ['fetch_api'],
            'actions': ['php scripts/php/pcbis.php processing ' + issue + ' ' + category],
            'targets': [json_file.replace('src', 'dist')],
        }


def task_create_template():
    """
    Creates base template fitting the current season
    """
    # Check if per-issue base template exists
    base_file = src_dir + '/templates/main.sla'

    if os.path.isfile(base_file) is False:
        # If it doesn't, choose common base template
        base_file = assets + '/templates/main.sla'

    # Remove unsuitable intro page
    page_number = 4 if season == 'spring' else 3

    # Build command
    create_template = [
        'scribus -g -ns -py',             # Scribus command
        'scripts/python/delete_page.py',  # Scribus script
        '%(targets)s',                    # Base template
        '--page ' + str(page_number),     # Page number
    ]

    return {
        'actions': [
            'cp ' + base_file + ' %(targets)s',
            ' '.join(create_template),
        ],
        'targets': [get_template('base')],
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
    for csv_file in get_files('csv', 'dist'):
        # Stripping path & extension
        category = os.path.basename(csv_file)[:-4]

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

        generate_partials = [
            # (1) Virtual environment python executable
            # (2) Python script `ScribusGenerator` by @berteh
            # See https://github.com/berteh/ScribusGenerator
            '.env/bin/python',
            'vendor/berteh/scribusgenerator/ScribusGeneratorCLI.py',
            '--single',            # Single file output
            '-c ' + csv_file,      # CSV file
            '-o ' + partials_dir,  # Output directory
            '-n ' + category,      # Output filename
            template_file,         # Template path
        ]

        yield {
            'name': partial_file,
            'file_dep': [csv_file],
            'actions': [
                ' '.join(generate_partials),
                (replace, [partial_file, '%%CATEGORY%%', headings[category]]),
            ],
            'targets': [partial_file],
        }


def task_import_partials():
    """
    Imports category partials into base template

    `ISSUE/dist/templates/unprocessed.sla` +
    `ISSUE/dist/templates/partials/*.sla` >> `ISSUE/dist/processed.sla`
    """
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

    # Create import for each category partial after its designated page number
    for category, page_number in structure:
        # Define category partial
        category_file = dist_dir + '/templates/partials/' + category + '.sla'

        # Build command
        import_partials = [
            'scribus -g -ns -py',               # Scribus command
            'scripts/python/import_partials.py',   # Scribus script
            '%(dependencies)s',                 # Base template
            category_file,                      # Import file
            '--page ' + str(page_number),       # Page number
            '--masterpage category_' + season,  # Masterpage
        ]

        # Remove cover page if corresponding category partial doesn't exist
        if os.path.isfile(category_file) is False:
            import_partials = [
                'scribus -g -ns -py',             # Scribus command
                'scripts/python/delete_page.py',  # Scribus script
                '%(dependencies)s',               # Base template
                '--page ' + str(page_number),     # Page number
            ]

        yield {
            'name': category_file,
            'file_dep': [get_template('base')],
            'actions': [' '.join(import_partials)],
        }


def task_prepare_editing():
    """
    Prepares base template for manual editing

    a) replace variables
    b) copy base template

    `ISSUE/dist/templates/base.sla` >> `ISSUE/dist/templates/edited.sla`
    """
    edited_template = get_template('edited')

    # Replace spring template names with autumn ones
    def apply_season(dependencies):
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
                replace(dependencies[0],
                    'MNAM="' + template,
                    'MNAM="' + template.replace('spring', 'autumn')
                )

    return {
        'file_dep': [get_template('base')],
        'actions': [
            (apply_season),
            (replace, ['%(dependencies)s', '%%SEASON%%', season_de]),
            (replace, ['%(dependencies)s', '%%YEAR%%', year]),
            (replace, ['%(dependencies)s', '%%NEXT_YEAR%%', next_year]),
            'cp %(dependencies)s ' + edited_template,
        ],
    }


def task_build_pdf():
    """
    Builds document from base template

    `ISSUE/dist/templates/edited.sla` >> `ISSUE/dist/documents/final.pdf`
    """
    # Build command
    build_pdf = [
        'scribus -g -py',               # Scribus command
        'scripts/python/build_pdf.py',  # Scribus script
        '--input %(dependencies)s',     # Input file
        '--output %(targets)s',         # Output file
    ]

    return {
        'file_dep': [get_template('edited')],
        'actions': [' '.join(build_pdf)],
        'targets': [get_template('document')],
    }


def task_optimize_pdf():
    """
    Optimizes document for smaller file size

    `ISSUE/dist/documents/pdf/bloated.pdf` >> `ISSUE/dist/optimized.pdf`
    """
    # Season slug
    season_slug = slug(season_de)

    # Printing resolutions
    dots_per_inch = [
        '50',   # XXS
        '75',  # XS
        '100',  # S
        '175',  # M
        '200',  # L
        '225',  # XL
        '250',  # XXL
    ]

    for dpi in dots_per_inch:
        # Build output filepath
        optimized_file = home_dir + '/' + str(now.year) + '-' + season_slug + '-buchempfehlungen_' + dpi + '.pdf'

        # Build command
        optimize_pdf = [
            'gs',
            '-dCompatibilityLevel=1.4',
            '-dNOPAUSE',
            '-dBATCH',
            '-dQUIET',

            # Performance
            # See https://ghostscript.com/doc/current/Use.htm#Improving_performance
            '-dNumRenderingThreads=8',               # Increase number of threads
            '-dBandHeight=100',                      # Increase band size
            '-dBufferSpace=1000000000',              # Reduce per-band overhead
            '-dNOGC',                                # Disable garbage collector

            # Font optimization
            '-dSubsetFonts=true',
            '-dCompressFonts=true',

            # Image quality & colors
            # Manually apply '-dPDFSETTINGS=XY' where XY ..
            # /default
            # /screen:    72dpi
            # /ebook:    150dpi
            # /printer:  300dpi
            # /prepress: 300dpi
            '-dMonoImageResolution=' + dpi,
            '-dGrayImageResolution=' + dpi,
            '-dColorImageResolution=' + dpi,
            '-dDownsampleMonoImages=true',
            '-dDownsampleGrayImages=true',
            '-dDownsampleColorImages=true',
            '-dConvertCMYKImagesToRGB=true',

            # I/O
            '-sDEVICE=pdfwrite',
            '-sOutputFile=%(targets)s',
            '-f %(dependencies)s',
        ]

        yield {
            'name': [optimized_file],
            'file_dep': [get_template('document')],
            'actions': [' '.join(optimize_pdf)],
            'targets': [optimized_file],
        }


def task_finish_issue():
    """
    Parses the redacted template for use in post-production

    >> `ISSUE/dist/documents/mails/publisher.eml`
    >> `ISSUE/meta/summary.txt`
    >> `ISSUE/config/data.json`
    """
    def compose_mails(targets):
        # Extract books from template
        books = extract_books(get_template('edited'))

        # Grab publishers
        publishers = {book['Verlag'] for book in books}

        # Build text block for each of them
        for publisher in sorted(publishers, key=str.casefold):
            text_blocks = []

            for book in books:
                if book['Verlag'] == publisher:
                    text_blocks.append({
                        'author': book['AutorIn'],
                        'title': book['Titel'],
                        'pages': book['Seitenzahl'],
                    })

            # Sort by (1) page number, (2) author & (3) book title
            text_blocks = [block['author'] + ' - "' + block['title'] + '" auf Seite ' + str(block['pages']) for block in sorted(text_blocks, key=itemgetter('pages', 'author', 'title'))]

            # Write summary
            with open(targets[0], 'a') as file:
                file.write(publisher + ':\n')
                file.writelines([line + '\n' for line in text_blocks])
                file.write('\n')

            # Build output filepath
            mail_file = dist_dir + '/documents/mails/' + slug(publisher) + '.eml'

            # Load text parts
            text_block = '<br>'.join(text_blocks)

            # (1) Grab season text
            with open(assets + '/mails/' + season + '.html', 'r') as file:
                season_text = ''.join(file.readlines())

            # (2) Replace year placeholders
            for placeholder, replacement in {
                '%%LAST_YEAR%%': last_year,
                '%%THIS_YEAR%%': year,
                '%%NEXT_YEAR%%': year + '/' + next_year[2:],
            }.items():
                season_text = season_text.replace(placeholder, replacement)

            # (3) Grab email signature
            with open(assets + '/mails/signature.html', 'r') as file:
                signature = ''.join(file.readlines())

            text = (
                '<html><head></head><body>'
                + season_text + '<p>' + text_block + '</p>' + signature +
                '</body></html>'
            )

            # Create subject
            subject = 'Empfehlungsliste ' + season_de + ' ' + year

            create_mail(
                is_from='info@fundevogel.de',
                subject=subject, text=text,
                output_path=mail_file
            )


    def extract_data(targets):
        # Parse Scribus template file
        text_elements = etree.parse(get_template('edited')).getroot().findall('.//PAGEOBJECT/StoryText/ITEXT')

        books = {}

        # Parsing JSON data files
        for json_file in get_files('json', 'dist'):
            # Buffer results for easier sorting later on
            buffer = []

            # Extract books from template
            for json_data in load_json(json_file):
                # Fix edge cases when author is undefined
                # See 978-3-649-64031-8
                if not json_data['AutorInnen']:
                    json_data['AutorInnen'] = ''

                # Go through all text elements
                for element in text_elements:
                    # Look for matching ISBN
                    if json_data['ISBN'] in element.attrib['CH']:
                        # Extract header
                        # (1) Grab previous 'PAGEOBJECT' element
                        page_object = element.getparent().getparent().getprevious()

                        # (2) Extract children
                        header = []

                        if len(page_object) > 0:
                            for child in page_object[0]:
                                if (child.tag == 'ITEXT'):
                                    header.append(child.attrib['CH'])

                        # (3) Fix edge cases where header comes AFTER body
                        if not header:
                            page_object = element.getparent().getparent().getnext()

                            if len(page_object) > 0:
                                for child in page_object[0]:
                                    if (child.tag == 'ITEXT'):
                                        header.append(child.attrib['CH'])

                        # Extract text
                        # (1) Grab parent element
                        parent = element.getparent()

                        # (2) Extract children
                        body = []

                        for child in parent:
                            if (child.tag == 'ITEXT'):
                                body.append(child.attrib['CH'])

                        # Stop
                        break

                # Build book data
                buffer.append({
                    # (1) ISBN, sorting order & author(s)
                    'isbn': json_data['ISBN'],
                    'sort': json_data['Sortierung'],
                    'author': json_data['AutorInnen'],

                    # (2) Header
                    'header': header,

                    # (3) Text body (excluding ISBN, age rating & retail price)
                    'body': body[:-2],
                })

            # Determine heading
            heading = headings[os.path.basename(json_file)[:-5]]

            books[heading] = sorted(buffer, key=itemgetter('sort'))

        # Store results
        dump_json(books, targets[1])


    return {
        # 'file_dep': [get_template('edited')],
        'actions': [
            'rm -f %(targets)s',
            compose_mails,
            extract_data,
        ],
        'targets': [
            meta_dir + '/summary.txt',
            home_dir + '/data.json',
        ],
    }

#
# TASKS (END)
###


###
# HELPERS (START)
#

def get_files(extension: str, mode: str) -> list:
    # Build categories
    # (1) Base
    categories = [
        'toddler',
        'bilderbuch',
        'vorlesebuch',
        'ab6',
        'ab8',
        'ab10',
        'ab12',
        'ab14',
        'sachbuch',
        'besonderes',
        'hoerbuch',
    ]

    # (2) Per-season
    per_season = {
        'spring': ['ostern'],
        'autumn': [
            'weihnachten',
            'kalender',
        ]
    }

    categories = categories + per_season[season]

    # (3) Occasionally
    if os.path.isfile(src_dir + '/csv/comic.csv'):
        categories.append('comic')

    if os.path.isfile(src_dir + '/csv/kreatives.csv'):
        categories.append('kreatives')

    # Build files listing
    files = [category + '.' + extension for category in categories]

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

    if template == 'duplicates':
        return conf_dir + '/duplicates.json'

    if template == 'age-ratings':
        return conf_dir + '/age-ratings.json'

#
# HELPERS (END)
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


def slug(string: str) -> str:
    # Slugify string using german custom replacements
    return slugify(string, replacements=([
        ['Ü', 'UE'],
        ['ü', 'ue'],
        ['Ö', 'OE'],
        ['ö', 'oe'],
        ['Ä', 'AE'],
        ['ä', 'ae'],
        ['ß', 'ss'],
    ]))


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
    time_tuple = now.timetuple()
    timestamp = mktime(time_tuple)

    return utils.formatdate(timestamp)


def add_attachment(file_path: str):
    # Checking if attachment file exists
    if os.path.isfile(file_path):

        # Detecting filetype
        file_type, encoding = guess_type(file_path)

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
