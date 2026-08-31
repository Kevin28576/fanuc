"""Runtime language detection for user-facing messages.

Anything shown to the user (exception messages, CLI output, logs) goes
through :func:`bi`, which picks *one* of the two strings based on the
current environment's language, not both. Docstrings and source
comments are English and don't use this.

Detection order: LANGUAGE, LC_ALL, LC_MESSAGES, LANG environment
variables (POSIX convention, checked first since they're explicit),
then the OS locale. Falls back to Chinese if nothing says otherwise,
since that's this project's own language.
"""

from __future__ import annotations

import locale
import os


def _detect_chinese() -> bool:
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value:
            return "zh" in value.lower()

    try:
        lang_code, _ = locale.getlocale()
    except (ValueError, TypeError):
        lang_code = None

    if lang_code:
        return "zh" in lang_code.lower() or "chinese" in lang_code.lower()

    # No usable signal either way; default to Chinese, this project's
    # own language.
    return True


#: Decided once at import time. A process's language doesn't change
#: mid-run, so there's no need to re-detect on every call.
_IS_CHINESE = _detect_chinese()


def bi(zh: str, en: str) -> str:
    return zh if _IS_CHINESE else en
