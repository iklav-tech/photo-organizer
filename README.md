# photo-organizer

Python command-line photo organizer for renaming and organizing files by date, time, and metadata.

Repository: https://github.com/iklav-tech/photo-organizer

## Changelog

Release history is tracked in [CHANGELOG.md](CHANGELOG.md), including delivered v0.1.0, v0.2.0, v0.3.0 and v0.4.0 scope.

## Current status

The project includes a tested v0.4.0 CLI workflow:

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
- GPS coordinate extraction from EXIF metadata;
- optional reverse geocoding from GPS coordinates to city, state and country;
- deterministic default naming rules;
- configurable filename patterns through CLI or configuration files;
- destination folder planning by date (`YYYY/MM/DD`), location, location plus
  date, custom destination pattern, or city/state/month hybrid strategy;
- explicit planning layer separated from execution;
- automatic destination directory creation;
- safe move behavior that removes the source only after a successful copy;
- filename collision handling with predictable suffixes (`_01`, `_02`, `_03`);
- `--dry-run` simulation with no filesystem changes;
- `--plan` inspection mode without execution;
- structured execution summaries;
- resilient per-file error handling for invalid files and malformed metadata;
- optional audit report export in JSON or CSV with `--report`;
- external JSON/YAML organization config with custom naming, destination and
  behavior rules;
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

**photo-organizer** is a Python command-line tool designed to rename, copy, move, and organize photos automatically based on metadata such as date, time and location.

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
- organize photos by city, state and month when GPS metadata is available;
- customize generated filenames and destination paths;
- avoid filename conflicts;
- run in simulation mode before changing real files;
- export an audit report of what happened;
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
- `photo-organizer organize SOURCE --config organizer.yaml`
- `photo-organizer organize SOURCE --output Organized --name-pattern "{date:%Y%m%d}_{stem}{ext}"`
- `photo-organizer organize SOURCE --output Organized --by city-state-month`
- grouped `organize` help sections for paths, execution, reports and mode;
- examples shown directly in help output;
- clear argument errors for missing required parameters, invalid report
  extensions, invalid configuration and invalid filename patterns.

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
- GPS coordinates normalized to decimal degrees when available;
- missing GPS data handled safely without interrupting the run;
- reverse geocoding failures are treated as unresolved location data.

### Metadata precedence and compatibility matrix

When multiple metadata sources can describe the same logical field, the
organizer follows a single precedence policy. Each candidate is classified as:

- **Primary**: preferred authoritative embedded metadata;
- **Fallback**: accepted embedded metadata when primary data is unavailable;
- **Heuristic**: derived or filesystem data used only when embedded metadata is
  missing or unusable.

Current support status:

- **Implemented**: already read or used by the current code;
- **Planned**: formal policy is defined, but extraction support is not yet
  implemented.

