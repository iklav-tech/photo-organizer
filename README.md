# photo-organizer

Python command-line photo organizer for renaming and organizing files by date, time, and metadata.

Repository: https://github.com/iklav-tech/photo-organizer

## Changelog

Release history is tracked in [CHANGELOG.md](CHANGELOG.md), including delivered v0.1.0, v0.2.0 and v0.3.0 scope.

## Current status

The project includes a tested v0.3.0 CLI workflow:

- CLI with `scan` and `organize` commands;
- `dedupe` command for read-only duplicate discovery;
- image scanning with recursive search;
- centralized and easily extensible supported image format list;
- case-insensitive extension matching;
- EXIF extraction for compatible JPEG/TIFF images;
- deterministic image hashing with chunked reads for large files;
- safe hash comparison for duplicate detection workflows;
- duplicate image grouping by content hash with original/duplicates output;
- structured duplicate reports in JSON or CSV for later analysis;
- date resolution with EXIF priority and fallback;
- deterministic naming rules;
- destination folder planning by date (`YYYY/MM/DD`);
- explicit planning layer separated from execution;
- automatic destination directory creation;
- safe move behavior that removes the source only after a successful copy;
- filename collision handling with predictable suffixes (`_01`, `_02`, `_03`);
- `--dry-run` simulation with no filesystem changes;
- `--plan` inspection mode without execution;
- structured execution summaries;
- resilient per-file error handling for invalid files and malformed metadata;
- optional audit report export in JSON or CSV with `--report`;
- improved CLI help with examples and grouped arguments;
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
- export an audit report of what happened;
- eventually organize by location;
- find duplicate images by content hash before organizing or cleaning a collection;
- export duplicate reports for spreadsheet or automated analysis.

## Implemented features

### CLI and commands

- `photo-organizer --help`
- `photo-organizer --version`
- `photo-organizer scan --help`
- `photo-organizer dedupe --help`
- `photo-organizer organize --help`
- `photo-organizer dedupe SOURCE --report duplicates.json`
- `photo-organizer dedupe SOURCE --report duplicates.csv`
- grouped `organize` help sections for paths, execution, reports and mode;
- examples shown directly in help output;
- clear argument errors for missing required parameters and invalid report extensions.

### Scan behavior

- recursive search in source directory;
- supported extensions: `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.webp`, `.bmp`;
- unsupported files are ignored;
- stable/consistent returned path list;
- user-friendly message when source directory does not exist.

Supported formats are configured in `photo_organizer.constants.IMAGE_FORMATS`.
To add another format, add one `ImageFormat` entry with its extensions and set
`supports_exif=True` only when the current metadata reader can reliably extract
EXIF from that format.

### Dedupe behavior

- `photo-organizer dedupe SOURCE` scans supported images recursively;
- duplicate groups are identified by deterministic content hash;
- output shows one original and one or more duplicates per group;
- files with different content are not grouped together;
- the command is read-only and does not move, copy or delete files;
- `--report duplicates.json` writes summary and grouped duplicate details;
- `--report duplicates.csv` writes one analysis-friendly row per duplicate-group file.

### Metadata behavior

- EXIF extraction for compatible JPEG and TIFF images;
- formats without real EXIF support in the current reader, such as PNG, WEBP
  and BMP, safely skip EXIF extraction and use file `mtime` fallback;
- safe handling when EXIF is missing;
- safe handling of EXIF read exceptions;
- safe handling of malformed EXIF data without interrupting the whole run;
- primary date resolution priority:
  1. `DateTimeOriginal`
  2. `CreateDate`
  3. file `mtime` fallback
- normalized output as `datetime`.

### Naming and planning

- default naming format: `YYYY-MM-DD_HH-MM-SS.ext`;
- original extension preserved;
- deterministic name generation;
- collision handling with suffixes such as `_01`, `_02`, `_03`;
- destination directory structure: `YYYY/MM/DD`;
- `pathlib`-based path generation for Linux/Windows compatibility.

### Plan and execution separation

- operations are planned first into an intermediate structure;
- each plan item contains source, destination, action (`move`/`copy`) and fallback metadata;
- plan can be inspected without execution using `--plan`.

### Dry-run and operation modes

- `--dry-run` simulates all operations without changing files;
- dry-run output shows exactly what would happen;
- behavior matches real execution except physical file operations;
- `--copy` and `--move` are supported (`move` is default);
- destination directories are created automatically for real operations;
- move operations are implemented safely: copy first, then remove source after success.

### Reporting and audit

- final execution summary includes processed, ignored, error and fallback counts;
- summary distinguishes `dry-run`, `execute` and `plan` modes;
- `--report path.json` exports a structured JSON report;
- `--report path.csv` exports a CSV report;
- report rows include source, destination, action, status and observations.

Duplicate reports:

- `photo-organizer dedupe SOURCE --report duplicates.json` writes `summary` and
  `duplicate_groups`;
