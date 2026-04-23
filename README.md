# photo-organizer

Python command-line photo organizer for renaming and organizing files by date, time, and metadata.

**Português:** Organizador de fotos em Python via linha de comando, com renomeação e organização por data, hora e metadados.

## About the project

**photo-organizer** is a Python command-line tool designed to rename, copy, move, and organize photos automatically based on metadata such as date, time, and, in the future, location.

This project was created for study and hands-on Python practice, covering topics such as:

- file and directory handling;
- CLI development;
- EXIF metadata reading;
- rule-based file organization;
- error handling;
- logging;
- automated testing.

## Goals

The main goal of the project is to allow photo collections to be organized automatically, predictably, and safely.

Example use cases:

- rename files based on the photo date/time;
- organize photos into folders by year, month, and day;
- avoid filename conflicts;
- run in simulation mode before changing real files;
- eventually organize by location and detect duplicates.

## Planned features

### Initial MVP

- recursive directory scanning;
- image file detection;
- extraction of the best available photo date;
- pattern-based renaming;
- date-based folder organization;
- support for `--dry-run`;
- support for `--copy` and `--move`;
- simple logs and execution reports.

### Future enhancements

- GPS/EXIF support for location-based organization;
- reverse geocoding for city/state/country;
- duplicate detection by hash;
- video support;
- configuration file support (`.yaml` or `.json`);
- extension filters;
- CSV/JSON reports;
- more complete automated tests.

## Suggested initial structure

```text
photo-organizer/
  pyproject.toml
  README.md
  src/
    photo_organizer/
      __init__.py
      cli.py
      scanner.py
      metadata.py
      naming.py
      planner.py
      executor.py
      duplicates.py
      report.py
  tests/
    test_naming.py
    test_metadata.py
    test_planner.py
```

## Module responsibilities

- `cli.py`: command-line interface;
- `scanner.py`: file scanning;
- `metadata.py`: EXIF reading and primary date resolution;
- `naming.py`: generation of filenames and destination paths;
- `planner.py`: planning the actions to execute;
- `executor.py`: copy, move, and rename operations;
- `duplicates.py`: duplicate file detection;
- `report.py`: report and summary generation.

## Organization rules

The initial strategy is to prioritize date/time in the following order:

1. EXIF `DateTimeOriginal`;
2. `CreateDate`;
3. file modification date as a fallback.

Example generated filename:

```text
2024-08-15_14-32-09.jpg
```

Example folder organization:

```text
Photos/2024/08/15/2024-08-15_14-32-09.jpg
```

When filename conflicts occur, the system may generate variations such as:

```text
2024-08-15_14-32-09.jpg
2024-08-15_14-32-09_01.jpg
2024-08-15_14-32-09_02.jpg
```

## Installation

### Requirements

- Python 3.10 or newer

### Cloning the repository

```bash
git clone https://github.com/YOUR_USERNAME/photo-organizer.git
cd photo-organizer
```

### Creating a virtual environment

#### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Installing dependencies

If the project is packaged with `pyproject.toml`:

```bash
pip install -e .
```

Or, if the project is still in an early stage and not yet fully packaged:

```bash
pip install -r requirements.txt
```

## Usage

### Example: scanning a directory

```bash
photo-organizer scan ~/Photos
```

### Example: organizing by date

```bash
photo-organizer organize ~/Photos --output ~/OrganizedPhotos --by date
```

### Example: simulation mode

```bash
photo-organizer organize ~/Photos --output ~/OrganizedPhotos --by date --dry-run
```

### Example: copying instead of moving

```bash
photo-organizer organize ~/Photos --output ~/OrganizedPhotos --by date --copy
```

### Example: future duplicate detection

```bash
photo-organizer dedupe ~/OrganizedPhotos
```

## Expected output example

```text
[INFO] Scanning directory: /home/user/Photos
[INFO] Found 248 image files
[INFO] Planning file operations
[INFO] DRY-RUN enabled: no files will be changed
[INFO] MOVE /home/user/Photos/IMG_1034.jpg -> /home/user/OrganizedPhotos/2024/08/15/2024-08-15_14-32-09.jpg
[INFO] Completed successfully
```

## Planned libraries

The project can start with the Python standard library and evolve gradually.

### Standard library

- `pathlib`
- `argparse`
- `datetime`
- `shutil`
- `hashlib`
- `logging`
- `csv`
- `json`

### Possible external libraries

- `Pillow` or `exifread` for EXIF support;
- `geopy` for geocoding;
- `typer` for a more modern CLI;
- `pytest` for testing.

## Best practices adopted

- separation of responsibilities;
- typing with `typing`;
- explicit error handling;
- clear logging;
- safe mode with `--dry-run`;
- test-ready code;
- simple and evolvable architecture.

## Roadmap

### Version 0.1.0
- basic image reading;
- date extraction;
- simple renaming;
- date-based organization;
- `dry-run` mode.

### Version 0.2.0
- copy/move support;
- conflict prevention;
- execution report;
- CLI improvements.

### Version 0.3.0
- hash-based duplicate detection;
- support for more extensions;
- automated tests.

### Version 0.4.0
- GPS/EXIF support;
- location-based organization;
- reverse geocoding;
- external configuration.

## Project status

In development.

## Motivation

This project was created as a practical exercise to study Python applied to real-world file organization and command-line automation problems.

## Contributing

Suggestions, improvements, and ideas are welcome.

## License

This project may be distributed under the MIT License.
