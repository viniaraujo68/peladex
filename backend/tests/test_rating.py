from datetime import date, timedelta

from tests.test_analysis import SEASON


def swap_season() -> str:
    days = []
    for index in range(8):
        day = date(2026, 1, 1) + timedelta(days=7 * index)
        early = index < 4
        winners = "old, ana, bia" if early else "new, ana, bia"
        losers = "new, caio, davi" if early else "old, caio, davi"
        days.append(f"{day.isoformat()}\nBRANCO: {winners}\nAZUL: {losers}\nBRANCO 1x0 AZUL")
    return "\n---\n".join(days) + "\n"


def notes(api, group, query=""):
    stats = api.get(f"/api/groups/{group}/stats{query}").json()
    return {row["name"]: row for row in stats["ranking"]}


def test_recent_form_outweighs_old_form(api, group):
    assert api.import_text(group, swap_season()).status_code == 200
    rows = notes(api, group)
    assert rows["new"]["rating"] > rows["old"]["rating"]
    assert rows["ana"]["rating"] > rows["caio"]["rating"]


def test_the_period_filter_rates_only_the_window(api, group):
    assert api.import_text(group, swap_season()).status_code == 200
    everything = notes(api, group)
    window = notes(api, group, "?date_from=2026-01-29")
    assert window["old"]["rating"] < everything["old"]["rating"]


def test_a_guest_with_one_matchday_is_provisional(api, group):
    guest_day = (
        "\n---\n2026-10-01\n"
        "BRANCO: ana, bia, zeca\n"
        "AZUL: caio, davi, edu\n"
        "BRANCO 1x0 AZUL: zeca\n"
    )
    assert api.import_text(group, SEASON + guest_day).status_code == 200
    rows = notes(api, group)
    assert rows["zeca"]["rating_provisional"] is True
    assert rows["zeca"]["rating"] is not None
    assert rows["ana"]["rating_provisional"] is False


def test_the_detail_explains_the_note(api, group):
    api.patch(f"/api/groups/{group}", json={"track_assists": True})
    assert api.import_text(group, SEASON).status_code == 200
    players = {p["name"]: p["id"] for p in api.get(f"/api/groups/{group}/players").json()}
    detail = api.get(f"/api/groups/{group}/players/{players['ana']}/detail").json()
    rating = detail["rating"]
    codes = [c["code"] for c in rating["components"]]
    assert codes == ["results", "team_attack", "team_defense", "scoring"]
    total = 6.5 + sum(c["contribution"] for c in rating["components"])
    assert abs(total - rating["note"]) <= 0.07
    assert detail["summary"]["rating"] == rating["note"]
    assert rating["note"] > 6.5


def test_scoring_is_left_out_when_scorers_are_not_tracked(api, group):
    api.patch(f"/api/groups/{group}", json={"track_scorers": False})
    assert api.import_text(group, SEASON).status_code == 200
    players = {p["name"]: p["id"] for p in api.get(f"/api/groups/{group}/players").json()}
    detail = api.get(f"/api/groups/{group}/players/{players['ana']}/detail").json()
    codes = [c["code"] for c in detail["rating"]["components"]]
    assert "scoring" not in codes
    assert "team_attack" in codes


def test_an_empty_group_has_no_notes(api, group):
    assert api.get(f"/api/groups/{group}/stats").json()["ranking"] == []


def test_hidden_ratings_stay_out_of_the_api(api, group):
    updated = api.patch(f"/api/groups/{group}", json={"show_ratings": False})
    assert updated.json()["show_ratings"] is False
    assert api.import_text(group, SEASON).status_code == 200
    rows = notes(api, group)
    assert all(row["rating"] is None for row in rows.values())
    players = {p["name"]: p["id"] for p in api.get(f"/api/groups/{group}/players").json()}
    detail = api.get(f"/api/groups/{group}/players/{players['ana']}/detail").json()
    assert detail["rating"] is None
