from app import message_check as mc

SMS = ("Abu Dhabi Police: You have an unpaid traffic fine of AED 300. Pay within 24 hours to avoid black points: "
       "https://tamm-fines-pay.xyz/pay?id=88 or call +971 50 123 4567. شرطة أبوظبي: لديك مخالفة غير مدفوعة")


def test_extracts_links_and_phones():
    assert mc.find_links(SMS) == ["https://tamm-fines-pay.xyz/pay?id=88"]
    assert mc.find_links("visit emiratespost-ae.top/track now.") == ["emiratespost-ae.top/track"]
    assert mc.find_links("pay AED.300 e.g. now, mail me@x.com") == []
    assert mc.find_phones(SMS) == ["+971 50 123 4567"]


def test_message_endpoint_flags_fine_sms(client):
    r = client.post("/api/check/message", json={"text": SMS}).json()
    assert r["kind"] == "message" and r["verdict"] == "FRAUD"
    kinds = {p["kind"] for p in r["parts"]}
    assert kinds == {"url", "phone"}
    assert any(x["code"] == "message_part_flagged" for x in r["reasons"])
    assert r["headline_ar"]


def test_message_endpoint_official_helpline_is_not_flagged(client):
    r = client.post("/api/check/message", json={"text": "Call TAMM on 800 555 for help with your fine."}).json()
    assert r["verdict"] in ("LEGIT", "UNKNOWN", "SUSPICIOUS")
    assert r["verdict"] != "FRAUD"


def test_message_endpoint_needs_input(client):
    assert client.post("/api/check/message", json={}).status_code == 422
    assert client.post("/api/check/message", json={"image": "data:text/html;base64,AAAA"}).status_code == 422
