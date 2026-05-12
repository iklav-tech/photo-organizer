# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic versioning.

## [Unreleased]

### Added

- Initial proprietary RAW format recognition scope:
  - Canon `.cr2`, `.cr3`, `.crw`
  - Nikon `.nef`
  - Sony `.arw`
  - Panasonic `.rw2`
  - Olympus/OM System `.orf`
  - Fujifilm `.raf`
- RAW extensions added to the centralized `IMAGE_FORMATS` list so scanner,
  hash, dedupe, inspect and organize flows share the same initial scope.
- RAW metadata backend for safe TIFF-style EXIF extraction:
  - capture date/time
  - camera manufacturer
  - camera model
  - GPS coordinates
- Internal normalized metadata schema for:
  - `date_taken`
  - `camera_make`
  - `camera_model`
  - GPS coordinates
- RAW sidecar organization support for same-basename `.xmp` files.
- Optional DNG interoperability candidate marking:
  - `--dng-candidates`
  - `--no-dng-candidates`
  - `interop.dng_candidates`
- README documentation for the first supported RAW wave and its current
  metadata limitations.

### Changed

- CLI help for scan, dedupe, inspect and organize now reflects the RAW
  extensions automatically through the centralized supported extension list.
- Roadmap now distinguishes initial RAW file recognition from future
  broader proprietary RAW metadata extraction.
- Date resolution, GPS extraction and camera-profile matching can use RAW
  EXIF/TIFF metadata when available.
- Date resolution, GPS extraction and camera-profile matching now consume
  normalized metadata fields instead of source-specific tag names.
- Equivalent fields from EXIF, XMP sidecars, RAW TIFF-style metadata and common
  vendor aliases are mapped before organization decisions are made.
- RAW organization planning now links same-basename `.xmp` sidecars to the RAW
  operation.
- Execution reports now include `sidecar_count`, `sidecar_sources` and
  `sidecar_destinations`.
- Execution reports now include `dng_candidate` and `dng_candidate_reason`
  when optional DNG interoperability marking is enabled.

### Behavior guarantees

- RAW extensions in the initial scope are recognized case-insensitively.
- RAW files are discoverable, hashable and eligible for organization planning.
- RAW parsing failures are handled per file and do not stop the full batch.
- When TIFF-style EXIF metadata is available, RAW files can provide capture
  date/time, camera make/model and GPS.
- Consumers do not need to know whether camera metadata came from `Make`,
  `CameraManufacturer`, `tiff:Make` or another supported alias.
- Original source tags remain available through `MetadataProvenance` for
  inspect, explain and debug output.
- Same-basename RAW `.xmp` sidecars are copied or moved with the RAW file and
  renamed to match the organized RAW basename.
- Sidecar destination collision handling follows the RAW destination suffix so
  linked files do not overwrite existing files.
- DNG candidate marking is optional and non-destructive; the app does not run
  conversion or require DNG files to be created.
- RAW files with missing or unsupported embedded metadata can still use
  sidecars, correction manifests, heuristics or filesystem `mtime` fallback.

### Validation

- Tests cover scanner recognition for the initial RAW extension set.
- Tests cover case-insensitive scanner matching for RAW extensions.
- CLI help tests cover RAW extension visibility.
- Metadata tests cover RAW capture date/time, camera make/model and GPS
  extraction.
- Metadata tests cover safe handling of malformed RAW files.
- Metadata tests cover vendor alias normalization and provenance preservation.
- Tests cover RAW sidecar detection, copy, move and execution report linkage.
- Tests cover DNG candidate marking from CLI/config, default disabled behavior
  and report fields.

## [0.6.0] - 2026-05-11

### Added

- HEIC/HEIF container detection for scan, hash, dedupe, inspect and organize
  pipelines:
  - `.heic`
  - `.heif`
  - `.hif`
- HEIF/HEIC metadata backend abstraction:
  - `photo_organizer.heif_backend.HeifBackend`
  - `PillowHeifBackend`
  - raw EXIF/XMP metadata access through `HeifMetadata`
  - container structure access through `HeifContainerInfo`
  - clear dependency guidance when `pillow-heif`/`libheif` is unavailable
- HEIF/HEIC EXIF extraction for backend-exposed:
  - date/time fields
  - orientation
  - camera make/model fields
  - GPS fields
- HEIF/HEIC XMP extraction for backend-exposed:
  - date fields
  - GPS fields
  - textual location fields
