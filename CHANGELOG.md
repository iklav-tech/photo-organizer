# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GUI source folder selection with `QFileDialog`, shared session state and header display of the selected path.
- GUI session state prepared for scanned file metrics, duplicate groups, operation preview data and logs.
- Dashboard metric cards for total files, total size and supported format distribution, backed by the GUI adapter scan summary.

### Fixed

- Replaced leftover mockup branding in the GUI with the project display name and package version.

## [1.1.0] - 2026-05-30

### Added

- Initial PySide6 desktop GUI entrypoint with `photo-organizer --gui`.
- GUI bootstrap with dependency validation and actionable install guidance when PySide6 is unavailable.
- Base GUI architecture with application bootstrap, organizer adapter, main window shell, navigation, theme helpers, window geometry helpers, reusable widgets and task worker structure.
- Initial desktop shell with sidebar, topbar, footer and organize page.

### Changed

- PySide6 is now installed with the default project dependencies so local editable installs can launch the GUI without requesting the `gui` extra separately.
- `requirements.txt` now lists the canonical `PySide6` package directly and leaves PySide6 addon/essential packages to dependency resolution.
- README was reorganized as the project entrypoint following Standard Readme conventions and updated for the current CLI, GUI, supported formats, reports, limitations and contribution flow.

## [1.0.0] - 2026-05-22

### Added

- Documented the project versioning and release policy, including Semantic Versioning usage, Git tag format and release checklist.
- Added focused coverage for journal/resume behavior, text normalization helpers and logging configuration.
- Added public package metadata for the stable release, including MIT license metadata, classifiers, keywords, documentation URL and changelog URL.

### Changed

- Promoted the project to the first stable public release, version `1.0.0`.
- Reviewed runtime dependencies and documented that `requirements.txt` mirrors `pyproject.toml`.

## [0.9.0] - 2026-05-22

### Added

- Standard Readme structure for the main `README.md`, making project purpose, installation, CLI usage, supported formats, limitations, contribution flow and license easier to scan.
- Keep a Changelog structure for `CHANGELOG.md`, with semantic categories and an explicit `Unreleased` section.
- Documentation site under `docs/`, with installation, usage, configuration, examples, roadmap and changelog pages.
- Jekyll/GitHub Pages documentation layout and project Pages configuration.
- Temporal event grouping for `organize` and `import`, configurable with `--event-window-minutes` or `events.window_minutes`.
- Optional event destination directories through `--event-directory` or `events.directory`.
- Event-based organization with `--by event` and configurable event directory patterns.
- Burst detection that marks close temporal sequences as `REVIEW_BURST` or `BURST` without deleting files.

### Changed

- README content now focuses on the current user-facing project state instead of duplicating release history.
- Changelog entries were consolidated into human-oriented release notes with consistent ordering and categories.

## [0.8.0] - 2026-05-16

### Added

- Safe-copy `import` workflow for cards, phone dumps and backups.
- Final JSON/CSV manifests for `organize` and `import`, including source, final destination, chosen date/location, metadata source, conflicts and observations.
- Destination conflict policies: `suffix`, `skip`, `overwrite-never`, `quarantine` and `fail-fast`.
- Quarantine flow under `<output>/.quarantine` with JSON reason sidecars.
- Optional original/derived asset segregation with configurable path and glob patterns.
- Report fields for derived classification: `asset_role`, `derived` and `derived_reason`.
- CLI help and sample configuration coverage for import, conflict policies and derivative segregation.

### Changed

- Execution reports are treated as final organization/import manifests and audit trails.
- Skipped operations are represented as `status: skipped`.
- `processed_files` no longer counts skipped operations as processed.
- Default conflict behavior remains the non-overwriting `suffix` policy.
- Derived assets, when enabled, are written under the configured derived subtree while preserving the normal date/location layout below it.

### Fixed

- Conflict handling now records skipped/error/quarantine outcomes consistently in reports.
- Fail-fast conflict behavior preserves source and existing destination before stopping.

## [0.7.0] - 2026-05-13

### Added

