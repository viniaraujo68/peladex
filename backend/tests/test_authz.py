import pytest

from tests.conftest import PELADA_TEXT


@pytest.fixture
def foreign_group(other_api):
    return other_api.group()


OWNER_ONLY = [
    ("get", "/api/groups/{gid}"),
    ("patch", "/api/groups/{gid}"),
    ("delete", "/api/groups/{gid}"),
    ("get", "/api/groups/{gid}/players"),
    ("post", "/api/groups/{gid}/players"),
    ("get", "/api/groups/{gid}/venues"),
    ("get", "/api/groups/{gid}/matchdays"),
    ("post", "/api/groups/{gid}/matchdays"),
    ("get", "/api/groups/{gid}/stats"),
    ("get", "/api/groups/{gid}/evolution"),
    ("post", "/api/groups/{gid}/import/preview"),
    ("post", "/api/groups/{gid}/import"),
]


def _call(http, method: str, url: str):
    body = {} if method in ("post", "put", "patch") else None
    return http.request(method.upper(), url, json=body)


@pytest.mark.parametrize("method,path", OWNER_ONLY)
def test_another_user_cannot_touch_the_group(api, foreign_group, method, path):
    response = _call(api.client, method, path.format(gid=foreign_group))
    assert response.status_code == 403


@pytest.mark.parametrize("method,path", OWNER_ONLY)
def test_an_anonymous_visitor_cannot_touch_the_group(client, foreign_group, method, path):
    response = _call(client, method, path.format(gid=foreign_group))
    assert response.status_code == 401


def test_a_private_group_needs_its_share_token(api, client):
    gid = api.group(visibility="private")
    slug = api.last_group["slug"]
    assert client.get(f"/api/public/{slug}").status_code == 403

    token = api.post(f"/api/groups/{gid}/rotate-share-token").json()["share_token"]
    assert client.get(f"/api/public/{slug}?t={token}").status_code == 200
    assert client.get(f"/api/public/{slug}?t=wrong").status_code == 403


def test_a_public_group_is_readable_by_anyone(api, client):
    gid = api.group(visibility="public")
    slug = api.last_group["slug"]
    api.import_text(gid, PELADA_TEXT)

    body = client.get(f"/api/public/{slug}").json()
    assert body["stats"]["total_matchdays"] == 1
    assert len(body["matchdays"]) == 1
    assert body["matchdays"][0]["mvp_name"] == "golin"

    player_id = body["stats"]["ranking"][0]["player_id"]
    detail = client.get(f"/api/public/{slug}/players/{player_id}")
    assert detail.status_code == 200
    assert detail.json()["summary"]["matchdays"] == 1


def test_a_missing_slug_is_a_404(client):
    assert client.get("/api/public/nao-existe").status_code == 404