- HEIF container audit fields in `inspect` JSON and CSV reports:
  - format
  - container status
  - found metadata
  - missing metadata
  - date evidence
  - location evidence
- Complex HEIF container reporting for:
  - multiple images or sequence-like structures
  - embedded thumbnails
  - auxiliary images
  - depth images
  - selected primary image index
  - backend selection warnings
- Optional HEIC/HEIF JPEG preview generation:
  - `photo-organizer organize SOURCE --output DIR --heic-preview`
  - `photo-organizer organize SOURCE --output DIR --no-heic-preview`
  - configuration through `preview.heic`
  - previews written under `.previews` next to organized HEIC/HEIF files
- `pillow-heif` added as a project dependency for HEIF/HEIC support.
- `requirements.txt` added with Python dependencies and native `libheif`
  installation guidance.
- Synthetic HEIC corpus fixtures covering:
  - iPhone-like HEIC with EXIF date and GPS
  - iPhone-like HEIC with EXIF date and no GPS
  - HEIC without EXIF
  - malformed `.HEIC` input
- Automated tests for:
  - HEIC extension support
  - HEIF backend metadata extraction
  - primary image selection
  - complex container reporting
  - HEIC inspect report fields
  - HEIC filesystem fallback
  - HEIC organize dry-run planning
  - optional JPEG preview generation

### Changed

- Supported image formats now include `.heic`, `.heif` and `.hif` in the
  centralized format list.
- Scan, hash, dedupe, inspect and organize flows now share HEIC/HEIF extension
  support.
- HEIC/HEIF files preserve the original extension in generated destination
  names.
- HEIF metadata extraction now uses the same date reconciliation and GPS
  normalization paths used by JPEG, TIFF and PNG metadata.
- `inspect` now emits a `HEIF container` metadata source for HEIC/HEIF files.
- `inspect` output now classifies HEIC date/location evidence as real metadata,
  real GPS, inferred, missing or fallback.
- HEIF primary image selection is deterministic:
  - backend primary flag
  - backend `primary_index`
  - image index `0` with a warning
- README updated to consolidate the delivered v0.6.0 workflow, HEIC/HEIF
  dependency setup, platform limitations, troubleshooting, compatibility matrix
  entries, preview behavior, project structure and roadmap.

### Fixed

- Missing HEIF native/backend dependencies now produce a clear warning with
  installation guidance instead of an opaque decoder failure.
- HEIF backend read errors are handled per file and do not stop unrelated files
  from being scanned, audited or organized.
- HEIC files with missing embedded metadata can fall back to sidecars,
  heuristics or filesystem `mtime`.
- Preview generation failures are logged as warnings and do not make the main
  copy/move operation fail.
- Malformed `.HEIC` inputs are handled safely during metadata extraction and
  audit reporting.

### Behavior guarantees in v0.6.0

- `.heic`, `.heif` and `.hif` are supported by scan, hash, dedupe, inspect and
  organize flows.
- HEIC/HEIF metadata extraction depends on `pillow-heif` and native `libheif`
  capability exposed in the local environment.
- If the HEIF backend cannot expose EXIF/XMP metadata, organization can still
  use sidecars, correction manifests, heuristics or filesystem `mtime`.
- Complex HEIF structures are reported, but only one deterministic primary
  image is used by the metadata pipeline.
- Optional HEIC previews are generated only when explicitly enabled.
- Preview failures do not roll back or fail successful organization operations.
- `inspect` and `explain` remain read-only for HEIC/HEIF files.

### Validation

- Tests cover HEIC/HEIF extension recognition in CLI help, scan and organize
  paths.
- Tests cover HEIF backend EXIF date, GPS and XMP extraction.
- Tests cover HEIF container inspection, complex container feature reporting
  and primary image selection fallback.
- Tests cover HEIC-specific `inspect` JSON and CSV report fields.
- Tests cover filesystem fallback for HEIC files without readable embedded
  metadata.
- Tests cover optional preview destination planning and JPEG preview generation.
- Generated HEIC corpus tests run when the local `pillow-heif`/`libheif` stack
  can write HEIC files; otherwise they are skipped with an explicit reason.

## [0.5.0] - 2026-05-05

### Added

- Read-only metadata audit command:
  - `photo-organizer inspect SOURCE`
  - `photo-organizer audit-metadata SOURCE`
  - JSON and CSV reports through `--report`
