# photo-organizer

Python command-line photo organizer for renaming and organizing files by date, time, and metadata.

Repository: https://github.com/iklav-tech/photo-organizer

## Changelog

Release history is tracked in [CHANGELOG.md](CHANGELOG.md). This README also
consolidates the delivered v0.1.0 through v0.5.0 scope below.

## Current status

The project includes a tested v0.5.0 CLI workflow:

- CLI with `scan` and `organize` commands;
- `dedupe` command for read-only duplicate discovery;
- `inspect` command for read-only metadata auditing;
- `explain` command for JSON decision-trail reports;
- image scanning with recursive search;
- centralized and easily extensible supported image format list;
- case-insensitive extension matching;
- EXIF extraction for compatible JPEG, PNG and TIFF images;
- XMP embedded packet and same-basename `.xmp` sidecar extraction;
- IPTC-IIM legacy dataset extraction;
- PNG `eXIf`, `iTXt`, `tEXt`, `zTXt` and `tIME` metadata handling;
- HEIC/HEIF container detection for scan, hash, inspect and organize pipelines;
- HEIC/HEIF EXIF/XMP metadata extraction through `pillow-heif` and native
  `libheif` support;
- documented format/source/field compatibility matrix;
- explicit metadata limitation documentation;
- deterministic image hashing with chunked reads for large files;
- safe hash comparison for duplicate detection workflows;
- duplicate image grouping by content hash with original/duplicates output;
- structured duplicate reports in JSON or CSV for later analysis;
- date resolution with precedence-based reconciliation and configurable
  conflict policy;
- GPS coordinate extraction from EXIF metadata;
- optional reverse geocoding from GPS coordinates to city, state and country;
- low-confidence date and location inference from sidecars, filenames, folders
  and sibling context;
- correction manifests for batch date/location overrides and camera clock
  offsets;
- provenance tracking with source, field, confidence and raw value;
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
- explain reports export chosen date/location, candidates, source and
  confidence in JSON;
- external JSON/YAML organization config with custom naming, destination and
  behavior rules;
- improved CLI help with examples and grouped arguments;
- structured logging with configurable log level;
- friendly error messages for invalid/missing source directory;
- synthetic legacy metadata corpus covering success, absence and conflict
  scenarios.

Quick local setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -c "import photo_organizer; print(photo_organizer.__version__)"
```

Alternative dependency installation:

```bash
pip install -r requirements.txt
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
- explain why each file received a chosen date/location without reading code;
- find duplicate images by content hash before organizing or cleaning a collection;
- export duplicate reports for spreadsheet or automated analysis.

## Implemented features

### CLI and commands

- `photo-organizer --help`
- `photo-organizer --version`
- `photo-organizer scan --help`
- `photo-organizer dedupe --help`
- `photo-organizer inspect --help`
- `photo-organizer explain --help`
- `photo-organizer organize --help`
- `photo-organizer inspect SOURCE --report metadata-audit.json`
- `photo-organizer explain SOURCE --report explain.json`
- `photo-organizer explain SOURCE --reverse-geocode --report explain.json`
- `photo-organizer dedupe SOURCE --report duplicates.json`
- `photo-organizer dedupe SOURCE --report duplicates.csv`
- `photo-organizer organize SOURCE --config organizer.yaml`
- `photo-organizer organize SOURCE --output Organized --name-pattern "{date:%Y%m%d}_{stem}{ext}"`
- `photo-organizer organize SOURCE --output Organized --by city-state-month`
- `photo-organizer organize SOURCE --output Organized --correction-manifest corrections.yaml`
- `photo-organizer organize SOURCE --output Organized --heic-preview`
- grouped `organize` help sections for paths, execution, reports and mode;
- examples shown directly in help output;
- clear argument errors for missing required parameters, invalid report
  extensions, invalid configuration and invalid filename patterns.

### Scan behavior

- recursive search in source directory;
- supported extensions: `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.webp`,
  `.bmp`, `.heic`, `.heif`, `.hif`;
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

- EXIF extraction for compatible JPEG, PNG `eXIf` and TIFF images;
- formats without real EXIF support in the current reader, such as WEBP, BMP
  and HEIF/HEIC, safely skip EXIF extraction and use file `mtime` fallback;