| Field | Priority | Source | Keys | Role | Status |
| --- | ---: | --- | --- | --- | --- |
| `date_taken` | 1 | EXIF | `DateTimeOriginal` | Primary | Implemented |
| `date_taken` | 2 | EXIF | `CreateDate`, `DateTime`, `DateTimeDigitized` | Fallback | Implemented |
| `date_taken` | 3 | XMP | `exif:DateTimeOriginal`, `xmp:CreateDate` | Fallback | Planned |
| `date_taken` | 4 | IPTC-IIM | `DateCreated`, `TimeCreated` | Fallback | Planned |
| `date_taken` | 5 | PNG metadata | `Creation Time`, `CreationTime` | Fallback | Planned |
| `date_taken` | 6 | Filesystem | `mtime` | Heuristic | Implemented |
| `location` | 1 | EXIF | `GPSInfo`, `GPSLatitude`, `GPSLongitude` | Primary | Implemented |
| `location` | 2 | XMP | `exif:GPSLatitude`, `exif:GPSLongitude` | Fallback | Planned |
| `location` | 3 | IPTC-IIM | `City`, `Province-State`, `Country-PrimaryLocationName` | Fallback | Planned |
| `location` | 4 | Reverse geocoding | `GPSLatitudeDecimal`, `GPSLongitudeDecimal` | Heuristic | Implemented |
| `title` | 1 | XMP | `dc:title`, `photoshop:Headline` | Primary | Planned |
| `title` | 2 | IPTC-IIM | `ObjectName`, `Headline` | Fallback | Planned |
| `title` | 3 | PNG metadata | `Title` | Fallback | Planned |
| `title` | 4 | EXIF | `ImageDescription` | Fallback | Planned |
| `author` | 1 | XMP | `dc:creator` | Primary | Planned |
| `author` | 2 | IPTC-IIM | `By-line`, `Writer-Editor` | Fallback | Planned |
| `author` | 3 | PNG metadata | `Author` | Fallback | Planned |
| `author` | 4 | EXIF | `Artist`, `Copyright` | Fallback | Planned |
| `description` | 1 | XMP | `dc:description` | Primary | Planned |
| `description` | 2 | IPTC-IIM | `Caption-Abstract` | Fallback | Planned |
| `description` | 3 | PNG metadata | `Description`, `Comment` | Fallback | Planned |
| `description` | 4 | EXIF | `ImageDescription`, `UserComment` | Fallback | Planned |

The current `date_taken` resolver implements the supported subset of this
policy: EXIF `DateTimeOriginal`, then EXIF `CreateDate`/aliases, then
filesystem `mtime` as a heuristic. Location organization currently uses EXIF
GPS coordinates and reverse geocoding; XMP, IPTC-IIM and PNG metadata entries
are reserved by policy for future extractors.

### Naming and planning

- default naming format: `YYYY-MM-DD_HH-MM-SS.ext`;
- optional configured naming format through `naming.pattern` or CLI
  `--name-pattern`;
- original extension preserved;
- deterministic name generation;
- collision handling with suffixes such as `_01`, `_02`, `_03`;
- destination directory structure: `YYYY/MM/DD`;
- optional configured destination format through `destination.pattern`;
- built-in organization strategies for date, location, location plus date, and
  city/state/month hybrid paths;
- location strategies automatically request reverse geocoding and fall back to
  date-based organization when GPS or location resolution is unavailable;
- `pathlib`-based path generation for Linux/Windows compatibility.

### External configuration

The `organize` command can read JSON, YAML or YML configuration files with
`--config PATH`. CLI arguments explicitly passed by the user take precedence
over equivalent config values.

Example YAML:

```yaml
output: ./OrganizedPhotos
naming:
  pattern: "{date:%Y%m%d_%H%M%S}_{stem}{ext}"
destination:
  strategy: city-state-month
behavior:
  mode: copy
  dry_run: true
  plan: false
  reverse_geocode: true
```

The same structure is accepted as JSON. Supported fields:

- `output`: destination root directory;
- `naming.pattern`: filename pattern with `{date}`, `{stem}`, `{ext}` and
  `{original}`;
- `destination.pattern`: directory pattern with `{date}`, `{country}`,
  `{state}` and `{city}`;
- `destination.strategy` or `behavior.organization_strategy`: `date`,
  `location`, `location-date` or `city-state-month`;
- `behavior.mode`: `copy` or `move`;
- `behavior.dry_run`, `behavior.plan`, `behavior.reverse_geocode`: booleans.

Filename patterns use Python datetime formatting for `{date:...}`. Supported
fields are:

- `{date}`: resolved photo datetime, optionally with a format such as
  `{date:%Y%m%d_%H%M%S}`;
- `{stem}`: original filename without extension;
- `{ext}`: original extension, including the leading dot;
- `{original}`: original filename with extension.

Filename patterns cannot contain path separators. Invalid fields produce a
clear CLI error before planning starts.

Organization strategies:

