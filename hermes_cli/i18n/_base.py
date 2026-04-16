from __future__ import annotations

import locale
from typing import Any, Literal

from .en import STRINGS as EN_STRINGS
from .zh import STRINGS as ZH_STRINGS

Locale = Literal["en", "zh"]

_SUPPORTED: dict[str, dict[str, Any]] = {
    "en": EN_STRINGS,
    "zh": ZH_STRINGS,
}

_active_locale: Locale | None = None


def _normalize_locale(value: str | None) -> Locale:
    text = (value or "").strip().lower().replace("-", "_")
    if not text:
        return "en"
    if text == "zh" or text.startswith("zh_"):
        return "zh"
    return "en"


def _read_configured_language() -> str:
    try:
        from hermes_cli.config import read_raw_config

        cfg = read_raw_config()
    except Exception:
        return ""

    if isinstance(cfg, dict):
        value = cfg.get("language", "")
        return str(value or "").strip()
    return ""


def _detect_locale() -> Locale:
    configured = _read_configured_language()
    if configured:
        return _normalize_locale(configured)

    try:
        system_locale = locale.getdefaultlocale()[0]
    except Exception:
        system_locale = None
    return _normalize_locale(system_locale)


def get_locale() -> Locale:
    global _active_locale
    if _active_locale is None:
        _active_locale = _detect_locale()
    return _active_locale


def set_locale(lang: str) -> Locale:
    global _active_locale
    _active_locale = _normalize_locale(lang)
    return _active_locale


def _resolve_key(strings: dict[str, Any], key: str) -> Any:
    current: Any = strings
    for part in key.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


def t(key: str, **kwargs: Any) -> str:
    try:
        locale_code = get_locale()
        localized = _resolve_key(_SUPPORTED.get(locale_code, EN_STRINGS), key)
        if localized is None:
            localized = _resolve_key(EN_STRINGS, key)
        if localized is None:
            return key
        text = str(localized)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text
    except Exception:
        return key
