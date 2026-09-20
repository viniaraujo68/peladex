from app import parser


def teams(*groups):
    return [{"name": name, "player_ids": ids} for name, ids in groups]


def test_parser_reads_an_assist_in_parentheses():
    text = "16/09/2026\nBRANCO: golin, galetti\nAZUL: ney\nBRANCO 1x0 AZUL: golin (galetti)\n"
    result = parser.parse(text)
    assert result.ok
    goal = result.matchdays[0].matches[0].goals[0]
    assert (goal.player, goal.assist, goal.own_goal) == ("golin", "galetti", False)


def test_parser_reads_the_venue_from_the_date_line():
    text = "16/09/2026 @ Campo do Ze\nBRANCO: a\nAZUL: b\nBRANCO 1x0 AZUL: a\n"
    result = parser.parse(text)
    assert result.ok
    assert result.matchdays[0].venue == "Campo do Ze"


def test_parser_keeps_own_goal_and_assist_apart():
    text = (
        "16/09/2026\nBRANCO: golin, galetti\nAZUL: ney, rod\n"
        "BRANCO 1x0 AZUL: ney (gc)\n"
        "BRANCO 1x0 AZUL: golin (galetti)\n"
    )
    result = parser.parse(text)
    assert result.ok
    own, assisted = (m.goals[0] for m in result.matchdays[0].matches)
    assert (own.own_goal, own.assist) == (True, None)
    assert (assisted.own_goal, assisted.assist) == (False, "galetti")


def test_parser_warns_when_the_assist_is_from_the_other_team():
    text = "16/09/2026\nBRANCO: golin\nAZUL: ney\nBRANCO 1x0 AZUL: golin (ney)\n"
    result = parser.parse(text)
    assert result.ok
    assert any(i.code == "assist_other_team" for i in result.issues)
    assert result.matchdays[0].matches[0].goals[0].assist is None


def test_parser_warns_on_a_self_assist():
    text = "16/09/2026\nBRANCO: golin, galetti\nAZUL: ney\nBRANCO 1x0 AZUL: golin (golin)\n"
    result = parser.parse(text)
    assert any(i.code == "self_assist" for i in result.issues)
    assert result.matchdays[0].matches[0].goals[0].assist is None


def test_parser_refuses_an_assist_on_an_own_goal():
    text = "16/09/2026\nBRANCO: golin\nAZUL: ney, rod\nBRANCO 1x0 AZUL: ney (gc) (rod)\n"
    result = parser.parse(text)
    assert any(i.code == "own_goal_assist" for i in result.issues)


def test_parser_applies_a_multiplier_before_or_after_the_assist():
    for body in ["golin x2 (galetti)", "golin (galetti) x2"]:
        text = f"16/09/2026\nBRANCO: golin, galetti\nAZUL: ney\nBRANCO 2x0 AZUL: {body}\n"
        goals = parser.parse(text).matchdays[0].matches[0].goals
        assert len(goals) == 2, body
        assert all(g.assist == "galetti" for g in goals), body


def test_api_stores_and_returns_the_assist(api, group):
    a, b, c = api.player(group, "ana"), api.player(group, "bia"), api.player(group, "caio")
    day = api.matchday(
        group, "2026-09-16", teams(("BRANCO", [a, b]), ("AZUL", [c])),
        [{"home_team_index": 0, "away_team_index": 1, "home_score": 1, "away_score": 0,
          "goals": [{"player_id": a, "assist_player_id": b}]}],
    )
    goal = day["matches"][0]["goals"][0]
    assert goal["assist_name"] == "bia"
    assert day["total_assists"] == 1
    assert day["top_assisters"][0]["name"] == "bia"

    stats = api.get(f"/api/groups/{group}/stats").json()
    by_name = {r["name"]: r for r in stats["ranking"]}
    assert by_name["bia"]["assists"] == 1
    assert by_name["ana"]["goals"] == 1
    assert by_name["ana"]["contributions"] == 1
    assert by_name["bia"]["contributions"] == 1
    assert stats["total_assists"] == 1


