import re

import pytest
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.main import app
from tests.conftest import BACKEND_ROOT, unique

EDGE = "172.18.0.4"
VISITOR = "203.0.113.8"
PUBLIC_PEER = "198.51.100.77"
LOGIN_LIMIT = 5


def trusted_proxies() -> str:
    match = re.search(r'"--forwarded-allow-ips=([^"]+)"', (BACKEND_ROOT / "Dockerfile").read_text())
    assert match, "the Dockerfile no longer sets --forwarded-allow-ips"
    return match.group(1)


def deployed(peer: str) -> TestClient:
    return TestClient(ProxyHeadersMiddleware(app, trusted_hosts=trusted_proxies()), client=(peer, 40000))


def bad_logins(client: TestClient, forwarded_for: list[str]) -> list[int]:
    name = unique("xff")
    return [
        client.post("/api/auth/login", json={"username": name, "password": "wrong-password"},
                    headers={"X-Forwarded-For": value}).status_code
        for value in forwarded_for
    ]


def test_the_dockerfile_trusts_only_internal_peers():
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text()
    assert "--proxy-headers" in dockerfile
    assert trusted_proxies() != "*"


@pytest.mark.ratelimit
def test_a_forged_leftmost_hop_does_not_escape_the_login_limit(rate_limits):
    hops = [f"198.51.100.{i}, {VISITOR}" for i in range(LOGIN_LIMIT + 1)]
    statuses = bad_logins(deployed(EDGE), hops)
    assert statuses[:LOGIN_LIMIT] == [401] * LOGIN_LIMIT
    assert statuses[LOGIN_LIMIT] == 429


@pytest.mark.ratelimit
def test_visitors_behind_the_edge_keep_separate_limits(rate_limits):
    visitors = [f"203.0.113.{i}" for i in range(1, LOGIN_LIMIT + 2)]
    assert 429 not in bad_logins(deployed(EDGE), visitors)


@pytest.mark.ratelimit
def test_a_public_peer_cannot_choose_its_address(rate_limits):
    forged = [f"203.0.113.{i}" for i in range(1, LOGIN_LIMIT + 2)]
    statuses = bad_logins(deployed(PUBLIC_PEER), forged)
    assert statuses[LOGIN_LIMIT] == 429
