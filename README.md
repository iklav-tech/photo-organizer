# photo-organizer

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://iklav-tech.github.io/photo-organizer/)

Python command-line photo organizer for renaming and organizing files by date, time, and metadata.

Repository: https://github.com/iklav-tech/photo-organizer

## Documentation

Project documentation lives in [`docs/`](docs/) and is prepared for publication
with GitHub Pages at:

https://iklav-tech.github.io/photo-organizer/

In the GitHub repository settings, configure `Settings > Pages > Source` as
`GitHub Actions`. The workflow in `.github/workflows/pages.yml` publishes the
site from the `docs/` directory on pushes to `main` and can also be run
manually.

## Changelog

Release history is tracked in [CHANGELOG.md](CHANGELOG.md). This README also
consolidates the delivered v0.1.0 through the current v0.8.0 scope below.

## Current status

The project includes a tested CLI workflow:

- CLI with `scan`, `organize` and safe-copy `import` commands;
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
- initial RAW format recognition and range-based metadata reading for Apple
  ProRAW/DNG, Canon, Nikon, Sony, Panasonic, Olympus/OM System and Fujifilm
  files;
- technical RAW audit output in `inspect`, including detected format, support
  status, workflow, field origins and partial-support warnings;
- documented format/source/field compatibility matrix, including HEIF/HEIC and
  a dedicated RAW compatibility matrix by manufacturer/container;
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
- destination folder planning by date (`YYYY/MM/DD`), event, location,
  location plus date, custom destination pattern, or city/state/month hybrid
  strategy;
- optional temporal event grouping with configurable time windows, available
  for reports or as generated destination directories;
- explicit planning layer separated from execution;
- automatic destination directory creation;
- safe move behavior that removes the source only after a successful copy;
- configurable destination conflict policy with safe suffix handling by default;
- optional segregation of edited/exported/derived files from originals;
- `--dry-run` simulation with no filesystem changes;
- `--plan` inspection mode without execution;
- structured execution summaries;
- resilient per-file error handling for invalid files and malformed metadata;
- optional audit report export in JSON or CSV with `--report`;
- final import manifests in JSON or CSV for batch audit trails;
- report fields that identify final destination, chosen date/location, metadata
  source, reconciliation conflicts, RAW details, DNG candidates and derived
  asset classification;
- explain reports export chosen date/location, candidates, source and
  confidence in JSON;
- external JSON/YAML organization config with custom naming, destination and
  behavior rules;
- optional JPEG preview generation for organized HEIC/HEIF files;
- improved CLI help with examples and grouped arguments;
- structured logging with configurable log level;
- friendly error messages for invalid/missing source directory;
- synthetic legacy metadata corpus covering success, absence and conflict
  scenarios;
- synthetic HEIC corpus covering iPhone-like EXIF/GPS samples, missing metadata
  and malformed container behavior when the local HEIF writer is available;
- synthetic RAW corpus covering every supported RAW-family extension, no-GPS
  files, corrupted input, cross-manufacturer normalization and large-file
  metadata performance behavior.

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

### HEIC/HEIF support

HEIC/HEIF support is enabled by installing the project dependencies, because
`pillow-heif` is listed in both `pyproject.toml` and `requirements.txt`:

```bash
pip install -e .
# or
pip install -r requirements.txt
```

`pillow-heif` uses the native `libheif` stack underneath. On many common Linux,
macOS and Windows Python environments, the wheel may already include the native
bits needed to decode HEIC. If the wheel for your platform does not include
them, install `libheif` with your operating system package manager and reinstall
the Python dependencies.

Common native dependency commands:

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install libheif1

# Fedora
sudo dnf install libheif

# Arch Linux
sudo pacman -S libheif

