import socket

import pytest

from app.workers import safety


def resolves_to(*ips):
    def fake(host, port, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in ips]

    return fake


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.0.5",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",
        "::1",
        "fc00::1",
        "fe80::1",
        "::ffff:127.0.0.1",
        "224.0.0.1",
    ],
)
def test_blocks_non_public_addresses(monkeypatch, ip):
    monkeypatch.setattr(safety, "_resolve", resolves_to(ip))
    with pytest.raises(safety.UnsafeURL):
        safety.assert_public_url("https://looks-normal.example/")


def test_blocks_when_any_record_is_private(monkeypatch):
    monkeypatch.setattr(safety, "_resolve", resolves_to("93.184.216.34", "10.0.0.1"))
    with pytest.raises(safety.UnsafeURL):
        safety.assert_public_url("https://mixed.example/")


def test_allows_public_address(monkeypatch):
    monkeypatch.setattr(safety, "_resolve", resolves_to("93.184.216.34"))
    assert safety.assert_public_url("https://public.example/") == ["93.184.216.34"]


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://files.example/",
        "http://user:pw@site.example/",
        "http://site.example:22/",
        "http:///no-host",
    ],
)
def test_rejects_bad_url_shapes(url):
    with pytest.raises(safety.UnsafeURL):
        safety.assert_public_url(url)


def test_unresolvable_host_is_unsafe(monkeypatch):
    def nx(*_args, **_kwargs):
        raise socket.gaierror("NXDOMAIN")

    monkeypatch.setattr(safety, "_resolve", nx)
    with pytest.raises(safety.UnsafeURL, match="cannot resolve"):
        safety.assert_public_url("https://missing.test/")
