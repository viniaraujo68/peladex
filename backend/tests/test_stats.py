from tests.conftest import PELADA_TEXT

FOUR_DAYS = """2026-09-03
BRANCO: ana, bia, caio
AZUL: davi, edu, fabio
BRANCO 1x0 AZUL: ana
BRANCO 2x0 AZUL: ana, bia
---
2026-09-10
BRANCO: ana, bia, davi
AZUL: caio, edu, fabio
BRANCO 1x0 AZUL: bia
BRANCO 3x0 AZUL: ana, ana, bia
---
2026-09-17
BRANCO: ana, bia, edu
AZUL: caio, davi, fabio
BRANCO 2x1 AZUL: ana, bia, caio
BRANCO 1x0 AZUL: ana
---
2026-09-24
BRANCO: ana, bia, fabio
AZUL: caio, davi, edu
AZUL 1x0 BRANCO: caio
BRANCO 1x0 AZUL: ana
"""


def test_the_real_matchday_produces_the_expected_table(api, group):
    api.import_text(group, PELADA_TEXT)
    stats = api.get(f"/api/groups/{group}/stats").json()
    assert stats["total_matchdays"] == 1
    assert stats["total_matches"] == 8
    assert stats["total_goals"] == 6

    by_name = {row["name"]: row for row in stats["ranking"]}
    golin = by_name["golin"]
    assert golin["matches"] == 6
    assert (golin["wins"], golin["draws"], golin["losses"]) == (3, 3, 0)
    assert golin["points"] == 12
    assert round(golin["win_rate"], 4) == round(12 / 18, 4)
    assert golin["goals"] == 3
    assert golin["titles"] == 1
    assert golin["mvp_count"] == 1

    vini = by_name["vini"]
    assert vini["points"] == 4
    assert round(vini["win_rate"], 4) == round(4 / 15, 4)
    assert vini["titles"] == 0

    ney = by_name["ney"]
    assert (ney["wins"], ney["draws"], ney["losses"]) == (0, 3, 2)
    assert ney["points"] == 3


def test_the_stats_report_the_draw_rate(api, group):
    api.import_text(group, PELADA_TEXT)
    stats = api.get(f"/api/groups/{group}/stats").json()
    assert round(stats["draw_rate"], 6) == round(5 / 8, 6)


def test_evolution_pads_series_before_a_player_debuts(api, group):
    api.import_text(group, FOUR_DAYS)
    evolution = api.get(f"/api/groups/{group}/evolution").json()
    assert len(evolution["dates"]) == 4
    for series in evolution["series"]:
        assert len(series["points"]) == 4
        assert series["points"][-1]["win_rate"] is not None


def test_partner_stats_need_a_minimum_of_shared_days(api, group):
    api.import_text(group, FOUR_DAYS)
    players = {p["name"]: p["id"] for p in api.get(f"/api/groups/{group}/players").json()}

    tight = api.get(
        f"/api/groups/{group}/players/{players['ana']}/detail?min_days=4"
    ).json()
    assert [p["name"] for p in tight["partners"]] == ["bia"]
    assert tight["partners"][0]["days"] == 4

    loose = api.get(
        f"/api/groups/{group}/players/{players['ana']}/detail?min_days=1"
    ).json()
    assert len(loose["partners"]) == 5

    bia = next(p for p in loose["partners"] if p["name"] == "bia")
    assert (bia["days"], bia["days_without"]) == (4, 0)
    assert bia["win_rate_without"] is None
    assert bia["delta"] is None

    caio = next(p for p in loose["partners"] if p["name"] == "caio")
    assert (caio["days"], caio["days_without"]) == (1, 3)
    assert caio["delta"] is not None


def test_partner_rate_is_measured_per_day_not_per_match(api, group):
    api.import_text(group, FOUR_DAYS)
    players = {p["name"]: p["id"] for p in api.get(f"/api/groups/{group}/players").json()}
    detail = api.get(f"/api/groups/{group}/players/{players['ana']}/detail?min_days=1").json()
    bia = next(p for p in detail["partners"] if p["name"] == "bia")
    assert bia["days"] == 4
    caio = next(p for p in detail["partners"] if p["name"] == "caio")
    assert caio["days"] == 1


def test_player_history_lists_every_day_they_played(api, group):
    api.import_text(group, FOUR_DAYS)
    players = {p["name"]: p["id"] for p in api.get(f"/api/groups/{group}/players").json()}
    detail = api.get(f"/api/groups/{group}/players/{players['ana']}/detail").json()
    assert len(detail["history"]) == 4
    assert [row["date"] for row in detail["history"]][0] == "2026-09-24"
    assert all(row["team_name"] == "branco" for row in detail["history"])
    assert detail["summary"]["titles"] == 3
    assert [row["champion"] for row in detail["history"]] == [False, True, True, True]


def test_opponent_stats_are_the_head_to_head_of_the_day(api, group):
    api.import_text(group, FOUR_DAYS)
    players = {p["name"]: p["id"] for p in api.get(f"/api/groups/{group}/players").json()}
    detail = api.get(f"/api/groups/{group}/players/{players['ana']}/detail?min_days=1").json()
    caio = next(o for o in detail["opponents"] if o["name"] == "caio")
    assert caio["days"] == 3
    bia = [o for o in detail["opponents"] if o["name"] == "bia"]
    assert bia == []


def test_a_group_with_no_matchdays_reports_empty_stats(api, group):
    stats = api.get(f"/api/groups/{group}/stats").json()
    assert stats["ranking"] == []
    assert stats["total_matchdays"] == 0
    assert stats["draw_rate"] == 0
