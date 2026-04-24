# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic versioning.

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
