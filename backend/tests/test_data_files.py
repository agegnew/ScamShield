"""Guards the hand-edited data files: a broken brands.json or scam_themes.json fails CI."""

from scripts.validate_data import check_brands, check_themes


def test_brands_file_is_valid():
    problems, _ = check_brands()
    assert problems == []


def test_scam_themes_file_is_valid():
    problems, _ = check_themes()
    assert problems == []
