"""Simon's discovery code: brand matching, radars and page parsing, without the network."""

from app.brand_match import match_brand
from app.brands import brand_by_id
from app.contracts import Source
from app.workers import fetcher
from app.workers.radar import ct, lookalikes, maps, search


def test_brand_match_needs_context_for_short_names():
    assert match_brand("tamm-fines-pay.xyz") == "tamm"
    assert match_brand("rta-fines.com") == "rta"
    assert match_brand("tammy-shop.com") is None
    assert match_brand("portal-shop.com") is None


def test_brand_match_long_tokens_match_anywhere():
    assert match_brand("emiratesnbd-help.com") == "emiratesnbd"
    assert match_brand("secure-adpolice-pay.online") == "adpolice"


def test_official_domains_never_match():
    assert match_brand("www.tamm.abudhabi") is None
    assert match_brand("emiratesnbd.com") is None


def test_lookalike_variants_skip_official_and_include_bait_combos():
    variants = lookalikes.generate(brand_by_id("tamm"))
    assert "tamm-pay.com" in variants and variants["tamm-pay.com"] == "combo"
    assert "tamm.abudhabi" not in variants
    assert not any(how == "typo" for how in variants.values())  # 'tamm' is too short for typos


def test_ct_keeps_recent_brand_certificates_only():
    rows = [
        {"not_before": "2026-11-20T00:00:00", "name_value": "*.uaepass-verify.online\nmail.example.com", "id": 1},
        {"not_before": "2025-01-01T00:00:00", "name_value": "uaepass-old.com", "id": 2},
        {"not_before": "2026-11-21T00:00:00", "name_value": "www.uaepass.ae", "id": 3},
    ]
    hosts = ct.hosts_from(rows, since="2026-10-25T00:00:00")
    assert list(hosts) == ["uaepass-verify.online"]
    assert hosts["uaepass-verify.online"]["brand"] == "uaepass"


def test_maps_flags_listing_with_unofficial_helpline(monkeypatch):
    answer = {
        "local_results": [
            {"title": "Emirates NBD Customer Service 24/7", "phone": "04 555 0199", "place_id": "abc"},
            {"title": "Emirates NBD Branch", "phone": "600 54 0000", "place_id": "ok1",
             "website": "https://www.emiratesnbd.com/"},
        ]
    }
    monkeypatch.setattr(maps, "serpapi", lambda params: answer)
    found = maps.listings(brand_by_id("emiratesnbd"))
    assert len({c.url for c in found}) == 1
    listing = found[0]
    assert listing.source == Source.MAPS
    assert listing.extra.phone == "+97145550199"
    assert listing.extra.details["flags"] == ["helpline_not_official"]
    assert "maps/place" in listing.url


def test_search_skips_official_and_news_and_marks_replayed(monkeypatch):
    answer = {
        "_replayed": True,
        "ads": [{"link": "https://pay-fines-uae.online/", "title": "Pay fines", "position": 1}],
        "organic_results": [
            {"link": "https://www.tamm.abudhabi/fines"},
            {"link": "https://gulfnews.com/uae/fine-scam"},
            {"link": "https://tamm-fines-pay.xyz/"},
        ],
    }
    monkeypatch.setattr(search, "serpapi", lambda params: answer)
    found = search.google("pay traffic fine abu dhabi", "en", None)
    assert [c.url for c in found] == ["https://pay-fines-uae.online/", "https://tamm-fines-pay.xyz/"]
    assert found[0].source == Source.SEARCH_AD
    assert found[1].extra.brand == "tamm"
    assert all(c.extra.details["replayed"] for c in found)


def test_fetcher_classifies_sensitive_fields():
    forms = fetcher.summarize_forms(
        [{"action": "/pay", "inputs": [
            {"type": "text", "hint": "cardnumber card number"},
            {"type": "password", "hint": "otp"},
            {"type": "text", "hint": "emirates id 784-"},
        ]}],
        "https://scam.test/checkout",
    )
    assert forms[0].action == "https://scam.test/pay"
    assert forms[0].sensitive == ["card", "emirates_id", "password"]


def test_fetcher_spots_remote_access_and_apk_links():
    signals = fetcher.download_signals(
        [{"href": "https://anydesk.com/download", "text": "Download AnyDesk"},
         {"href": "https://x.test/bank.apk", "text": "Install"},
         {"href": "https://x.test/about", "text": "About"}],
        "Please install TeamViewer QuickSupport",
    )
    assert [s.kind for s in signals] == ["remote_access_link", "app_download_link", "remote_access_text"]


def test_fetcher_ignores_generic_remote_access_wording():
    assert fetcher.download_signals([], "Real-time alerts with instant remote access") == []
    assert fetcher.download_signals([], "Install AnyDesk and send us the code")[0].kind == "remote_access_text"


def test_fetcher_labels_placeholder_pages():
    cases = {
        ("http://a.site/", "Parked Domain name on Hostinger DNS system", ""): "parked",
        ("https://forsale.godaddy.com/forsale/x.xyz", "", ""): "for_sale",
        ("http://a.com/", "Access Denied", ""): "blocked",
        ("http://a.com/", "Not Found", "404 Not Found"): "error",
        ("http://a.com/", "", "THIS SITE IS BRAND NEW PLEASE CHECK BACK"): "coming_soon",
        ("http://a.com/", "", ""): "empty",
        ("https://moi-portal.com/", "Ministry of Interior — Official Verification Portal",
         "MINISTRY OF INTERIOR Official Government Portal Verify a document"): "content",
    }
    for (url, title, text), kind in cases.items():
        assert fetcher.page_kind(url, title, text) == kind, (url, title)
