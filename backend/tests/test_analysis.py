SEASON = """2026-09-03
BRANCO: ana, bia, caio
AZUL: davi, edu, fabio
BRANCO 1x0 AZUL: ana (bia)
BRANCO 2x0 AZUL: ana (bia), bia
---
2026-09-10
BRANCO: ana, bia, davi
AZUL: caio, edu, fabio
BRANCO 1x0 AZUL: bia (ana)
BRANCO 3x0 AZUL: ana, ana (bia), bia
---
2026-09-17
BRANCO: ana, bia, edu
AZUL: caio, davi, fabio
BRANCO 2x1 AZUL: ana (bia), bia, caio
BRANCO 1x0 AZUL: ana (bia)
---
2026-09-24
BRANCO: ana, bia, fabio
AZUL: caio, davi, edu
AZUL 1x0 BRANCO: caio (davi)
BRANCO 1x0 AZUL: ana
"""


def seeded(api):
    group = api.group()
    assert api.import_text(group, SEASON).status_code == 200
    return group


def players_of(api, group):
    return {p["name"]: p["id"] for p in api.get(f"/api/groups/{group}/players").json()}


def combo(api, group, **sides):
    response = api.post(f"/api/groups/{group}/combo", json=sides)
    assert response.status_code == 200
    return response.json()


def test_the_period_filter_narrows_every_number(api):
    group = seeded(api)
    everything = api.get(f"/api/groups/{group}/stats").json()
    assert everything["total_matchdays"] == 4
    assert everything["first_date"] == "2026-09-03"
    assert everything["last_date"] == "2026-09-24"

    window = api.get(
        f"/api/groups/{group}/stats?date_from=2026-09-10&date_to=2026-09-17"
    ).json()
    assert window["total_matchdays"] == 2
    assert window["first_date"] == "2026-09-10"
    assert window["last_date"] == "2026-09-17"
    assert window["total_goals"] < everything["total_goals"]

    by_name = {r["name"]: r for r in window["ranking"]}
    assert by_name["ana"]["matchdays"] == 2


def test_the_period_filter_reaches_the_evolution_chart(api):
    group = seeded(api)
    full = api.get(f"/api/groups/{group}/evolution").json()
    window = api.get(f"/api/groups/{group}/evolution?date_from=2026-09-17").json()
    assert len(full["dates"]) == 4
    assert len(window["dates"]) == 2


def test_presence_and_streaks_are_reported(api):
    group = seeded(api)
    by_name = {r["name"]: r for r in api.get(f"/api/groups/{group}/stats").json()["ranking"]}
    assert by_name["ana"]["presence"] == 1.0
    assert by_name["ana"]["matchdays"] == 4
    assert by_name["ana"]["best_title_streak"] == 3
    assert by_name["ana"]["title_streak"] == 0
    assert by_name["ana"]["recent_win_rate"] is not None


def test_the_ranking_counts_the_goals_each_players_team_conceded(api):
    group = seeded(api)
    by_name = {r["name"]: r for r in api.get(f"/api/groups/{group}/stats").json()["ranking"]}
    ana = by_name["ana"]
    assert ana["goals_conceded"] == 2
    assert ana["goals_conceded_per_match"] == 2 / 8
    assert ana["goals_conceded_per_matchday"] == 2 / 4
    assert by_name["caio"]["goals_conceded"] == 8


def test_assists_reach_the_ranking(api):
    group = seeded(api)
    stats = api.get(f"/api/groups/{group}/stats").json()
    by_name = {r["name"]: r for r in stats["ranking"]}
    assert by_name["bia"]["assists"] == 5
    assert by_name["ana"]["assists"] == 1
    assert by_name["ana"]["contributions"] == by_name["ana"]["goals"] + 1

    assert by_name["ana"]["matchdays"] == 4


def test_the_pair_board_ranks_who_assists_whom(api):
    group = seeded(api)
    board = api.get(f"/api/groups/{group}/pairs").json()
    assert sum(link["goals"] for link in board["assists"]) == 7
    top = board["assists"][0]
    assert (top["assist_name"], top["scorer_name"], top["goals"]) == ("bia", "ana", 5)


