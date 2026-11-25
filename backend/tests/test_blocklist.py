from app.blocklist import blockable


def test_blockable_hosts():
    assert blockable("aramexdelivery.live")
    assert blockable("www.moi-portal.com")
    assert blockable("tamm-pay.pages.dev")  # a scam on a shared platform
    assert not blockable("pages.dev")  # the platform itself
    assert not blockable("sites.google.com")  # anyone can publish there
    assert not blockable("tamm.abudhabi")  # official
    assert not blockable("emiratesnbd.com")  # official
    assert not blockable("adpolice.gov.ae")
    assert not blockable("")


def test_blocklist_endpoint(client):
    data = client.get("/api/blocklist").json()
    assert data["count"] == len(data["domains"])
    hosts = [d["domain"] for d in data["domains"]]
    assert len(hosts) == len(set(hosts))
    for d in data["domains"]:
        assert d["score"] >= 0 and d["case_id"]
        assert blockable(d["domain"])
