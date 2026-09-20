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