def test_the_pair_leaderboard_respects_the_minimum(api):
    group = seeded(api)
    strict = api.get(f"/api/groups/{group}/pairs?min_days=4").json()
    assert strict["min_days"] == 4
    assert [(r["player_a"], r["player_b"]) for r in strict["together"]] == [("ana", "bia")]
    assert strict["together"][0]["days"] == 4

    ana_bia = strict["together"][0]
    assert (ana_bia["assists_a_to_b"], ana_bia["assists_b_to_a"]) == (1, 5)

    loose = api.get(f"/api/groups/{group}/pairs?min_days=1&limit=50").json()
    assert len(loose["together"]) > 1
    assert loose["together"][0]["delta"] >= loose["together"][-1]["delta"]


def test_a_pair_shows_the_same_win_rate_as_its_combo(api):
    group = seeded(api)
    ids = players_of(api, group)
    row = api.get(f"/api/groups/{group}/pairs?min_days=4").json()["together"][0]
    assert row["win_rate"] == combo(api, group, together=[ids["ana"], ids["bia"]])["win_rate"]
    assert abs(row["delta"] - (row["win_rate"] - row["expected"])) < 1e-9


def test_rivalries_put_the_player_who_wins_more_first(api):
    group = seeded(api)
    board = api.get(f"/api/groups/{group}/rivalries?min_days=3").json()
    assert board["min_days"] == 3
    rows = {frozenset((r["leader"], r["trailer"])): r for r in board["lopsided"]}
    ana_caio = rows[frozenset(("ana", "caio"))]
    assert (ana_caio["leader"], ana_caio["trailer"]) == ("ana", "caio")
    assert (ana_caio["wins"], ana_caio["draws"], ana_caio["losses"]) == (5, 0, 1)
    assert (ana_caio["days"], ana_caio["matches"]) == (3, 6)
    assert ana_caio["win_rate"] == 15 / 18
    rates = [r["win_rate"] for r in board["lopsided"]]
    assert rates == sorted(rates, reverse=True)


def test_rivalries_match_the_head_to_head_combo(api):
    group = seeded(api)
    board = api.get(f"/api/groups/{group}/rivalries?min_days=1&limit=50").json()
    for row in board["lopsided"]:
        result = combo(api, group, together=[row["leader_id"]], against=[row["trailer_id"]])
        assert (result["wins"], result["draws"], result["losses"]) == (
            row["wins"], row["draws"], row["losses"])
        assert result["days"] == row["days"]


def test_classics_are_the_pairs_that_faced_each_other_most(api):
    group = seeded(api)
    board = api.get(f"/api/groups/{group}/rivalries?min_days=1&limit=50").json()
    matches = [r["matches"] for r in board["classics"]]
    assert matches == sorted(matches, reverse=True)
    assert len(board["classics"]) == len(board["lopsided"])


def test_the_closest_rivalries_have_the_smallest_gap_between_wins_and_losses(api):
    group = seeded(api)
    board = api.get(f"/api/groups/{group}/rivalries?min_days=1&limit=50").json()
    gaps = [abs(r["wins"] - r["losses"]) / r["matches"] for r in board["balanced"]]
    assert gaps == sorted(gaps)
    assert len(board["balanced"]) == len(board["lopsided"])


def test_combo_measures_players_on_the_same_team(api):
    group = seeded(api)
    ids = players_of(api, group)
    result = combo(api, group, together=[ids["ana"], ids["bia"]])
    assert result["days"] == 4
    assert result["matches"] == 8
    assert result["wins"] + result["draws"] + result["losses"] == 8
    assert result["dates"] == ["2026-09-03", "2026-09-10", "2026-09-17", "2026-09-24"]


def test_combo_skips_days_where_they_were_split(api):
    group = seeded(api)
    ids = players_of(api, group)
    result = combo(api, group, together=[ids["ana"], ids["caio"]])
    assert result["days"] == 1
    assert result["dates"] == ["2026-09-03"]


def test_combo_can_pit_one_side_against_another(api):
    group = seeded(api)
    ids = players_of(api, group)
    result = combo(api, group, together=[ids["ana"], ids["bia"]], against=[ids["caio"]])
    assert result["days"] == 3
    assert result["matches"] == 6


