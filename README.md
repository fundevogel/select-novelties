# Recommended novelties

## About this project
Every year we put together two [lists of recommended novelties](https://fundevogel.de/en/recommendations) (~ 300 books) that become our spring and autumn editions.

This repository houses the workflow for doing so, all the logic for using [CSV files](https://en.wikipedia.org/wiki/Comma-separated_values), exported from KNV's `pcbis.de` backend, fetching bibliographic data from their WSDL API (powered by [`php-pcbis`](https://github.com/fundevogel/php-pcbis)) and creating each issue from an individual [Scribus](https://www.scribus.net) template using the excellent [`ScribusGenerator`](https://github.com/berteh/ScribusGenerator) library.


## Setup
Create a virtual environment with `python2`, since ScribusGenerator doesn't work with v3, and activate it:

```bash
  # Create virtual environment
    virtualenv -p python3 .env
    source .env/bin/activate

    # Install dependencies
    python -m pip install -r requirements.txt
```


## Roadmap
- [x] Auto PDF generation from python
- [x] Adding masterpages via import script
- [x] ~~Implement python WSDL workflow (eg using Zeep)~~
- [x] Generate list: book>page, sorted by publisher
- [x] ~~Improving string-replacement~~
- [ ] Adding tests
- [ ] Fixing bug that causes imported pages to be "stacked" somehow (maybe Scribus)


:copyright: Fundevogel Kinder- und Jugendbuchhandlung
