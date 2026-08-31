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
- `tests/test_transport.py`: tests for `MappdkTransport`, using both a
  real loopback TCP server and a hand-rolled fake socket for the error
  paths that are impractical to provoke reliably over a real socket
  (timeout, peer close, a response that never terminates), bringing
  `transport.py`'s test coverage from 25% to 94%.
- `tests/test_robot.py`: offline tests for `FanucRobot`'s command
  construction and response parsing (connect/disconnect, motion,
  registers, I/O, the extended-driver-only commands, the joint/pose
  legality checks, the end-effector edge cases), mocking `_send`
  directly rather than needing a real controller. Brought `robot.py`'s
  test coverage from 53% to 94%.
- `tests/test_i18n.py`: tests for `_detect_chinese()`'s language
  detection (env var precedence, OS locale fallback, the
  no-usable-signal default) and `bi()`, calling `_detect_chinese()`
  directly with the environment monkeypatched since it otherwise only
  ever runs once, at import time, against whatever the process's own
  environment happens to be. Brought `_i18n.py`'s test coverage from
  75% to 100%.
- Added targeted tests closing the remaining gaps in `protocol.py`,
  `robot.py`, `app.py`, `types.py`, `transport.py`, `cli.py`, and
  `__main__.py`: every previously-uncovered validation branch,
  parsing error path, sequence-protocol dunder, and the two module
  entry-point guards (exercised in-process via `runpy` rather than a
  subprocess, so coverage.py can see them). `cli.py`'s
  `argcomplete`-not-installed branch is tested by forcing the import
  to fail with `sys.modules["argcomplete"] = None` and reloading the
  module. Brought the project total from 94% to 100% line and branch
  coverage.

### Fixed

- `transport.py`'s response reassembly had a latent bug: once a
  response that arrived split across two TCP packets was confirmed
  complete after draining the trailing bytes, the code fell through to
  another blocking `recv()` instead of returning right away. In real
  usage the peer has nothing more to send at that point, so this would
  have hung until the socket timeout. Found while writing
  `tests/test_transport.py`'s split-packet regression test, which is
  the first test in this project to actually exercise that code path;
  fixed by re-checking completeness against the drained data before
  falling through to another read.
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
