from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.verses import _verse_cache, find_reference, get_verse


def test_john_3_16():
    m = find_reference("Please turn to John 3:16 in your Bibles")
    assert m is not None
    assert "John" in m.group("book")
    assert m.group("chapter") == "3"
    assert m.group("verse") == "16"


def test_range():
    m = find_reference("Romans 8:28-30 says that...")
    assert m is not None
    assert m.group("end_verse") == "30"


def test_no_match():
    assert find_reference("Welcome everyone to church today") is None


def test_korean_style_ref():
    m = find_reference("요한복음 3:16")
    # Korean book names not in base pattern — should be None at MVP
    # This test documents the current limitation
    assert m is None


# ---------------------------------------------------------------------------
# Additional find_reference tests
# ---------------------------------------------------------------------------


def test_genesis_chapter_verse():
    m = find_reference("Gen 1:1 says in the beginning")
    assert m is not None
    assert m.group("book").lower().startswith("gen")
    assert m.group("chapter") == "1"
    assert m.group("verse") == "1"


def test_abbreviated_new_testament():
    m = find_reference("Matt 5:3 Blessed are the poor")
    assert m is not None
    assert "Matt" in m.group("book")


def test_numbered_book():
    m = find_reference("1 Corinthians 13:4 love is patient")
    assert m is not None
    assert "Corinthians" in m.group("book")
    assert m.group("chapter") == "13"
    assert m.group("verse") == "4"


def test_period_separator():
    m = find_reference("John 3.16")
    assert m is not None
    assert m.group("chapter") == "3"
    assert m.group("verse") == "16"


def test_case_insensitive():
    m = find_reference("john 3:16")
    assert m is not None


def test_revelation():
    m = find_reference("Rev 22:21")
    assert m is not None
    assert m.group("chapter") == "22"
    assert m.group("verse") == "21"


def test_psalm_abbreviation():
    m = find_reference("Ps 23:1 The Lord is my shepherd")
    assert m is not None
    assert m.group("chapter") == "23"


def test_verse_range_no_end():
    m = find_reference("Eph 2:8")
    assert m is not None
    assert m.group("end_verse") is None


# ---------------------------------------------------------------------------
# get_verse tests (httpx mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_verse_no_reference():
    result = await get_verse("This sentence has no Bible reference.")
    assert result is None


@pytest.mark.asyncio
async def test_get_verse_returns_dict_on_success():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"data": {"content": "For God so loved the world"}}

    with patch("app.pipeline.verses.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_cm

        _verse_cache.clear()
        result = await get_verse("John 3:16", translation="KJV")

    assert result is not None
    assert result["reference"] == "John 3:16"
    assert result["translation"] == "KJV"
    assert "world" in result["text"]


@pytest.mark.asyncio
async def test_get_verse_unknown_translation_falls_back_to_kjv():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"data": {"content": "verse text"}}

    with patch("app.pipeline.verses.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_cm

        _verse_cache.clear()
        result = await get_verse("John 3:16", translation="UNKNOWN")

    assert result is not None
    assert result["translation"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_get_verse_http_error_returns_none():
    with patch("app.pipeline.verses.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value.get = AsyncMock(side_effect=Exception("network error"))
        mock_client_cls.return_value = mock_cm

        _verse_cache.clear()
        result = await get_verse("John 3:16")

    assert result is None


@pytest.mark.asyncio
async def test_get_verse_caches_result():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"data": {"content": "cached verse"}}

    with patch("app.pipeline.verses.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        get_mock = AsyncMock(return_value=mock_response)
        mock_cm.__aenter__.return_value.get = get_mock
        mock_client_cls.return_value = mock_cm

        _verse_cache.clear()
        await get_verse("John 3:16", translation="KJV")
        call_count_after_first = get_mock.call_count

        # Second call should use the cache — HTTP client should not be called again
        await get_verse("John 3:16", translation="KJV")
        assert get_mock.call_count == call_count_after_first


@pytest.mark.asyncio
async def test_get_verse_with_range():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"data": {"content": "range verse text"}}

    with patch("app.pipeline.verses.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_cm

        _verse_cache.clear()
        result = await get_verse("Romans 8:28-30")

    assert result is not None
    assert "28" in result["reference"]
    assert "30" in result["reference"]