- Initial RAW recognition for `.dng`, `.cr2`, `.cr3`, `.crw`, `.nef`, `.arw`, `.rw2`, `.orf` and `.raf`.
- RAW metadata backend for bounded TIFF-style EXIF reads, including capture date/time, camera make/model and GPS when exposed.
- RAW audit data in `inspect` JSON/CSV reports, including format, flow, status, found/missing fields and warnings.
- RAW-family fields in execution reports: `raw_family`, `raw_format` and `raw_flow`.
- Synthetic RAW fixtures and performance tests for supported RAW-family extensions.
- Same-basename RAW `.xmp` sidecar organization.
- Optional DNG interoperability candidate marking through `--dng-candidates` or `interop.dng_candidates`.

### Changed

- Scan, hash, dedupe, inspect and organize flows share the RAW extensions from the centralized format list.
- Date resolution, GPS extraction and camera profile matching use normalized metadata fields across EXIF, XMP, RAW and aliases.
- Apple ProRAW `.dng` is treated as RAW-family input through the Linear DNG workflow.
- RAW organization planning skips generic full-file embedded XMP/IPTC scans for performance while preserving same-basename sidecar support.

### Fixed

- RAW parsing failures are isolated per file and do not stop the full batch.
- Sidecar destination collision handling follows the RAW destination suffix so linked files do not overwrite existing files.

## [0.6.0] - 2026-05-11

### Added

- HEIC/HEIF support for `.heic`, `.heif` and `.hif` across scan, hash, dedupe, inspect and organize flows.
- HEIF backend abstraction using `pillow-heif`/`libheif` for EXIF/XMP and container inspection.
- HEIF/HEIC EXIF extraction for backend-exposed date/time, orientation, camera and GPS fields.
- HEIF/HEIC XMP extraction for backend-exposed date, GPS and textual location fields.
- HEIF container audit fields in `inspect` reports, including selected primary image, found/missing metadata and date/location evidence.
- Optional JPEG preview generation for organized HEIC/HEIF files through `--heic-preview` or `preview.heic`.
- Synthetic HEIC corpus fixtures and tests for backend behavior, malformed input and preview generation.

### Changed

- Supported image formats include HEIC/HEIF extensions in the centralized format list.
- HEIC/HEIF files preserve their original extension in generated destination names.
- HEIF metadata uses the same date reconciliation and GPS normalization paths as JPEG, TIFF and PNG.
- Primary image selection in complex HEIF containers is deterministic.

### Fixed

- Missing HEIF native/backend dependencies now produce clear installation guidance.
- HEIF backend read errors, malformed HEIC files and preview failures are handled per file without stopping unrelated work.

## [0.5.0] - 2026-05-05

### Added

- Read-only `inspect`/`audit-metadata` command with JSON and CSV reports.
- Read-only `explain` command with JSON decision reports.
- Metadata provenance model with source, field, confidence and raw value.
- Date reconciliation model with all parsed candidates, selected candidate, conflict status, policy and reason.
- Reconciliation policies: `precedence`, `newest`, `oldest` and `filesystem`.
- Embedded XMP packet extraction and same-basename `.xmp` sidecar extraction.
- PNG metadata support for `eXIf`, `iTXt`, `tEXt`, `zTXt`, `tIME` and XMP text packets.
- IPTC-IIM extraction for date/time, city, state, country, title, author and description.
- Low-confidence date and location inference from sidecars, filenames, folders and sibling context.
- Correction manifests in CSV, JSON, YAML and YML with selectors for path, folder, glob, filename pattern and camera profile.
- Global `--clock-offset` and correction priority options.
- Synthetic metadata corpus covering success, absence and conflict scenarios.

### Changed

- Date resolution now uses an explicit metadata precedence matrix instead of a simple EXIF/mtime chain.
- Date decisions distinguish captured values from inferred values.
- Metadata conflicts keep all candidates for reports and debug output.
- Execution reports include date provenance, and location-aware reports include GPS/location provenance.
- XMP sidecar values override embedded XMP values within the XMP tier.
- PNG `tIME` is treated as a low-confidence modification timestamp.

### Fixed

- Pillow-specific EXIF values are serialized safely in explain JSON reports.
- Malformed XMP parse errors no longer interrupt metadata audits.
- Missing date metadata can be reported as expected absence when heuristics are disabled.
- Correction clock offsets preserve the original datetime in provenance.