- safe handling when EXIF is missing;
- safe handling of EXIF read exceptions;
- safe handling of malformed EXIF data without interrupting the whole run;
- partially inconsistent JPEG/TIFF IFDs are recovered from known tags when
  possible, while truly absent EXIF is logged separately from fatal read errors;
- primary date resolution priority:
  1. `DateTimeOriginal`
  2. `CreateDate`
  3. XMP date fields
  4. IPTC-IIM date fields
  5. PNG date fields
  6. low-confidence heuristics and filesystem fallback
- normalized output as `datetime`.
- GPS coordinates normalized to decimal degrees when available;
- embedded XMP packets parsed for date and GPS fields when present;
- PNG `iTXt` chunks parsed as UTF-8 text, including XMP packets stored in
  `XML:com.adobe.xmp`;
- PNG legacy `tEXt` and `zTXt` chunks parsed for textual metadata;
- PNG `tIME` image modification timestamps are used only as a low-confidence
  secondary fallback, never as the original capture date;
- same-basename `.xmp` sidecar files parsed for date and GPS fields when
  present;
- same-basename external JSON manifests can provide low-confidence date and
  location hints;
- legacy IPTC-IIM datasets parsed for date, time, city, state, country, title,
  author and description when present;
- conflicting date candidates are recorded and reconciled with
  `precedence`, `newest`, `oldest` or `filesystem` policy;
- missing GPS data handled safely without interrupting the run;
- reverse geocoding failures are treated as unresolved location data.

### HEIC preview behavior

- `organize --heic-preview` generates optional JPEG previews for HEIC/HEIF
  files after the main copy or move succeeds;
- previews are written next to the organized file under a `.previews` directory;
- preview generation uses the optional HEIF backend and only runs when enabled;
- preview failures are logged as warnings and do not make the file organization
  fail;
- config files can enable the same feature with `preview.heic: true`.

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

#### Format x metadata source x supported fields

| Format | Metadata source | Source class | Supported fields | Status |
| --- | --- | --- | --- | --- |
| JPEG (`.jpg`, `.jpeg`) | EXIF | Embedded metadata | `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, `Make`, `Model` | Implemented |
| JPEG (`.jpg`, `.jpeg`) | XMP packet inside file bytes | Embedded metadata | `exif:DateTimeOriginal`, `xmp:CreateDate`, `exif:GPSLatitude`, `exif:GPSLongitude`, `photoshop:City`, `photoshop:State`, `photoshop:Country`, `tiff:Make`, `tiff:Model` | Implemented |
| JPEG (`.jpg`, `.jpeg`) | IPTC-IIM datasets | Embedded metadata | `DateCreated`, `TimeCreated`, `City`, `Province-State`, `Country-PrimaryLocationName`, `ObjectName`, `Headline`, `By-line`, `Writer-Editor`, `Caption-Abstract` | Implemented |
| TIFF (`.tif`, `.tiff`) | EXIF/TIFF tags | Embedded metadata | `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, `Make`, `Model` when exposed by Pillow | Implemented |
| PNG (`.png`) | eXIf chunk via Pillow EXIF reader | Embedded metadata | `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, `Make`, `Model` | Implemented |
| PNG (`.png`) | `iTXt`, `tEXt`, `zTXt`, `tIME` chunks | Embedded metadata | `XML:com.adobe.xmp`, `Creation Time`, `CreationTime`, `tIME`, arbitrary text keywords for inspection | Implemented |
| PNG (`.png`) | XMP packet in `iTXt` or raw file bytes | Embedded metadata | `exif:DateTimeOriginal`, `xmp:CreateDate`, `exif:GPSLatitude`, `exif:GPSLongitude`, `photoshop:City`, `photoshop:State`, `photoshop:Country`, `tiff:Make`, `tiff:Model` | Implemented |
| JPEG, TIFF, PNG | Same-basename `.xmp` file, for example `IMG_001.xmp` | Sidecar | `exif:DateTimeOriginal`, `xmp:CreateDate`, `exif:GPSLatitude`, `exif:GPSLongitude`, `photoshop:City`, `photoshop:State`, `photoshop:Country`, `tiff:Make`, `tiff:Model` | Implemented |
| JPEG, TIFF, PNG | Same-basename `.json` external manifest | Heuristic sidecar | `date_taken`, `datetime`, `created_at`, `DateTimeOriginal`, `CreateDate`, `city`, `state`, `country` | Implemented |
| JPEG, TIFF, PNG | Filename, parent folder and sibling batch context | Heuristic | Safe date patterns and location-like folder names | Implemented |
| JPEG, TIFF, PNG, WEBP, BMP, HEIF | Filesystem | Filesystem | `mtime` | Implemented |
| WEBP (`.webp`) | Embedded EXIF/XMP | Embedded metadata | None in the current reader | Not supported |
| BMP (`.bmp`) | Embedded EXIF/XMP | Embedded metadata | None in the current reader | Not supported |
| HEIF (`.heic`, `.heif`, `.hif`) | EXIF via HEIF backend | Embedded metadata | `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, `Make`, `Model` when exposed by `pillow-heif`/Pillow | Implemented |
| HEIF (`.heic`, `.heif`, `.hif`) | XMP via HEIF backend | Embedded metadata | `exif:DateTimeOriginal`, `xmp:CreateDate`, `exif:GPSLatitude`, `exif:GPSLongitude`, `photoshop:City`, `photoshop:State`, `photoshop:Country`, `tiff:Make`, `tiff:Model` | Implemented |

