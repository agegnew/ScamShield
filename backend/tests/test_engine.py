from datetime import datetime, timedelta, timezone

import pytest

from app import engine
from app.contracts import Candidate, CandidateExtra, Evidence, FormInfo, Label, Rdap, Source
from app.engine import feeds, model

NOW = datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def no_model(monkeypatch):
    """Rule checks are tested on their own; the URL model has its own evaluation."""
    monkeypatch.setattr(model, "phishing_probability", lambda url: None)


def codes(verdict):
    return {r.code for r in verdict.reasons}


def page(url, **kwargs):
    return Evidence(url=url, fetched_at=NOW, **{"final_url": url, **kwargs})


def test_official_domain_is_legit():
    v = engine.score("https://www.tamm.abudhabi/en/fines")
    assert (v.verdict, v.score) == (Label.LEGIT, 0)


def test_redirect_to_official_domain_is_legit():
    v = engine.score("https://bit.ly/x", evidence=page("https://bit.ly/x", final_url="https://rta.ae/"))
    assert v.verdict == Label.LEGIT


def test_uae_brand_in_domain_is_lookalike():
    v = engine.score("https://tamm-fines-pay.xyz/pay")
    assert "lookalike_domain" in codes(v)
    assert v.brand_target == "tamm"
    assert v.verdict != Label.LEGIT


def test_short_brand_token_needs_word_boundary():
    assert "lookalike_domain" not in codes(engine.score("https://portal-shop.example/"))
    assert "lookalike_domain" in codes(engine.score("https://rta-fines.example/"))


def test_typosquat_of_official_domain():
    v = engine.score("https://emiratesnbb.com/login")
    assert "typosquat" in codes(v)
    assert v.brand_target == "emiratesnbd"


def test_global_brand_in_unrelated_domain():
    assert "lookalike_domain" in codes(engine.score("https://paypal-secure-login.xyz/"))
    assert "lookalike_domain" not in codes(engine.score("https://www.paypal.com/signin"))


def test_brand_name_on_free_platform():
    v = engine.score("https://tamm-fines.vercel.app/")
    assert {"free_platform"} <= codes(v)
    assert v.brand_target == "tamm"


def test_old_platform_whois_is_not_trusted_when_shared_hosting():
    old = Rdap(created=NOW - timedelta(days=4000), registrar="Platform")
    shared = engine.score(
        "https://pay.example/", evidence=page("https://pay.example/", rdap=old, shared_hosting=True)
    )
    own = engine.score("https://pay.example/", evidence=page("https://pay.example/", rdap=old))
    assert "old_domain" not in codes(shared)
    assert "old_domain" in codes(own)


def test_new_domain_raises_risk():
    fresh = Rdap(created=NOW - timedelta(days=3))
    v = engine.score("https://pay.example/", evidence=page("https://pay.example/", rdap=fresh))
    assert "new_domain" in codes(v)


def test_page_asking_for_card_and_otp_on_brand_lookalike_is_fraud():
    ev = page(
        "https://tamm-violations.example/pay",
        title="TAMM - Traffic fine payment",
        text_excerpt="Pay your traffic fine now to avoid black points",
        forms=[FormInfo(input_types=["text", "password"], field_hints=["card number", "cvv", "otp"])],
        rdap=Rdap(created=NOW - timedelta(days=2)),
    )
    v = engine.score("https://tamm-violations.example/pay", evidence=ev)
    assert {"credential_form", "brand_on_wrong_domain", "scam_theme_page", "new_domain"} <= codes(v)
    assert v.verdict == Label.FRAUD


def test_remote_access_request_is_flagged():
    ev = page("https://help.example/", text_excerpt="To get your refund, download AnyDesk and share the code")
    assert "remote_access" in codes(engine.score("https://help.example/", evidence=ev))


def test_maps_listing_with_fake_helpline():
    cand = Candidate(
        url="https://enbd-help.example/",
        source=Source.MAPS,
        discovered_at=NOW,
        extra=CandidateExtra(listing_name="Emirates NBD Customer Care", phone="04 555 0199"),
    )
    v = engine.score(cand.url, candidate=cand)
    assert "helpline_mismatch" in codes(v)


