"""Evidence produced by the workers must validate against the shared contract."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.contracts import Evidence  # noqa: E402

from workers.evidence import collect  # noqa: E402


def test_live_page_matches_contract():
    evidence = Evidence.model_validate(collect("http://github.com/login"))
    assert evidence.final_url == "https://github.com/login"
    assert evidence.screenshot_path and not evidence.screenshot_path.startswith("/")
    assert any("password" in form.input_types for form in evidence.forms)
    assert evidence.rdap and evidence.rdap.created
    assert evidence.hosting_org


def test_offline_domain_matches_contract():
    evidence = Evidence.model_validate(collect("https://adcb-secure-login-xyz-404.com/"))
    assert evidence.fetch_error and evidence.http_status is None


def test_private_address_is_blocked():
    evidence = Evidence.model_validate(collect("http://10.0.0.1/"))
    assert "non-public" in evidence.fetch_error
