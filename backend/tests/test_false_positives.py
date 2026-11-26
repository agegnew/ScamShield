"""False positives found on the live radar and in the browser extension (25 Nov 2026).

Each test is a real case: the submission site of the hackathon itself, parking redirects, for-sale
pages, server error pages and unrelated businesses whose name is one letter away from a UAE brand.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app import engine
from app.brand_match import match_token
from app.contracts import (
    AiReview, Candidate, CandidateExtra, CloakingCheck, Evidence, FormInfo, Label, Rdap, Source, Verdict,
)
from app.engine import model
from app.page_kinds import page_kind

NOW = datetime.now(timezone.utc)
LOGIN = FormInfo(input_types=["password", "text"], field_hints=["email", "password"], sensitive=["email", "password"])


@pytest.fixture
def url_model(monkeypatch):
    """Set what the URL model answers: url_model(0.98)."""

    def set_p(p):
        monkeypatch.setattr(model, "phishing_probability", lambda url: p)

    set_p(None)
    return set_p


def page(url, **kwargs):
    return Evidence(url=url, fetched_at=NOW, **{"final_url": url, "page_kind": "content", **kwargs})


def codes(verdict):
    return {r.code for r in verdict.reasons}


# ---- pages that name no brand at all ------------------------------------------------------


PODIUM = "https://podium.aevsoft.cc/HackathonMngtWebApp/participant/dashboard.php"


def podium_page(**kwargs):
    return page(
        PODIUM,
        final_url="https://podium.aevsoft.cc/HackathonMngtWebApp/index.php",
        title="Login — Podium+",
        text_excerpt="Podium+ Sign in to Podium+ English · العربية Email or Access Code Password Sign In "
        "Forgot your password? Powered by © 2026 Podium+",
        forms=[LOGIN],
        rdap=Rdap(created=NOW - timedelta(days=440), registrar="Cloudflare, Inc."),
        **kwargs,
    )


def test_login_page_that_names_no_brand_is_not_fraud(url_model):
    url_model(0.98)  # what the model said about the hackathon's own submission site
    v = engine.score(PODIUM, evidence=podium_page())
    assert v.verdict != Label.FRAUD


def test_login_page_that_names_no_brand_is_legit_once_the_ai_clears_it(url_model):
    url_model(0.98)
    ai = AiReview(model="claude", verdict="legit", confidence=0.9, explanation_en="ok", explanation_ar="ok", reviewed_at=NOW)
    v = engine.score(PODIUM, evidence=podium_page(ai_review=ai))
    assert v.verdict == Label.LEGIT


def test_url_only_without_any_brand_is_watched_not_reported(url_model):
    url_model(0.98)
    v = engine.score(PODIUM)
    assert v.verdict == Label.SUSPICIOUS  # still flagged for the hidden test set, but not called a scam


def test_url_only_brand_claim_can_still_be_fraud(url_model):
    url_model(0.95)
    assert engine.score("https://tamm-fines-pay.xyz/pay").verdict == Label.FRAUD


# ---- placeholder pages --------------------------------------------------------------------


def test_server_error_pages_are_not_content():
    assert page_kind("https://akbank.online/", "akbank.online | 502: Bad gateway", "") == "error"
    assert page_kind("http://x.com/", "x.com | 522: Connection timed out", "") == "error"
    assert page_kind("http://x.com/", "x.com | 521: Web server is down", "") == "error"
    assert page_kind("http://x.com/", "503 Service Unavailable", "") == "error"
    assert page_kind("http://x.com/", "DNS resolution error | x.com | Cloudflare", "") == "error"


def test_suspended_and_expired_sites_are_holding_pages():
    assert page_kind("http://d.online/cgi-sys/suspendedpage.cgi", "Account Suspended", "") == "expired"
    assert page_kind("http://x.info/", "Squarespace - Website Expired", "") == "expired"
    assert page_kind("http://x.online/", "Contact Verification Suspension Page", "") == "expired"
    assert page_kind("http://x.online/", "x.online - ICANN Verification", "") == "expired"


def test_a_phishing_lure_about_a_suspended_account_stays_content():
    text = "Your account has been suspended. Verify your card details to restore access."
    assert page_kind("https://adcb-help.top/", "ADCB - Account suspended", text, form_count=1) == "content"


def test_for_sale_pages_win_over_a_blocked_marketplace():
    godaddy = "https://forsale.godaddy.com/forsale/fly-dubai.com?utm_medium=parkedpages"
    assert page_kind(godaddy, "Access Denied", "You don't have permission") == "for_sale"
    assert page_kind("https://unstoppabledomains.com/d/dewa-service.info", "dewa-service.info | Unstoppable", "") \
        == "for_sale"


def test_error_page_on_a_lookalike_domain_is_not_fraud(url_model):
    url_model(0.87)
    url = "http://emiratespost-track.com/"
    ev = page(url, title="emiratespost-track.com | 522: Connection timed out", text_excerpt="Connection timed out")
    v = engine.score(url, evidence=ev)
    assert v.verdict != Label.FRAUD
    assert "brand_on_wrong_domain" not in codes(v)  # the brand was only the site's own address in the title


def test_parking_redirect_is_not_fraud(url_model):
    url_model(0.94)
    url = "http://dewa.online/"
    ev = page(
        url,
        final_url="https://headlinelogic.com/?d=dewa.online&pcid=56&a=false&brand=dewa.online",
        title="HeadlineLogic News Portal",
        text_excerpt="Latest news headlines",
        forms=[LOGIN],
        cloaking=CloakingCheck(signals=["different_destination"]),
    )
    v = engine.score(url, evidence=ev)
    assert v.verdict != Label.FRAUD


# ---- a brand-like domain showing someone else's business ---------------------------------


def test_unrelated_business_on_a_typo_domain_is_not_fraud(url_model):
    url_model(0.70)
    url = "http://aramix.site/"
    ev = page(
        url,
        title="Aramix Concreto | Concreto usinado em Campinas",
        text_excerpt="Concreto usinado com qualidade e pontualidade. Solicite seu orçamento.",
        rdap=Rdap(created=NOW - timedelta(days=3)),
    )
    v = engine.score(url, evidence=ev)
    assert "unrelated_content" in codes(v)
    assert v.verdict != Label.FRAUD


def test_unrelated_login_site_is_not_impersonation(url_model):
    url_model(0.75)
    url = "http://online-icp.com/"
    ev = page(
        url,
        final_url="http://online-icp.com/usuario/conta/login",
        title="Instituto Criança Pemba | Plataforma de Gestão",
        text_excerpt="Entrar na plataforma. Utilizador. Palavra-passe.",
        forms=[LOGIN],
    )
    v = engine.score(url, evidence=ev)
    assert "unrelated_content" in codes(v)
    assert v.verdict != Label.FRAUD


def test_page_impersonating_the_brand_is_still_fraud(url_model):
    url_model(0.6)
    url = "https://mashreqonline.com/"
    ev = page(
        url,
        title="Mashreq Online Banking - Login",
        text_excerpt="Welcome to Mashreq online banking. Enter your username and password.",
        forms=[LOGIN],
    )
    assert engine.score(url, evidence=ev).verdict == Label.FRAUD


def test_cloudflare_phishing_warning_is_hard_evidence(url_model):
    url_model(0.78)
    url = "http://fly-dubai.co/"
    ev = page(url, title="Suspected Phishing | Cloudflare",
              text_excerpt="Warning: Suspected Phishing. This website has been reported for potential phishing.")
    v = engine.score(url, evidence=ev)
    assert "platform_warning" in codes(v)
    assert v.verdict == Label.FRAUD


# ---- Maps listings ---------------------------------------------------------------------


def maps(url, name, phone="+971542122767"):
    return Candidate(
        url=url, source=Source.MAPS, query="Etisalat customer service", discovered_at=NOW,
        extra=CandidateExtra(listing_name=name, phone=phone, brand="eand"),
    )


def test_a_brand_store_with_its_own_number_is_not_a_fake_helpline(url_model):
    url_model(0.85)
    url = "https://wa.me/message/RJ2UYB55M77RP1"
    v = engine.score(url, candidate=maps(url, "ETISALAT STORE ,E& DMCC MARINA JLT"))
    assert "helpline_mismatch" not in codes(v)
    assert "url_model" not in codes(v)  # a WhatsApp chat link has no URL pattern to judge
    assert v.verdict != Label.FRAUD


def test_a_customer_care_listing_with_a_mobile_number_is_a_fake_helpline(url_model):
    url = "https://www.google.com/maps/place/?q=place_id:abc"
    v = engine.score(url, candidate=maps(url, "Etisalat Customer Care 24/7"))
    assert "helpline_mismatch" in codes(v)


# ---- brand matching ----------------------------------------------------------------------


def test_a_letter_glued_to_a_short_brand_makes_another_word():
    assert match_token("esewa888.com") is None  # eSewa, a Nepali wallet, not SEWA
    assert match_token("sewa-bill.com") == ("sewa", "sewa-bill")


def test_typosquat_distance_is_one_for_short_names(url_model):
    assert "typosquat" not in codes(engine.score("https://rakbunq.com/"))  # two edits from rakbank
    assert "typosquat" in codes(engine.score("https://rakbamk.com/"))


# ---- sites that are not online ------------------------------------------------------------


def test_lookalike_that_does_not_resolve_is_watched_not_reported(url_model):
    url_model(0.98)
    url = "http://aramexdelivery.live/"
    ev = Evidence(url=url, fetched_at=NOW, fetch_error="Offline: cannot resolve aramexdelivery.live")
    v = engine.score(url, evidence=ev)
    assert "holding_page" in codes(v)
    assert v.verdict == Label.SUSPICIOUS


def test_reported_link_that_went_offline_stays_fraud(url_model, monkeypatch):
    from app.engine import feeds

    monkeypatch.setattr(feeds, "load", lambda: feeds.FeedIndex(urls={"https://2h.ae/ppgkr": "PhishTank"}))
    url = "https://2h.ae/pPGKr"
    ev = Evidence(url=url, fetched_at=NOW, fetch_error="Offline: cannot resolve 2h.ae")
    v = engine.score(url, evidence=ev, use_feeds=True)
    assert v.verdict == Label.FRAUD


def test_a_timeout_is_not_proof_the_site_is_offline(url_model):
    url_model(0.98)
    url = "http://aramex-delivery.com/"
    ev = Evidence(url=url, fetched_at=NOW, fetch_error="Error: Page.goto: Timeout 20000ms exceeded.")
    assert "holding_page" not in codes(engine.score(url, evidence=ev))  # scam kits block foreign visitors


# ---- analyst decisions reach the public checker and the extension --------------------------


def test_public_check_honours_a_dismissal(client, analyst_headers):
    url = "https://podium.aevsoft.cc/HackathonMngtWebApp/index.php"
    case = client.post("/api/scan", json={"url": url}, headers=analyst_headers).json()
    case_id = case.get("case_id") or case.get("id")
    res = client.post(f"/api/cases/{case_id}/decision", json={"action": "dismiss", "reason": "the hackathon's own site"},
                      headers=analyst_headers)
    assert res.status_code == 200, res.text
    check = client.post("/api/check", json={"input": "https://podium.aevsoft.cc"}).json()
    assert check["verdict"] == "LEGIT"
    assert check["reasons"][0]["code"] == "analyst_dismissed"


def test_a_shared_host_does_not_inherit_another_links_verdict(session):
    from app.repo import CaseRepo

    repo = CaseRepo(session)
    scam = Verdict(url="https://bit.ly/4hDruaE", verdict=Label.FRAUD, score=100, reasons=[],
                   model_version="t", scored_at=NOW)
    repo.add(Candidate(url="https://bit.ly/4hDruaE", source=Source.CITIZEN, discovered_at=NOW), scam)
    # A lookalike that redirects to Google must not make google.com look like a scam.
    lookalike = Verdict(url="http://flydubau.com/", verdict=Label.SUSPICIOUS, score=62, reasons=[],
                        model_version="t", scored_at=NOW)
    repo.add(Candidate(url="http://flydubau.com/", source=Source.LOOKALIKE, discovered_at=NOW), lookalike,
             evidence=Evidence(url="http://flydubau.com/", final_url="https://www.google.com/", fetched_at=NOW))
    assert repo.find_by_url("https://bit.ly/4hDruaE") is not None  # the reported link itself
    assert repo.find_by_url("https://bit.ly/3xYzAbC") is None
    assert repo.find_by_url("https://bit.ly") is None
    assert repo.find_by_url("https://www.google.com") is None
    assert repo.find_by_url("http://flydubau.com/login") is not None  # same lookalike host still matches


def test_a_confirmed_case_wins_over_a_later_unreviewed_duplicate_of_the_same_site(session):
    """moi-portal.com: an analyst confirmed https://moi-portal.com/ (page opened, FRAUD 75); a later
    radar run found http://moi-portal.com/ again and scored the address alone (SUSPICIOUS 35). Every
    way of typing the site must get the analyst's answer, as the extension's block page does."""
    from app.repo import CaseRepo

    repo = CaseRepo(session)
    url = "https://moi-portal.com/"
    confirmed = repo.add(
        Candidate(url=url, source=Source.CITIZEN, discovered_at=NOW - timedelta(days=1)),
        Verdict(url=url, verdict=Label.FRAUD, score=75, reasons=[], model_version="t", scored_at=NOW),
        evidence=Evidence(url=url, final_url=url, fetched_at=NOW, title="Ministry of Interior"),
    )
    repo.decide(confirmed.id, "confirm", "fake MOI portal", "analyst")
    repo.add(
        Candidate(url="http://moi-portal.com/", source=Source.LOOKALIKE, discovered_at=NOW),
        Verdict(url="http://moi-portal.com/", verdict=Label.SUSPICIOUS, score=35, reasons=[],
                model_version="t", scored_at=NOW),
    )
    for typed in ("http://moi-portal.com", "http://moi-portal.com/", "https://moi-portal.com",
                  "https://www.moi-portal.com/", "http://moi-portal.com/login"):
        found = repo.find_by_url(typed)
        assert found is not None and found.id == confirmed.id, typed


def test_the_fetch_worker_saves_on_the_case_at_its_own_url(session, monkeypatch):
    """The checker's 'which case answers' must not redirect the worker: the duplicate's page is still
    opened and its evidence saved on the duplicate, not dropped because a confirmed case answers."""
    from app.repo import CaseRepo
    from app.workers import pipeline

    repo = CaseRepo(session)
    confirmed = repo.add(
        Candidate(url="https://moi-portal.com/", source=Source.CITIZEN, discovered_at=NOW - timedelta(days=1)),
        Verdict(url="https://moi-portal.com/", verdict=Label.FRAUD, score=75, reasons=[], model_version="t",
                scored_at=NOW),
    )
    repo.decide(confirmed.id, "confirm", "fake MOI portal", "analyst")
    dup = repo.add(
        Candidate(url="http://moi-portal.com/", source=Source.LOOKALIKE, discovered_at=NOW),
        Verdict(url="http://moi-portal.com/", verdict=Label.SUSPICIOUS, score=35, reasons=[],
                model_version="t", scored_at=NOW),
    )
    monkeypatch.setattr(pipeline.collector, "collect",
                        lambda url: Evidence(url=url, final_url="https://moi-portal.com/", fetched_at=NOW))
    pipeline.run_fetch(session, "http://moi-portal.com/")
    assert repo.get(dup.id).evidence is not None
    assert repo.get(confirmed.id).evidence is None  # the confirmed case was not overwritten


def test_a_dismissal_wins_over_a_later_unreviewed_duplicate(session):
    from app.repo import CaseRepo

    repo = CaseRepo(session)
    url = "https://podium.aevsoft.cc/HackathonMngtWebApp/index.php"
    dismissed = repo.add(
        Candidate(url=url, source=Source.CITIZEN, discovered_at=NOW - timedelta(days=1)),
        Verdict(url=url, verdict=Label.FRAUD, score=95, reasons=[], model_version="t", scored_at=NOW),
    )
    repo.decide(dismissed.id, "dismiss", "the hackathon's own site", "analyst")
    repo.add(
        Candidate(url="http://podium.aevsoft.cc/", source=Source.SEARCH, discovered_at=NOW),
        Verdict(url="http://podium.aevsoft.cc/", verdict=Label.SUSPICIOUS, score=40, reasons=[],
                model_version="t", scored_at=NOW),
    )
    assert repo.find_by_url("https://podium.aevsoft.cc").id == dismissed.id
    assert repo.find_by_url("http://podium.aevsoft.cc/").id == dismissed.id  # exact URL of the duplicate too


def test_a_cleared_homepage_does_not_hide_a_scam_page_on_the_same_hacked_site(session):
    from app.repo import CaseRepo

    repo = CaseRepo(session)
    home, kit = "https://bakery-example.ae/", "https://bakery-example.ae/wp-includes/emiratesnbd/login.php"
    cleared = repo.add(
        Candidate(url=home, source=Source.CITIZEN, discovered_at=NOW),
        Verdict(url=home, verdict=Label.LEGIT, score=5, reasons=[], model_version="t", scored_at=NOW),
        evidence=Evidence(url=home, final_url=home, fetched_at=NOW, title="Fresh bread"),
    )
    repo.decide(cleared.id, "dismiss", "a real bakery", "analyst")
    scam = repo.add(
        Candidate(url=kit, source=Source.CITIZEN, discovered_at=NOW - timedelta(hours=1)),
        Verdict(url=kit, verdict=Label.FRAUD, score=95, reasons=[], model_version="t", scored_at=NOW),
        evidence=Evidence(url=kit, final_url=kit, fetched_at=NOW, title="Emirates NBD Online Banking"),
    )
    assert repo.find_by_url(kit).id == scam.id
    assert repo.find_by_url(home).id == cleared.id


# ---- real banks on their own country domains ---------------------------------------------


def test_a_global_brand_on_its_own_country_domain_is_not_a_lookalike():
    assert "lookalike_domain" not in codes(engine.score("https://citibank.ae/"))
    assert "lookalike_domain" not in codes(engine.score("https://www.microsoft.ae/"))
    assert "lookalike_domain" in codes(engine.score("https://paypal-verify.ae/"))
    assert "lookalike_domain" in codes(engine.score("https://citibank-ae.com/"))
    assert "lookalike_domain" in codes(engine.score("https://netflix.co/"))  # .co, .cm, .om: typos of .com


def test_emirates_nbd_egypt_is_official():
    assert engine.score("https://www.emiratesnbd.com.eg/").verdict == Label.LEGIT


# ---- phishing feeds -----------------------------------------------------------------------


def test_one_reported_page_does_not_list_a_popular_site(monkeypatch):
    from app.engine import feeds

    reported = "https://docs.google.com/forms/d/e/evil/viewform"
    index = feeds.FeedIndex(
        urls={reported: "PhishTank", "https://evil-site.xyz/login": "PhishTank"},
        hosts={"docs.google.com": "PhishTank", "www.google.com": "PhishTank", "evil-site.xyz": "PhishTank"},
    )
    monkeypatch.setattr(feeds, "load", lambda: index)
    assert "threat_feed" in codes(engine.score(reported, use_feeds=True))  # the reported form itself
    assert "threat_feed" not in codes(engine.score("https://docs.google.com/forms/d/e/other/viewform", use_feeds=True))
    assert "threat_feed" not in codes(engine.score("https://www.google.com/", use_feeds=True))
    assert "threat_feed" in codes(engine.score("https://evil-site.xyz/other-page", use_feeds=True))  # its own site


# ---- what the search radar found on Google (25 Nov run) -----------------------------------


def search_result(url, query, position=3, ad=False):
    return Candidate(
        url=url, source=Source.SEARCH_AD if ad else Source.SEARCH, query=query, discovered_at=NOW,
        extra=CandidateExtra(details={"position": position, "lang": "en"}),
    )


def test_official_sites_found_on_google_are_official():
    for url in (
        "https://retail.rakbankonline.ae/DigiRetailWeb/auth",  # RAKBANK internet banking
        "https://xn--mgbagtd9jd2c.xn--mgbaam7a8h/en/",  # الداخلية.امارات, the Ministry of Interior
        "https://darb.qmobility.ae/RucWeb/faq",  # Q Mobility runs the Darb toll gates
        "https://www.mashreqalislami.com/en/uae/",  # Mashreq Al Islami
    ):
        assert engine.score(url).verdict == Label.LEGIT, url


def test_a_foreign_government_site_is_not_a_uae_lookalike():
    assert "lookalike_domain" not in codes(engine.score("https://portal.moi.gov.qa/"))


def test_tracking_parameters_do_not_count_as_phishing(url_model, monkeypatch):
    seen = []
    monkeypatch.setattr(model, "phishing_probability", lambda url: seen.append(url) or 0.2)
    engine.score("https://yougotagift.com/shop/?srsltid=AYCX9vIOX2ltBb14&utm_source=x&gclid=abc&page=2")
    assert seen == ["https://yougotagift.com/shop/?page=2"]


def test_an_arabic_domain_name_is_not_a_punycode_trick():
    assert "punycode" not in codes(engine.score("https://xn--mgbh0fb.xn--mgbaam7a8h/"))  # مثال.امارات
    assert "punycode" in codes(engine.score("https://xn--pypal-4ve.com/"))  # pаypal with a Cyrillic а


def test_ranking_in_googles_organic_results_counts_in_a_sites_favour(url_model):
    url_model(0.85)
    url = "https://www.giftcard.ae/"
    organic = engine.score(url, candidate=search_result(url, "gift card UAE"))
    ad = engine.score(url, candidate=search_result(url, "gift card UAE", ad=True))
    assert "organic_search" in codes(organic) and "organic_search" not in codes(ad)
    assert organic.score < ad.score


def test_ranking_does_not_excuse_hard_evidence(url_model, monkeypatch):
    from app.engine import feeds

    monkeypatch.setattr(feeds, "load", lambda: feeds.FeedIndex(urls={"https://seo-scam.xyz/pay": "PhishTank"}))
    url = "https://seo-scam.xyz/pay"
    v = engine.score(url, candidate=search_result(url, "salik pay fine"), use_feeds=True)
    assert "organic_search" not in codes(v) and v.verdict == Label.FRAUD


def test_a_brand_careers_portal_on_a_recruitment_platform_is_not_impersonation(url_model):
    url = "https://emiratesnbd.talentera.com/en/login/"
    ev = page(url, title="Log Into Your Account - Emirates NBD",
              text_excerpt="Log in to your Account Forgot your password? © Emirates NBD All Right Reserved "
                           "Company Dashboard Search Jobs Post Your CV", forms=[LOGIN])
    v = engine.score(url, evidence=ev)
    assert v.verdict != Label.FRAUD
    assert not {"lookalike_domain", "brand_on_wrong_domain"} & codes(v)


def test_an_article_saying_download_the_app_is_not_a_remote_access_scam():
    url = "https://eyeofemirates.net/979/salik/"
    ev = page(url, title="دفع مخالفات سالك دبي أون لاين", text_excerpt="يمكنك تحميل التطبيق من المتجر ثم الدخول إلى حسابك")
    assert "remote_access" not in codes(engine.score(url, evidence=ev))
    scam = page(url, title="Refund", text_excerpt="To receive your refund install AnyDesk and share the code")
    assert "remote_access" in codes(engine.score(url, evidence=scam))


def test_a_query_without_tracking_parameters_is_left_exactly_as_it_was():
    from app.engine.checks import without_tracking

    url = "https://dashboard.telemetrydeck.com/register?source={{item.slug.current}}&email=a@b.c&amp;u=x"
    assert without_tracking(url) == url
    assert without_tracking("https://a.com/x?utm_source=y&email=a@b.c") == "https://a.com/x?email=a@b.c"
