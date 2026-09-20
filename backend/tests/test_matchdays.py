def teams(*groups):
    return [{"name": name, "player_ids": ids} for name, ids in groups]


def test_create_read_and_delete_a_matchday(api, group):
    a, b = api.player(group, "ana"), api.player(group, "bia")
    day = api.matchday(
        group, "2026-09-16",
        teams(("BRANCO", [a]), ("AZUL", [b])),
        [{"home_team_index": 0, "away_team_index": 1, "home_score": 2, "away_score": 1,
          "goals": [{"player_id": a}, {"player_id": a}, {"player_id": b}]}],
    )
    assert day["total_goals"] == 3
    assert day["goal_mismatch"] is False
    assert [s["name"] for s in day["standings"]] == ["branco", "azul"]
    assert day["champion_team_id"] == day["standings"][0]["team_id"]
    assert [s["goals"] for s in day["top_scorers"]] == [2, 1]

    assert api.get(f"/api/groups/{group}/matchdays/{day['id']}").status_code == 200
    assert api.delete(f"/api/groups/{group}/matchdays/{day['id']}").status_code == 204
    assert api.get(f"/api/groups/{group}/matchdays/{day['id']}").status_code == 404
    assert api.get(f"/api/groups/{group}/matchdays").json() == []


def test_updating_a_matchday_replaces_its_teams_and_matches(api, group):
    a, b = api.player(group), api.player(group)
    day = api.matchday(group, "2026-09-16", teams(("BRANCO", [a]), ("AZUL", [b])),
                       [{"home_team_index": 0, "away_team_index": 1,
                         "home_score": 1, "away_score": 0, "goals": [{"player_id": a}]}])
    updated = api.put(
        f"/api/groups/{group}/matchdays/{day['id']}",
        json={"date": "2026-09-17", "teams": teams(("VERDE", [a]), ("PRETO", [b])),
              "matches": [{"home_team_index": 0, "away_team_index": 1,
                           "home_score": 0, "away_score": 3,
                           "goals": [{"player_id": b}] * 3}]},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["date"] == "2026-09-17"
    assert {s["name"] for s in body["standings"]} == {"verde", "preto"}
    assert body["standings"][0]["name"] == "preto"
    assert len(api.get(f"/api/groups/{group}/matchdays").json()) == 1


def test_own_goal_is_credited_to_the_other_team(api, group):
    a, b = api.player(group, "ana"), api.player(group, "bia")
    day = api.matchday(
        group, "2026-09-16", teams(("BRANCO", [a]), ("AZUL", [b])),
        [{"home_team_index": 0, "away_team_index": 1, "home_score": 1, "away_score": 0,
          "goals": [{"player_id": b, "own_goal": True}]}],
    )
    branco = next(s for s in day["standings"] if s["name"] == "branco")
    assert day["goal_mismatch"] is False
    assert day["matches"][0]["goals"][0]["team_id"] == branco["team_id"]
    assert day["top_scorers"] == []


def test_scores_stay_authoritative_when_scorers_are_missing(api, group):
    a, b = api.player(group), api.player(group)
    day = api.matchday(
        group, "2026-09-16", teams(("BRANCO", [a]), ("AZUL", [b])),
        [{"home_team_index": 0, "away_team_index": 1, "home_score": 3, "away_score": 0,
          "goals": [{"player_id": a}]}],
    )
    assert day["total_goals"] == 3
    assert day["goal_mismatch"] is True
    assert day["standings"][0]["goals_for"] == 3


def test_a_team_cannot_play_itself(api, group):
    a = api.player(group)
    r = api.post(f"/api/groups/{group}/matchdays", json={
        "date": "2026-09-16", "teams": teams(("BRANCO", [a])),
        "matches": [{"home_team_index": 0, "away_team_index": 0}],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "same_team_twice"


def test_a_player_cannot_be_on_two_teams_the_same_day(api, group):
    a = api.player(group)
    r = api.post(f"/api/groups/{group}/matchdays", json={
        "date": "2026-09-16", "teams": teams(("BRANCO", [a]), ("AZUL", [a])), "matches": [],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "player_in_two_teams"


def test_a_scorer_must_be_playing_that_day(api, group):
    a, b = api.player(group), api.player(group)
    outsider = api.player(group)
    r = api.post(f"/api/groups/{group}/matchdays", json={
        "date": "2026-09-16", "teams": teams(("BRANCO", [a]), ("AZUL", [b])),
        "matches": [{"home_team_index": 0, "away_team_index": 1, "home_score": 1,
                     "away_score": 0, "goals": [{"player_id": outsider}]}],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "scorer_not_playing"


def test_a_player_from_another_group_is_rejected(api, other_api, group):
    stranger = other_api.player(other_api.group())
    r = api.post(f"/api/groups/{group}/matchdays", json={
        "date": "2026-09-16", "teams": teams(("BRANCO", [stranger])), "matches": [],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "player_in_other_group"


def test_a_tie_at_the_top_leaves_the_day_without_a_champion(api, group):
    a, b = api.player(group), api.player(group)
    day = api.matchday(group, "2026-09-16", teams(("BRANCO", [a]), ("AZUL", [b])),
                       [{"home_team_index": 0, "away_team_index": 1,
                         "home_score": 0, "away_score": 0}])
    assert day["champion_team_id"] is None


def test_deleting_a_player_with_history_only_deactivates_them(api, group):
    a, b = api.player(group), api.player(group)
    api.matchday(group, "2026-09-16", teams(("BRANCO", [a]), ("AZUL", [b])), [])
    assert api.delete(f"/api/groups/{group}/players/{a}").status_code == 204
    players = {p["id"]: p for p in api.get(f"/api/groups/{group}/players").json()}
    assert players[a]["active"] is False


def test_player_names_are_stored_lowercase(api, group):
    r = api.post(f"/api/groups/{group}/players", json={"name": "  Golin   Da  Silva "})
    assert r.status_code == 201, r.text
    assert r.json()["name"] == "golin da silva"

    player_id = r.json()["id"]
    r = api.patch(f"/api/groups/{group}/players/{player_id}", json={"name": "GOLIN"})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "golin"


def test_venue_names_keep_the_original_case(api, group):
    r = api.post(f"/api/groups/{group}/venues", json={"name": "Campo do Zé"})
    assert r.status_code == 201, r.text
    assert r.json()["name"] == "Campo do Zé"
