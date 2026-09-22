import math
from dataclasses import dataclass

from . import models, schemas

HALF_LIFE_MATCHDAYS = 8.0
PRIOR_MATCHDAYS = 3.0
CENTER = 6.5
ASSIST_WEIGHT = 0.75
OWN_GOAL_WEIGHT = 0.5
ATTACK_RATE_FLOOR = 0.05
MIN_APPEARANCES = 3
RIDGE_LAMBDA = 3.0
RIDGE_GAIN = 1.5
GAINS = {"team_attack": 1.2, "team_defense": 1.2, "scoring": 0.6, "mvp": 0.3}
CAPS = {"results": 1.25, "team_attack": 0.75, "team_defense": 0.75, "scoring": 0.5, "mvp": 0.25}
FULL_SPAN = sum(CAPS.values())
COMPONENTS = ("results", "team_attack", "team_defense", "scoring", "mvp")


@dataclass
class _Tally:
    points: float = 0.0
    max_points: float = 0.0
    matches: float = 0.0
    goals_for: float = 0.0
    goals_against: float = 0.0
    attack_value: float = 0.0
    attack_exposure: float = 0.0
    mvp: float = 0.0
    mvp_days: float = 0.0
    weight: float = 0.0
    appearances: int = 0

    def add(self, other: "_Tally") -> None:
        for name in ("points", "max_points", "matches", "goals_for", "goals_against",
                     "attack_value", "attack_exposure", "mvp", "mvp_days", "weight"):
            setattr(self, name, getattr(self, name) + getattr(other, name))


def _soft(value: float, cap: float) -> float:
    return cap * math.tanh(value / cap)


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def _coverage(match: models.Match, team_id: int, score: int) -> float:
    if score == 0:
        return 1.0
    listed = sum(1 for goal in match.goals if goal.team_id == team_id)
    return min(1.0, listed / score)


def _match_points(match: models.Match, group: models.Group) -> tuple[int, int]:
    if match.home_score > match.away_score:
        return group.win_points, group.loss_points
    if match.home_score < match.away_score:
        return group.loss_points, group.win_points
    return group.draw_points, group.draw_points


def _rosters(matchday: models.Matchday) -> dict[int, list[int]]:
    return {team.id: [member.player_id for member in team.members] for team in matchday.teams}


def _teammate_adjusted_results(matchdays: list[models.Matchday], weights: list[float],
                               players: list[int]) -> dict[int, float]:
    index = {pid: i for i, pid in enumerate(players)}
    size = len(players)
    normal = [[0.0] * size for _ in range(size)]
    target = [0.0] * size
    for matchday, weight in zip(matchdays, weights):
        rosters = _rosters(matchday)
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
                row = normal[i]
                for j, cj in coefficients:
                    row[j] += weight * ci * cj
    for i in range(size):
        normal[i][i] += RIDGE_LAMBDA
    for col in range(size):
        pivot_row = normal[col]
        pivot = pivot_row[col]
        for r in range(col + 1, size):
            factor = normal[r][col] / pivot
            if factor:
                row = normal[r]
                for c in range(col, size):
                    row[c] -= factor * pivot_row[c]
                target[r] -= factor * target[col]
    beta = [0.0] * size
    for i in range(size - 1, -1, -1):
        rest = sum(normal[i][j] * beta[j] for j in range(i + 1, size))
        beta[i] = (target[i] - rest) / normal[i][i]
    return dict(zip(players, beta))