- each JSON duplicate group includes `group_id`, `hash`, `quantity`, `original`,
  `duplicates` and `paths`;
- `photo-organizer dedupe SOURCE --report duplicates.csv` writes one row per file
  in a duplicate group;
- CSV duplicate rows include `group_id`, `hash`, `quantity`, `role` and `path`.

### Logging

- logs include start/end markers and processed counts;
- logs include fallback decisions for date resolution;
- logs include per-file errors for invalid files or malformed metadata while
  processing continues for remaining files;
- logs include execution summary counters;
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
      hashing.py
      naming.py
      planner.py
      executor.py
      logging_config.py
  tests/
    test_import.py
    test_cli.py
    test_scanner.py
    test_executor.py
    test_integration.py
    test_naming.py
    test_metadata.py
    test_hashing.py
    test_planner.py
```

## Module responsibilities

- `cli.py`: command-line interface and command orchestration;
- `scanner.py`: recursive file scanning and extension filtering;
- `metadata.py`: EXIF extraction and best-date resolution;
- `hashing.py`: deterministic file/image hashes, safe digest comparison and duplicate grouping;
- `naming.py`: deterministic filename generation;
- `planner.py`: destination folder planning by date;
- `executor.py`: operation planning and execution/simulation;
- `logging_config.py`: logging setup and level control;
- `constants.py`: centralized image format definitions, including EXIF capability flags.

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

When a destination already exists, the organizer does not overwrite it by default. It appends the next available numeric suffix:

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

### Example: finding duplicate images

```bash
photo-organizer dedupe ~/Photos
```

The command is read-only. It prints duplicate groups with the hash, quantity,
original file and duplicated files:

```text
Duplicate group 1:
  Hash: de7030234493a8bea844dbe1d8676e68a2c1a4b014c721f0425a22b6df66faec
  Quantity: 2
  Original: /home/user/Photos/a.jpg
  Duplicate: /home/user/Photos/copy/a.jpg
```

### Example: export duplicate reports

```bash
photo-organizer dedupe ~/Photos --report duplicates.json
photo-organizer dedupe ~/Photos --report duplicates.csv
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

### Example: export JSON audit report

```bash
photo-organizer organize ~/Photos --output ~/OrganizedPhotos --report audit.json
```

### Example: export CSV audit report

```bash
photo-organizer organize ~/Photos --output ~/OrganizedPhotos --report audit.csv
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
[INFO] Execution summary: mode=dry-run processed_files=248 ignored_files=12 error_files=0 fallback_files=31
[INFO] Execution finished: organize processed_files=248
```

## Audit report format

JSON reports include a summary and operation rows:

```json
{
  "summary": {
    "mode": "execute",
    "processed_files": 1,
    "ignored_files": 0,
    "error_files": 0,
    "fallback_files": 1
  },
  "operations": [
    {
      "source": "/home/user/Photos/IMG_1034.jpg",
      "destination": "/home/user/OrganizedPhotos/2024/08/15/2024-08-15_14-32-09.jpg",
      "action": "move",
      "status": "success",
      "observations": ""
    }
  ]
}
```

CSV reports use the following columns:

```text
source,destination,action,status,observations
```

## Duplicate report format

JSON duplicate reports include a summary and grouped details:

```json
{
  "summary": {
    "duplicate_files": 1,
    "duplicate_groups": 1,
    "total_files_in_duplicate_groups": 2
  },
  "duplicate_groups": [
    {
      "duplicates": [
        "/home/user/Photos/copy/a.jpg"
      ],
      "group_id": 1,
      "hash": "de7030234493a8bea844dbe1d8676e68a2c1a4b014c721f0425a22b6df66faec",
      "original": "/home/user/Photos/a.jpg",
      "paths": [
        "/home/user/Photos/a.jpg",
        "/home/user/Photos/copy/a.jpg"
      ],
      "quantity": 2
    }
  ]
}
```

CSV duplicate reports use the following columns:

```text
group_id,hash,quantity,role,path
```

## Libraries

The project uses mostly Python standard library plus Pillow for EXIF handling.

### Standard library

- `pathlib`
- `argparse`
- `datetime`
- `shutil`
- `hashlib`
- `hmac`
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
- safe move behavior;
- non-overwriting destination conflict handling;
- structured audit reports;
- structured duplicate reports;
- deterministic chunked hashing for large files;
- safe digest comparison;
- test-ready code;
- simple and evolvable architecture.

## Version v0.1.0 delivered scope

This section consolidates what was implemented in v0.1.0 according to completed issues.

### CLI foundations

- root help works (`photo-organizer --help`);
- subcommand help works (`scan --help`, `organize --help`);
- clear required argument errors;
- root options include `--version` and `--log-level`.

### Scan and file discovery

- recursive scan of input directory;
- centralized supported image format configuration;
- case-insensitive extension checks;
- unsupported files are ignored;
- stable/consistent discovered path list;
- clear error message when source directory does not exist.

