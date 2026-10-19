import pytest

TWO_ROTATION_DAYS_THEN_A_SINGLE_GAME = """2026-09-03
BRANCO: ana, bia
AZUL: caio, davi
BRANCO 1x0 AZUL: ana
AZUL 0x0 BRANCO
---
2026-09-10
BRANCO: ana, caio
AZUL: bia, davi
AZUL 2x0 BRANCO: bia, davi
BRANCO 1x1 AZUL: ana, davi
---
2026-10-14
AZUL: ana, bia, zeca
VERMELHO: caio, davi
AZUL 4x2 VERMELHO: ana x3, zeca, caio, davi
MVP: ana
"""

ONLY_SINGLE_GAMES = """2026-10-14
AZUL: ana, bia
VERMELHO: caio, davi
AZUL 4x2 VERMELHO: ana x3, bia, caio, davi
---
2026-10-21
AZUL: ana, caio
VERMELHO: bia, davi
AZUL 1x3 VERMELHO: ana, bia, bia, davi
"""


@pytest.fixture
def season(api, group) -> int:
    assert api.import_text(group, TWO_ROTATION_DAYS_THEN_A_SINGLE_GAME).status_code == 200
    return group


def stats(api, group, query=""):
    return api.get(f"/api/groups/{group}/stats{query}").json()


def ranking(api, group, query="") -> dict[str, dict]:
    return {row["name"]: row for row in stats(api, group, query)["ranking"]}


def player_ids(api, group) -> dict[str, int]:
    return {p["name"]: p["id"] for p in api.get(f"/api/groups/{group}/players").json()}


def test_the_rotation_view_is_the_default_when_there_are_rotation_days(api, season):
    body = stats(api, season)
    assert body["days"] == {
        "day_type": "rotation", "rotation_matchdays": 2, "single_game_matchdays": 1,
    }
    assert body["total_matchdays"] == 2
    ana = {row["name"]: row for row in body["ranking"]}["ana"]
    assert (ana["matchdays"], ana["matches"], ana["goals"], ana["titles"]) == (2, 4, 2, 1)
    assert ana["win_rate"] == pytest.approx(5 / 12)
    assert ana["mvp_count"] == 0
    assert "zeca" not in {row["name"] for row in body["ranking"]}


def test_the_single_game_view_counts_only_single_games(api, season):
    body = stats(api, season, "?day_type=single")
    assert body["days"]["day_type"] == "single"
    assert (body["total_matchdays"], body["total_matches"], body["total_goals"]) == (1, 1, 6)
    rows = {row["name"]: row for row in body["ranking"]}
    assert set(rows) == {"ana", "bia", "zeca", "caio", "davi"}
    ana = rows["ana"]
    assert (ana["matches"], ana["wins"], ana["goals"], ana["titles"], ana["mvp_count"]) == (
        1, 1, 3, 1, 1
    )
    assert ana["win_rate"] == 1.0
    assert ana["goal_share"] == pytest.approx(3 / 4)


def test_the_all_view_mixes_every_day(api, season):
    body = stats(api, season, "?day_type=all")
    assert body["days"]["day_type"] == "all"
    assert body["total_matchdays"] == 3
    ana = {row["name"]: row for row in body["ranking"]}["ana"]
    assert (ana["matchdays"], ana["matches"], ana["goals"], ana["titles"]) == (3, 5, 5, 2)


def test_a_group_without_rotation_days_defaults_to_every_day(api, group):
    assert api.import_text(group, ONLY_SINGLE_GAMES).status_code == 200
    body = stats(api, group)
    assert body["days"] == {
        "day_type": "all", "rotation_matchdays": 0, "single_game_matchdays": 2,
    }
    assert body["total_matchdays"] == 2


def test_an_unknown_day_type_is_rejected(api, season):
    assert api.get(f"/api/groups/{season}/stats?day_type=both").status_code == 422


def test_a_day_with_two_teams_and_several_matches_is_a_rotation_day(api, season):
    body = stats(api, season, "?date_to=2026-09-10")
    assert body["days"]["single_game_matchdays"] == 0
    assert body["days"]["rotation_matchdays"] == 2


def test_the_player_detail_follows_the_day_type(api, season):
    ana = player_ids(api, season)["ana"]
    rotation = api.get(f"/api/groups/{season}/players/{ana}/detail").json()
    assert rotation["days"]["day_type"] == "rotation"
    assert [row["single_game"] for row in rotation["history"]] == [False, False]

    single = api.get(f"/api/groups/{season}/players/{ana}/detail?day_type=single").json()
    assert [row["single_game"] for row in single["history"]] == [True]
    assert single["summary"]["goals"] == 3


def test_evolution_timeline_and_assists_follow_the_day_type(api, season):
    base = f"/api/groups/{season}"
    assert api.get(f"{base}/evolution").json()["dates"] == ["2026-09-03", "2026-09-10"]
    assert api.get(f"{base}/evolution?day_type=single").json()["dates"] == ["2026-10-14"]

    timeline = api.get(f"{base}/timeline?day_type=all").json()
    assert [point["single_game"] for point in timeline["points"]] == [False, False, True]
    assert len(api.get(f"{base}/timeline").json()["points"]) == 2


def test_pairs_follow_the_day_type(api, season):
    base = f"/api/groups/{season}/pairs?min_days=1"
    rotation = api.get(base).json()
    single = api.get(f"{base}&day_type=single").json()
    names = lambda board: {(r["player_a"], r["player_b"]) for r in board["together"]}  # noqa: E731
    assert not any("zeca" in pair for pair in names(rotation))
    assert any("zeca" in pair for pair in names(single))


def test_the_combo_follows_the_day_type(api, season):
    ana = player_ids(api, season)["ana"]
    url = f"/api/groups/{season}/combo"
    assert api.post(url, json={"together": [ana]}).json()["days"] == 2
    assert api.post(url, json={"together": [ana], "day_type": "single"}).json()["days"] == 1
    assert api.post(url, json={"together": [ana], "day_type": "all"}).json()["days"] == 3


def test_the_matchday_list_keeps_every_day_and_flags_the_single_game(api, season):
    matchdays = api.get(f"/api/groups/{season}/matchdays").json()
    flags = {day["date"]: day["single_game"] for day in matchdays}
    assert flags == {"2026-09-03": False, "2026-09-10": False, "2026-10-14": True}


def test_the_public_group_splits_the_stats_but_lists_every_day(api, client):
    group = api.group(visibility="public")
    slug = api.last_group["slug"]
    api.import_text(group, TWO_ROTATION_DAYS_THEN_A_SINGLE_GAME)

    default = client.get(f"/api/public/{slug}").json()
    assert default["stats"]["days"]["day_type"] == "rotation"
    assert default["stats"]["total_matchdays"] == 2
    assert len(default["matchdays"]) == 3
    assert default["evolution"]["dates"] == ["2026-09-03", "2026-09-10"]

    single = client.get(f"/api/public/{slug}?day_type=single").json()
    assert single["stats"]["total_matchdays"] == 1
    assert len(single["matchdays"]) == 3

    ana = {row["name"]: row["player_id"] for row in single["stats"]["ranking"]}["ana"]
    detail = client.get(f"/api/public/{slug}/players/{ana}?day_type=single").json()
    assert detail["summary"]["goals"] == 3
    timeline = client.get(f"/api/public/{slug}/timeline?day_type=single").json()
    assert len(timeline["points"]) == 1