def rate_players(matchdays: list[models.Matchday],
                 group: models.Group) -> dict[int, schemas.PlayerRating]:
    if not matchdays:
        return {}
    last = len(matchdays) - 1
    weights = [0.5 ** ((last - i) / HALF_LIFE_MATCHDAYS) for i in range(len(matchdays))]
    tallies: dict[int, _Tally] = {}
    any_goal = False

    for matchday, weight in zip(matchdays, weights):
        rosters = _rosters(matchday)
        played: set[int] = set()
        for match in matchday.matches:
            home = rosters.get(match.home_team_id, [])
            away = rosters.get(match.away_team_id, [])
            if not home or not away:
                continue
            home_points, away_points = _match_points(match, group)
            sides = (
                (home, home_points, match.home_score, match.away_score,
                 _coverage(match, match.home_team_id, match.home_score)),
                (away, away_points, match.away_score, match.home_score,
                 _coverage(match, match.away_team_id, match.away_score)),
            )
            for members, points, scored, conceded, coverage in sides:
                for pid in members:
                    t = tallies.setdefault(pid, _Tally())
                    t.points += weight * points
                    t.max_points += weight * group.win_points
                    t.matches += weight
                    t.goals_for += weight * scored
                    t.goals_against += weight * conceded
                    if group.track_scorers:
                        t.attack_exposure += weight * coverage
                    played.add(pid)
            if not group.track_scorers:
                continue
            for goal in match.goals:
                any_goal = True
                scorer = tallies.setdefault(goal.player_id, _Tally())
                scorer.attack_value += weight * (-OWN_GOAL_WEIGHT if goal.own_goal else 1.0)
                if goal.assist_player_id is not None and not goal.own_goal and group.track_assists:
                    helper = tallies.setdefault(goal.assist_player_id, _Tally())
                    helper.attack_value += weight * ASSIST_WEIGHT
        for pid in played:
            t = tallies[pid]
            t.weight += weight
            t.appearances += 1
            if matchday.mvp_player_id is not None:
                t.mvp_days += weight
                if matchday.mvp_player_id == pid:
                    t.mvp += weight

    tallies = {pid: t for pid, t in tallies.items() if t.appearances}
    if not tallies:
        return {}
    pooled = _Tally()
    for t in tallies.values():
        pooled.add(t)

    group_rates = {
        "results": _ratio(pooled.points, pooled.max_points),
        "team_attack": _ratio(pooled.goals_for, pooled.matches),
        "team_defense": _ratio(pooled.goals_against, pooled.matches),
        "scoring": _ratio(pooled.attack_value, pooled.attack_exposure) if any_goal else None,
        "mvp": _ratio(pooled.mvp, pooled.mvp_days),
    }
    exposure_per_matchday = {
        "team_attack": pooled.matches / pooled.weight,
        "team_defense": pooled.matches / pooled.weight,
        "scoring": pooled.attack_exposure / pooled.weight,
        "mvp": pooled.mvp_days / pooled.weight,
    }
    beta = _teammate_adjusted_results(matchdays, weights, sorted(tallies))

    def exposure(t: _Tally, code: str) -> tuple[float, float]:
        return {
            "results": (t.points, t.max_points),
            "team_attack": (t.goals_for, t.matches),
            "team_defense": (t.goals_against, t.matches),
            "scoring": (t.attack_value, t.attack_exposure),
            "mvp": (t.mvp, t.mvp_days),
        }[code]

    def shrunk(code: str, numerator: float, denominator: float) -> float | None:
        mean = group_rates[code]
        prior = PRIOR_MATCHDAYS * exposure_per_matchday[code]
        if mean is None or denominator + prior == 0:
            return None
        return (numerator + mean * prior) / (denominator + prior)

    ratings: dict[int, schemas.PlayerRating] = {}
    for pid, t in tallies.items():
        shrunk_rates = {code: shrunk(code, *exposure(t, code)) for code in COMPONENTS[1:]}
        parts: dict[str, float] = {}
        if group_rates["results"] is not None:
            parts["results"] = _soft(RIDGE_GAIN * beta[pid], CAPS["results"])
        team_attack = shrunk_rates["team_attack"]
        if team_attack is not None and group_rates["team_attack"]:
            mean = group_rates["team_attack"]
            parts["team_attack"] = _soft(
                GAINS["team_attack"] * (team_attack - mean) / mean, CAPS["team_attack"]
            )
        team_defense = shrunk_rates["team_defense"]
        if team_defense is not None and group_rates["team_defense"]:
            mean = group_rates["team_defense"]
            parts["team_defense"] = _soft(
                GAINS["team_defense"] * (mean - team_defense) / mean, CAPS["team_defense"]
            )
        scoring = shrunk_rates["scoring"]
        if scoring is not None:
            mean = group_rates["scoring"]
            parts["scoring"] = _soft(
                GAINS["scoring"] * (scoring - mean) / max(mean, ATTACK_RATE_FLOOR), CAPS["scoring"]
            )
        mvp = shrunk_rates["mvp"]
        if mvp is not None and group_rates["mvp"]:
            parts["mvp"] = _soft(GAINS["mvp"] * (mvp / group_rates["mvp"] - 1.0), CAPS["mvp"])
        if parts:
            scale = FULL_SPAN / sum(CAPS[code] for code in parts)
            parts = {code: value * scale for code, value in parts.items()}
        note = round(max(0.0, min(10.0, CENTER + sum(parts.values()))), 1)
        components = []
        for code in COMPONENTS:
            if code not in parts:
                continue
            rate = _ratio(*exposure(t, code))
            components.append(schemas.RatingComponent(
                code=code,
                contribution=round(parts[code], 2),
                rate=rate if rate is not None else group_rates[code],
                group_rate=group_rates[code],
            ))
        ratings[pid] = schemas.PlayerRating(
            note=note,
            provisional=t.appearances < MIN_APPEARANCES,
            appearances=t.appearances,
            components=components,
        )
    return ratings