def test_api_rejects_an_assist_from_the_other_team(api, group):
    a, c = api.player(group), api.player(group)
    r = api.post(f"/api/groups/{group}/matchdays", json={
        "date": "2026-09-16", "teams": teams(("BRANCO", [a]), ("AZUL", [c])),
        "matches": [{"home_team_index": 0, "away_team_index": 1, "home_score": 1,
                     "away_score": 0, "goals": [{"player_id": a, "assist_player_id": c}]}],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "assist_other_team"


def test_api_rejects_a_self_assist(api, group):
    a, c = api.player(group), api.player(group)
    r = api.post(f"/api/groups/{group}/matchdays", json={
        "date": "2026-09-16", "teams": teams(("BRANCO", [a]), ("AZUL", [c])),
        "matches": [{"home_team_index": 0, "away_team_index": 1, "home_score": 1,
                     "away_score": 0, "goals": [{"player_id": a, "assist_player_id": a}]}],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "self_assist"


def test_api_rejects_an_assist_on_an_own_goal(api, group):
    a, c = api.player(group), api.player(group)
    b = api.player(group)
    r = api.post(f"/api/groups/{group}/matchdays", json={
        "date": "2026-09-16", "teams": teams(("BRANCO", [a, b]), ("AZUL", [c])),
        "matches": [{"home_team_index": 0, "away_team_index": 1, "home_score": 0,
                     "away_score": 1, "goals": [
                         {"player_id": a, "own_goal": True, "assist_player_id": b}]}],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "own_goal_assist"


def test_import_carries_assists_through(api, group):
    text = (
        "16/09/2026 @ Campo do Ze\n"
        "BRANCO: golin, galetti\n"
        "AZUL: ney, rod\n"
        "BRANCO 2x0 AZUL: golin (galetti), galetti (golin)\n"
    )
    assert api.import_text(group, text).status_code == 200
    day = api.get(f"/api/groups/{group}/matchdays").json()[0]
    assert day["venue_name"] == "Campo do Ze"
    assert [g["assist_name"] for g in day["matches"][0]["goals"]] == ["galetti", "golin"]
    assert day["total_assists"] == 2


def test_group_tracking_flags_round_trip(api, group):
    assert api.get(f"/api/groups/{group}").json()["track_assists"] is False
    updated = api.patch(f"/api/groups/{group}",
                        json={"track_assists": True, "track_scorers": False})
    assert updated.status_code == 200
    body = updated.json()
    assert body["track_assists"] is True
    assert body["track_scorers"] is False


def test_the_group_can_carry_a_default_venue(api, group):
    venue = api.venue(group, "Campo do Ze")
    updated = api.patch(f"/api/groups/{group}", json={"default_venue_id": venue})
    assert updated.status_code == 200
    body = updated.json()
    assert body["default_venue_id"] == venue
    assert body["default_venue_name"] == "Campo do Ze"

    cleared = api.patch(f"/api/groups/{group}", json={"default_venue_id": None})
    assert cleared.status_code == 200
    assert cleared.json()["default_venue_id"] is None


def test_an_import_without_a_venue_falls_back_to_the_default(api, group):
    venue = api.venue(group, "Campo do Ze")
    api.patch(f"/api/groups/{group}", json={"default_venue_id": venue})

    text = "16/09/2026\nBRANCO: a, b\nAZUL: c, d\nBRANCO 1x0 AZUL: a\n"
    assert api.import_text(group, text).status_code == 200
    day = api.get(f"/api/groups/{group}/matchdays").json()[0]
    assert day["venue_name"] == "Campo do Ze"


def test_a_venue_written_in_the_text_beats_the_default(api, group):
    venue = api.venue(group, "Campo do Ze")
    api.patch(f"/api/groups/{group}", json={"default_venue_id": venue})

    text = "16/09/2026 @ Society da Vila\nBRANCO: a, b\nAZUL: c, d\nBRANCO 1x0 AZUL: a\n"
    assert api.import_text(group, text).status_code == 200
    day = api.get(f"/api/groups/{group}/matchdays").json()[0]
    assert day["venue_name"] == "Society da Vila"


def test_deleting_the_default_venue_clears_it(api, group):
    venue = api.venue(group, "Campo do Ze")
    api.patch(f"/api/groups/{group}", json={"default_venue_id": venue})
    assert api.delete(f"/api/groups/{group}/venues/{venue}").status_code == 204
    assert api.get(f"/api/groups/{group}").json()["default_venue_id"] is None


def test_a_default_venue_from_another_group_is_rejected(api, other_api, group):
    stranger = other_api.venue(other_api.group())
    r = api.patch(f"/api/groups/{group}", json={"default_venue_id": stranger})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "venue_in_other_group"