Source classes used in reports and explanations:

- **Embedded metadata**: metadata stored inside the media file itself, such as
  EXIF, TIFF tags, IPTC-IIM, XMP packets or PNG text chunks.
- **Sidecar**: an external file with the same basename, currently `.xmp`, used
  as structured metadata. Inside the XMP tier, sidecar values override embedded
  XMP values because they usually represent later metadata edits.
- **Filesystem**: operating-system file attributes. Only `mtime` is used, and
  only as a low-confidence date fallback/explicit reconciliation policy.
- **Heuristic**: inferred context that is not authoritative embedded metadata,
  such as external JSON manifests, filename dates, folder names and sibling
  batch patterns.

| Field | Priority | Source | Keys | Role | Status |
| --- | ---: | --- | --- | --- | --- |
| `date_taken` | 1 | EXIF | `DateTimeOriginal` | Primary | Implemented |
| `date_taken` | 2 | EXIF | `CreateDate`, `DateTime`, `DateTimeDigitized` | Fallback | Implemented |
| `date_taken` | 3 | XMP | `exif:DateTimeOriginal`, `xmp:CreateDate` | Fallback | Implemented |
| `date_taken` | 4 | IPTC-IIM | `DateCreated`, `TimeCreated` | Fallback | Implemented |
| `date_taken` | 5 | PNG metadata | `Creation Time`, `CreationTime`, `tIME` | Fallback | Implemented |
| `date_taken` | 6 | Sidecar external | `date_taken`, `datetime`, `created_at`, `DateTimeOriginal`, `CreateDate` | Heuristic | Implemented |
| `date_taken` | 7 | Filename | `date pattern` | Heuristic | Implemented |
| `date_taken` | 8 | Folder | `date pattern` | Heuristic | Implemented |
| `date_taken` | 9 | Sequence batch | `sibling date pattern` | Heuristic | Implemented |
| `date_taken` | 10 | Filesystem | `mtime` | Heuristic | Implemented |
| `location` | 1 | EXIF | `GPSInfo`, `GPSLatitude`, `GPSLongitude` | Primary | Implemented |
| `location` | 2 | XMP | `exif:GPSLatitude`, `exif:GPSLongitude` | Fallback | Implemented |
| `location` | 3 | IPTC-IIM | `City`, `Province-State`, `Country-PrimaryLocationName` | Fallback | Implemented |
| `location` | 4 | Reverse geocoding | `GPSLatitudeDecimal`, `GPSLongitudeDecimal` | Heuristic | Implemented |
| `title` | 1 | XMP | `dc:title`, `photoshop:Headline` | Primary | Planned |
| `title` | 2 | IPTC-IIM | `ObjectName`, `Headline` | Fallback | Implemented |
| `title` | 3 | PNG metadata | `Title` | Fallback | Planned |
| `title` | 4 | EXIF | `ImageDescription` | Fallback | Planned |
| `author` | 1 | XMP | `dc:creator` | Primary | Planned |
| `author` | 2 | IPTC-IIM | `By-line`, `Writer-Editor` | Fallback | Implemented |
| `author` | 3 | PNG metadata | `Author` | Fallback | Planned |
| `author` | 4 | EXIF | `Artist`, `Copyright` | Fallback | Planned |
| `description` | 1 | XMP | `dc:description` | Primary | Planned |
| `description` | 2 | IPTC-IIM | `Caption-Abstract` | Fallback | Implemented |
| `description` | 3 | PNG metadata | `Description`, `Comment` | Fallback | Planned |
| `description` | 4 | EXIF | `ImageDescription`, `UserComment` | Fallback | Planned |

