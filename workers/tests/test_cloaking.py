from workers.cloaking import compare


def page(status="ok", final_url="https://a-fines.com/", title="Pay fine", sensitive=(), dhash="0" * 16):
    return {"status": status, "final_url": final_url, "title": title,
            "forms": [{"sensitive": list(sensitive)}], "fingerprints": {"screenshot_dhash": dhash}}


def test_same_page_has_no_signal():
    assert compare(page(), page()) == []


def test_cloaked_scam_is_flagged():
    mobile = page(sensitive=["card", "otp"], dhash="ffffffffffffffff")
    desktop = page(final_url="https://www.google.com/", title="Google", dhash="0000000000000000")
    assert compare(mobile, desktop) == ["different_destination", "forms_hidden_from_desktop", "different_page"]


def test_desktop_blocked():
    assert compare(page(), page(status="error")) == ["desktop_blocked"]
