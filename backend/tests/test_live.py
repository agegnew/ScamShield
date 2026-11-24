"""Real-network checks of the fetcher and enrichment (Simon's contract tests).

Skipped by default. Run with:  pytest -m live   (needs internet and `playwright install chromium`)
"""

import pytest

from app.contracts import Evidence
from app.workers.enrich import enrich
from app.workers.fetcher import fetch

pytestmark = pytest.mark.live


def collect(url: str) -> Evidence:
    return enrich(fetch(url))


def test_live_page_matches_contract():
    evidence = collect("http://github.com/login")
    assert evidence.final_url == "https://github.com/login"
    assert evidence.screenshot_path and not evidence.screenshot_path.startswith("/")
    assert any("password" in form.input_types for form in evidence.forms)
    assert evidence.rdap and evidence.rdap.created
    assert evidence.hosting_org


def test_offline_domain_matches_contract():
    evidence = collect("https://adcb-secure-login-xyz-404.com/")
    assert evidence.fetch_error and evidence.http_status is None


def test_private_address_is_blocked():
    evidence = collect("http://10.0.0.1/")
    assert "non-public" in evidence.fetch_error