The current `date_taken` resolver implements the supported subset of this
policy: EXIF `DateTimeOriginal`, EXIF `CreateDate`/aliases, XMP date fields,
IPTC-IIM `DateCreated`/`TimeCreated`, PNG `Creation Time`/`CreationTime`,
PNG `tIME` as a secondary low-confidence modification-time fallback, then
low-confidence inferred dates from same-basename external sidecars, filename
patterns, folder names, sibling batch context and filesystem `mtime`.
XMP can come from embedded metadata or from a same-basename sidecar file such as
`IMG_001.xmp`; within the XMP tier, sidecar values override embedded XMP
values. Location organization currently uses EXIF GPS coordinates, XMP GPS
coordinates, IPTC-IIM city/state/country fields and reverse geocoding. PNG text
metadata currently contributes date and embedded XMP fields; title, author and
description PNG policy entries remain reserved for future user-facing fields.

When supported date sources disagree, the reconciliation engine records all
parsed candidates, selects a winner and logs the policy, winning source and
reason. The default `precedence` policy applies the matrix above. Users can
override it with `--reconciliation-policy precedence|newest|oldest|filesystem`
or `behavior.reconciliation_policy` in config.
Date values are reported as `captured` when they come from embedded/sidecar
metadata sources and `inferred` when they come from heuristics. Inferred date
heuristics are enabled by default and can be disabled with
`--no-date-heuristics` or `behavior.date_heuristics: false`.

When GPS coordinates are unavailable, location strategies can infer a
low-confidence, non-GPS location from IPTC/XMP text fields, same-basename
external manifests, folder or album names, or a consistent sibling batch
manifest. These locations are reported with `location_status: inferred` and
never populate GPS coordinate fields. Users who do not want location inference
can use `--no-location-inference` or `behavior.location_inference: false`; in
that mode location-based strategies organize under `UnknownLocation`.

Batch correction manifests can provide manual overrides for old collections
through `--correction-manifest PATH` or `behavior.correction_manifest`. The
manifest may be CSV, JSON, YAML or YML and can target files by exact path,
folder, glob or filename pattern. Supported override fields include date,
timezone, camera clock offset, city/state/country and event name. Date and clock
offset overrides enter the date reconciliation engine as `Correction manifest`
candidates; priority can be configured with
`--correction-priority highest|metadata|heuristic` or
`behavior.correction_priority`. Reports include the manifest path, matched
selectors, event name and `Correction manifest` provenance.

### Metadata provenance model

Resolved metadata values carry provenance so reports, logs and debug output can
explain why a value was selected. The internal provenance model stores:

- `source`: metadata source, such as `EXIF`, `XMP`, `IPTC-IIM`, `PNG`,
  `filesystem` or `Reverse geocoding`;
- `field`: source field, such as `DateTimeOriginal`, `GPSInfo` or `mtime`;
- `confidence`: `high`, `medium` or `low`;
- `raw_value`: original value used before normalization.

Examples:

- `EXIF:DateTimeOriginal` with high confidence for the capture date;
- `EXIF:GPSInfo` with high confidence for GPS coordinates;
- `XMP sidecar:xmp:CreateDate` with medium confidence when `image.xmp`
  provides the selected date;
- `IPTC-IIM:2:55,2:60` with medium confidence when legacy IIM date/time fields
  provide the selected date;
- `Reverse geocoding:GPSLatitudeDecimal,GPSLongitudeDecimal` with medium
  confidence for city/state/country derived from coordinates;
- `filesystem:mtime` with low confidence when no embedded date is available.

This makes it possible to answer questions such as "why was this date chosen?"
or "why was this location selected?" from the planned operation and audit
report data.

### Known Metadata Limitations

- RAW and manufacturer-specific formats such as CR2/CR3, NEF, ARW and ORF are
  not supported by the current metadata reader.