- Explainable decision report command:
  - `photo-organizer explain SOURCE`
  - JSON report through `--report explain.json`
  - optional `--reverse-geocode`
- Explain report fields for each file:
  - `chosen_date`
  - `chosen_location`
  - `candidates`
  - `sources`
  - source field and confidence
  - raw values when available
- Metadata provenance model with:
  - source
  - field
  - confidence
  - raw value
- Date reconciliation model that records:
  - selected candidate
  - all parsed candidates
  - conflict status
  - reconciliation policy
  - selection reason
- Configurable reconciliation policies:
  - `precedence`
  - `newest`
  - `oldest`
  - `filesystem`
- Embedded XMP packet extraction for supported image files.
- Same-basename `.xmp` sidecar extraction for date and GPS fields.
- XMP sidecar precedence within the XMP tier.
- PNG metadata support for:
  - `eXIf`
  - `iTXt`
  - `tEXt`
  - `zTXt`
  - `tIME`
  - XMP packets stored in `XML:com.adobe.xmp`
- IPTC-IIM legacy dataset extraction for:
  - date and time
  - city, state and country
  - title
  - author
  - description
- Low-confidence date heuristics from:
  - same-basename external sidecars
  - filename patterns
  - parent folder date patterns
  - sibling batch context
  - filesystem `mtime`
- Non-GPS location inference from:
  - IPTC-IIM textual location
  - XMP textual location
  - external manifests
  - folder or album names
  - sibling batch context
- Correction manifests for batch overrides:
  - CSV
  - JSON
  - YAML
  - YML
- Correction manifest selectors:
  - exact file path
  - folder
  - glob
  - filename pattern
  - camera profile
- Correction manifest fields:
  - date
  - timezone
  - clock offset
  - city
  - state
  - country
  - event name
- Correction priority options:
  - `highest`
  - `metadata`
  - `heuristic`
- Global `--clock-offset` support.
- Config support for:
  - `behavior.reconciliation_policy`
  - `behavior.date_heuristics`
  - `behavior.location_inference`
  - `behavior.correction_manifest`
  - `behavior.correction_priority`
  - `behavior.clock_offset`
- Text normalization observations in reports.
- Format/source/field compatibility matrix in README.
- Explicit metadata limitation documentation in README.
- Synthetic legacy metadata corpus fixtures covering:
  - JPEG/EXIF
  - TIFF tags
  - IPTC-IIM
  - embedded XMP
  - XMP sidecar
  - PNG `eXIf`
  - PNG `iTXt`/`tEXt`
  - files without usable metadata
  - conflicting metadata
- Automated corpus tests for:
  - successful extraction
  - missing metadata
  - metadata conflict
  - date precedence matrix

### Changed

- Date resolution now uses an explicit metadata precedence matrix instead of a
  simple EXIF/mtime chain.
- Date decisions now distinguish captured values from inferred values.
- Metadata conflict handling now keeps all candidates for reporting and debug
  output.
- Execution reports now include date provenance fields.
- Location-aware execution reports now include GPS/location provenance fields.
- Plan operations now carry date reconciliation, location provenance, location
  status and correction manifest details.
- XMP values from same-basename sidecars override embedded XMP values within
  the XMP tier.
- PNG `tIME` is treated as a low-confidence image modification timestamp rather
  than an original capture timestamp.
- Location-based organization can infer non-GPS location metadata when
  configured.
- README updated to consolidate the delivered v0.5.0 workflow, explain
  reports, compatibility matrix, known limitations and metadata test corpus.
- Project structure documentation now includes:
  - `correction_manifest.py`
  - `text_normalization.py`
  - `tests/fixtures/metadata_corpus.py`
  - `tests/test_metadata_corpus.py`

### Fixed

- Pillow-specific EXIF values such as rational numbers are now serialized
  safely in explain JSON reports.
- `pytest` and `.venv/bin/python -m pytest` both collect the metadata corpus
  tests correctly.
- Malformed XMP parse errors are handled without interrupting metadata audits.
- Missing date metadata can be reported as an expected absence when heuristics
  are disabled.
- Correction clock offsets preserve the original datetime in provenance.
- Text normalization changes are surfaced in report observations.

### Behavior guarantees in v0.5.0

- `inspect` and `explain` are read-only commands.
- `explain --report` writes JSON only.
- Explain reports include chosen date, chosen location, candidates, source and
  confidence for debugging decisions without reading code.
