# Fundevogel book recommendations

## What
This project serves as an example workflow for collecting information from [CSV files](https://en.wikipedia.org/wiki/Comma-separated_values), powered by [`pcbis2pdf`](https://github.com/fundevogel/pcbis2pdf).


## Why
In the future this repository should house our [lists of recommendations](https://fundevogel.de/en/recommendations) (~ 300 books), which get published biannually.

## Setup
Create a virtual environment with `python2`, since ScribusGenerator doesn't work with v3, and activate it:

```text
    virtualenv -p python2 .venv
    source .venv/bin/activate
```


## Roadmap
- [ ] Auto PDF generation from python:
```
FUNCTION:
PDFfile

SYNTAX:
Exporting PDF

Class PDFfile() provides the PDF exporting
for Python scripting as you know it from Save as PDF
menu.
Example:
pdf = PDFfile()
pdf.thumbnails = 1 # generate thumbnails too
pdf.file = 'mypdf.pdf'
pdf.save()
```
- [ ] Adding masterpages via import script
- [ ] Adding tests

:copyright: Fundevogel Kinder- und Jugendbuchhandlung