- `date`: writes to `YYYY/MM/DD`;
- `location`: writes to `Country/State/City`;
- `location-date`: writes to `Country/State/City/YYYY/MM`;
- `city-state-month`: writes to `City-State/YYYY-MM`, for example
  `Paraty-RJ/2024-08`.

Location-based strategies enable reverse geocoding automatically. If GPS data
is missing or location resolution fails, organization falls back to the default
date path.

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
      config.py
      constants.py
      geocoding.py
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
    test_config.py
    test_geocoding.py
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
- `config.py`: external JSON/YAML configuration loading and validation;
- `scanner.py`: recursive file scanning and extension filtering;
- `metadata.py`: EXIF extraction, GPS extraction and best-date resolution;
- `geocoding.py`: reverse geocoding from GPS coordinates to city, state and country;
- `hashing.py`: deterministic file/image hashes, safe digest comparison and duplicate grouping;
- `naming.py`: deterministic and pattern-based filename generation;
- `planner.py`: destination folder planning by date, location and custom patterns;
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

Custom filename pattern example:

```bash
photo-organizer organize ~/Photos --output ~/OrganizedPhotos --name-pattern "{date:%Y%m%d_%H%M%S}_{stem}{ext}"
```

For an original file named `IMG_1034.jpg` taken at `2024-08-15 14:32:09`,
that pattern produces:

```text
20240815_143209_IMG_1034.jpg
```

Example folder organization:

```text
Photos/2024/08/15/2024-08-15_14-32-09.jpg
```

Example hybrid location and month organization:

```text
Photos/Paraty-RJ/2024-08/2024-08-15_14-32-09.jpg
```

Available filename fields:

- `{date}`: resolved photo datetime, with optional datetime formatting such as
  `{date:%Y%m%d_%H%M%S}`;
- `{stem}`: original filename without extension;
- `{ext}`: original extension, including the leading dot;
- `{original}`: original filename with extension.

Filename patterns cannot contain path separators. Unknown fields or invalid
patterns return a clear CLI/configuration error before planning starts.

Available destination fields for `destination.pattern`:

- `{date}`: resolved photo datetime, with optional datetime formatting;
- `{country}`: resolved country or `Unknown`;
- `{state}`: resolved state or `Unknown`;
- `{city}`: resolved city or `Unknown`.

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

### Example: organizing by city, state and month

```bash
photo-organizer organize ~/Photos --output ~/OrganizedPhotos --by city-state-month
```

This strategy uses reverse geocoding and writes files under paths like
`Paraty-RJ/2024-08`. If GPS is missing or the location cannot be resolved, it
falls back to the default date path.

### Example: custom filename pattern

```bash
photo-organizer organize ~/Photos --output ~/OrganizedPhotos --name-pattern "{date:%Y%m%d_%H%M%S}_{stem}{ext}"
```

### Example: external configuration file

```bash
photo-organizer organize ~/Photos --config organizer.yaml
```

```yaml
output: ~/OrganizedPhotos
naming:
  pattern: "{date:%Y%m%d_%H%M%S}_{stem}{ext}"
destination:
  strategy: city-state-month
behavior:
  mode: copy
  dry_run: true
  reverse_geocode: true
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
[INFO] Execution summary: mode=dry-run processed_files=248 ignored_files=12 error_files=0 fallback_files=31 location_files=0 gps_files=0 missing_gps_files=0 organization_fallback_files=0
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
    "fallback_files": 1,
    "location_files": 0,
    "gps_files": 0,
    "missing_gps_files": 0,
    "organization_fallback_files": 0
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

When reverse geocoding is enabled, execution reports also include location
fields:

```text
location_status,organization_fallback,latitude,longitude,city,state,country
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

The project uses mostly Python standard library, plus Pillow for EXIF handling
and PyYAML for YAML configuration files.

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
- `urllib`

### External libraries