- HEIF/HEIC containers (`.heic`, `.heif`, `.hif`) are detected and can enter
  scan/hash/inspect/organize flows. Embedded HEIF EXIF/XMP metadata uses
  `pillow-heif` and native `libheif` support. Date/time, orientation and GPS
  are read when present in backend-exposed EXIF, and XMP date/GPS/location
  fields are read when present. If the native backend is unavailable, the app
  logs an orientative warning and falls back to sidecars, heuristics or
  filesystem `mtime`.
- HEIF containers with multiple images, sequence-like structures, thumbnails,
  auxiliary images or depth images are reported by `inspect` as a `HEIF
  container` metadata source. The app deterministically selects one primary
  image for metadata: backend `primary` flag, then backend `primary_index`,
  then image index `0` with a warning. Non-primary images and auxiliary
  structures are reported clearly and are not extracted by the current
  pipeline.
- WEBP and BMP are recognized as image files for scanning/hashing, but embedded
  metadata is not read from them; date organization falls back to heuristics or
  filesystem `mtime`.
- The reader depends on Pillow for EXIF/TIFF/eXIf extraction. Tags not exposed
  by Pillow or malformed IFDs may be unavailable, although known date/GPS tags
  are recovered when possible.
- PNG `tIME` is treated as an image modification timestamp, not an original
  capture timestamp. It is low-confidence and secondary to `Creation Time`,
  XMP and EXIF dates.
- IPTC-IIM extraction reads a documented subset of legacy datasets. Unknown
  datasets are ignored.
- XMP extraction reads a focused allowlist used by organization and reports; it
  is not a full XMP/RDF implementation.
- Textual title, author and description policy entries exist for future
  user-facing fields, but organization decisions currently use date and
  location fields.
- Reverse geocoding requires GPS coordinates and may fail or return no result
  depending on the configured geocoding provider/network behavior.

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
  reconciliation_policy: precedence
  date_heuristics: true
  location_inference: true
  correction_manifest: corrections.yaml
  correction_priority: highest
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
- `behavior.dry_run`, `behavior.plan`, `behavior.reverse_geocode`: booleans;
- `behavior.reconciliation_policy`: `precedence`, `newest`, `oldest` or
  `filesystem`;
- `behavior.date_heuristics`: boolean to enable or disable inferred date
  recovery;
- `behavior.location_inference`: boolean to enable or disable non-GPS location
  inference;
- `behavior.correction_manifest`: CSV, JSON, YAML or YML correction manifest;
- `behavior.correction_priority`: `highest`, `metadata` or `heuristic`.

Example correction manifest:

```yaml
priority: highest
rules:
  - glob: "old-camera/*.jpg"
    date: "1969-07-20T20:17:00"
    timezone: "-03:00"
    clock_offset: "+00:05"
    city: "Houston"
    state: "TX"
    country: "USA"
    event: "Moon landing archive"
  - folder: "scans"
    city: "Paraty"
    state: "RJ"
    country: "Brasil"
  - camera: "Canon PowerShot A530"
    clock_offset: "+3h"
  - camera_make: "Olympus"
    camera_model: "C-2020Z"
    clock_offset: "-1d"
```

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
- report rows include source, destination, action, status and observations;
- execution reports include provenance fields for selected date and, when
  location is enabled, GPS/location source, confidence and raw values.

Explain reports:

- `photo-organizer explain SOURCE --report explain.json` writes a read-only JSON
  decision report;
- each file contains `chosen_date`, `chosen_location`, `candidates` and
  `sources`;
- date candidates include parsed value, source, field, confidence, raw value,
  role and whether they are captured or inferred;
- location candidates include GPS, XMP/IPTC textual location, external
  manifests and folder/batch inference when available;
- the report is designed for debugging problematic files without opening the
  code.

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
      correction_manifest.py
      constants.py
      geocoding.py
      scanner.py
      metadata.py
      hashing.py
      text_normalization.py
      naming.py
      planner.py
      executor.py
      logging_config.py
  tests/
    fixtures/
      README.md
      metadata_corpus.py
    test_import.py
    test_cli.py
    test_config.py
    test_correction_manifest.py
    test_geocoding.py
    test_scanner.py
    test_executor.py
    test_integration.py
    test_naming.py
    test_metadata.py
    test_metadata_corpus.py
    test_hashing.py
    test_planner.py