- Date reconciliation is deterministic for the default `precedence` policy.
- `newest`, `oldest` and `filesystem` policies use precedence as a tie-breaker
  where applicable.
- Sidecar XMP values override embedded XMP values only inside the XMP tier; EXIF
  still has higher default date precedence.
- Inferred dates use low confidence.
- Files without usable metadata fail clearly when date heuristics are disabled.
- Unknown IPTC-IIM datasets are ignored safely.
- WEBP and BMP remain supported for scan/hash flows but embedded metadata
  is not read by the current metadata reader.

### Validation

- Local automated tests passing for v0.5.0 scope (`pytest`, 239 tests).
- Tests cover explain report JSON generation and serialization of non-JSON EXIF
  value types.
- Tests cover inspect reports, metadata source audit and final date/location
  decisions.
- Tests cover correction manifests, correction priorities and clock offsets.
- Tests cover XMP embedded metadata, XMP sidecars and sidecar precedence.
- Tests cover IPTC-IIM date and textual metadata extraction.
- Tests cover PNG `eXIf`, `iTXt`, `tEXt`, `zTXt` and `tIME` metadata paths.
- Tests cover missing metadata and disabled date heuristics.
- Tests cover metadata conflict recording and precedence winners.
- Tests cover the synthetic legacy metadata corpus and compatibility matrix.

## [0.4.0] - 2026-05-01

### Added

- External organization configuration files for `organize`:
  - JSON (`.json`)
  - YAML (`.yaml`)
  - YML (`.yml`)
- `--config PATH` CLI option for loading organization rules.
- Configuration support for:
  - output directory
  - filename pattern
  - destination pattern
  - organization strategy
  - operation mode
  - dry-run mode
  - plan mode
  - reverse geocoding behavior
- Minimal configuration validation with clear errors for:
  - missing config files
  - unsupported config extensions
  - invalid JSON/YAML structure
  - invalid field types
  - invalid mode values
  - invalid organization strategies
  - invalid filename and destination pattern fields
- Custom filename pattern support through config `naming.pattern`.
- Custom filename pattern support through CLI `--name-pattern`.
- Supported filename pattern fields:
  - `{date}`
  - `{stem}`
  - `{ext}`
  - `{original}`
- Destination pattern support through config `destination.pattern`.
- Supported destination pattern fields:
  - `{date}`
  - `{country}`
  - `{state}`
  - `{city}`
- GPS coordinate extraction from EXIF metadata as decimal latitude/longitude.
- Reverse geocoding helper for resolving GPS coordinates into:
  - city
  - state
  - country
- Location-aware organization strategies:
  - `location`
  - `location-date`
- Hybrid city/state/month organization strategy:
  - `city-state-month`
  - example path: `Paraty-RJ/2024-08`
- Location status tracking in planned operations:
  - `disabled`
  - `missing-gps`
  - `unresolved`
  - `resolved`
  - `error`
- Organization fallback tracking when a location strategy cannot resolve a location.
- Execution summary counters for:
  - resolved location files
  - files with GPS coordinates
  - files missing GPS
  - organization fallback files
- Location-aware audit report fields when reverse geocoding is enabled:
  - location status
  - organization fallback flag
  - latitude
  - longitude
  - city
  - state
  - country
- Tests for:
  - GPS coordinate extraction
  - absence of GPS metadata
  - reverse geocoding behavior
  - location fallback behavior
  - external configuration loading and validation
  - custom filename patterns
  - custom destination patterns
  - `city-state-month` strategy

### Changed

- `organize --help` now documents:
  - `--config`
  - `--name-pattern`
  - `city-state-month`
  - supported organization strategies
- CLI-provided values now take precedence over equivalent config values where applicable.
- `--name-pattern` overrides config `naming.pattern`.
- Location-based strategies automatically enable reverse geocoding unless the user explicitly disables it.
- README updated to document the v0.4.0 workflow, configuration files, naming patterns, destination patterns, GPS/location behavior, fallback behavior and roadmap updates.
- Project structure and module responsibility documentation now includes `config.py`, `geocoding.py`, `test_config.py` and `test_geocoding.py`.
- Roadmap updated to mark v0.4.0 as implemented and add planned v0.6.0 HEIC/HEIF and v0.7.0 proprietary RAW work.
- PyYAML added as a project dependency for YAML configuration support.