- `Pillow` for EXIF support;
- `PyYAML` for YAML configuration support;
- `pytest` for development testing.

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
- external configuration validation;
- configurable naming and destination patterns;
- GPS and reverse-geocoding workflows with fallback behavior;
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

## Version v0.4.0 delivered scope

This section consolidates the configuration, naming and location work delivered
after the v0.3.0 workflow.

### External configuration

- `organize` accepts `--config PATH` for JSON, YAML and YML files;
- configuration can define output directory, filename pattern, destination
  pattern, strategy and behavior settings;
- supported behavior settings include operation mode, dry-run, plan mode and
  reverse geocoding;
- configuration is validated before planning starts;
- invalid file paths, unsupported extensions, invalid field types and invalid
  strategy values produce clear errors.

### Custom filename patterns

- filenames can be customized with `naming.pattern` in config files;
- filenames can also be customized directly with CLI `--name-pattern`;
- CLI `--name-pattern` takes precedence over config `naming.pattern`;
- supported filename fields are `{date}`, `{stem}`, `{ext}` and `{original}`;
- invalid fields, empty patterns and path separators produce clear errors.

### Destination patterns and strategies

- destination paths can be customized with `destination.pattern`;
- destination patterns support `{date}`, `{country}`, `{state}` and `{city}`;
- built-in strategies include `date`, `location`, `location-date` and
  `city-state-month`;
- `city-state-month` creates paths like `Paraty-RJ/2024-08`;
- location-based strategies automatically enable reverse geocoding unless the
  user explicitly disables it, in which case the CLI returns a clear error.

### GPS and location behavior

- EXIF GPS latitude and longitude can be extracted and normalized to decimal
  coordinates;
- GPS absence is represented as missing location data instead of an execution
  failure;
- reverse geocoding resolves coordinates into city, state and country;
- network/service failures during reverse geocoding are handled as unresolved
  location data;
- when a location strategy cannot resolve a location, organization falls back
  to the default date-based path and marks `organization_fallback`.

### Reports and tests

- execution summaries include GPS, resolved location, missing GPS and
  organization fallback counters;
- location-aware reports include location status, fallback flag, coordinates,
  city, state and country;
- tests cover GPS coordinate extraction, missing GPS, reverse geocoding,
  location fallback, custom filename patterns, external config and the
  `city-state-month` strategy.

## Roadmap

### Version 0.1.0
- implemented and stabilized (see Version v0.1.0 delivered scope section).

### Version 0.2.0
- implemented and stabilized (see Version v0.2.0 delivered scope section).

### Version 0.3.0
- implemented and stabilized (see Version v0.3.0 delivered scope section).

### Version 0.4.0
- implemented and stabilized (see Version v0.4.0 delivered scope section).

### Version 0.5.0
- support for more media types (including videos);
- richer filtering (include/exclude and depth controls);
- performance improvements for large collections;
- richer report analytics.

### Version 0.6.0
- HEIC/HEIF support for iPhone and iPad photo collections;
- investigate metadata extraction and decoding requirements for the HEIF
  ecosystem, including Apple's `public.heic` type;
- evaluate standard non-Apple decoding paths such as `libheif` and compatible
  Python bindings;
- define install and fallback behavior for environments without HEIF decoding
  libraries.

### Version 0.7.0
- proprietary RAW format support;
- evaluate manufacturer-specific formats such as Canon CR2/CR3, Nikon NEF,
  Sony ARW and Panasonic RW2;
- investigate ExifTool integration for broad metadata extraction across RAW
  formats;
- evaluate Adobe DNG as a more universal RAW interchange/conversion target;
- define extension handling, metadata reliability and fallback behavior for
  camera-specific RAW files.

## Project status

In active development, with a stable tested v0.4.0 workflow for scan, organize
and dedupe flows.

## Motivation

This project was created as a practical exercise to study Python applied to real-world file organization and command-line automation problems.

## Contributing

Suggestions, improvements, and ideas are welcome.

## License

This project may be distributed under the MIT License.