# macOS with Homebrew
brew install libheif
```

Windows support depends on the `pillow-heif` wheel available for your Python
version and architecture. Prefer a current 64-bit CPython and install with
`pip install -e .`. If the wheel cannot load its native backend, use WSL2 with
the Linux instructions above or install a compatible native `libheif` runtime
for your environment.

Validate local HEIC support:

```bash
python -c "import pillow_heif; pillow_heif.register_heif_opener(); print(pillow_heif.__version__)"
photo-organizer inspect ./Photos --report heic-audit.json
```

HEIC/HEIF limitations by platform:

- Linux: distribution packages may lag behind recent `libheif` features. Very
  new iPhone HEIC variants, auxiliary images or sequence features may require a
  newer distro package or a wheel that bundles a newer native library.
- macOS: Homebrew installations are usually the simplest path when the wheel
  cannot load native support. System Preview/Photos support does not guarantee
  Python `libheif` support.
- Windows: support is wheel-dependent. Microsoft HEIF/HEVC Store extensions
  help Windows apps but do not necessarily satisfy Python native library
  loading for `pillow-heif`.

Current application limitations:

- scan/hash/inspect/organize recognize `.heic`, `.heif` and `.hif`;
- embedded EXIF/XMP is read only when exposed by `pillow-heif`/`libheif`;
- `inspect` reports HEIF container details, metadata found/missing and whether
  chosen date/location values came from real embedded metadata/GPS or from
  fallback/inference;
- containers with multiple images, image sequences, thumbnails, auxiliary
  images or depth images are reported, but only one deterministic primary image
  is used by the metadata pipeline;
- optional HEIC preview generation writes JPEG previews only when the backend
  can decode the source image; preview failures do not stop organization.

#### HEIC troubleshooting

If HEIC files are detected but metadata is missing, first run:

```bash
photo-organizer --log-level DEBUG inspect ./Photos --report heic-audit.json
```

Common symptoms and fixes:

- `HEIF backend unavailable`: install project dependencies and the native
  `libheif` package for your OS, then reinstall with `pip install -e .`.
- `Failed to read HEIF container` or `Failed to read HEIF metadata`: the file
  may be corrupt, encrypted, unsupported by the installed `libheif`, or using a
  newer HEIF feature than the backend exposes. Update `pillow-heif` and
  `libheif`, then rerun `inspect`.
- Date falls back to `filesystem:mtime`: the HEIC file had no backend-exposed
  EXIF/XMP capture date. Check the JSON report's `heif.found_metadata`,
  `heif.missing_metadata` and `heif.date_evidence` fields.
- GPS/location is missing or inferred: the file has no backend-exposed GPS
  metadata, reverse geocoding is disabled, or only textual/folder sidecar
  location hints were available. Check `heif.location_evidence` and the
  `location` decision in the report.
- Tests that generate synthetic HEIC are skipped: the local environment cannot
  write HEIC through `pillow-heif`/`libheif`; install or update the native
  backend and rerun `pytest`.

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
- `photo-organizer import --help`
- `photo-organizer inspect SOURCE --report metadata-audit.json`
- `photo-organizer explain SOURCE --report explain.json`
- `photo-organizer explain SOURCE --reverse-geocode --report explain.json`
- `photo-organizer dedupe SOURCE --report duplicates.json`
- `photo-organizer dedupe SOURCE --report duplicates.csv`
- `photo-organizer import SOURCE --output Organized --report import.json`
- `photo-organizer organize SOURCE --config organizer.yaml`
- `photo-organizer organize SOURCE --output Organized --name-pattern "{date:%Y%m%d}_{stem}{ext}"`
- `photo-organizer organize SOURCE --output Organized --by city-state-month`
- `photo-organizer organize SOURCE --output Organized --by event`
- `photo-organizer organize SOURCE --output Organized --by event --event-window-minutes 30`
- `photo-organizer organize SOURCE --output Organized --correction-manifest corrections.yaml`
- `photo-organizer organize SOURCE --output Organized --conflict-policy skip`
- `photo-organizer organize SOURCE --output Organized --event-window-minutes 60`
- `photo-organizer organize SOURCE --output Organized --event-window-minutes 60 --event-directory`
- `photo-organizer organize SOURCE --output Organized --segregate-derivatives`
- `photo-organizer organize SOURCE --output Organized --heic-preview`
- `photo-organizer organize SOURCE --output Organized --dng-candidates --report audit.json`
- grouped `organize` help sections for paths, execution, reports and mode;
- examples shown directly in help output;
- clear argument errors for missing required parameters, invalid report
  extensions, invalid configuration and invalid filename patterns.

### Scan behavior

- recursive search in source directory;
- supported extensions: `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.webp`,
  `.bmp`, `.heic`, `.heif`, `.hif`, `.dng`, `.cr2`, `.cr3`, `.crw`, `.nef`, `.arw`,
  `.rw2`, `.orf`, `.raf`;
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
- formats without real EXIF support in the current reader, such as WEBP and BMP,
  safely skip EXIF extraction and use file `mtime` fallback;
- HEIF/HEIC EXIF and XMP are read through the HEIF backend when
  `pillow-heif`/`libheif` exposes the embedded metadata;
- safe handling when EXIF is missing;
- safe handling of EXIF read exceptions;
- safe handling of malformed EXIF data without interrupting the whole run;
- partially inconsistent JPEG/TIFF IFDs are recovered from known tags when
  possible, while truly absent EXIF is logged separately from fatal read errors;
- heterogeneous source tags are normalized into an internal schema for
  `date_taken`, `camera_make`, `camera_model` and GPS coordinates before
  organization logic consumes them;
- original metadata source, field and raw value remain available through
  provenance for inspect, explain and debug reports;
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

### Initial RAW format scope

The first RAW support wave is explicit. These formats are accepted by scan,
hash, dedupe, inspect and organize flows, and they appear in CLI help through
the centralized supported extension list:

| Manufacturer | Extensions |
| --- | --- |
| Apple ProRAW / Linear DNG | `.dng` |
| Canon | `.cr2`, `.cr3`, `.crw` |
| Nikon | `.nef` |
| Sony | `.arw` |
| Panasonic | `.rw2` |
| Olympus/OM System | `.orf` |
| Fujifilm | `.raf` |

#### RAW compatibility matrix

Support status in this matrix is scoped to the current RAW layer: discovery,
hashing, inspect/organize participation, range-based TIFF-style metadata reads,
sidecar handling and reports. It does not imply RAW pixel decoding.

| Manufacturer / container | Extensions | Support status | Supported fields | Known limitations |
| --- | --- | --- | --- | --- |
| Apple ProRAW / Linear DNG | `.dng` | Full for DNG/TIFF metadata workflow | `Make`, `Model`, `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, decimal GPS derived from EXIF GPS, same-basename `.xmp` sidecar linkage, RAW audit/report fields | No RAW pixel decoding; embedded XMP/IPTC full-file scans are skipped for performance; only TIFF/DNG-exposed metadata is read |
| Canon CR2 | `.cr2` | Full for TIFF-style EXIF metadata workflow | `Make`, `Model`, `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, decimal GPS derived from EXIF GPS, same-basename `.xmp` sidecar linkage, RAW audit/report fields | Maker notes and camera-specific proprietary blocks are not decoded; fields missing from TIFF-style EXIF are reported as partial |
| Canon CR3 | `.cr3` | Experimental | Discovery, hashing, organization, sidecar linkage, DNG-candidate reporting, RAW audit shell; TIFF-style EXIF fields when exposed in a readable TIFF-like header | Real CR3 files commonly use newer container layouts; metadata extraction may be partial or unavailable without a broader parser/ExifTool integration |
| Canon CRW | `.crw` | Experimental | Discovery, hashing, organization, sidecar linkage, DNG-candidate reporting, RAW audit shell; TIFF-style EXIF fields when exposed in a readable TIFF-like header | Older Canon layouts can differ from TIFF-style IFDs; metadata extraction may be partial or unavailable |
| Nikon NEF | `.nef` | Partial | `Make`, `Model`, `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, decimal GPS derived from EXIF GPS, same-basename `.xmp` sidecar linkage, RAW audit/report fields when TIFF-style metadata is exposed | Nikon maker notes and proprietary structures are not decoded; embedded XMP/IPTC full-file scans are skipped |
| Sony ARW | `.arw` | Partial | `Make`, `Model`, `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, decimal GPS derived from EXIF GPS, same-basename `.xmp` sidecar linkage, RAW audit/report fields when TIFF-style metadata is exposed | Sony maker notes and proprietary structures are not decoded; unsupported embedded metadata falls back to sidecars/heuristics/filesystem |
| Panasonic RW2 | `.rw2` | Partial | `Make`, `Model`, `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, decimal GPS derived from EXIF GPS, same-basename `.xmp` sidecar linkage, RAW audit/report fields when TIFF-style metadata is exposed | Panasonic maker notes and proprietary structures are not decoded; metadata can be partial on files with nonstandard tags |
| Olympus / OM System ORF | `.orf` | Partial | `Make`, `Model`, `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, decimal GPS derived from EXIF GPS, same-basename `.xmp` sidecar linkage, RAW audit/report fields when TIFF-style metadata is exposed | Olympus/OM maker notes and proprietary structures are not decoded; metadata can be partial on files with nonstandard tags |
| Fujifilm RAF | `.raf` | Partial | `Make`, `Model`, `DateTimeOriginal`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, decimal GPS derived from EXIF GPS, same-basename `.xmp` sidecar linkage, RAW audit/report fields when TIFF-style metadata is exposed | Fujifilm-specific RAF structures and maker notes are not decoded; metadata can be partial on files with nonstandard tags |

Status meanings:

- Full: the app has an explicit RAW workflow for the format and the supported
  TIFF-style metadata fields are expected to be readable when present.
- Partial: the app recognizes and organizes the format, and reads the supported
  fields when they are exposed through TIFF-style metadata, but it does not
  decode manufacturer-specific metadata structures.
- Experimental: the app recognizes and organizes the format, but real-world
  metadata extraction may be incomplete because the container is not reliably
  represented by the current TIFF-style reader.

The current RAW metadata reader focuses on safe EXIF/TIFF metadata extraction:
capture date/time, camera manufacturer, camera model and GPS coordinates when
those tags are exposed by the RAW file. Apple ProRAW is included here because
Apple exposes it through a DNG/Linear DNG workflow; the app treats `.dng` as
RAW-family input and reports its flow as `Apple ProRAW / Linear DNG`. It does
not decode RAW image pixels and does not aim to be a complete
manufacturer-specific RAW parser. When RAW metadata is missing or cannot be
parsed safely, files can still be discovered, hashed, reported and organized
through sidecars, correction manifests, filename/folder heuristics or
filesystem `mtime` fallback.

HEIC and ProRAW are intentionally different paths. HEIC/HEIF (`.heic`,
`.heif`, `.hif`) is a compressed HEIF container handled by the HEIF backend and
can optionally produce JPEG previews. Apple ProRAW (`.dng`) is handled by the
RAW layer as a DNG/Linear DNG file, participates in RAW sidecar handling and can
be marked for the optional DNG interoperability workflow.

`inspect` includes a dedicated RAW audit block for RAW-family files. It reports
the detected RAW format, workflow, support status, camera make, camera model,
capture date/time and GPS coordinates when those fields are available from
TIFF-style EXIF. Each field carries its source, original field name and
confidence. If only part of that technical metadata is available, the status is
`partial` and the missing fields are listed explicitly.

RAW metadata reads are range-based. The RAW backend reads only the TIFF header,
IFD entries and referenced metadata values needed for audit and organization;
it does not decode RAW pixels and does not load the full file into memory. For
large RAW batches, generic full-file scans such as embedded XMP/IPTC search are
skipped for RAW-family files, while same-basename sidecars remain supported.

When a RAW file has a same-basename `.xmp` sidecar, organization treats the
sidecar as linked data for that RAW file. Copy and move operations apply to both
files, using the RAW destination basename for the sidecar as well. For example,
`IMG_0001.cr2` organized as `2024-08-15_14-32-09.cr2` carries
`IMG_0001.xmp` to `2024-08-15_14-32-09.xmp`. Reports include the sidecar count,
source path and destination path so the relationship is visible after the run.

### Optional DNG interoperability marking

The app can optionally mark RAW files as candidates for a DNG interoperability
workflow with `--dng-candidates` or `interop.dng_candidates: true`. This is a
non-destructive marker only: photo-organizer does not run a converter, does not
rewrite RAW files and does not require DNG output to exist.

This path helps when a camera-specific RAW file is recognized but downstream
tools have better support for DNG than for that proprietary RAW variant. The
report then highlights which organized RAW files should be considered for an
external conversion/interop step, while preserving the original RAW and any
linked `.xmp` sidecar behavior.

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
| RAW family (`.dng`, `.cr2`, `.cr3`, `.crw`, `.nef`, `.arw`, `.rw2`, `.orf`, `.raf`) | EXIF/TIFF via RAW backend | Embedded metadata | `DateTimeOriginal`, `CreateDate`, `DateTime`, `GPSInfo`, `GPSLatitude`, `GPSLongitude`, `Make`, `Model` when exposed in TIFF-style metadata; see the RAW compatibility matrix for per-format status | Implemented with full/partial/experimental status by format |

#### Internal normalized metadata schema

Metadata extraction can produce brand- or backend-specific field names. Before
organization decisions consume those values, the app maps supported equivalents
to a common internal schema:

| Internal field | Source aliases |
| --- | --- |
| `date_taken` | `DateTimeOriginal`, `CaptureDate`, `DateCreated`, `CreateDate`, `DateTime`, `DateTimeDigitized`, `exif:DateTimeOriginal`, `xmp:CreateDate` |
| `camera_make` | `Make`, `CameraMake`, `CameraManufacturer`, `Manufacturer`, `tiff:Make`, `exif:Make` |
| `camera_model` | `Model`, `CameraModel`, `CameraModelName`, `tiff:Model`, `exif:Model` |
| `gps` | `GPSInfo`, `GPSLatitudeDecimal`, `GPSLongitudeDecimal`, `GPSLatitude`, `GPSLongitude`, `exif:GPSLatitude`, `exif:GPSLongitude` |

Consumers such as date resolution, GPS extraction and camera-profile matching
use these normalized fields instead of checking manufacturer-specific tags. The
selected values still carry original provenance, so reports can show where a
normalized value came from, for example `EXIF:CameraManufacturer` or
`XMP sidecar:tiff:Model`.

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

- RAW formats in the initial scope (`.dng`, `.cr2`, `.cr3`, `.crw`, `.nef`,
  `.arw`, `.rw2`, `.orf`, `.raf`) are recognized by scanner/hash/inspect/
  organize flows. The RAW compatibility matrix documents each format as full,
  partial or experimental. `inspect` reports the detected RAW format plus
  TIFF-style EXIF make, model, capture date/time and GPS field origins when
  available. The current RAW backend is not a full manufacturer-specific RAW
  decoder, so files with incomplete readable metadata are marked as partially
  supported and list the missing RAW audit fields.
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
  metadata is not read from them. RAW files with missing or unsupported metadata
  fall back to sidecars, correction manifests, heuristics or filesystem `mtime`.
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
  conflict_policy: suffix
  date_heuristics: true
  location_inference: true
  correction_manifest: corrections.yaml
  correction_priority: highest
  clock_offset: "+01:00"
preview:
  heic: false
interop:
  dng_candidates: false
derivatives:
  enabled: false
  path: Derivatives
  patterns: "*_edit*,*-edit*,*_export*,*-export*"
```

