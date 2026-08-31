"""Tests for fanuc._i18n.

_detect_chinese() only runs once, at import time, against whatever the
test process's own environment actually is; that naturally exercises
just one branch. To hit the others, call it directly with the
environment monkeypatched instead of relying on process startup.
"""

from __future__ import annotations

from fanuc._i18n import _detect_chinese, bi


def _clear_locale_vars(monkeypatch):
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)


def test_detect_chinese_from_env_var(monkeypatch):
    _clear_locale_vars(monkeypatch)
    monkeypatch.setenv("LANG", "zh_TW.UTF-8")
    assert _detect_chinese() is True


def test_detect_english_from_env_var(monkeypatch):
    _clear_locale_vars(monkeypatch)
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert _detect_chinese() is False


def test_env_var_precedence_order(monkeypatch):
    # LANGUAGE beats LC_ALL/LC_MESSAGES/LANG even when they disagree.
    _clear_locale_vars(monkeypatch)
    monkeypatch.setenv("LANGUAGE", "en_US")
    monkeypatch.setenv("LANG", "zh_CN.UTF-8")
    assert _detect_chinese() is False


def test_falls_back_to_os_locale_when_no_env_vars(monkeypatch):
    _clear_locale_vars(monkeypatch)
    monkeypatch.setattr("locale.getlocale", lambda: ("zh_TW", "UTF-8"))
    assert _detect_chinese() is True


def test_os_locale_matches_on_the_word_chinese_too(monkeypatch):
    _clear_locale_vars(monkeypatch)
    monkeypatch.setattr("locale.getlocale", lambda: ("Chinese (Traditional)_Taiwan", "950"))
    assert _detect_chinese() is True


def test_os_locale_error_falls_through_to_default(monkeypatch):
    _clear_locale_vars(monkeypatch)

    def _boom():
        raise ValueError("unsupported locale setting")

    monkeypatch.setattr("locale.getlocale", _boom)
    # no env vars, locale.getlocale() itself blows up: nothing usable
    # to go on, defaults to Chinese.
    assert _detect_chinese() is True


def test_no_signal_at_all_defaults_to_chinese(monkeypatch):
    _clear_locale_vars(monkeypatch)
    monkeypatch.setattr("locale.getlocale", lambda: (None, None))
    assert _detect_chinese() is True


def test_bi_picks_chinese_when_flag_is_true(monkeypatch):
    monkeypatch.setattr("fanuc._i18n._IS_CHINESE", True)
    assert bi("中文", "english") == "中文"


def test_bi_picks_english_when_flag_is_false(monkeypatch):
    monkeypatch.setattr("fanuc._i18n._IS_CHINESE", False)
    assert bi("中文", "english") == "english"