### Metadata and date resolution

- EXIF extraction for compatible JPEG files;
- safe behavior when EXIF is missing;
- safe handling of EXIF read exceptions;
- date resolution order:
  1. `DateTimeOriginal`
  2. `CreateDate`
  3. `mtime` fallback

### Naming and destination planning

- deterministic name generation with format `YYYY-MM-DD_HH-MM-SS.ext`;
- original extension preservation;
- destination tree generation in `YYYY/MM/DD`;
- `pathlib` compatibility for Linux and Windows.

### Planning, execution and simulation

- explicit operation planning before execution;
- intermediate operation items with source, destination and action;
- inspectable planning mode with `--plan`;
- execution modes with `--move` (default) and `--copy`;
- dry-run simulation mode with `--dry-run` that does not alter files;
- end-to-end tested dry-run flow.

### Logging and observability

- start/end execution logs;
- processed/planned file counters;
- fallback-decision logs for metadata date resolution;
- contextual error logs;
- configurable log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

### Automated tests

- unit tests for scanner, metadata, naming, planner and executor;
- CLI behavior tests;
- end-to-end dry-run test for `organize`;
- local suite currently green.

## Version v0.2.0 delivered scope

This section consolidates what was implemented after the v0.1.0 MVP.

### Safer execution

- move operations now remove the source only after the destination is successfully created;
- missing destination directories are created automatically;
- existing destination files are not overwritten by default.

### Conflict handling

- filename collisions are resolved with deterministic suffixes (`_01`, `_02`, `_03`, ...);
- suffix generation is applied consistently for copy, move and dry-run planning;
- tests cover collision behavior and ensure existing files are preserved.

### Execution summaries

- `organize` prints a final execution summary;
- summary includes processed, ignored, error and fallback counts;
- summary distinguishes `dry-run`, `execute` and `plan` modes.

### Audit reports

- `--report` exports an audit report when the path ends in `.json` or `.csv`;
- JSON reports contain `summary` and `operations`;
- CSV reports contain one row per operation;
- operation records include source, destination, action, status and observations.

### CLI UX

- help output now includes examples;
- `organize --help` groups related arguments;
- errors for missing `--output` and invalid report extensions are clearer.

### Integration tests

- integration tests cover the complete planning and execution pipeline using temporary directories;
- copy, move and dry-run flows are tested end to end;
- tests cover automatic directory creation and destination conflicts.

## Version v0.3.0 delivered scope

This section consolidates what was implemented after the v0.2.0 workflow.

### Hashing and duplicate detection

- SHA-256 hashes are calculated in chunks so large files are not loaded fully
  into memory;
- hash values are deterministic for identical content;
- digest comparison uses `hmac.compare_digest`;
- duplicate groups expose the content hash, original file and duplicate files;
- files with different content are not reported as duplicates.

### Dedupe command

- `photo-organizer dedupe SOURCE` scans supported images recursively;
- the command is read-only by default and also accepts `--read-only` explicitly;
- output lists duplicate groups with hash, quantity, original and duplicates;
- missing or invalid source directories return a clear non-zero error;
- `--report duplicates.json` and `--report duplicates.csv` export structured
  duplicate reports for later analysis.

### Additional image formats

- supported image extensions now include `.jpg`, `.jpeg`, `.png`, `.tif`,
  `.tiff`, `.webp` and `.bmp`;
- format support is centralized in `IMAGE_FORMATS`;
- EXIF extraction is attempted only for formats marked with `supports_exif=True`;
- formats without reliable EXIF support safely use file modification time as
  the date fallback.

### Resilience

- invalid files and malformed metadata are handled per file;
- failures while reading EXIF, planning an operation or hashing a file are logged
  with the affected path and error message;
- processing continues for remaining files instead of aborting the whole run.

### Automated hash and dedupe tests

- tests cover equal and different file content;
- tests use temporary files and directories;
- CLI tests cover `dedupe`, duplicate reports and no-duplicate output.

## Roadmap

### Version 0.1.0
- implemented and stabilized (see Version v0.1.0 delivered scope section).

### Version 0.2.0
- implemented and stabilized (see Version v0.2.0 delivered scope section).

### Version 0.3.0
- implemented and stabilized (see Version v0.3.0 delivered scope section).

### Version 0.4.0
- support for more media types (including videos);
- richer filtering (include/exclude and depth controls);
- performance improvements for large collections.

### Version 0.5.0
- GPS/EXIF support;
- location-based organization;
- reverse geocoding;
- external configuration;
- richer report analytics.

## Project status

In active development, with a stable tested v0.3.0 workflow for scan, organize
and dedupe flows.

## Motivation

This project was created as a practical exercise to study Python applied to real-world file organization and command-line automation problems.

## Contributing

Suggestions, improvements, and ideas are welcome.

## License

This project may be distributed under the MIT License.