The same structure is accepted as JSON. Supported fields:

- `output`: destination root directory;
- `naming.pattern`: filename pattern with `{date}`, `{stem}`, `{ext}` and
  `{original}`;
- `destination.pattern`: directory pattern with `{date}`, `{country}`,
  `{state}` and `{city}`;
- `destination.strategy` or `behavior.organization_strategy`: `date`, `event`,
  `location`, `location-date` or `city-state-month`;
- `behavior.mode`: `copy` or `move`;
- `behavior.dry_run`, `behavior.plan`, `behavior.reverse_geocode`: booleans;
- `behavior.reconciliation_policy`: `precedence`, `newest`, `oldest` or
  `filesystem`;
- `behavior.conflict_policy`: `suffix`, `skip`, `overwrite-never`,
  `quarantine` or `fail-fast`;
- `behavior.date_heuristics`: boolean to enable or disable inferred date
  recovery;
- `behavior.location_inference`: boolean to enable or disable non-GPS location
  inference;
- `behavior.correction_manifest`: CSV, JSON, YAML or YML correction manifest;
- `behavior.correction_priority`: `highest`, `metadata` or `heuristic`;
- `behavior.clock_offset`: global camera clock correction, using formats such
  as `+3h`, `-1d`, `+00:30` or `-5:45`;
