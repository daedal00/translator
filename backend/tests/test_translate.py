"""
Tests for the translation pipeline.

NLLBTranslator internals rely on optional ML dependencies (ctranslate2,
transformers) which are stubbed out in conftest.py.  We test the pure-Python
logic paths that do not require a real model.
"""
import threading

import pytest

from app.pipeline.translate import LANG_CODES, NLLBTranslator


# ---------------------------------------------------------------------------
# LANG_CODES dictionary
# ---------------------------------------------------------------------------


def test_lang_codes_contains_common_languages():
    for lang in ("en", "ko", "es", "zh", "fr", "de", "pt", "ar", "vi", "tl"):
        assert lang in LANG_CODES, f"Expected '{lang}' in LANG_CODES"


def test_lang_codes_flores_format():
    """FLORES-200 codes follow the pattern <iso>_<Script>."""
    for code in LANG_CODES.values():
        assert "_" in code, f"Unexpected FLORES code format: {code}"


def test_english_flores_code():
    assert LANG_CODES["en"] == "eng_Latn"


def test_korean_flores_code():
    assert LANG_CODES["ko"] == "kor_Hang"


# ---------------------------------------------------------------------------
# NLLBTranslator pure-Python paths (no real model needed)
# ---------------------------------------------------------------------------


def _make_translator() -> NLLBTranslator:
    """Construct a NLLBTranslator without loading real model weights."""
    t = object.__new__(NLLBTranslator)
    t._cache = {}
    t._lock = threading.Lock()
    # _tokenizer and _translator are irrelevant for the paths we test
    return t


@pytest.mark.asyncio
async def test_translate_same_language_returns_input():
    t = _make_translator()
    result = await t.translate("hello world", "en", "en")
    assert result == "hello world"


@pytest.mark.asyncio
async def test_translate_same_language_skips_cache_write():
    t = _make_translator()
    await t.translate("no cache", "ko", "ko")
    assert len(t._cache) == 0


def test_translate_sync_unknown_source_returns_input():
    t = _make_translator()
    result = t._translate_sync("untouched", "xx", "en")
    assert result == "untouched"


def test_translate_sync_unknown_target_returns_input():
    t = _make_translator()
    result = t._translate_sync("untouched", "en", "zz")
    assert result == "untouched"


def test_translate_sync_both_unknown_returns_input():
    t = _make_translator()
    result = t._translate_sync("untouched", "xx", "zz")
    assert result == "untouched"


@pytest.mark.asyncio
async def test_translate_cache_eviction():
    """When cache is full, it is cleared and the new result is stored."""
    from app.pipeline.translate import _CACHE_MAX

    t = _make_translator()
    # Fill the cache to capacity with dummy entries
    for i in range(_CACHE_MAX):
        t._cache[(f"text{i}", "en", "ko")] = f"trans{i}"

    # translate() with same language returns immediately (no cache write),
    # so use _translate_sync with unknown codes to test the eviction branch
    # via the async path by stubbing _translate_sync.
    original_sync = t._translate_sync
    t._translate_sync = lambda text, src, tgt: "result"

    result = await t.translate("new text", "en", "ko")
    assert result == "result"
    # Cache should have been cleared and only the new entry stored
    assert len(t._cache) == 1
    assert t._cache[("new text", "en", "ko")] == "result"

    t._translate_sync = original_sync


@pytest.mark.asyncio
async def test_translate_returns_cached_result():
    t = _make_translator()
    t._cache[("hello", "en", "ko")] = "cached_translation"

    original_sync = t._translate_sync
    t._translate_sync = lambda *a: "should_not_be_called"

    result = await t.translate("hello", "en", "ko")
    assert result == "cached_translation"

    t._translate_sync = original_sync