## [0.4.0] - 2026-05-01

### Added

- External organization configuration files for JSON, YAML and YML.
- `--config PATH` for `organize`.
- Configurable output, naming pattern, destination pattern, organization strategy, operation mode, dry-run, plan and reverse geocoding behavior.
- Custom filename patterns through config and `--name-pattern`.
- Custom destination patterns with date and location fields.
- EXIF GPS extraction and reverse geocoding helper for city, state and country.
- Location-aware strategies: `location`, `location-date` and `city-state-month`.
- Location status and fallback tracking in planned operations, summaries and reports.

### Changed

- CLI-provided values take precedence over equivalent config values.
- Location-based strategies enable reverse geocoding unless explicitly disabled.
- PyYAML became a project dependency for YAML configuration support.

### Fixed

- Invalid filename and destination patterns now fail before planning with clear validation errors.
- Location strategies fall back to date-based organization when GPS is missing or reverse geocoding fails.
- Reverse geocoding network/service failures are handled as unresolved location data instead of aborting organization.

## [0.3.0] - 2026-04-28

### Added

- Deterministic file hashing with chunked reads.
- Safe hash comparison with `hmac.compare_digest`.
- Duplicate grouping by content hash.
- Read-only `dedupe` command with human-readable output.
- JSON and CSV duplicate reports.
- Additional supported extensions: `.tif`, `.tiff`, `.webp` and `.bmp`.
- Centralized image format configuration with per-format EXIF capability flags.
- Resilient per-file error handling for malformed EXIF, planning failures and hash failures.

### Changed

- Scanner and hash flows now share the centralized supported format list.
- EXIF extraction is attempted only for formats marked with real EXIF support.
- PNG, WEBP and BMP safely skip EXIF extraction and use date fallback behavior when needed.

### Fixed

- Malformed EXIF no longer interrupts metadata processing.
- A single problematic file no longer aborts organization planning or duplicate detection for remaining files.
- Different files are not reported as duplicates when content hashes differ.

## [0.2.0] - 2026-04-27

### Added

- Safe move execution that copies the destination first and removes the source only after success.
- Automatic destination directory creation.
- Deterministic filename collision suffixes such as `_01`, `_02` and `_03`.
- Execution summaries for processed, ignored, error and date-fallback counts.
- JSON and CSV audit report export with `--report`.
- Improved CLI help with examples and grouped `organize --help` arguments.
- Integration tests for planning and execution.

### Changed

- `organize` reports the effective destination after collision resolution.
- Move mode uses copy-then-remove behavior instead of direct move semantics.
- Date resolution exposes fallback information while preserving the datetime helper.
- CLI validation gives clearer errors for missing `--output` and unsupported report extensions.

### Fixed

- Existing destination files are no longer overwritten by default.
- Multiple operations targeting the same destination receive unique suffixes in the same batch.
- Dry-run reserves destination names consistently with real planning.
- Source files are preserved when a move operation fails before source removal.
- Copied destination artifacts are cleaned up when source removal fails during safe move.

## [0.1.0] - 2026-04-24

### Added

- Initial CLI entrypoint with root command support.
- `scan` command with recursive image discovery.
- `organize` command with date-based planning and execution.
- Root options `--version` and `--log-level`.
- Initial supported image extensions: `.jpg`, `.jpeg` and `.png`.
- EXIF extraction for compatible JPEG files.
- Best date resolution with `DateTimeOriginal`, `CreateDate` and filesystem `mtime` fallback.
- Deterministic default naming rule: `YYYY-MM-DD_HH-MM-SS.ext`.
- Date-based destination planner using `YYYY/MM/DD`.
- Operation modes `move`, `copy`, `dry-run` and `plan`.
- Structured logging setup.
- Initial automated tests for CLI, scanner, metadata, naming, planner and executor.

### Changed

- `organize` established the project flow: scan, metadata, naming, planning and execution/simulation.
- Logging reports lifecycle events and command counters.

### Fixed

- Invalid source directories produce friendly errors for `scan` and `organize`.
- Missing or unreadable EXIF is handled safely without breaking execution.