```

## Module responsibilities

- `cli.py`: command-line interface and command orchestration;
- `config.py`: external JSON/YAML configuration loading and validation;
- `correction_manifest.py`: batch date/location correction manifest parsing,
  matching and validation;
- `scanner.py`: recursive file scanning and extension filtering;
- `metadata.py`: EXIF, XMP, IPTC-IIM, PNG metadata extraction, GPS extraction,
  provenance and best-date reconciliation;
- `geocoding.py`: reverse geocoding from GPS coordinates to city, state and country;
- `hashing.py`: deterministic file/image hashes, safe digest comparison and duplicate grouping;
- `naming.py`: deterministic and pattern-based filename generation;
- `planner.py`: destination folder planning by date, location and custom patterns;
- `executor.py`: operation planning and execution/simulation;
- `text_normalization.py`: Unicode/path-safe text normalization and
  report-friendly normalization observations;
- `logging_config.py`: logging setup and level control;
- `constants.py`: centralized image format definitions, including EXIF capability flags.

## Organization rules

Default date decision strategy:

1. EXIF `DateTimeOriginal`;
2. EXIF `CreateDate`, `DateTime` or `DateTimeDigitized`;
3. XMP `exif:DateTimeOriginal` or `xmp:CreateDate`, including same-basename
   `.xmp` sidecars;
4. IPTC-IIM `DateCreated` and `TimeCreated`;
5. PNG `Creation Time`, `CreationTime` and then low-confidence `tIME`;
6. correction-manifest candidates according to configured priority;
7. low-confidence heuristics from external sidecars, filenames, folders,
   sibling batch context and filesystem `mtime`.

The default reconciliation policy is `precedence`. It can be changed to
`newest`, `oldest` or `filesystem` with `--reconciliation-policy` or
`behavior.reconciliation_policy`.

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

### Example: inspect metadata before organizing

```bash
photo-organizer inspect ~/Photos
photo-organizer inspect ~/Photos --report metadata-audit.json
photo-organizer audit-metadata ~/Photos --report metadata-audit.csv
```

The inspect command is read-only. It lists available metadata sources per file
and shows the final date and location decisions that would drive organization.
Reports can be exported as JSON or CSV.

### Example: explain decision trails

```bash
photo-organizer explain ~/Photos --report explain.json
photo-organizer explain ~/Photos --reverse-geocode --report explain.json
```

The explain command is read-only. Its JSON report is meant for debugging
problem files without reading code: each file includes `chosen_date`,
`chosen_location`, candidate values, source fields and confidence.

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
  reconciliation_policy: precedence
  date_heuristics: true
  location_inference: true
  correction_manifest: corrections.yaml
  correction_priority: highest
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
source,destination,action,status,observations,date_source,date_field,date_confidence,date_raw_value
```

When reverse geocoding is enabled, execution reports also include location
fields:

```text
location_status,organization_fallback,latitude,longitude,city,state,country,gps_source,gps_field,gps_confidence,gps_raw_value,location_source,location_field,location_confidence,location_raw_value
```

## Explain report format

`photo-organizer explain SOURCE --report explain.json` writes one JSON item per
file with final choices and the trail of candidates:

