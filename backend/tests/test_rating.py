import itertools
import random
import time
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app import parser, rating
from scripts import seed_demo
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
        "AZUL 0x0 BRANCO\n"
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


def dense_solve(matchdays, weights, players):
    index = {pid: i for i, pid in enumerate(players)}
    size = len(players)
    normal = [[0.0] * size for _ in range(size)]
    target = [0.0] * size
    for matchday, weight in zip(matchdays, weights):
        rosters = rating._rosters(matchday)
        for match in matchday.matches:
            home = rosters.get(match.home_team_id, [])
            away = rosters.get(match.away_team_id, [])
            if not home or not away:
                continue
            outcome = (match.home_score > match.away_score) - (match.home_score < match.away_score)
            coefficients = [(index[pid], 1.0 / len(home)) for pid in home] + [
                (index[pid], -1.0 / len(away)) for pid in away
            ]
            for i, ci in coefficients:
                target[i] += weight * ci * outcome
                for j, cj in coefficients:
                    normal[i][j] += weight * ci * cj
    for i in range(size):
        normal[i][i] += rating.RIDGE_LAMBDA
    for col in range(size):
        pivot_row = normal[col]
        for r in range(col + 1, size):
            factor = normal[r][col] / pivot_row[col]
            if factor:
                for c in range(col, size):
                    normal[r][c] -= factor * pivot_row[c]
                target[r] -= factor * target[col]
    beta = [0.0] * size
    for i in range(size - 1, -1, -1):
        rest = sum(normal[i][j] * beta[j] for j in range(i + 1, size))
        beta[i] = (target[i] - rest) / normal[i][i]
    return dict(zip(players, beta))


def matchdays_from_text(text):
    ids = itertools.count(1)
    player_ids: dict[str, int] = {}
    matchdays = []
    for day in parser.parse(text).matchdays:
        team_ids = {team.name: next(ids) for team in day.teams}
        matchdays.append(SimpleNamespace(
            teams=[
                SimpleNamespace(id=team_ids[team.name], members=[
                    SimpleNamespace(player_id=player_ids.setdefault(name, len(player_ids) + 1))
                    for name in team.players
                ])
                for team in day.teams
            ],
            matches=[
                SimpleNamespace(home_team_id=team_ids[m.home_team], away_team_id=team_ids[m.away_team],
                                home_score=m.home_score, away_score=m.away_score)
                for m in day.matches
            ],
        ))
    return matchdays


def rotating_season(seed, days, pool, team_count, team_size, matches):
    rng = random.Random(seed)
    blocks = []
    for index in range(days):
        day = date(2025, 1, 1) + timedelta(days=7 * index)
        picked = rng.sample(range(pool), team_count * team_size)
        lines = [day.isoformat()]
        for team in range(team_count):
            members = picked[team * team_size:(team + 1) * team_size]
            lines.append(f"t{team}: " + ", ".join(f"p{p}" for p in members))
        for _ in range(matches):
            home, away = rng.sample(range(team_count), 2)
            lines.append(f"t{home} {rng.randint(0, 4)}x{rng.randint(0, 4)} t{away}")
        blocks.append("\n".join(lines))
    return "\n---\n".join(blocks) + "\n"


@pytest.mark.parametrize("text", [
    seed_demo.build_season(),
    SEASON,
    rotating_season(11, 40, 120, 4, 9, 12),
    rotating_season(23, 6, 300, 20, 12, 30),
], ids=["demo_season", "analysis_season", "rotating_120", "rotating_300"])
def test_the_iterative_solve_matches_the_dense_solve(text):
    matchdays = matchdays_from_text(text)
    last = len(matchdays) - 1
    weights = [0.5 ** ((last - i) / rating.HALF_LIFE_MATCHDAYS) for i in range(len(matchdays))]
    players = sorted({m.player_id for day in matchdays for t in day.teams for m in t.members})
    iterative = rating._teammate_adjusted_results(matchdays, weights, players)
    dense = dense_solve(matchdays, weights, players)
    assert max(abs(iterative[pid] - dense[pid]) for pid in players) < 1e-9


@pytest.mark.timing
def test_a_public_group_with_a_full_roster_renders_fast(api, client):
    group = api.group(visibility="public")
    slug = api.last_group["slug"]
    text = rotating_season(
        5, 4, parser.MAX_MATCHDAY_TEAMS * parser.MAX_TEAM_PLAYERS,
        parser.MAX_MATCHDAY_TEAMS, parser.MAX_TEAM_PLAYERS, 30,
    )
    assert api.import_text(group, text).status_code == 200
    start = time.perf_counter()
    r = client.get(f"/api/public/{slug}")
    assert time.perf_counter() - start < 3.0
    assert r.status_code == 200
    assert any(row["rating"] is not None for row in r.json()["stats"]["ranking"])