### Fixed

- Invalid filename patterns now fail before planning instead of being discovered per file.
- Filename patterns with path separators are rejected clearly.
- Unknown filename and destination pattern fields now return clear validation errors.
- Location organization strategies now fall back to date-based organization when GPS is missing or reverse geocoding cannot resolve a location.
- Reverse geocoding network/service failures are handled as unresolved location data instead of aborting organization.

### Behavior guarantees in v0.4.0

- Default naming remains `YYYY-MM-DD_HH-MM-SS.ext` when no custom pattern is configured.
- Original file extensions remain preserved unless the user explicitly changes the pattern.
- CLI `--name-pattern` has precedence over config `naming.pattern`.
- Configured organization behavior is validated before execution.
- `date`, `location`, `location-date` and `city-state-month` are supported organization strategies.
- `city-state-month` produces a stable `City-State/YYYY-MM` destination directory.
- Missing GPS data does not fail the organization run.
- Unresolved location data does not fail the organization run.
- Location fallback is visible in operation metadata, summaries and location-aware reports.

### Validation

- Local automated tests passing for v0.4.0 scope (`pytest`, 135 tests).
- Tests cover JSON and YAML config loading.
- Tests cover invalid config and invalid pattern errors.
- Tests cover CLI/config precedence for custom filename patterns.
- Tests cover GPS coordinate extraction and missing GPS behavior.
- Tests cover reverse geocoding resolution and failure handling.
- Tests cover date fallback for location-based organization.
- Tests cover `city-state-month` planning and end-to-end organization.

## [0.3.0] - 2026-04-28

### Added

- File hashing utilities using deterministic SHA-256 by default.
- Chunked file hashing so large files are processed without loading the whole file into memory.
- Safe hash comparison using `hmac.compare_digest`.
- Duplicate grouping by content hash with:
  - content hash
  - original file
  - duplicate files
- `dedupe` CLI subcommand for read-only duplicate discovery:
  - `photo-organizer dedupe SOURCE`
  - `photo-organizer dedupe SOURCE --read-only`
- Human-readable duplicate output with:
  - group number
  - hash
  - quantity
  - original path
  - duplicate paths
- Structured duplicate reports with `dedupe --report`:
  - JSON when the path ends in `.json`
  - CSV when the path ends in `.csv`
- JSON duplicate reports containing:
  - summary
  - duplicate groups
  - hash
  - quantity
  - original
  - duplicates
  - all paths
- CSV duplicate reports with analysis-friendly rows containing:
  - group id
  - hash
  - quantity
  - role (`original` or `duplicate`)
  - path
- Additional supported image extensions:
  - `.tif`
  - `.tiff`
  - `.webp`
  - `.bmp`
- Centralized image format configuration with per-format EXIF capability flags.
- Resilient per-file error handling for:
  - malformed EXIF data
  - metadata planning failures
  - hash calculation failures
- Automated tests specific to hash and dedupe behavior.

### Changed

- Supported image formats are now configured through `IMAGE_FORMATS` instead of a flat extension-only list.
- Scanner and hash flows now share the centralized supported format configuration.
- EXIF extraction is attempted only for formats marked with real EXIF support.
- PNG, WEBP and BMP safely skip EXIF extraction and use file modification time fallback.
- README updated to describe the current v0.3.0 workflow, duplicate reports, supported formats, resilience and tests.
- Roadmap updated to mark v0.3.0 as implemented and move future media/filtering work to later versions.

### Fixed

- A malformed EXIF payload no longer interrupts the full metadata flow.
- A single problematic file no longer aborts organization planning for remaining files.
- A single unreadable/problematic file no longer aborts duplicate detection for remaining files.
- Different files are not reported as duplicate groups when their content hashes differ.

### Behavior guarantees in v0.3.0

- Hashes are deterministic for identical file content.
- Hashing reads files in bounded chunks.
- Duplicate detection groups only files with identical content hashes.
- `dedupe` is read-only and does not move, copy or delete files.
- Duplicate reports are valid JSON or CSV and include hash, quantity and paths.
- Unsupported image formats are ignored by scan and dedupe flows.
- Formats without real EXIF support are handled safely through date fallback.
- Invalid files and malformed metadata are logged with context while processing continues.

### Validation

