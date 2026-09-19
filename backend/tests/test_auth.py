import pytest

from tests.conftest import PASSWORD, unique


def test_register_logs_the_user_in(client):
    name = unique("newuser")
    r = client.post("/api/auth/register", json={"username": name, "password": PASSWORD})
    assert r.status_code == 201
    assert client.get("/api/auth/me").json()["username"] == name


def test_a_duplicate_username_is_refused(api, client):
    r = client.post("/api/auth/register",
                    json={"username": api.username, "password": PASSWORD})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "username_taken"


def test_a_wrong_password_is_refused(api, client):
    r = client.post("/api/auth/login",
                    json={"username": api.username, "password": "errada123"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_credentials"


def test_an_unknown_username_reports_the_same_error(client):
    r = client.post("/api/auth/login",
                    json={"username": unique("ghost"), "password": PASSWORD})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_credentials"


def test_logout_drops_the_session(api):
    assert api.post("/api/auth/logout").status_code == 204
    assert api.get("/api/auth/me").status_code == 401


def test_changing_the_password_keeps_this_session_and_kills_the_others(api):
    from fastapi.testclient import TestClient

    from app.main import app

    second = TestClient(app)
    assert second.post("/api/auth/login",
                       json={"username": api.username, "password": PASSWORD}).status_code == 200

    r = api.post("/api/auth/change-password",
                 json={"current_password": PASSWORD, "new_password": "novasenha1"})
    assert r.status_code == 204
    assert api.get("/api/auth/me").status_code == 200
    assert second.get("/api/auth/me").status_code == 401


def test_a_short_password_is_refused(client):
    r = client.post("/api/auth/register", json={"username": unique("short"), "password": "123"})
    assert r.status_code == 422


@pytest.mark.ratelimit
def test_login_is_rate_limited(client, rate_limits):
    name = unique("bruteforce")
    client.post("/api/auth/register", json={"username": name, "password": PASSWORD})
    statuses = [
        client.post("/api/auth/login", json={"username": name, "password": "errada"}).status_code
        for _ in range(8)
    ]
    assert 429 in statuses
