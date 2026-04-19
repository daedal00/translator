"""
Detects Bible verse references in transcribed text and fetches verse content.
Caches all lookups — verse text is immutable.
"""
import re

import httpx

from app.core.config import settings

# fmt: off
_BOOK_NAMES = (
    "Genesis|Gen|Exodus|Exod|Ex|Leviticus|Lev|Numbers|Num|Deuteronomy|Deut|Dt"
    "|Joshua|Josh|Judges|Judg|Ruth|1 Samuel|1Sam|2 Samuel|2Sam|1 Kings|1Kgs"
    "|2 Kings|2Kgs|1 Chronicles|1Chr|2 Chronicles|2Chr|Ezra|Nehemiah|Neh"
    "|Esther|Job|Psalms|Psalm|Ps|Proverbs|Prov|Ecclesiastes|Eccl|Song of Solomon"
    "|Song|Isaiah|Isa|Jeremiah|Jer|Lamentations|Lam|Ezekiel|Ezek|Daniel|Dan"
    "|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Mic|Nahum|Habakkuk|Hab|Zephaniah|Zeph"
    "|Haggai|Hag|Zechariah|Zech|Malachi|Mal"
    "|Matthew|Matt|Mark|Luke|John|Acts|Romans|Rom"
    "|1 Corinthians|1Cor|2 Corinthians|2Cor|Galatians|Gal|Ephesians|Eph"
    "|Philippians|Phil|Colossians|Col|1 Thessalonians|1Thess|2 Thessalonians|2Thess"
    "|1 Timothy|1Tim|2 Timothy|2Tim|Titus|Philemon|Hebrews|Heb|James|Jas"
    "|1 Peter|1Pet|2 Peter|2Pet|1 John|1Jn|2 John|2Jn|3 John|3Jn|Jude|Revelation|Rev"
)
# fmt: on

_VERSE_RE = re.compile(
    rf"(?P<book>(?:[123] )?(?:{_BOOK_NAMES}))\s+(?P<chapter>\d+)[:.](?P<verse>\d+)(?:-(?P<end_verse>\d+))?",
    re.IGNORECASE,
)

_BIBLE_IDS = {
    "NIV": "78a9f6124f344018-01",
    "ESV": "f421fe261da7624f-01",
    "KJV": "de4e12af7f28f599-02",
    "NLT": "1713df4e49a22f54-01",
    "NASB": "c315fa9f71d4af3d-01",
}

# Immutable verse text — cache indefinitely, capped to avoid unbounded growth
_verse_cache: dict[tuple, str | None] = {}
_VERSE_CACHE_MAX = 4096


def find_reference(text: str) -> re.Match | None:
    return _VERSE_RE.search(text)


async def _fetch_verse(bible_id: str, book: str, chapter: str, verse: str, end_verse: str | None) -> str | None:
    key = (bible_id, book, chapter, verse, end_verse)
    if key in _verse_cache:
        return _verse_cache[key]

    url = f"https://api.scripture.api.bible/v1/bibles/{bible_id}/passages/{book}.{chapter}.{verse}"
    params = {"content-type": "text", "include-notes": "false", "include-titles": "false"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url, params=params, headers={"api-key": settings.bible_api_key})
            r.raise_for_status()
            content = r.json()["data"]["content"].strip()
    except Exception:
        content = None

    if len(_verse_cache) >= _VERSE_CACHE_MAX:
        _verse_cache.clear()
    _verse_cache[key] = content
    return content


async def get_verse(text: str, translation: str = "KJV") -> dict | None:
    """Return verse data if text contains a Bible reference, else None."""
    match = find_reference(text)
    if not match:
        return None

    bible_id = _BIBLE_IDS.get(translation.upper(), _BIBLE_IDS["KJV"])
    content = await _fetch_verse(
        bible_id,
        match.group("book").replace(" ", ""),
        match.group("chapter"),
        match.group("verse"),
        match.group("end_verse"),
    )
    if not content:
        return None

    ref = f"{match.group('book')} {match.group('chapter')}:{match.group('verse')}"
    if match.group("end_verse"):
        ref += f"-{match.group('end_verse')}"

    return {"reference": ref, "text": content, "translation": translation}
