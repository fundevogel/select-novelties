#!/usr/bin/python
# ~*~ coding=utf-8 ~*~

import datetime  # datetime.now
import mimetypes
import os  # path.basename, path.isfile
import time  # mktime

from email import generator  # Generator
from email import encoders  # encode_base64
from email import utils  # formatdate
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import scripts.lib.example as example


def get_rfc2822_date():
    # See https://tools.ietf.org/html/rfc2822
    now = datetime.datetime.now()
    time_tuple = now.timetuple()
    timestamp = time.mktime(time_tuple)

    return utils.formatdate(timestamp)


def add_attachment(file_path):

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

        file_name = os.path.basename(file_path)
        data.add_header('Content-Disposition',
                        'attachment', filename=file_name)

        return data

    return False


def _create_mail(
    is_from='info@fundevogel.de',
    goes_to='',
    cc='',
    bcc='',
    subject='',
    text='',
    attachments=[],
    output_path='mail.eml',
):
    ###
    # Creating `eml` file
    #
    # Adding message header
    mail = MIMEMultipart()
    mail['Subject'] = subject
    mail['To'] = goes_to
    mail['From'] = is_from
    mail['Cc'] = cc
    mail['Bcc'] = bcc
    mail['Date'] = get_rfc2822_date()

    # Adding message text
    data = (
        '<html><head></head><body>'
        + example.text +
        '<p>' + text + '</p>'
        + example.signature +
        '</body></html>'
    )
    body = MIMEText(data, 'html', 'utf-8')
    mail.attach(body)

    # Adding message attachments
    if attachments:
        for attachment in attachments:
            attachment = add_attachment(attachment)
            mail.attach(attachment)

    # Writing message to disk
    with open(output_path, 'w') as file:
        output_path = generator.Generator(file)
        output_path.flatten(mail)

    return True


def create_mail(subject, text, output_path):
    return _create_mail(
        subject=subject,
        text=text,
        output_path=output_path
    )