- `preview.heic`: boolean to generate optional JPEG previews for organized
  HEIC/HEIF files;
- `interop.dng_candidates`: boolean to mark RAW files in reports as candidates
  for an optional external DNG interoperability workflow.
- `derivatives.enabled`: boolean to place derived files in a separate subtree;
- `derivatives.path`: relative output subtree for derived files, defaulting to
  `Derivatives`;
- `derivatives.patterns`: filename glob patterns used to classify derived files
  such as edits, exports or working files.
- `events.window_minutes`: positive integer used to group consecutive photos
  into temporal events;
- `events.directory`: boolean to place organized files below generated event
  directories instead of using event grouping only in reports.
- `events.directory_pattern`: directory pattern used by `--by event`, with
  `{date}`, `{event}`, `{event_id}` and `{index}` fields.

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
- `event`: groups photos by temporal proximity and writes to
  `YYYY/YYYY-MM-DD_event`, using `evento-001`, `evento-002`, ... unless a
  correction manifest rule provides an `event` name;
- `location`: writes to `Country/State/City`;
- `location-date`: writes to `Country/State/City/YYYY/MM`;
- `city-state-month`: writes to `City-State/YYYY-MM`, for example
  `Paraty-RJ/2024-08`.

Location-based strategies enable reverse geocoding automatically. If GPS data
is missing or location resolution fails, organization falls back to the default
date path.

