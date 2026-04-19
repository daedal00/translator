from app.pipeline.verses import find_reference


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