```json
{
  "summary": {
    "explained_files": 1,
    "date_resolved_files": 1,
    "location_resolved_files": 1,
    "date_conflict_files": 0
  },
  "files": [
    {
      "path": "/home/user/Photos/IMG_1034.jpg",
      "chosen_date": {
        "value": "2024-08-15T14:32:09",
        "source": "EXIF",
        "field": "DateTimeOriginal",
        "confidence": "high"
      },
      "chosen_location": {
        "city": "Sao Paulo",
        "state": "Sao Paulo",
        "country": "Brazil",
        "source": "Reverse geocoding",
        "confidence": "medium"
      },
      "candidates": {
        "date": [],
        "location": []
      }
    }
  ]
}
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
- `pillow-heif` for HEIF/HEIC opening through `libheif`;
- `pytest` for development testing.

## Testing

Run the full suite from the repository root:

```bash
pytest
```

The suite uses temporary directories and synthetic files, so it does not need a
checked-in binary photo collection. The metadata corpus in
`tests/fixtures/metadata_corpus.py` generates deterministic samples for:

- JPEG with EXIF;
- TIFF tags;
- IPTC-IIM;
- embedded XMP;
- XMP sidecar;
- PNG eXIf;
- PNG `iTXt`/`tEXt`;
- files without usable metadata;
- conflicting EXIF/XMP metadata.

Corpus tests cover successful extraction, missing metadata behavior,
conflicting candidates and the automated date precedence matrix.

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
- explainable decision reports;
- external configuration validation;
- configurable naming and destination patterns;
- GPS and reverse-geocoding workflows with fallback behavior;
- metadata compatibility and limitation documentation;
- synthetic legacy metadata corpus tests;
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

- EXIF extraction for compatible JPEG, PNG and TIFF files;
- safe behavior when EXIF is missing;
- safe handling of EXIF read exceptions;
- date resolution order:
  1. `DateTimeOriginal`
  2. `CreateDate`
  3. XMP and IPTC-IIM date fields
  4. PNG `Creation Time`/`CreationTime`
  5. PNG `tIME` as a secondary fallback
  6. `mtime` fallback

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

## Version v0.5.0 delivered scope

This section consolidates the metadata audit, explainability and compatibility
work delivered after the v0.4.0 workflow.

### Metadata reconciliation and provenance

- date decisions are resolved through an explicit precedence matrix;
- supported candidates include EXIF, XMP, IPTC-IIM, PNG metadata, correction
  manifests, external sidecars, filename/folder/batch heuristics and filesystem
  `mtime`;
- every resolved value carries source, field, confidence and raw value
  provenance;
- conflicting date candidates are retained in the reconciliation decision;
- reconciliation policy can be `precedence`, `newest`, `oldest` or
  `filesystem`;
- date values are classified as `captured` or `inferred`.

### Metadata audit and explain reports

- `inspect` audits available metadata sources and final decisions without
  modifying files;
- `audit-metadata` remains available as an alias for `inspect`;
- `explain` writes a JSON report focused on decision debugging;
- explain reports include `chosen_date`, `chosen_location`, `candidates`,
  `sources` and confidence values;
- JSON serialization handles Pillow-specific EXIF value types such as
  rational numbers.

### Legacy and sidecar metadata support

- embedded XMP packets are parsed from supported image files and PNG `iTXt`
  chunks;
- same-basename `.xmp` sidecars are parsed and take precedence within the XMP
  tier;
- IPTC-IIM legacy datasets are parsed for date/time, location and textual
  fields;
- PNG `eXIf`, `iTXt`, `tEXt`, `zTXt` and `tIME` metadata paths are covered;
- same-basename JSON external manifests can provide low-confidence inferred
  date and location hints.

### Corrections and inference

- correction manifests support exact path, folder, glob, filename pattern and
  camera-based matching;
- correction fields include date, timezone, clock offset, event name and
  city/state/country;
- correction priority can be `highest`, `metadata` or `heuristic`;
- global and per-file clock offsets preserve original datetimes in provenance;
- date heuristics and location inference can be disabled through CLI or config.

### Compatibility documentation and test corpus

- README now includes a format/source/field compatibility matrix;
- README differentiates embedded metadata, sidecars, filesystem values and
  heuristics;
- known limitations are documented explicitly;
- synthetic legacy corpus fixtures cover JPEG/EXIF, TIFF tags, IPTC-IIM,
  embedded XMP, XMP sidecar, PNG eXIf, PNG text chunks, missing metadata and
  conflicting metadata;
- automated corpus tests cover success, absence, conflict and precedence
  behavior.

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
- implemented and stabilized (see Version v0.5.0 delivered scope section).

### Version 0.6.0
- support for more media types (including videos);
- richer filtering (include/exclude and depth controls);
- performance improvements for large collections;
- richer report analytics;
- HEIC/HEIF detection and `pillow-heif` backend integration for EXIF/XMP in
  iPhone and iPad photo collections is implemented;
- continue validating metadata extraction behavior across the HEIF ecosystem,
  including Apple's `public.heic` type;
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

In active development, with a stable tested v0.5.0 workflow for scan, dedupe,
inspect, explain and organize flows.

## Motivation

This project was created as a practical exercise to study Python applied to real-world file organization and command-line automation problems.

## Contributing

Suggestions, improvements, and ideas are welcome.

## License

This project may be distributed under the MIT License.
