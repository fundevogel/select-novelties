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
- [x] Auto PDF generation from python, see `e14f969`
- [x] Adding masterpages via import script, see `bafac00`
- [ ] Adding tests


## Troubleshooting
After exporting `.csv` files from `pcbis`, they're saved as Latin-3 encoded text (ISO-8859-3). Changing this by hand (eg when removing duplicate entries) causes trouble.


:copyright: Fundevogel Kinder- und Jugendbuchhandlung
