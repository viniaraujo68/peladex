import pytest

from app.services import min_qualifying_matchdays
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

GUEST_ON_THE_LAST_DAY = """2026-09-03
BRANCO: ana, bia
AZUL: caio, davi
BRANCO 1x0 AZUL: ana
AZUL 1x0 BRANCO: caio
---
2026-09-10
BRANCO: ana, bia
AZUL: caio, davi
BRANCO 1x0 AZUL: bia
AZUL 2x0 BRANCO: caio, davi
---
2026-09-17
BRANCO: ana, zeca
AZUL: caio, davi
BRANCO 1x0 AZUL: zeca
BRANCO 2x0 AZUL: zeca, ana
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


@pytest.mark.parametrize(
    ("total", "expected"),
    [(0, 0), (1, 1), (2, 1), (3, 2), (5, 2), (8, 3), (40, 3)],
)
def test_the_qualifying_minimum_is_forty_percent_of_the_days_capped_at_three(total, expected):
    assert min_qualifying_matchdays(total) == expected


def test_players_below_the_minimum_rank_after_the_qualified_ones(api, group):
    api.import_text(group, GUEST_ON_THE_LAST_DAY)
    stats = api.get(f"/api/groups/{group}/stats").json()
    assert stats["min_matchdays"] == 2

    by_name = {row["name"]: row for row in stats["ranking"]}
    assert by_name["zeca"]["win_rate"] == 1.0
    assert by_name["zeca"]["qualified"] is False
    assert all(by_name[name]["qualified"] for name in ("ana", "bia", "caio", "davi"))
    assert stats["ranking"][-1]["name"] == "zeca"


def test_goal_rates_are_reported_per_match_and_per_day(api, group):
    api.import_text(group, FOUR_DAYS)
    ana = next(
        row for row in api.get(f"/api/groups/{group}/stats").json()["ranking"]
        if row["name"] == "ana"
    )
    assert (ana["goals"], ana["matches"], ana["matchdays"]) == (7, 8, 4)
    assert ana["goals_per_match"] == pytest.approx(7 / 8)
    assert ana["goals_per_matchday"] == pytest.approx(7 / 4)
    assert ana["contributions_per_match"] == pytest.approx(7 / 8)
    assert ana["assists_per_match"] == 0


def test_goal_share_is_measured_against_the_goals_of_the_players_teams(api, group):
    api.import_text(group, FOUR_DAYS)
    by_name = {
        row["name"]: row for row in api.get(f"/api/groups/{group}/stats").json()["ranking"]
    }
    assert by_name["ana"]["team_goals"] == 11
    assert by_name["ana"]["goal_share"] == pytest.approx(7 / 11)
    assert by_name["ana"]["contribution_share"] == pytest.approx(7 / 11)
    assert by_name["fabio"]["team_goals"] == 2
    assert by_name["fabio"]["goal_share"] == 0


def test_goal_share_is_empty_when_the_players_teams_never_scored(api, group):
    api.import_text(group, """2026-09-24
BRANCO: ana, bia
AZUL: caio, gil
AZUL 1x0 BRANCO: caio
""")
    by_name = {
        row["name"]: row for row in api.get(f"/api/groups/{group}/stats").json()["ranking"]
    }
    assert by_name["ana"]["team_goals"] == 0
    assert by_name["ana"]["goal_share"] is None
    assert by_name["gil"]["team_goals"] == 1
    assert by_name["gil"]["goal_share"] == 0


def test_evolution_carries_the_running_matches_and_days(api, group):
    api.import_text(group, GUEST_ON_THE_LAST_DAY)
    evolution = api.get(f"/api/groups/{group}/evolution").json()
    series = {s["name"]: s["points"] for s in evolution["series"]}
    assert [(p["matches"], p["matchdays"]) for p in series["bia"]] == [(2, 1), (4, 2), (4, 2)]
    assert [(p["matches"], p["matchdays"]) for p in series["zeca"]] == [
        (None, None), (None, None), (2, 1)
    ]
