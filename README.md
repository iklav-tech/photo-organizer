# photo-organizer

Python command-line photo organizer for renaming and organizing files by date, time, and metadata.

Repository: https://github.com/iklav-tech/photo-organizer

## Current status

The project already includes an end-to-end MVP with automated tests:

- CLI with `scan` and `organize` commands;
- image scanning with recursive search;
- centralized supported extension list (`.jpg`, `.jpeg`, `.png`);
- case-insensitive extension matching;
- EXIF extraction for compatible JPEG images;
- date resolution with EXIF priority and fallback;
- deterministic naming rules;
- destination folder planning by date (`YYYY/MM/DD`);
- explicit planning layer separated from execution;
- `--dry-run` simulation with no filesystem changes;
- `--plan` inspection mode without execution;
- structured logging with configurable log level;
- friendly error messages for invalid/missing source directory.

Quick local setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -c "import photo_organizer; print(photo_organizer.__version__)"
```

Portuguese summary: Organizador de fotos em Python via linha de comando, com renomeacao e organizacao por data, hora e metadados.

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

## Implemented features

### CLI and commands

- `photo-organizer --help`
- `photo-organizer --version`
- `photo-organizer scan --help`
- `photo-organizer organize --help`
- clear argument errors for missing required parameters.

### Scan behavior

- recursive search in source directory;
- supported extensions: `.jpg`, `.jpeg`, `.png`;
- unsupported files are ignored;
- stable/consistent returned path list;
- user-friendly message when source directory does not exist.

### Metadata behavior

- EXIF extraction for compatible JPEG images;
- safe handling when EXIF is missing;
- safe handling of EXIF read exceptions;
- primary date resolution priority:
  1. `DateTimeOriginal`
  2. `CreateDate`
  3. file `mtime` fallback
- normalized output as `datetime`.

### Naming and planning

- default naming format: `YYYY-MM-DD_HH-MM-SS.ext`;
- original extension preserved;
- deterministic name generation;
- destination directory structure: `YYYY/MM/DD`;
- `pathlib`-based path generation for Linux/Windows compatibility.

### Plan and execution separation

- operations are planned first into an intermediate structure;
- each plan item contains source, destination, and action (`move`/`copy`);
- plan can be inspected without execution using `--plan`.

### Dry-run and operation modes

- `--dry-run` simulates all operations without changing files;
- dry-run output shows exactly what would happen;
- behavior matches real execution except physical file operations;
- `--copy` and `--move` are supported (`move` is default).

### Logging

- logs include start/end markers and processed counts;
- logs include fallback decisions for date resolution;
- errors include contextual details;
- log verbosity configurable with `--log-level` (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).

## Current project structure

```text
photo-organizer/
  pyproject.toml
  README.md
  src/
    photo_organizer/
      __init__.py
      __main__.py
      cli.py
      constants.py
      scanner.py
      metadata.py
      naming.py
      planner.py
      executor.py
      logging_config.py
  tests/
    test_import.py
    test_cli.py
    test_scanner.py
    test_executor.py
    test_naming.py
    test_metadata.py
    test_planner.py
```

## Module responsibilities

- `cli.py`: command-line interface and command orchestration;
- `scanner.py`: recursive file scanning and extension filtering;
- `metadata.py`: EXIF extraction and best-date resolution;
- `naming.py`: deterministic filename generation;
- `planner.py`: destination folder planning by date;
- `executor.py`: operation planning and execution/simulation;
- `logging_config.py`: logging setup and level control;
- `constants.py`: centralized extension definitions.

## Organization rules

Date priority strategy:

1. EXIF `DateTimeOriginal`;
2. `CreateDate`;
3. file modification date as fallback.

Example generated filename:

```text
2024-08-15_14-32-09.jpg
```

Example folder organization:

```text
Photos/2024/08/15/2024-08-15_14-32-09.jpg
```

Current implementation focuses on deterministic naming; conflict handling is planned as a future enhancement.

## Installation

### Requirements

- Python 3.10 or newer

### Cloning the repository

```bash
git clone https://github.com/iklav-tech/photo-organizer.git
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

```bash
pip install -e .
```

## Usage

### Common options

```bash
photo-organizer --version
photo-organizer --log-level DEBUG scan ~/Photos
```

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

### Example: explicit move mode

```bash
photo-organizer organize ~/Photos --output ~/OrganizedPhotos --by date --move
```

### Example: inspect plan without execution

```bash
photo-organizer organize ~/Photos --output ~/OrganizedPhotos --plan
```

### Scan behavior when directory does not exist

```bash
photo-organizer scan ~/Photos
```

If the directory does not exist, the CLI returns a clear error message and non-zero exit code instead of showing a traceback.

## Expected output example

```text
[INFO] Execution started: organize source=/home/user/Photos output=/home/user/OrganizedPhotos mode=move dry_run=True plan_only=False
[INFO] Generated execution plan: operations=248 strategy=date
[INFO] DRY-RUN enabled: no files will be changed
[INFO] [DRY-RUN] MOVE /home/user/Photos/IMG_1034.jpg -> /home/user/OrganizedPhotos/2024/08/15/2024-08-15_14-32-09.jpg
[INFO] Execution finished: organize processed_files=248
```

## Libraries

The project uses mostly Python standard library plus Pillow for EXIF handling.

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

- `Pillow` for EXIF support;
- `geopy` for geocoding;
- `typer` for a more modern CLI;
- `pytest` for testing.

## Best practices adopted

- separation of responsibilities;
- typing with `typing`;
- explicit error handling;
- clear logging;
- planning and execution separation;
- safe mode with `--dry-run`;
- test-ready code;
- simple and evolvable architecture.

## Roadmap

### Version 0.1.0
- basic image scanning;
- extension filtering;
- date extraction and fallback chain;
- deterministic naming;
- date-based organization;
- `dry-run` mode.

### Version 0.2.0
- copy/move support;
- plan inspection mode (`--plan`);
- improved logging and error messages;
- CLI option maturity.

### Version 0.3.0
- filename conflict prevention;
- hash-based duplicate detection;
- support for more media extensions;
- richer execution report.

### Version 0.4.0
- GPS/EXIF support;
- location-based organization;
- reverse geocoding;
- external configuration;
- report export formats (CSV/JSON).

## Project status

In active development, with a stable tested MVP for scan + organize flows.

## Motivation

This project was created as a practical exercise to study Python applied to real-world file organization and command-line automation problems.

## Contributing

Suggestions, improvements, and ideas are welcome.

## License

This project may be distributed under the MIT License.
