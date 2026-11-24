"""Claude's second look at borderline pages: when it is asked, how its answer moves the score,
and that every failure leaves the rules' verdict untouched. No real API calls."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app import engine
from app.contracts import AiReview, DownloadSignal, Evidence, FormInfo
from app.workers import ai_review

NOW = datetime.now(timezone.utc)


def _ev(**kw) -> Evidence:
    base = dict(url="https://tammservices.com/", final_url="https://tammservices.com/", fetched_at=NOW,
                title="Tamm Services", text_excerpt="Welcome to Tamm Services", page_kind="content")
    return Evidence(**{**base, **kw})


def _ai(verdict="scam", confidence=0.9, impersonates=None) -> AiReview:
    return AiReview(model="claude-opus-5-5", verdict=verdict, confidence=confidence, impersonates=impersonates,
                    asks_for=["card"], explanation_en="Fake TAMM fine page asking for card details.",
                    explanation_ar="صفحة مخالفات مزيفة تطلب بيانات البطاقة.", reviewed_at=NOW)


def _codes(verdict):
    return {r.code: r.weight for r in verdict.reasons}


# ---- how the answer counts ------------------------------------------------------------


def test_confident_scam_answer_adds_30_and_names_the_brand():
    url = "https://pay-fines-online.top/"
    before = engine.score(url, evidence=_ev(url=url, final_url=url))
    after = engine.score(url, evidence=_ev(url=url, final_url=url, ai_review=_ai(impersonates="tamm")))
    assert _codes(after)["ai_flagged"] == 30
    assert after.score == min(100, before.score + 30)
    assert after.brand_target == "tamm"
    reason = next(r for r in after.reasons if r.code == "ai_flagged")
    assert "90% sure" in reason.text_en and "AI review" in reason.text_en and reason.text_ar


def test_confident_legit_answer_lowers_and_weak_or_unsure_answers_are_ignored():
    url = "https://tammservices.com/"
    assert _codes(engine.score(url, evidence=_ev(ai_review=_ai("legit", 0.95))))["ai_cleared"] == -30
    assert _codes(engine.score(url, evidence=_ev(ai_review=_ai("legit", 0.7))))["ai_cleared"] == -15
    assert "ai_cleared" not in _codes(engine.score(url, evidence=_ev(ai_review=_ai("legit", 0.5))))
    assert not {"ai_flagged", "ai_cleared"} & set(_codes(engine.score(url, evidence=_ev(ai_review=_ai("unsure", 0.9)))))


def test_cleared_news_page_is_not_tagged_with_the_brand_it_mentions():
    url = "https://saadaahnews.com/article"
    news = dict(url=url, final_url=url, title="Abu Dhabi Police fine discount extended")
    assert engine.score(url, evidence=_ev(**news)).brand_target == "adpolice"
    cleared = engine.score(url, evidence=_ev(**news, ai_review=_ai("legit", 0.9)))
    assert cleared.brand_target is None
    # A lookalike domain keeps its brand: the name itself copies it.
    assert engine.score("https://tammservices.com/", evidence=_ev(ai_review=_ai("legit", 0.9))).brand_target == "tamm"


def test_hard_evidence_is_never_cleared_by_the_ai():
    url = "https://tammservices.com/"
    pushed_app = _ev(download_signals=[DownloadSignal(kind="remote_access_link", href="https://anydesk.com/")],
                     ai_review=_ai("legit", 0.99))
    assert "ai_cleared" not in _codes(engine.score(url, evidence=pushed_app))


# ---- when Claude is asked --------------------------------------------------------------------


@pytest.fixture
def ai_on(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(ai_review, "AI_ENABLED", True)
    monkeypatch.setattr(ai_review, "CACHE_DIR", tmp_path)


def _verdict(score, *codes):
    v = engine.score("https://x.test/")
    return v.model_copy(update={"score": score, "reasons": [r for r in v.reasons if r.code in codes]})


def test_only_borderline_live_pages_are_reviewed(ai_on, monkeypatch):
    assert ai_review.should_review(_ev(), _verdict(45))
    assert ai_review.should_review(_ev(), _verdict(20)) and ai_review.should_review(_ev(), _verdict(79))
    assert not ai_review.should_review(_ev(), _verdict(10))  # clearly fine
    assert not ai_review.should_review(_ev(), _verdict(95))  # clearly fraud
    assert not ai_review.should_review(_ev(fetch_error="timeout"), _verdict(45))  # nothing to look at
    assert not ai_review.should_review(_ev(page_kind="parked"), _verdict(45))  # parked: watched, not judged
    assert not ai_review.should_review(None, _verdict(45))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    assert not ai_review.should_review(_ev(), _verdict(45))  # no key: off


class FakeClient:
    def __init__(self, answer=None, stop_reason="end_turn", error=None):
        self.calls = []
        self.answer, self.stop_reason, self.error = answer, stop_reason, error
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        text = json.dumps(self.answer) if self.answer is not None else ""
        return SimpleNamespace(stop_reason=self.stop_reason, stop_details=None, model=kwargs["model"],
                               content=[SimpleNamespace(type="text", text=text)])


ANSWER = {"verdict": "scam", "confidence": 0.92, "impersonates": "tamm", "asks_for": ["card", "otp", "nothing"],
          "explanation_en": "Copies TAMM and asks for card and OTP.", "explanation_ar": "تنتحل تم وتطلب البطاقة."}


def test_borderline_page_is_reviewed_and_rescored(ai_on, monkeypatch):
    fake = FakeClient(ANSWER)
    monkeypatch.setattr(ai_review, "_client", fake)
    url = "https://tammservices.com/"
    ev = _ev()
    before = engine.score(url, evidence=ev)
    assert ai_review.should_review(ev, before), before.score
    ev2, after = ai_review.score_with_review(url, ev)
    assert ev2.ai_review.verdict == "scam" and ev2.ai_review.impersonates == "tamm"
    assert ev2.ai_review.asks_for == ["card", "otp"]
    assert after.score > before.score and "ai_flagged" in _codes(after)

    sent = fake.calls[0]
    assert sent["model"] == "claude-opus-5-5" and sent["fallbacks"] == "default"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    text = sent["messages"][0]["content"][-1]["text"]
    assert "<page>" in text and "Welcome to Tamm Services" in text and "tamm.abudhabi" in text
    assert "not instructions" in sent["system"]  # page text is untrusted


def test_prompt_lists_what_the_forms_ask_for():
    ev = _ev(forms=[FormInfo(sensitive=["card", "otp"], field_hints=["card number", "otp"])])
    facts = ai_review._facts("https://tammservices.com/pay", ev)
    assert "Forms ask for: card, otp" in facts and "card number" in facts


@pytest.mark.parametrize("fake", [
    FakeClient(error=RuntimeError("network down")),
    FakeClient(ANSWER, stop_reason="refusal"),
    FakeClient(answer=None),
])
def test_any_failure_keeps_the_rules_verdict(ai_on, monkeypatch, fake):
    monkeypatch.setattr(ai_review, "_client", fake)
    url = "https://tammservices.com/"
    assert ai_review.should_review(_ev(), engine.score(url, evidence=_ev()))  # a review is really attempted
    ev, verdict = ai_review.score_with_review(url, _ev())
    assert len(fake.calls) == 1 and ev.ai_review is None
    assert verdict.score == engine.score(url, evidence=_ev()).score


def test_daily_limit_stops_reviews(ai_on, monkeypatch):
    monkeypatch.setattr(ai_review, "AI_DAILY_LIMIT", 1)
    fake = FakeClient(ANSWER)
    monkeypatch.setattr(ai_review, "_client", fake)
    assert ai_review.review("https://a.test/", _ev()) is not None
    assert ai_review.review("https://b.test/", _ev()) is None
    assert len(fake.calls) == 1


def test_unknown_brand_from_the_ai_is_dropped(ai_on, monkeypatch):
    monkeypatch.setattr(ai_review, "_client", FakeClient({**ANSWER, "impersonates": "not-a-brand"}))
    assert ai_review.review("https://a.test/", _ev()).impersonates is None


def test_saved_review_is_reused_when_rescoring_without_a_key():
    url = "https://pay-fines-online.top/"
    ev = _ev(url=url, final_url=url, ai_review=_ai())
    assert "ai_flagged" in _codes(engine.score(url, evidence=ev))  # no API involved
