from datetime import date, timedelta

from tests.conftest import PELADA_TEXT

START = date(2026, 1, 8)


def _seed(api, group, days: int) -> None:
    for week in range(days):
        day = START + timedelta(weeks=week)
        text = (
            f"{day.isoformat()}\n"
            "BRANCO: ana, bia\nAZUL: caio, davi\n"
            "BRANCO 1x0 AZUL: ana\nAZUL 2x1 BRANCO: caio, davi, bia\n"
        )
        assert api.import_text(group, text).status_code == 200, day


def test_listing_matchdays_does_not_scale_its_query_count(api, queries):
    group = api.group()
    _seed(api, group, 2)
    with queries as q:
        api.get(f"/api/groups/{group}/matchdays")
    small = q.count

    bigger = api.group()
    _seed(api, bigger, 8)
    with queries as q:
        api.get(f"/api/groups/{bigger}/matchdays")
    assert q.count == small


def test_stats_do_not_scale_their_query_count(api, queries):
    group = api.group()
    _seed(api, group, 2)
    with queries as q:
        api.get(f"/api/groups/{group}/stats")
    small = q.count

    bigger = api.group()
    _seed(api, bigger, 8)
    with queries as q:
        api.get(f"/api/groups/{bigger}/stats")
    assert q.count == small


def test_listing_groups_does_not_scale_its_query_count(api, queries):
    api.group()
    with queries as q:
        api.get("/api/groups")
    one = q.count

    for _ in range(5):
        api.group()
    with queries as q:
        api.get("/api/groups")
    assert q.count == one


def test_the_public_page_is_one_bounded_read(api, client, queries):
    group = api.group(visibility="public")
    slug = api.last_group["slug"]
    api.import_text(group, PELADA_TEXT)
    with queries as q:
        client.get(f"/api/public/{slug}")
    assert q.count < 30
