from workers.fingerprint import contacts, hamming, murmur3_32, tracking_ids


def test_murmur3_matches_reference():
    assert (murmur3_32(b"hello"), murmur3_32(b""), murmur3_32(b"abc")) == (613153351, 0, -1277324294)


def test_trackers_and_contacts():
    html = """<script>gtag('config','G-AB12CD34EF');fbq('init', '123456789012345');</script>
              <a href="https://wa.me/971501234567">WhatsApp</a> <a href="https://t.me/fines_support">tg</a>"""
    assert tracking_ids(html) == ["facebook_pixel:123456789012345", "google_analytics:G-AB12CD34EF"]
    found = contacts("Call 050 123 4567 or mail help@pay-fines.com", html)
    assert found["phones"] == ["+971501234567"]
    assert found["whatsapp"] == ["+971501234567"]
    assert found["telegram"] == ["fines_support"]
    assert found["emails"] == ["help@pay-fines.com"]


def test_hamming():
    assert hamming("ff00", "ff01") == 1