def test_combo_counts_each_players_goals_and_assists_in_those_matches(api):
    group = seeded(api)
    ids = players_of(api, group)
    result = combo(api, group, together=[ids["ana"]], against=[ids["caio"]])
    scoring = {p["name"]: (p["goals"], p["assists"]) for p in result["players"]}
    assert scoring == {"ana": (5, 1), "caio": (2, 0)}
    reverse = combo(api, group, together=[ids["caio"]], against=[ids["ana"]])
    caio = next(p for p in result["players"] if p["name"] == "caio")
    assert caio["win_rate"] == reverse["win_rate"]
    assert result["goals_for"] > scoring["ana"][0]


def test_combo_players_carry_ranking_rows_from_their_own_side(api):
    group = seeded(api)
    ids = players_of(api, group)
    result = combo(api, group, together=[ids["ana"], ids["bia"]], against=[ids["caio"]])
    rows = {p["name"]: p for p in result["players"]}
    for name in ("ana", "bia"):
        row = rows[name]
        assert (row["matchdays"], row["matches"]) == (3, 6)
        assert (row["wins"], row["draws"], row["losses"]) == (
            result["wins"], result["draws"], result["losses"]
        )
        assert row["goals_conceded"] == result["goals_against"]
        assert row["win_rate"] == result["win_rate"]
    caio = rows["caio"]
    assert (caio["wins"], caio["losses"]) == (result["losses"], result["wins"])
    assert caio["goals_conceded"] == result["goals_for"]


def test_combo_players_carry_the_day_level_numbers_of_those_days(api):
    group = seeded(api)
    ids = players_of(api, group)
    overall = {r["name"]: r for r in api.get(f"/api/groups/{group}/stats").json()["ranking"]}
    result = combo(api, group, together=[ids["ana"], ids["bia"]])
    ana = next(p for p in result["players"] if p["name"] == "ana")
    for key in ("titles", "top_scorer_days", "mvp_count", "matchdays", "win_rate"):
        assert ana[key] == overall["ana"][key]
    assert len(ana["recent_form"]) == 4
    assert ana["presence"] == 1.0
    split = combo(api, group, together=[ids["ana"], ids["caio"]])
    assert next(p for p in split["players"] if p["name"] == "ana")["presence"] == 0.25


def test_combo_lists_the_assists_between_the_chosen_players(api):
    group = seeded(api)
    ids = players_of(api, group)
    result = combo(api, group, together=[ids["ana"], ids["bia"]], against=[ids["caio"]])
    links = [
        (link["assist_name"], link["scorer_name"], link["goals"]) for link in result["assist_links"]
    ]
    assert links == [("bia", "ana", 3), ("ana", "bia", 1)]
    assert combo(api, group, together=[ids["ana"]], against=[ids["caio"]])["assist_links"] == []


def test_the_combo_follows_the_period(api):
    group = seeded(api)
    ids = players_of(api, group)
    result = combo(api, group, together=[ids["ana"], ids["bia"]], date_from="2026-09-17")
    assert (result["days"], result["matches"]) == (2, 4)


def test_a_combo_side_takes_at_most_eight_players(api):
    group = seeded(api)
    url = f"/api/groups/{group}/combo"
    assert api.post(url, json={"together": list(range(1, 10))}).status_code == 422


def test_the_public_surface_exposes_the_new_views(api, client):
    group = api.group(visibility="public")
    slug = api.last_group["slug"]
    api.import_text(group, SEASON)
    ids = players_of(api, group)

    assert client.get(f"/api/public/{slug}/pairs?min_days=1").status_code == 200
    assert client.get(f"/api/public/{slug}/rivalries?min_days=1").status_code == 200
    url = f"/api/public/{slug}/combo"
    together = client.post(url, json={"together": [ids["ana"], ids["bia"]]})
    assert together.status_code == 200
    assert together.json()["days"] == 4
    assert client.post(url, json={"together": [ids["ana"]], "against": [ids["bia"]]}).json()["days"] == 0

    body = client.get(f"/api/public/{slug}?date_from=2026-09-17").json()
    assert body["stats"]["total_matchdays"] == 2
    assert body["track_assists"] is False


def test_the_public_period_filters_the_stats_but_lists_every_matchday(api, client):
    group = api.group(visibility="public")
    slug = api.last_group["slug"]
    api.import_text(group, SEASON)

    body = client.get(f"/api/public/{slug}?date_from=2026-09-10&date_to=2026-09-17").json()
    assert body["stats"]["total_matchdays"] == 2
    assert len(body["matchdays"]) == 4