Event organization uses `--event-window-minutes` when provided and otherwise
defaults to a 60-minute threshold. The default directory pattern is
`{date:%Y}/{date:%Y-%m-%d}_{event}`. A custom pattern such as
`{date:%Y}/{date:%m}/{date:%Y-%m-%d}_{event}` produces paths like
`2024/08/2024-08-15_viagem-paraty`. The `{event}` value is derived from the
first correction-manifest `event` name found in the temporal group; when no rule
provides a name, it is generated as `evento-001`, `evento-002`, and so on.

### Plan and execution separation

- operations are planned first into an intermediate structure;
- each plan item contains source, destination, action (`move`/`copy`), fallback
  metadata and linked RAW sidecars when present;
- optional temporal event grouping runs during planning, after dates and
  destinations are resolved;
- `--by event` uses the same temporal groups to replace the destination
  directory with a human-oriented event path;
- plan can be inspected without execution using `--plan`.

### Dry-run and operation modes

- `--dry-run` simulates all operations without changing files;
- dry-run output shows exactly what would happen;
- behavior matches real execution except physical file operations;
- `--copy` and `--move` are supported (`move` is default);
- destination directories are created automatically for real operations;
- move operations are implemented safely: copy first, then remove source after success.
- same-basename RAW `.xmp` sidecars are copied or moved with the RAW file and
  renamed to match the organized RAW basename.

### Reporting and audit

- final execution summary includes processed, ignored, error and fallback counts;
- summary distinguishes `dry-run`, `execute` and `plan` modes;
- `--report path.json` exports a structured JSON report;
- `--report path.csv` exports a CSV report;
- on `import`, the report is the final import manifest and audit trail;
- report rows include source, final destination, action, status, observations,
  chosen date, chosen location, metadata source and reconciliation conflicts;
- report rows identify original versus derived assets with `asset_role`,
  `derived` and `derived_reason`;
- when temporal event grouping is enabled, report rows include event id, label,
  index, size, start/end timestamps and configured time window;
- report rows include RAW sidecar linkage fields: `sidecar_count`,
  `sidecar_sources` and `sidecar_destinations`;
- execution reports identify RAW-family operations with `raw_family`,
  `raw_format` and `raw_flow`, and DNG interoperability markers with
  `dng_candidate` and `dng_candidate_reason`;
- execution reports include provenance fields for selected date and, when
  location is enabled, GPS/location source, confidence and raw values.

Inspect/audit reports:

- `photo-organizer inspect SOURCE --report metadata-audit.json` writes one item
  per inspected file with source evidence, chosen date/location and
  format-specific audit blocks;
- HEIC/HEIF files include a `heif` audit block with container status, selected
  image, found/missing metadata and date/location evidence classification;
- RAW-family files include a `raw` audit block with `is_raw`, `format`,
  `extension`, `flow`, `status`, field-level make/model/datetime/GPS entries,
  `found_fields`, `missing_fields` and partial-support warnings;
- CSV inspect reports include `raw_family`, `raw_format`, `raw_flow`,
  `raw_status`, `raw_found_fields` and `raw_missing_fields` for spreadsheet
  analysis.

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
  CHANGELOG.md
  docs/
    index.md
    installation.md
    usage.md
    configuration.md
    examples.md
    roadmap.md
    changelog.md
  src/
    photo_organizer/
      __init__.py
      __main__.py
      cli.py
      config.py
      correction_manifest.py
      constants.py
      geocoding.py
      heif_backend.py
      scanner.py
      metadata.py
      hashing.py
      preview.py
      raw_backend.py
      text_normalization.py
      naming.py
      planner.py
      executor.py
      logging_config.py
  tests/
    fixtures/
      README.md
      metadata_corpus.py
      heic_corpus.py
      raw_corpus.py
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
    test_heif_backend.py
    test_heic_corpus.py
    test_raw_corpus.py
    test_hashing.py
    test_planner.py
    test_preview.py
