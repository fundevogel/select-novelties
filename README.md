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
- [x] Auto PDF generation from python
- [x] Adding masterpages via import script
- [ ] Fixing bug that causes imported pages to be "stacked" somehow (maybe Scribus)
- [ ] Adding tests
- [x] Generate list: book>page, sorted by publisher
- [ ] Improving string-replacement
  - Neuausg > Neuausgabe
  - 1Zweitauflage (?)
  - farbigen Tab > farbige Tabellen
  - + > und (?)
  - 3 Aufl > Drittauflage / 3. Auflage
  - 17 Aufl > 17. Auflage
  - Großformatiges Paperback Klappenbroschur > Großformatiges Paperback (Klappenbroschur)
  - Mit zahlreichen bunten zum Teil ausklappb Bild > Mit zahlreichen bunten und zum Teil ausklappbaren Bildern
  - Mit farbige Abbildungen > Mit farbigen Abbildungen
  - 1 Auflage > Erstauflage
  - Mit Illustrationen und Sticker > Mit Illustrationen und Stickern
  - 6, überarb Aufl > Sechste, überarbeitete Auflage
  - (2 mp3 CD) > (2 CDs)



## Troubleshooting
After exporting saved lists (called *Speicherlisten*) as `.csv` files from [`pcbis`](https://www.pcbis.de), they're saved as Latin-3 encoded text ([ISO-8859-3](https://en.wikipedia.org/wiki/ISO/IEC_8859-3)). Changing this by hand, let's say when removing duplicate entries, will render certain characters (especially [umlauts](https://en.wikipedia.org/wiki/Diaeresis_(diacritic)#Umlaut)) unreadable during the process.


:copyright: Fundevogel Kinder- und Jugendbuchhandlung