SPLIT_SEASON = """2026-09-03 @ Campo do Ze
BRANCO: ana, bia
AZUL: caio, davi
BRANCO 2x0 AZUL: ana (bia), ana
---
2026-09-10 @ Campo do Ze
BRANCO: ana, caio
AZUL: bia, davi
BRANCO 0x1 AZUL: bia
---
2026-09-17 @ Society
VERDE: ana, davi
AZUL: bia, caio
VERDE 1x1 AZUL: ana, caio
"""


def test_partner_stats_compare_with_against_without(api):
    group = api.group()
    api.import_text(group, SPLIT_SEASON)
    ids = players_of(api, group)
    detail = api.get(
        f"/api/groups/{group}/players/{ids['ana']}/detail?min_days=1"
    ).json()

    bia = next(p for p in detail["partners"] if p["name"] == "bia")
    assert (bia["days"], bia["days_without"]) == (1, 2)
    assert bia["win_rate"] == 1.0
    assert bia["win_rate_without"] is not None
    assert round(bia["delta"], 6) == round(bia["win_rate"] - bia["win_rate_without"], 6)


def test_opponent_stats_compare_facing_against_not_facing(api):
    group = api.group()
    api.import_text(group, SPLIT_SEASON)
    ids = players_of(api, group)
    detail = api.get(
        f"/api/groups/{group}/players/{ids['ana']}/detail?min_days=1"
    ).json()

    caio = next(p for p in detail["opponents"] if p["name"] == "caio")
    assert caio["days"] == 2
    assert caio["days_without"] >= 1


def test_a_player_who_never_played_apart_has_no_delta(api):
    group = api.group()
    api.import_text(group, "2026-09-03\nBRANCO: ana, bia\nAZUL: caio\nBRANCO 1x0 AZUL: ana\n")
    ids = players_of(api, group)
    detail = api.get(
        f"/api/groups/{group}/players/{ids['ana']}/detail?min_days=1"
    ).json()
    bia = next(p for p in detail["partners"] if p["name"] == "bia")
    assert bia["days_without"] == 0
    assert bia["delta"] is None


def test_the_timeline_reports_goals_per_matchday_and_per_match(api):
    group = seeded(api)
    timeline = api.get(f"/api/groups/{group}/timeline").json()
    assert len(timeline["points"]) == 4
    first = timeline["points"][0]
    assert (first["date"], first["matches"], first["goals"]) == ("2026-09-03", 2, 3)
    assert round(first["goals_per_match"], 6) == 1.5
    assert first["players"] == 6

    total_matches = sum(p["matches"] for p in timeline["points"])
    total_goals = sum(p["goals"] for p in timeline["points"])
    assert round(timeline["goals_per_match"], 6) == round(total_goals / total_matches, 6)
    assert round(timeline["goals_per_matchday"], 6) == round(total_goals / 4, 6)


def test_the_timeline_distribution_normalises_scorelines(api):
    group = seeded(api)
    timeline = api.get(f"/api/groups/{group}/timeline").json()
    labels = {row["label"]: row for row in timeline["scorelines"]}
    assert all(int(k.split("x")[0]) >= int(k.split("x")[1]) for k in labels)
    assert sum(row["count"] for row in timeline["scorelines"]) == sum(
        p["matches"] for p in timeline["points"]
    )
    assert abs(sum(row["share"] for row in timeline["scorelines"]) - 1.0) < 1e-9


def test_the_timeline_honours_the_period(api):
    group = seeded(api)
    window = api.get(f"/api/groups/{group}/timeline?date_from=2026-09-17").json()
    assert len(window["points"]) == 2


def test_evolution_carries_cumulative_goals_and_assists(api):
    group = seeded(api)
    evolution = api.get(f"/api/groups/{group}/evolution").json()
    ana = next(s for s in evolution["series"] if s["name"] == "ana")
    goals = [p["goals"] for p in ana["points"]]
    assert goals == sorted(goals)
    assert goals[-1] > 0
    assists = [p["assists"] for p in ana["points"]]
    assert assists[-1] == 1


def test_the_public_timeline_is_reachable(api, client):
    group = api.group(visibility="public")
    slug = api.last_group["slug"]
    api.import_text(group, SEASON)
    r = client.get(f"/api/public/{slug}/timeline")
    assert r.status_code == 200
    assert len(r.json()["points"]) == 4