- Local automated tests passing for v0.3.0 scope (`pytest`, 83 tests).
- Tests cover equal and different file content.
- Tests cover duplicate grouping, no-duplicate output and duplicate reports.
- Tests use temporary files and directories for hash and dedupe scenarios.

## [0.2.0] - 2026-04-27

### Added

- Safe move execution that copies the destination first and removes the source only after success.
- Automatic destination directory creation before real copy/move operations.
- Filename collision handling with deterministic suffixes:
  - `_01`
  - `_02`
  - `_03`
  - and the next available numeric suffix.
- Execution summary at the end of `organize` with:
  - processed file count
  - ignored file count
  - error count
  - date fallback count
  - execution mode (`dry-run`, `execute` or `plan`)
- Audit report export with `--report`:
  - JSON when the path ends in `.json`
  - CSV when the path ends in `.csv`
- Structured report rows containing:
  - source
  - destination
  - action
  - status
  - observations
- Improved CLI help with examples.
- Grouped `organize --help` arguments:
  - paths
  - execution
  - audit report
  - operation mode
- Integration tests for the complete planning and execution pipeline using temporary directories.

### Changed

- `organize` now reports the effective destination path after collision resolution.
- Move mode now behaves as a safer copy-then-remove operation instead of relying on direct move semantics.
- `FileOperation` now records whether date resolution used the file modification time fallback.
- Metadata date resolution now exposes fallback information while preserving the existing datetime-only helper.
- README updated to document the delivered v0.2.0 scope, report formats and updated roadmap.
- CLI validation now gives clearer errors for missing `--output`.
- CLI validation now rejects unsupported report extensions before execution.

### Fixed

- Existing destination files are no longer overwritten by default.
- Multiple operations targeting the same planned destination now receive unique suffixes in the same batch.
- Dry-run now reserves destination names consistently, matching real execution planning.
- Source files are preserved when a move operation fails before successful source removal.
- Copied destination artifacts are cleaned up when source removal fails during safe move.

### Behavior guarantees in v0.2.0

- Missing destination directories are created automatically for real operations.
- Move operations remove the source only after the destination exists.
- Name collisions are resolved predictably using the next available suffix.
- Dry-run does not create output directories or output files.
- JSON and CSV reports are valid and include one row per operation.
- CLI help exposes practical examples for common workflows.

### Validation

- Local automated tests passing for v0.2.0 scope (`pytest -q`, 58 tests).
- Integration tests cover copy, move, dry-run, directory creation and destination conflicts.

## [0.1.0] - 2026-04-24

### Added

- CLI entrypoint with root command support.
- Command help pages:
  - `photo-organizer --help`
  - `photo-organizer scan --help`
  - `photo-organizer organize --help`
- Root CLI options:
  - `--version`
  - `--log-level` with `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `scan` command with recursive image discovery.
- Supported image extensions centralized in one place (`.jpg`, `.jpeg`, `.png`).
- EXIF extraction for compatible JPEG files.
- Best date resolution strategy with explicit priority chain.
- Deterministic default naming rule: `YYYY-MM-DD_HH-MM-SS.ext`.
- Date-based destination planner using `YYYY/MM/DD`.
- Planning layer with intermediate operation structure containing:
  - source
  - destination
  - action (`move` or `copy`)
- Execution modes:
  - default `move`
  - explicit `--move`
  - `--copy`
- Simulation mode `--dry-run` for non-destructive runs.
- Plan inspection mode `--plan` for non-executing preview.
- Structured logging configuration module.
- Test suite covering CLI, scanner, metadata, naming, planner and executor.
- End-to-end dry-run test for the organize flow.

### Changed

- `organize` now follows a clear flow: scan -> metadata -> naming -> planning -> execute/simulate.
- Logging now reports lifecycle events and counters for command execution.
- README updated to document delivered v0.1.0 scope and usage options.

### Fixed

- Friendly error handling for `scan` when source directory does not exist.
- Friendly error handling for `organize` when source path is invalid.
- EXIF absence/read failures now handled safely without breaking execution.

### Behavior guarantees in v0.1.0

- Unsupported files are ignored during scan.
- Extension matching is case-insensitive.
- Date fallback order is deterministic:
  1. `DateTimeOriginal`
  2. `CreateDate`
  3. `mtime`
- Name generation is deterministic and preserves original extension.
- Dry-run does not move/copy files and does not create output artifacts.

### Validation

- Local automated tests passing for v0.1.0 scope (`pytest -q`).
