# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic versioning.

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
