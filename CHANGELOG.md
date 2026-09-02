# Changelog

All notable changes to this project are documented here. Format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Downloads badge switched from `img.shields.io/pypi/dm/fanuc-python`
  (pypistats.org-backed) to `static.pepy.tech/badge/fanuc-python`: the
  shields.io badge intermittently shows "rate limited by upstream
  service" instead of a number, a recurring characteristic of that
  badge source, not something specific to this project. pepy.tech now
  has the package indexed (it didn't yet the first time this was
  tried, right after the initial release).

## [1.1.5] - 2026-09-02

### Added

- `examples/patrol_route.py` (and the Traditional Chinese version in
  `examples/chinese/`): a complete multi-point patrol loop built
  directly in code, relative to wherever the robot currently is,
  using `move_joint()`/`move_pose()` with CNT blending between
  waypoints and one linear Cartesian leg, distinct from
  `move_sequence.py`'s file-driven waypoint runner.
- `PRIO-230 Ethernet Adapter error` documented in
  `docs/controller-setup/prerequisites.md` (and the Chinese version):
  what to check (R648 actually installed, the controller's Ethernet
  interface/IP configured on real hardware, a stale connection still
  holding the port), and that it's a controller-side prerequisite
  issue, not something either driver's KAREL code can fix.
- `CITATION.cff` at the repo root, so GitHub renders a "Cite this
  repository" button; a "Citing this project" section with the same
  information as BibTeX in both READMEs.
- A note in both READMEs, right after the "inspired by" citations,
  pointing out that `driver/` is primarily derived from
  [fanucpy](https://github.com/torayeff/fanucpy)'s MAPPDK driver and
  linking to [NOTICE](NOTICE) for the file-by-file account of what
  changed. `NOTICE` itself now also documents the `STRING[1]` ->
  `STRING[254]` fix as a modification, which had been missing from it.

### Fixed

- `driver/mappdk_server.kl`'s `uframe_str`/`tool_str` were declared as
  `STRING[1]`, one character too small for `CNV_INT_STR`'s
  space-padded output; a single-digit frame/tool number (the ER-4iA's
  own default `UFRAMENUM 8`, `TOOLNUM 1` included) already overflowed
  the buffer, silently truncating it and breaking the `GET_VAR` calls
  that are supposed to refresh `$UFRAME`/`$UTOOL` after selecting a
  non-default frame. Widened to `STRING[254]`, matching every other
  `CNV_INT_STR` output buffer in the driver, so raising `UFRAMENUM`/
  `TOOLNUM` past a single digit for a different robot can't reopen the
  same overflow. Same bug reported against
  upstream fanucpy
  ([torayeff/fanucpy#30](https://github.com/torayeff/fanucpy/issues/30)),
  and likely the cause of a related symptom reported there too
  ([torayeff/fanucpy#28](https://github.com/torayeff/fanucpy/issues/28):
  `get_curpos()` not matching the TP display after selecting a
  non-default UFRAME). Recompiled `driver/upload/mappdk_server.pc`
  with ktrans V9.40 (matching the version this project's driver has
  always compiled with); `mappdk_logger.kl` doesn't set `$UFRAME`/
  `$UTOOL` at all and wasn't affected, so `mappdk_logger.pc` didn't
  need recompiling for this fix. Verified: after selecting a
  non-default UFRAME, `get_curpos()` now matches the TP display.

## [1.1.4] - 2026-08-31

Renamed the PyPI distribution from `fanuc` to `fanuc-python`, to avoid
using FANUC Corporation's bare trademark as a standalone package name
and match the naming convention every other FANUC-related PyPI
package already follows (`fanucpy`, `pyfanuc`, `UnderAutomation.Fanuc`).
Nothing else changes: same repository, same source, same import name
`fanuc`, same CLI command `fanuc`; only the name you `pip install`
changes.

A final `1.1.4` was briefly published under the old `fanuc` name as a
goodbye notice pointing here; that PyPI project has since been deleted
entirely rather than left as a stub, so `pip install fanuc` no longer
resolves to anything. See
[fanuc-python on PyPI](https://pypi.org/project/fanuc-python/) for all
releases from here on.

### Added

- `unofficial`/`third-party` keywords in `pyproject.toml`, alongside
  the existing disclaimer, to make the non-affiliation clear wherever
  the package is discovered, not just on the README.
- Expanded the ROBOGUIDE-first warning and moved it up to right below
  the disclaimer, at the very top of both READMEs: built-in
  safeguards (the `--confirm` gate, legality checks) should prevent
  most accidents under ordinary conditions, but certain conditions or
  configurations can still produce unexpected behavior, so testing on
  a virtual controller before pointing at real hardware is strongly
  recommended.

## [1.1.3] - 2026-08-31

### Added

- A disclaimer at the top of both READMEs stating this is an
  independent third-party project with no affiliation to, sponsorship
  from, or endorsement by FANUC CORPORATION.

## [1.1.2] - 2026-08-31

### Changed

- READMEs now tell end users to `pip install fanuc` (and
  `pip install "fanuc[complete]"` for shell TAB completion), not
  `pip install -e .`, now that the package is actually on PyPI. The
  editable/dev install is kept as a separate note for contributors
  working from a repo clone.

## [1.1.1] - 2026-08-31

### Added

- A PyPI downloads badge in both READMEs.

### Fixed

- `README.md`/`README.zh.md`'s architecture diagram used a relative
  path (`media/CommProtocol.svg`), which only renders on GitHub's own
  repo page; PyPI's project page (which renders `README.md` as the
  package description) couldn't display it. Switched to an absolute
  `raw.githubusercontent.com` URL, which works wherever the README is
  displayed. This release exists specifically to get that fix (and
  the downloads badge) onto PyPI's project page, since PyPI freezes
  the README at whatever it was when a version was published and
  doesn't pick up later changes to the same version.

## [1.1.0] - 2026-08-31

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
  coverage locally.
- CI now installs the `complete` extra (`pip install -e ".[dev,complete]"`)
  so `argcomplete` is actually present there too. Without it, CI's
  environment never exercised `cli.py`'s "argcomplete is installed"
  branch the way local runs did, so Codecov reported 98.91% for
  `cli.py` even though local coverage said 100%; installing the extra
  in CI closes that gap for real instead of just locally.

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

Where the project stood right after the first commit. Never actually
tagged or published; folded straight into 1.1.0, the first real PyPI
release. Kept here for the record of what that snapshot looked like.

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

[Unreleased]: https://github.com/Kevin28576/fanuc/compare/v1.1.5...HEAD
[1.1.5]: https://github.com/Kevin28576/fanuc/compare/v1.1.4...v1.1.5
[1.1.4]: https://github.com/Kevin28576/fanuc/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/Kevin28576/fanuc/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/Kevin28576/fanuc/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/Kevin28576/fanuc/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/Kevin28576/fanuc/releases/tag/v1.1.0
[1.0.0]: https://github.com/Kevin28576/fanuc/compare/7351db2...545003e
