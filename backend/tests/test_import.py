import time

import pytest

from tests.conftest import PELADA_TEXT


def test_preview_reports_the_day_without_writing(api, group):
    r = api.post(f"/api/groups/{group}/import/preview", json={"text": PELADA_TEXT})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert len(body["new_players"]) == 21
    day = body["matchdays"][0]
    assert day["already_exists"] is False
    assert [s["name"] for s in day["standings"]] == ["branco", "vermelho", "azul"]
    assert [s["points"] for s in day["standings"]] == [12, 4, 3]
    assert api.get(f"/api/groups/{group}/matchdays").json() == []


def test_commit_creates_players_venue_and_the_matchday(api, group):
    r = api.import_text(group, PELADA_TEXT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["created_players"]) == 21
    assert body["replaced"] == 0

    days = api.get(f"/api/groups/{group}/matchdays").json()
    assert len(days) == 1
    day = days[0]
    assert day["date"] == "2026-09-16"
    assert day["venue_name"] == "Campo do Ze"
    assert day["mvp_name"] == "golin"
    assert day["total_goals"] == 6
    assert day["goal_mismatch"] is False
    champion = next(s for s in day["standings"] if s["team_id"] == day["champion_team_id"])
    assert champion["name"] == "branco"
    assert day["top_scorers"][0] == {"player_id": day["top_scorers"][0]["player_id"],
                                     "name": "golin", "goals": 3}


def test_importing_the_same_day_twice_conflicts_unless_replacing(api, group):
    api.import_text(group, PELADA_TEXT)
    again = api.import_text(group, PELADA_TEXT)
    assert again.status_code == 409
    assert again.json()["detail"]["code"] == "matchday_exists"

    replaced = api.import_text(group, PELADA_TEXT, replace_existing=True)
    assert replaced.status_code == 200
    assert replaced.json()["replaced"] == 1
    assert len(api.get(f"/api/groups/{group}/matchdays").json()) == 1


def test_a_second_import_reuses_the_players_already_created(api, group):
    api.import_text(group, PELADA_TEXT)
    text = (
        "2026-09-23\n"
        "BRANCO: golin, galetti\n"
        "AZUL: ney, rod\n"
        "BRANCO 1x0 AZUL\n"
        "golin\n"
    )
    r = api.import_text(group, text)
    assert r.status_code == 200
    assert r.json()["created_players"] == []
    assert len(api.get(f"/api/groups/{group}/players").json()) == 21


def test_a_text_with_errors_is_refused(api, group):
    r = api.import_text(group, "2026-09-16\nAZUL: a\nBRANCO: b\nAZUL 0x0 AZUL\n")
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "import_invalid"
    assert api.get(f"/api/groups/{group}/matchdays").json() == []


def test_new_players_are_refused_when_creation_is_off(api, group):
    r = api.post(f"/api/groups/{group}/import",
                 json={"text": PELADA_TEXT, "create_missing_players": False})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "unknown_players"


def test_several_matchdays_import_in_one_go(api, group):
    text = (
        "2026-09-16\nBRANCO: a, b\nAZUL: c, d\nBRANCO 1x0 AZUL: a\n"
        "---\n"
        "2026-09-23\nBRANCO: a, c\nAZUL: b, d\nAZUL 2x0 BRANCO: b, d\n"
    )
    r = api.import_text(group, text)
    assert r.status_code == 200
    assert len(r.json()["created_matchday_ids"]) == 2
    assert len(api.get(f"/api/groups/{group}/matchdays").json()) == 2


def preview(api, group, text):
    return api.post(f"/api/groups/{group}/import/preview", json={"text": text})


def test_a_huge_goal_count_is_an_import_error_not_a_huge_response(api, group):
    text = "2026-01-01\na: p1\nb: p2\na 1x0 b\np1(300000)\n"
    r = preview(api, group, text)
    assert r.status_code == 200
    assert len(r.content) < 10_000
    assert r.json()["ok"] is False
    assert any(i["code"] == "bad_goal_count" for i in r.json()["issues"])

    committed = api.import_text(group, text)
    assert committed.status_code == 400
    assert committed.json()["detail"]["code"] == "import_invalid"


@pytest.mark.parametrize("annotation", ["9" * 4301, "\u1369"],
                         ids=["4301_digits", "ethiopic_digit"])
def test_odd_goal_count_annotations_are_not_server_errors(api, group, annotation):
    text = f"2026-01-01\na: p1\nb: p2\na 1x0 b\np1({annotation})\n"
    assert preview(api, group, text).status_code == 200
    assert api.import_text(group, text).status_code == 400


def test_more_scorers_than_the_score_cannot_be_committed(api, group):
    r = api.import_text(group, "2026-01-01\na: p1\nb: p2\na 1x0 b: p1, p1, p2\n")
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "import_invalid"
    assert api.get(f"/api/groups/{group}/matchdays").json() == []


@pytest.mark.parametrize("text", [
    "2026-01-01\n" + "t" * 41 + ": p1\nb: p2\n",
    "2026-01-01\n: p1\nb: p2\n",
    "2026-01-01\na: " + "x" * 81 + "\nb: p2\n",
    "2026-01-01 @ " + "v" * 81 + "\na: p1\nb: p2\n",
    "2026-01-01\na: " + ", ".join(f"p{i}" for i in range(41)) + "\nb: q\n",
    "2026-01-01\n" + "\n".join(f"t{i}: p{i}" for i in range(21)) + "\n",
    "2026-01-01\na: p1\nb: p2\nObs: " + "n" * 2001 + "\n",
], ids=["team_name", "empty_team_name", "player_name", "venue_name", "team_players",
        "matchday_teams", "notes"])
def test_values_past_the_write_limits_are_refused_not_server_errors(api, group, text):
    assert preview(api, group, text).json()["ok"] is False
    r = api.import_text(group, text)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "import_invalid"
    assert api.get(f"/api/groups/{group}/players").json() == []


def test_a_full_roster_still_imports(api, group):
    home = ", ".join(f"h{i}" for i in range(40))
    away = ", ".join(f"a{i}" for i in range(40))
    r = api.import_text(group, f"2026-01-01\nbranco: {home}\nazul: {away}\nbranco 1x0 azul: h0\n")
    assert r.status_code == 200, r.text
    assert len(r.json()["created_players"]) == 80


@pytest.mark.timing
def test_a_200k_single_line_preview_is_fast_and_small(api, group):
    text = ("2026-01-01\na: p1\nb: p2\nc: " + "p1 " * 100_000)[:200_000]
    start = time.perf_counter()
    r = preview(api, group, text)
    assert time.perf_counter() - start < 3.0
    assert r.status_code == 200
    assert len(r.content) < 200_000


@pytest.mark.ratelimit
@pytest.mark.parametrize("path", ["import/preview", "import"])
def test_the_import_routes_are_rate_limited(api, group, rate_limits, path):
    statuses = [
        api.post(f"/api/groups/{group}/{path}", json={"text": "x"}).status_code
        for _ in range(25)
    ]
    assert 429 in statuses


def test_issues_carry_their_parameters_for_translation(api, group):
    r = preview(api, group, "2026-09-16\nAZUL: ana\nBRANCO: bia\nAZUL 1x0 ROXO\n")
    assert r.status_code == 200
    issue = next(i for i in r.json()["issues"] if i["code"] == "unknown_team")
    assert issue["params"] == {"team": "ROXO"}
    assert issue["message"] == "Team “ROXO” was not lined up on this day."