def test_official_helpline_on_listing_is_not_flagged():
    cand = Candidate(
        url="https://branch-info.example/",
        source=Source.MAPS,
        discovered_at=NOW,
        extra=CandidateExtra(listing_name="Emirates NBD Branch", phone="600 54 0000"),
    )
    assert "helpline_mismatch" not in codes(engine.score(cand.url, candidate=cand))


def test_feed_match_only_when_feeds_enabled(monkeypatch):
    index = feeds.FeedIndex(urls={"https://bad.example/login": "PhishTank"})
    monkeypatch.setattr(feeds, "load", lambda: index)
    assert "threat_feed" in codes(engine.score("https://bad.example/login", use_feeds=True))
    assert "threat_feed" not in codes(engine.score("https://bad.example/login", use_feeds=False))


def test_maps_listing_link_is_judged_on_its_phone_not_on_google():
    cand = Candidate(
        url="https://www.google.com/maps/place/?q=place_id:abc",
        source=Source.MAPS,
        discovered_at=NOW,
        extra=CandidateExtra(
            listing_name="Emirates NBD Customer Service", phone="+97145550199", brand="emiratesnbd"
        ),
    )
    v = engine.score(cand.url, candidate=cand)
    assert codes(v) == {"helpline_mismatch"}
    assert v.verdict == Label.SUSPICIOUS
    assert v.brand_target == "emiratesnbd"


def test_download_signals_and_emirates_id_field():
    from app.contracts import DownloadSignal

    ev = page(
        "https://help.example/",
        download_signals=[DownloadSignal(kind="remote_access_link", href="https://anydesk.com", text="AnyDesk")],
        forms=[FormInfo(input_types=["text"], sensitive=["emirates_id"])],
    )
    v = engine.score("https://help.example/", evidence=ev)
    assert {"remote_access", "credential_form"} <= codes(v)
    assert any("Emirates ID" in r.text_en for r in v.reasons)


def test_mentioning_a_brand_is_not_impersonating_it():
    blog = page("https://driverguide.example/", title="Gulf Driver Guide",
                text_excerpt="How to pay a TAMM traffic fine on the official site")
    assert "brand_on_wrong_domain" not in codes(engine.score("https://driverguide.example/", evidence=blog))
    phish = page("https://pay.example/", title="Pay fines",
                 text_excerpt="TAMM payment", forms=[FormInfo(sensitive=["card"])])
    assert "brand_on_wrong_domain" in codes(engine.score("https://pay.example/", evidence=phish))


def test_one_generic_theme_word_is_not_enough():
    # 'tickets' alone is on every airline and cinema site; a scam phrase or two keywords is needed.
    plain = page("https://cinema.example/", text_excerpt="Buy tickets for tonight's show")
    assert "scam_theme_page" not in codes(engine.score("https://cinema.example/", evidence=plain))
    scammy = page("https://deal.example/", text_excerpt="VIP tickets, last tickets, sold out soon")
    assert "scam_theme_page" in codes(engine.score("https://deal.example/", evidence=scammy))
    phrase = page("https://fine.example/", text_excerpt="Get a 90% discount on your fine today")
    assert "scam_theme_page" in codes(engine.score("https://fine.example/", evidence=phrase))


def test_theme_words_match_whole_words_only():
    # 'otp' must not match inside 'footprint'; form-field words count only through credential_form.
    ev = page("https://eco.example/", text_excerpt="Reduce your carbon footprint and reactivate savings")
    assert "scam_theme_page" not in codes(engine.score("https://eco.example/", evidence=ev))


def test_common_arabic_word_is_not_taken_for_a_brand_name():
    # 'تم' is TAMM's Arabic name but also the everyday word 'was / done'.
    ev = page("https://news.example/", text_excerpt="تم افتتاح المتجر الجديد اليوم")
    assert "brand_on_wrong_domain" not in codes(engine.score("https://news.example/", evidence=ev))


def test_visual_match_and_cloaking_raise_risk():
    from app.contracts import CloakingCheck, VisualMatch

    ev = page(
        "https://pay-portal.example/",
        visual_match=VisualMatch(brand="tamm", kind="same_favicon"),
        cloaking=CloakingCheck(signals=["different_destination"]),
    )
    v = engine.score("https://pay-portal.example/", evidence=ev)
    assert {"visual_match", "cloaking"} <= codes(v)
    assert v.brand_target == "tamm"


