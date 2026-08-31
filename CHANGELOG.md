# Changelog

All notable changes to this project are documented here. Format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- CI now runs on every push/PR (`.github/workflows/ci.yml`), separate
  from the release-only publish workflow, with test coverage reported
  to Codecov.
- A prominent security note (no authentication or encryption in the
  MAPPDK wire protocol) in both READMEs and `docs/protocol.md`, plus a
  step-by-step guide for moving off the default ports in
  `docs/controller-setup/server-tags.md`.
- `CHANGELOG.md` (this file), linked from both READMEs.
- `tests/test_cli.py`: offline tests for the `fanuc` command-line tool
  (connect/pos/watch/io/move/call/reg/din/chkjnt/chkpos/power/status,
  plus `main()`'s exception handling), bringing `cli.py`'s test
  coverage from 0% to 98% and the project total from 54% to 77%.

### Fixed

- `MotionTracer`'s background polling thread only caught `FanucError`;
  any other exception (a bug, or in one case a test double running
  dry) crashed the thread with an uncaught traceback printed to
  stderr instead of surfacing through `stop()` like every other
  failure mode. Broadened to catch any exception.
- TP menu names quoted throughout `docs/controller-setup/` were
  Simplified Chinese; the actual controller's TP is Traditional
  Chinese. Converted every quote (character form only, no vocabulary
  changes). The English documentation tree had the same Chinese menu
  quotes embedded inline instead of English labels; translated those
  to their standard FANUC English equivalents (flagged as unverified
  against a real English-mode TP screen, since verifying that needs
  hardware access this project doesn't currently have).

## [1.0.0] - 2026-08-31

Initial public release.

### Added

- Python client (`src/fanuc/`) for the MAPPDK KAREL driver: reading
  and writing position, joint angles, registers, digital I/O; gripper
  control (single- and dual-signal); motion commands; running TP
  programs; reading alarm state; a `RobotApp` task framework;
  `MotionTracer` for recording a trajectory via the S7/logger
  connection while a move is in flight.
- `fanuc` command-line tool (`fanuc pos`, `watch`, `io`, `reg`, `move`,
  `call`, `status`, `connect`, ...), with optional shell TAB completion.
- Extended KAREL driver (`driver/`) adding 15 commands beyond the
  original upstream driver's 12 (register/position-register/
  string-register/joint-position-register access, alarm reading,
  joint/pose legality checks, numeric system variables), all verified
  on real hardware (FANUC ER-4iA + R-30iB Mate Plus).
- Bilingual documentation: English (`README.md`, `docs/`) and
  Traditional Chinese (`README.zh.md`, `docs/zh/`), plus English and
  Chinese versions of every example script (`examples/`,
  `examples/chinese/`).
- PyPI publishing via GitHub Actions using OIDC trusted publishing, no
  stored token.
- `py.typed` marker; the whole `src/fanuc/` package passes
  `mypy --strict`.

[Unreleased]: https://github.com/Kevin28576/fanuc/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Kevin28576/fanuc/releases/tag/v1.0.0