```

## Module responsibilities

- `cli.py`: command-line interface and command orchestration;
- `config.py`: external JSON/YAML configuration loading and validation;
- `correction_manifest.py`: batch date/location correction manifest parsing,
  matching and validation;
- `scanner.py`: recursive file scanning and extension filtering;
- `metadata.py`: EXIF, XMP, IPTC-IIM, PNG metadata extraction, normalized
  metadata schema, GPS extraction, provenance and best-date reconciliation;
- `geocoding.py`: reverse geocoding from GPS coordinates to city, state and country;
- `heif_backend.py`: optional `pillow-heif`/`libheif` integration, HEIF metadata
  access and container inspection;
- `hashing.py`: deterministic file/image hashes, safe digest comparison and duplicate grouping;
- `naming.py`: deterministic and pattern-based filename generation;
- `planner.py`: destination folder planning by date, location and custom patterns;
- `executor.py`: operation planning and execution/simulation;
- `preview.py`: optional JPEG preview generation for organized HEIC/HEIF files;
- `raw_backend.py`: safe TIFF-style EXIF metadata reader for RAW-family files
  in the initial RAW scope, including Apple ProRAW/DNG;
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

When a destination already exists, the organizer does not overwrite it by
default. The default conflict policy is `suffix`, which appends the next
available numeric suffix:

```text
2024-08-15_14-32-09.jpg
2024-08-15_14-32-09_01.jpg
2024-08-15_14-32-09_02.jpg
```

Destination conflict handling is configurable with `--conflict-policy` or
`behavior.conflict_policy` in the config file:

- `suffix`: default and safest; keep existing files and write `_01`, `_02`, ...
- `skip`: leave existing files untouched and skip the incoming operation;
- `overwrite-never`: leave existing files untouched, record an error, and
  continue processing the rest of the batch;
- `quarantine`: copy the incoming file to `<output>/.quarantine` with a JSON
  reason sidecar;
- `fail-fast`: stop the batch immediately at the first destination conflict.

### Original and derived file segregation

The organizer can optionally keep originals and derived files apart. Enable it
with `--segregate-derivatives` or `derivatives.enabled: true`. Derived files are
classified by filename glob patterns and written below a separate subtree while
keeping the normal date/location structure:

```bash
photo-organizer organize ~/Photos --output ~/Library --segregate-derivatives
photo-organizer organize ~/Photos --output ~/Library --segregate-derivatives --derived-path Working --derived-pattern "*-proof"
```

With the default `Derivatives` subtree, a file such as
`IMG_1034_edited.jpg` is written to:

```text
Library/Derivatives/2024/08/15/2024-08-15_14-32-09.jpg
```

Reports identify this decision with `asset_role`, `derived` and
`derived_reason`.

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
For HEIC/HEIF files, `inspect` also emits a `HEIF container` source and a
dedicated `heif` audit block in JSON reports with the detected format,
container status, selected primary image, metadata found/missing, and whether
the chosen date/location came from real embedded metadata/GPS or from
fallback/inference. Reports can be exported as JSON or CSV.

For RAW-family files, `inspect` emits a dedicated `raw` audit block in JSON
reports and prints the same technical summary in terminal output: detected RAW
format, workflow, support status, make, model, capture date/time, GPS and field
origin. Partially readable RAW files are marked as `partial` with clear missing
field warnings.

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
  conflict_policy: suffix
  date_heuristics: true
  location_inference: true
  correction_manifest: corrections.yaml
  correction_priority: highest
  clock_offset: "+01:00"
preview:
  heic: true
interop:
  dng_candidates: true
derivatives:
  enabled: true
  path: Derivatives
  patterns: "*_edit*,*_export*"
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

## Import manifest and audit report format

`organize --report` and `import --report` write the final batch manifest. The
manifest is the audit trail for the run: each row records the original source,
the final destination actually used after conflict suffixes, the chosen date,
the chosen location, the metadata source that drove the date decision and any
metadata reconciliation conflicts.

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
      "observations": "",
      "date_source": "filesystem",
      "date_field": "mtime",
      "date_confidence": "low",
      "date_raw_value": "1700000000.0",
      "chosen_date": "2024-08-15T14:32:09",
      "chosen_location": "",
      "metadata_source": "filesystem:mtime",
      "conflict": false,
      "conflict_sources": "",
      "conflict_reason": "",
      "date_kind": "inferred",
      "event_name": "",
      "raw_family": false,
      "raw_format": "",
      "raw_flow": "",
      "asset_role": "original",
      "derived": false,
      "derived_reason": "",
      "dng_candidate": false,
      "dng_candidate_reason": ""
    }
  ]
}
```

CSV reports use the following columns:

```text
source,destination,action,status,observations,date_source,date_field,date_confidence,date_raw_value,chosen_date,chosen_location,metadata_source,conflict,conflict_sources,conflict_reason,date_kind,event_name,sidecar_count,sidecar_sources,sidecar_destinations,raw_family,raw_format,raw_flow,asset_role,derived,derived_reason,dng_candidate,dng_candidate_reason
```

When reverse geocoding is enabled, execution reports also include location
fields:

```text
location_status,location_kind,organization_fallback,latitude,longitude,city,state,country,gps_source,gps_field,gps_confidence,gps_raw_value,location_source,location_field,location_confidence,location_raw_value
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

The project uses mostly Python standard library, plus Pillow for EXIF handling,
PyYAML for YAML configuration files and `pillow-heif`/`libheif` for HEIC/HEIF
decoding.

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
- `pillow-heif` for Python HEIF/HEIC integration;
- native `libheif` support, provided by the `pillow-heif` wheel or installed
  through the operating system package manager;
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

When the local `pillow-heif`/`libheif` stack can write HEIC files, the HEIC
corpus in `tests/fixtures/heic_corpus.py` also generates:

- iPhone-like HEIC with EXIF date and GPS;
- iPhone-like HEIC with EXIF date and no GPS;
- HEIC without EXIF;
- malformed `.HEIC` input for read-error coverage.

The RAW corpus in `tests/fixtures/raw_corpus.py` generates minimal TIFF-style
RAW-family samples for `.dng`, `.cr2`, `.cr3`, `.crw`, `.nef`, `.arw`, `.rw2`,
`.orf` and `.raf`, plus no-GPS and corrupted-file cases. These fixtures verify
valid extraction, safe handling of malformed RAW input and normalized camera,
date and GPS behavior across manufacturers.

RAW performance tests also create large sparse RAW-family files to verify that
metadata extraction and organization planning stay range-based. To validate the
same behavior against local camera RAW samples, set `PHOTO_ORGANIZER_REAL_RAW_DIR`
to a directory containing supported RAW files before running the test suite.

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
- HEIF/HEIC backend, audit and preview coverage;
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
- built-in strategies include `date`, `event`, `location`, `location-date` and
  `city-state-month`;
- `event` creates paths like `2024/2024-08-15_evento-001` or, when a correction
  manifest rule supplies an event name, `2024/08/2024-08-15_viagem-paraty`;
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

## Version v0.6.0 delivered scope

This section consolidates the HEIC/HEIF work delivered after the v0.5.0
metadata workflow.

### HEIC/HEIF format support

- `.heic`, `.heif` and `.hif` are part of the centralized supported format
  list;
- scan, hash, dedupe, inspect and organize flows recognize HEIC/HEIF files
  case-insensitively;
- HEIC/HEIF files preserve their original extension in generated destination
  names;
- unsupported or unreadable HEIC metadata falls back to sidecars, heuristics or
  filesystem `mtime` instead of aborting the run.

### HEIF backend integration

- `pillow-heif` is a project dependency and is documented together with native
  `libheif` installation guidance;
- `PillowHeifBackend` provides backend-neutral methods for opening images,
  reading raw EXIF/XMP metadata and inspecting HEIF container structure;
- missing native/backend dependencies produce a clear guidance message instead
  of an opaque decoder error;
- backend read errors are logged with context and do not stop unrelated files
  from being processed.

### HEIC metadata extraction

- backend-exposed EXIF date/time fields feed the same reconciliation pipeline
  used by JPEG, TIFF and PNG;
- backend-exposed EXIF GPS fields are normalized into decimal coordinates;
- backend-exposed XMP date, GPS and textual location fields are parsed;
- camera fields such as make/model are available for camera-profile correction
  rules when exposed by the backend.

### HEIF container audit

- `inspect` reports a `HEIF container` source for HEIC/HEIF files;
- JSON and CSV audit reports include HEIF format/status, metadata found/missing
  and date/location evidence classification;
- multiple images, sequences, thumbnails, auxiliary images and depth images are
  detected and reported as complex container features;
- primary image selection is deterministic: backend primary flag, then backend
  `primary_index`, then image index `0` with a warning.

### HEIC previews

- `organize --heic-preview` generates optional JPEG previews for HEIC/HEIF
  files after the main copy/move succeeds;
- config files can enable the same behavior with `preview.heic: true`;
- previews are written under `.previews` next to the organized file;
- preview generation resizes to a bounded JPEG and logs failures as warnings
  without failing organization.

### HEIC tests and documentation

- tests cover HEIC extension support in scan/CLI flows;
- tests cover backend metadata extraction, container selection and complex
  container reporting;
- tests cover HEIC inspect reports, filesystem fallback and organize dry-run
  planning;
- tests cover optional preview destination and JPEG generation;
- when local HEIF writing is available, generated HEIC corpus tests cover
  iPhone-like EXIF/GPS samples, missing GPS, missing EXIF and malformed input;
- README documents dependencies, platform limitations, troubleshooting,
  compatibility matrix entries and current application limitations for
  HEIC/HEIF.

## Version v0.7.0 RAW delivered scope

This section consolidates the RAW-family work delivered after the HEIC/HEIF
scope.

### RAW format support

- `.dng`, `.cr2`, `.cr3`, `.crw`, `.nef`, `.arw`, `.rw2`, `.orf` and `.raf`
  are part of the centralized supported format list;
- Apple ProRAW is treated as RAW-family input through the `.dng` / Linear DNG
  workflow, not as HEIC/JPEG output;
- scan, hash, dedupe, inspect and organize flows recognize RAW-family files
  case-insensitively;
- same-basename RAW `.xmp` sidecars are copied or moved with the RAW file and
  renamed to match the organized basename;
- optional `--dng-candidates` / `interop.dng_candidates` report marking remains
  non-destructive and never converts or rewrites RAW files.

### RAW metadata and inspect

- the RAW backend reads TIFF-style EXIF metadata for capture date/time, camera
  make, camera model and GPS when those fields are exposed by the file;
- metadata reads are range-based and bounded so large RAW files are not loaded
  fully into memory;
- generic embedded XMP/IPTC full-file scans are skipped for RAW-family files to
  keep large batches responsive; same-basename `.xmp` sidecars still apply;
- `inspect` prints and reports a dedicated RAW audit block with detected
  format, workflow, support status, field origins and partial-support warnings;
- execution reports include RAW classification fields (`raw_family`,
  `raw_format`, `raw_flow`) alongside sidecar and DNG-candidate fields.

### RAW tests and documentation

- synthetic RAW corpus fixtures cover every supported RAW-family extension;
- tests cover valid RAW metadata, corrupted RAW files, valid RAW without GPS and
  cross-manufacturer normalization;
- large sparse RAW tests verify range-based metadata reads and responsive batch
  planning without full RAW reads;
- optional real-file performance validation can run with
  `PHOTO_ORGANIZER_REAL_RAW_DIR`;
- README documents a RAW compatibility matrix by manufacturer/container with
  full, partial and experimental status, supported fields and known limitations.

## Version v0.8.0 import, conflict and asset-role delivered scope

This section consolidates the batch-audit and library-layout work delivered
after the RAW-family scope.

### Import command and final manifests

- `photo-organizer import SOURCE --output DIR` is available as a safe-copy
  workflow for SD cards, phone dumps, old backups and other inbound batches;
- `import` shares the same planning, metadata, naming, location, correction,
  conflict and reporting behavior as `organize`;
- `import` defaults to copy mode so the source batch is not modified unless the
  user explicitly opts into move behavior;
- `organize --report` and `import --report` write final batch manifests in JSON
  or CSV;
- manifest rows include the original source, final destination actually used,
  action, status, observations, chosen date, chosen location, metadata source
  and reconciliation conflict fields;
- manifests preserve audit fields for RAW sidecars, RAW format/flow, DNG
  candidates, correction manifests, clock offsets and derived asset decisions.

### Configurable destination conflict policy

- destination conflict handling is explicitly configurable with
  `--conflict-policy` or `behavior.conflict_policy`;
- supported policies are `suffix`, `skip`, `overwrite-never`, `quarantine` and
  `fail-fast`;
- `suffix` remains the default safe behavior and never overwrites existing
  files;
- `skip` records a skipped operation and leaves both source and destination
  untouched;
- `overwrite-never` records a per-item error while continuing the remaining
  batch;
- `quarantine` copies the incoming conflicting file to `<output>/.quarantine`
  with a JSON reason sidecar;
- `fail-fast` aborts the batch on the first destination conflict.

### Original and derived asset segregation

- derived-file segregation can be enabled with `--segregate-derivatives` or
  `derivatives.enabled: true`;
- derived files are classified by configurable filename glob patterns through
  repeated `--derived-pattern` flags or `derivatives.patterns`;
- the derived subtree is configurable with `--derived-path` or
  `derivatives.path` and defaults to `Derivatives`;
- when a file is classified as derived, the normal date/location organization
  path is preserved below the derived subtree;
- reports clearly identify derived handling with `asset_role`, `derived` and
  `derived_reason`.

### Configuration, documentation and tests

- sample configuration now documents `behavior.conflict_policy` and the
  `derivatives` section;
- README examples cover import manifests, conflict policies and
  original/derived segregation;
- tests cover CLI/config plumbing, executor behavior, report fields and
  end-to-end safe defaults for the new policies.

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
- implemented and stabilized for HEIC/HEIF support (see Version v0.6.0
  delivered scope section).

### Version 0.7.0
- initial RAW recognition scope implemented for Apple ProRAW/DNG, Canon
  CR2/CR3/CRW, Nikon NEF, Sony ARW, Panasonic RW2, Olympus/OM System ORF and
  Fujifilm RAF;
- scanner, hash, dedupe, inspect and organize flows recognize the initial RAW
  extension set through `IMAGE_FORMATS`;
- RAW metadata backend implemented for range-based TIFF-style EXIF capture
  date, camera make/model and GPS extraction;
- RAW inspect audit, RAW execution report fields, RAW corpus tests, large-file
  performance policy and compatibility matrix are implemented;

### Version 0.8.0
- import final manifests, configurable destination conflict policies and
  optional original/derived asset segregation are implemented and documented
  (see the Version v0.8.0 delivered scope section).

### Future work
- support for more media types (including videos);
- richer filtering (include/exclude and depth controls);
- richer report analytics;
- broader manufacturer-specific RAW metadata extraction support;
- richer event naming controls beyond the deterministic generated event label;
- investigate ExifTool integration for broad metadata extraction across RAW
  formats;
- expand real-camera RAW validation beyond the synthetic corpus and optional
  `PHOTO_ORGANIZER_REAL_RAW_DIR` test hook.

## Project status

In active development, with stable tested workflows for scan, dedupe, inspect,
explain, organize and import across JPEG/PNG/TIFF, HEIC/HEIF and the current
RAW-family scope.

## Motivation

This project was created as a practical exercise to study Python applied to real-world file organization and command-line automation problems.

## Contributing

Suggestions, improvements, and ideas are welcome.

## License

This project may be distributed under the MIT License.