def test_every_reason_has_both_languages():
    ev = page(
        "https://tamm-violations.example/pay",
        title="TAMM",
        forms=[FormInfo(input_types=["password"])],
        rdap=Rdap(created=NOW - timedelta(days=2)),
    )
    for reason in engine.score("https://tamm-violations.example/pay", evidence=ev).reasons:
        assert reason.text_en and reason.text_ar


def test_domain_and_page_both_claiming_the_brand_is_fraud_despite_a_normal_url(monkeypatch):
    # moi-portal.com: the URL model rates the address as normal (38%), the page says it is the MOI.
    monkeypatch.setattr(model, "phishing_probability", lambda url: 0.38)
    ev = page("https://moi-portal.com/", title="Ministry of Interior — Official Verification Portal")
    v = engine.score("https://moi-portal.com/", evidence=ev)
    assert {"lookalike_domain", "brand_on_wrong_domain", "impersonation_confirmed"} <= codes(v)
    assert "url_model" not in codes(v)
    assert v.verdict == Label.FRAUD


def test_normal_url_still_lowers_risk_when_the_page_does_not_impersonate(monkeypatch):
    monkeypatch.setattr(model, "phishing_probability", lambda url: 0.38)
    ev = page("https://moi-portal.com/", title="Portal for car parts")
    v = engine.score("https://moi-portal.com/", evidence=ev)
    assert "url_model" in codes(v) and "impersonation_confirmed" not in codes(v)


def test_parked_lookalike_is_watched_not_reported(monkeypatch):
    # tamm-service.site: an empty Hostinger parking page on a lookalike name.
    monkeypatch.setattr(model, "phishing_probability", lambda url: 0.93)
    ev = page("https://tamm-service.site/", title="Parked Domain name on Hostinger DNS system", page_kind="parked")
    v = engine.score("https://tamm-service.site/", evidence=ev)
    assert "holding_page" in codes(v)
    assert (v.verdict, v.score) == (Label.SUSPICIOUS, 60)
    assert v.score == sum(r.weight for r in v.reasons)


def test_parked_page_listed_by_a_feed_stays_fraud(monkeypatch):
    monkeypatch.setattr(model, "phishing_probability", lambda url: 0.93)
    monkeypatch.setattr(feeds, "load", lambda: feeds.FeedIndex(urls={"https://tamm-service.site": "OpenPhish"}))
    ev = page("https://tamm-service.site/", page_kind="parked")
    v = engine.score("https://tamm-service.site/", evidence=ev, use_feeds=True)
    assert "holding_page" not in codes(v)
    assert v.verdict == Label.FRAUD


def test_placeholder_label_does_not_hide_a_credential_form(monkeypatch):
    monkeypatch.setattr(model, "phishing_probability", lambda url: 0.93)
    ev = page(
        "https://tamm-service.site/",
        page_kind="coming_soon",
        forms=[FormInfo(input_types=["password"], field_hints=["card number"])],
    )
    v = engine.score("https://tamm-service.site/", evidence=ev)
    assert "holding_page" not in codes(v)
    assert v.verdict == Label.FRAUD


def test_reported_phishing_url_on_an_old_hacked_site_is_fraud(monkeypatch):
    # rallysteelworks.ae/fonts/: a phishing kit on a years-old business site, listed by PhishTank.
    monkeypatch.setattr(model, "phishing_probability", lambda url: 0.37)
    monkeypatch.setattr(feeds, "load", lambda: feeds.FeedIndex(urls={"https://rallysteelworks.ae/fonts": "PhishTank"}))
    ev = page("https://rallysteelworks.ae/fonts/", rdap=Rdap(created=NOW - timedelta(days=9 * 365)))
    v = engine.score("https://rallysteelworks.ae/fonts/", evidence=ev, use_feeds=True)
    assert "threat_feed" in codes(v) and not {"url_model", "old_domain"} & codes(v)
    assert v.verdict == Label.FRAUD


def test_old_domain_still_counts_without_strong_evidence(monkeypatch):
    monkeypatch.setattr(model, "phishing_probability", lambda url: 0.37)
    ev = page("https://rallysteelworks.ae/about/", rdap=Rdap(created=NOW - timedelta(days=9 * 365)))
    assert {"url_model", "old_domain"} <= codes(engine.score("https://rallysteelworks.ae/about/", evidence=ev))


def test_typos_of_an_ordinary_word_are_not_brand_typosquats():
    # economy.gov.ae is official for Consumer Protection, but "iconomy" is not imitating it.
    assert "typosquat" not in codes(engine.score("https://iconomy.online/"))
    assert "typosquat" in codes(engine.score("https://emiratesnbb.com/"))


def test_ordinary_words_in_a_title_are_not_a_brand_claim():
    ev = page("https://news.example/", title="The Economy Times - Recently added stories")
    assert "brand_on_wrong_domain" not in codes(engine.score("https://news.example/", evidence=ev))


def test_for_sale_page_naming_the_brand_is_not_a_brand_claim():
    ev = page("http://emiratespost.com/", title="EmiratesPost.com is for sale - Premium Domain", page_kind="for_sale")
    v = engine.score("http://emiratespost.com/", evidence=ev)
    assert "brand_on_wrong_domain" not in codes(v) and v.verdict == Label.SUSPICIOUS


def test_business_sharing_a_brand_name_is_not_confirmed_impersonation():
    ev = page("http://uaetamm.com/", title="Tamm Real Estate | Sales | Buying | Leasing")
    v = engine.score("http://uaetamm.com/", evidence=ev)
    assert "brand_on_wrong_domain" in codes(v) and "impersonation_confirmed" not in codes(v)
    assert v.verdict == Label.SUSPICIOUS


def test_site_on_a_uae_government_network_is_not_flagged():
    ev = page(
        "http://adpol1ce.ae/",
        title="الرئيسية | عن شرطة أبوظبي",
        text_excerpt="أهلا بكم في الموقع الرسمي للقيادة العامة لشرطة ابوظبي",
        asn=201678,
        hosting_org="ADNET - Abu Dhabi Digital Authority, AE",
    )
    v = engine.score("http://adpol1ce.ae/", evidence=ev)
    assert "government_network" in codes(v) and v.verdict == Label.LEGIT


def test_reported_phishing_on_a_government_network_is_still_flagged(monkeypatch):
    monkeypatch.setattr(feeds, "load", lambda: feeds.FeedIndex(urls={"https://site.ae/x/login": "PhishTank"}))
    ev = page("https://site.ae/x/login", asn=201678, hosting_org="ADNET - Abu Dhabi Digital Authority, AE")
    v = engine.score("https://site.ae/x/login", evidence=ev, use_feeds=True)
    assert "government_network" not in codes(v) and v.verdict == Label.FRAUD


def test_abu_dhabi_police_alias_domain_is_official():
    assert (engine.score("https://adpolice.ae/").verdict, engine.score("https://adpolice.ae/").score) == (Label.LEGIT, 0)


def test_live_unrelated_business_on_a_brand_token_is_not_fraud(monkeypatch):
    # icp-online.xyz: a Japanese company's site, nothing about the UAE's ICP, no form. The name match
    # is a coincidence, so neither it nor the URL model's view of the name counts.
    monkeypatch.setattr(model, "phishing_probability", lambda url: 0.93)
    ev = page("http://icp-online.xyz/", title="ICP株式会社", text_excerpt="会社概要 事業内容 お問い合わせ", page_kind="content")
    v = engine.score("http://icp-online.xyz/", evidence=ev)
    assert "unrelated_content" in codes(v) and v.verdict == Label.LEGIT
    assert v.brand_target is None


def test_unrelated_content_rule_needs_a_page_without_any_scam_sign(monkeypatch):
    monkeypatch.setattr(model, "phishing_probability", lambda url: 0.93)
    names_brand = page("http://aramex-track.xyz/", title="Track your parcel", text_excerpt="Aramex shipment on hold", page_kind="content")
    with_form = page("http://aramex-track.xyz/", title="Track", forms=[FormInfo(input_types=["text"], field_hints=["card number"])], page_kind="content")
    parked = page("http://aramex-track.xyz/", title="Parked", page_kind="parked")
    for ev in (names_brand, with_form, parked):
        assert "unrelated_content" not in codes(engine.score("http://aramex-track.xyz/", evidence=ev))
