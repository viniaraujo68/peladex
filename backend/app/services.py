from collections import defaultdict
from collections.abc import Iterable

from slugify import slugify
from sqlalchemy.orm import selectinload
from sqlmodel import Session as DBSession
from sqlmodel import func, select

from . import models, schemas
from .security import new_token

MIN_PAIR_DAYS = 3


def unique_slug(db: DBSession, name: str) -> str:
    base = slugify(name) or "pelada"
    slug = base
    i = 2
    while db.exec(select(models.Group).where(models.Group.slug == slug)).first():
        slug = f"{base}-{i}"
        i += 1
    return slug


def player_names(db: DBSession, group_id: int) -> dict[int, str]:
    rows = db.exec(select(models.Player).where(models.Player.group_id == group_id)).all()
    return {p.id: p.name for p in rows}


def venue_names(db: DBSession, group_id: int) -> dict[int, str]:
    rows = db.exec(select(models.Venue).where(models.Venue.group_id == group_id)).all()
    return {v.id: v.name for v in rows}


def group_counts(db: DBSession, group_ids: Iterable[int]) -> tuple[dict[int, int], dict[int, int]]:
    ids = list(group_ids)
    if not ids:
        return {}, {}
    matchdays = dict(
        db.exec(
            select(models.Matchday.group_id, func.count(models.Matchday.id))
            .where(models.Matchday.group_id.in_(ids), models.Matchday.deleted_at == None)  # noqa: E711
            .group_by(models.Matchday.group_id)
        ).all()
    )
    players = dict(
        db.exec(
            select(models.Player.group_id, func.count(models.Player.id))
            .where(models.Player.group_id.in_(ids), models.Player.active == True)  # noqa: E712
            .group_by(models.Player.group_id)
        ).all()
    )
    return matchdays, players


def active_matchdays(db: DBSession, group_id: int) -> list[models.Matchday]:
    return list(
        db.exec(
            select(models.Matchday)
            .where(models.Matchday.group_id == group_id, models.Matchday.deleted_at == None)  # noqa: E711
            .order_by(models.Matchday.date, models.Matchday.id)
            .options(
                selectinload(models.Matchday.teams).selectinload(models.Team.members),
                selectinload(models.Matchday.matches).selectinload(models.Match.goals),
            )
        ).all()
    )


def _blank_tally(team: models.Team) -> dict:
    return {
        "team": team, "played": 0, "wins": 0, "draws": 0, "losses": 0,
        "goals_for": 0, "goals_against": 0, "points": 0, "win_rate": 0.0,
    }


def tally(matchday: models.Matchday, group: models.Group) -> dict[int, dict]:
    tallies = {team.id: _blank_tally(team) for team in matchday.teams}
    for match in matchday.matches:
        home = tallies.get(match.home_team_id)
        away = tallies.get(match.away_team_id)
        if home is None or away is None:
            continue
        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += match.home_score
        home["goals_against"] += match.away_score
        away["goals_for"] += match.away_score
        away["goals_against"] += match.home_score
        if match.home_score > match.away_score:
            home["wins"] += 1
            away["losses"] += 1
        elif match.home_score < match.away_score:
            home["losses"] += 1
            away["wins"] += 1
        else:
            home["draws"] += 1
            away["draws"] += 1
    for row in tallies.values():
        row["points"] = (
            row["wins"] * group.win_points
            + row["draws"] * group.draw_points
            + row["losses"] * group.loss_points
        )
        row["goal_diff"] = row["goals_for"] - row["goals_against"]
        best = row["played"] * group.win_points
        row["win_rate"] = (row["points"] / best) if best else 0.0
    return tallies


def _standing_key(row: dict) -> tuple:
    return (row["win_rate"], row["goal_diff"], row["goals_for"], -row["goals_against"])


def ranked_tallies(tallies: dict[int, dict]) -> list[dict]:
    return sorted(tallies.values(), key=_standing_key, reverse=True)


def champion_team_id(tallies: dict[int, dict]) -> int | None:
    order = ranked_tallies(tallies)
    if not order or order[0]["played"] == 0:
        return None
    if len(order) > 1 and _standing_key(order[0]) == _standing_key(order[1]):
        return None
    return order[0]["team"].id


def matchday_goals(matchday: models.Matchday) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for match in matchday.matches:
        for goal in match.goals:
            if not goal.own_goal:
                counts[goal.player_id] += 1
    return counts


def _goal_mismatch(matchday: models.Matchday) -> bool:
    for match in matchday.matches:
        if not match.goals:
            continue
        credited = defaultdict(int)
        for goal in match.goals:
            credited[goal.team_id] += 1
        if (credited[match.home_team_id] != match.home_score
                or credited[match.away_team_id] != match.away_score):
            return True
    return False


def serialize_matchday(
    db: DBSession,
    matchday: models.Matchday,
    group: models.Group,
    names: dict[int, str] | None = None,
    venues: dict[int, str] | None = None,
) -> schemas.MatchdayOut:
    if names is None:
        names = player_names(db, matchday.group_id)
    if venues is None:
        venues = venue_names(db, matchday.group_id)

    tallies = tally(matchday, group)
    order = ranked_tallies(tallies)
    team_names = {team.id: team.name for team in matchday.teams}

    standings = [
        schemas.TeamStandingOut(
            team_id=row["team"].id,
            name=row["team"].name,
            color=row["team"].color,
            played=row["played"],
            wins=row["wins"],
            draws=row["draws"],
            losses=row["losses"],
            goals_for=row["goals_for"],
            goals_against=row["goals_against"],
            goal_diff=row["goal_diff"],
            points=row["points"],
            win_rate=row["win_rate"],
            members=[
                schemas.TeamMemberOut(player_id=m.player_id, name=names.get(m.player_id, "?"))
                for m in sorted(row["team"].members, key=lambda m: names.get(m.player_id, ""))
            ],
        )
        for row in order
    ]

    matches = [
        schemas.MatchOut(
            id=match.id,
            sort_index=match.sort_index,
            home_team_id=match.home_team_id,
            home_team_name=team_names.get(match.home_team_id, "?"),
            away_team_id=match.away_team_id,
            away_team_name=team_names.get(match.away_team_id, "?"),
            home_score=match.home_score,
            away_score=match.away_score,
            goals=[
                schemas.GoalOut(
                    id=goal.id,
                    player_id=goal.player_id,
                    player_name=names.get(goal.player_id, "?"),
                    team_id=goal.team_id,
                    own_goal=goal.own_goal,
                )
                for goal in goals_in_order(match)
            ],
        )
        for match in sorted(matchday.matches, key=lambda m: (m.sort_index, m.id))
    ]

    goals = matchday_goals(matchday)
    top = sorted(goals.items(), key=lambda kv: (-kv[1], names.get(kv[0], "")))
    return schemas.MatchdayOut(
        id=matchday.id,
        date=matchday.date,
        venue_id=matchday.venue_id,
        venue_name=venues.get(matchday.venue_id) if matchday.venue_id else None,
        mvp_player_id=matchday.mvp_player_id,
        mvp_name=names.get(matchday.mvp_player_id) if matchday.mvp_player_id else None,
        notes=matchday.notes,
        standings=standings,
        matches=matches,
        champion_team_id=champion_team_id(tallies),
        top_scorers=[
            schemas.ScorerOut(player_id=pid, name=names.get(pid, "?"), goals=count)
            for pid, count in top
        ],
        total_goals=sum(m.home_score + m.away_score for m in matchday.matches),
        goal_mismatch=_goal_mismatch(matchday),
    )


def goals_in_order(match: models.Match) -> list[models.Goal]:
    return sorted(match.goals, key=lambda g: g.id or 0)


def _aggregate(matchdays: list[models.Matchday], group: models.Group) -> dict[int, dict]:
    agg: dict[int, dict] = defaultdict(
        lambda: {
            "matchdays": 0, "matches": 0, "wins": 0, "draws": 0, "losses": 0,
            "points": 0, "goals": 0, "own_goals": 0, "mvp_count": 0, "titles": 0,
        }
    )
    for matchday in matchdays:
        tallies = tally(matchday, group)
        champion = champion_team_id(tallies)
        for team in matchday.teams:
            row = tallies[team.id]
            for member in team.members:
                bucket = agg[member.player_id]
                bucket["matchdays"] += 1
                bucket["matches"] += row["played"]
                bucket["wins"] += row["wins"]
                bucket["draws"] += row["draws"]
                bucket["losses"] += row["losses"]
                bucket["points"] += row["points"]
                if champion is not None and team.id == champion:
                    bucket["titles"] += 1
        for match in matchday.matches:
            for goal in match.goals:
                key = "own_goals" if goal.own_goal else "goals"
                agg[goal.player_id][key] += 1
        if matchday.mvp_player_id:
            agg[matchday.mvp_player_id]["mvp_count"] += 1
    return agg


def _player_row(pid: int, name: str, bucket: dict, group: models.Group) -> schemas.PlayerRow:
    best = bucket["matches"] * group.win_points
    days = bucket["matchdays"]
    return schemas.PlayerRow(
        player_id=pid,
        name=name,
        matchdays=days,
        matches=bucket["matches"],
        wins=bucket["wins"],
        draws=bucket["draws"],
        losses=bucket["losses"],
        points=bucket["points"],
        win_rate=(bucket["points"] / best) if best else 0.0,
        goals=bucket["goals"],
        own_goals=bucket["own_goals"],
        goals_per_matchday=(bucket["goals"] / days) if days else 0.0,
        mvp_count=bucket["mvp_count"],
        titles=bucket["titles"],
        title_rate=(bucket["titles"] / days) if days else 0.0,
    )


def _records(matchdays: list[models.Matchday], group: models.Group,
             names: dict[int, str], agg: dict[int, dict]) -> list[schemas.Record]:
    best_rout = None
    best_day_scorer = None
    for matchday in matchdays:
        team_names = {team.id: team.name for team in matchday.teams}
        for match in matchday.matches:
            margin = abs(match.home_score - match.away_score)
            if margin and (best_rout is None or margin > best_rout[0]):
                best_rout = (
                    margin,
                    f"{team_names.get(match.home_team_id, '?')} {match.home_score}x"
                    f"{match.away_score} {team_names.get(match.away_team_id, '?')}",
                    matchday.date,
                )
        for pid, count in sorted(matchday_goals(matchday).items(),
                                 key=lambda kv: names.get(kv[0], "")):
            if best_day_scorer is None or count > best_day_scorer[0]:
                best_day_scorer = (count, pid, matchday.date)

    def top(field: str) -> tuple[int, int, int] | None:
        rows = [(bucket[field], pid) for pid, bucket in agg.items() if bucket[field] > 0]
        if not rows:
            return None
        best = max(value for value, _ in rows)
        tied = sorted((pid for value, pid in rows if value == best),
                      key=lambda pid: names.get(pid, ""))
        return best, tied[0], len(tied)

    def tie_detail(record: tuple[int, int, int] | None) -> str:
        if record is None or record[2] < 2:
            return ""
        return f"empatado com mais {record[2] - 1}"

    records: list[schemas.Record] = []

    scorer = top("goals")
    records.append(schemas.Record(
        code="top_scorer",
        player_name=names.get(scorer[1]) if scorer else None,
        value=float(scorer[0]) if scorer else None,
        detail=tie_detail(scorer),
    ))
    records.append(schemas.Record(
        code="most_goals_matchday",
        player_name=names.get(best_day_scorer[1]) if best_day_scorer else None,
        value=float(best_day_scorer[0]) if best_day_scorer else None,
        matchday_date=best_day_scorer[2] if best_day_scorer else None,
    ))
    titles = top("titles")
    records.append(schemas.Record(
        code="most_titles",
        player_name=names.get(titles[1]) if titles else None,
        value=float(titles[0]) if titles else None,
        detail=tie_detail(titles),
    ))
    mvps = top("mvp_count")
    records.append(schemas.Record(
        code="most_mvp",
        player_name=names.get(mvps[1]) if mvps else None,
        value=float(mvps[0]) if mvps else None,
        detail=tie_detail(mvps),
    ))
    records.append(schemas.Record(
        code="biggest_rout",
        player_name=None,
        value=float(best_rout[0]) if best_rout else None,
        detail=best_rout[1] if best_rout else "",
        matchday_date=best_rout[2] if best_rout else None,
    ))
    return records


def compute_stats(db: DBSession, group: models.Group) -> schemas.StatsOut:
    matchdays = active_matchdays(db, group.id)
    names = player_names(db, group.id)
    agg = _aggregate(matchdays, group)

    ranking = [_player_row(pid, names.get(pid, "?"), bucket, group) for pid, bucket in agg.items()]
    ranking.sort(key=lambda r: (r.win_rate, r.points, r.goals), reverse=True)

    return schemas.StatsOut(
        ranking=ranking,
        records=_records(matchdays, group, names, agg),
        total_matchdays=len(matchdays),
        total_matches=sum(len(m.matches) for m in matchdays),
        total_goals=sum(
            match.home_score + match.away_score for m in matchdays for match in m.matches
        ),
    )


def compute_evolution(db: DBSession, group: models.Group) -> schemas.EvolutionOut:
    matchdays = active_matchdays(db, group.id)
    names = player_names(db, group.id)
    dates = [m.date for m in matchdays]

    running: dict[int, dict] = defaultdict(lambda: {"points": 0, "matches": 0})
    seen: set[int] = set()
    series: dict[int, list[schemas.EvolutionPoint]] = defaultdict(list)

    for index, matchday in enumerate(matchdays):
        tallies = tally(matchday, group)
        present: dict[int, tuple[int, int]] = {}
        for team in matchday.teams:
            row = tallies[team.id]
            for member in team.members:
                present[member.player_id] = (row["points"], row["played"])
        for pid in present:
            if pid not in seen:
                seen.add(pid)
                series[pid] = [
                    schemas.EvolutionPoint(date=d, win_rate=None, points=None)
                    for d in dates[:index]
                ]
        for pid in seen:
            points, played = present.get(pid, (0, 0))
            running[pid]["points"] += points
            running[pid]["matches"] += played
            best = running[pid]["matches"] * group.win_points
            series[pid].append(
                schemas.EvolutionPoint(
                    date=matchday.date,
                    win_rate=(running[pid]["points"] / best) if best else None,
                    points=running[pid]["points"],
                )
            )

    out = [
        schemas.EvolutionSeries(player_id=pid, name=names.get(pid, "?"), points=points)
        for pid, points in series.items()
    ]
    out.sort(key=lambda s: s.points[-1].win_rate if s.points and s.points[-1].win_rate else 0,
             reverse=True)
    return schemas.EvolutionOut(dates=dates, series=out)


def _pairs(matchdays: list[models.Matchday], group: models.Group):
    partners: dict[tuple[int, int], list[float]] = defaultdict(list)
    opponents: dict[tuple[int, int], list[float]] = defaultdict(list)

    for matchday in matchdays:
        tallies = tally(matchday, group)
        members = {team.id: [m.player_id for m in team.members] for team in matchday.teams}

        for team_id, ids in members.items():
            row = tallies[team_id]
            if row["played"] == 0:
                continue
            rate = row["win_rate"]
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    partners[(a, b)].append(rate)
                    partners[(b, a)].append(rate)

        head_to_head: dict[tuple[int, int], dict] = defaultdict(
            lambda: {"played": 0, "points": defaultdict(int)}
        )
        for match in matchday.matches:
            if match.home_team_id not in members or match.away_team_id not in members:
                continue
            key = (min(match.home_team_id, match.away_team_id),
                   max(match.home_team_id, match.away_team_id))
            bucket = head_to_head[key]
            bucket["played"] += 1
            if match.home_score > match.away_score:
                bucket["points"][match.home_team_id] += group.win_points
                bucket["points"][match.away_team_id] += group.loss_points
            elif match.home_score < match.away_score:
                bucket["points"][match.away_team_id] += group.win_points
                bucket["points"][match.home_team_id] += group.loss_points
            else:
                bucket["points"][match.home_team_id] += group.draw_points
                bucket["points"][match.away_team_id] += group.draw_points

        for (left, right), bucket in head_to_head.items():
            best = bucket["played"] * group.win_points
            if not best:
                continue
            left_rate = bucket["points"][left] / best
            right_rate = bucket["points"][right] / best
            for a in members[left]:
                for b in members[right]:
                    opponents[(a, b)].append(left_rate)
                    opponents[(b, a)].append(right_rate)

    return partners, opponents


def _pair_rows(source: dict[tuple[int, int], list[float]], player_id: int,
               names: dict[int, str], baseline: float, min_days: int) -> list[schemas.PairRow]:
    rows = []
    for (a, b), values in source.items():
        if a != player_id or len(values) < min_days:
            continue
        rate = sum(values) / len(values)
        rows.append(schemas.PairRow(
            player_id=b, name=names.get(b, "?"), days=len(values),
            win_rate=rate, delta=rate - baseline,
        ))
    rows.sort(key=lambda r: (r.delta, r.days), reverse=True)
    return rows


def compute_player_detail(db: DBSession, group: models.Group, player_id: int,
                          min_days: int = MIN_PAIR_DAYS) -> schemas.PlayerDetailOut | None:
    player = db.get(models.Player, player_id)
    if not player or player.group_id != group.id:
        return None

    matchdays = active_matchdays(db, group.id)
    names = player_names(db, group.id)
    agg = _aggregate(matchdays, group)
    summary = _player_row(player_id, player.name, agg[player_id], group)

    history: list[schemas.PlayerMatchdayRow] = []
    for matchday in matchdays:
        team = next(
            (t for t in matchday.teams if any(m.player_id == player_id for m in t.members)),
            None,
        )
        if team is None:
            continue
        tallies = tally(matchday, group)
        order = ranked_tallies(tallies)
        row = tallies[team.id]
        history.append(schemas.PlayerMatchdayRow(
            matchday_id=matchday.id,
            date=matchday.date,
            team_name=team.name,
            position=next(i for i, r in enumerate(order, start=1) if r["team"].id == team.id),
            teams=len(order),
            played=row["played"],
            wins=row["wins"],
            draws=row["draws"],
            losses=row["losses"],
            win_rate=row["win_rate"],
            goals=matchday_goals(matchday).get(player_id, 0),
            champion=champion_team_id(tallies) == team.id,
            mvp=matchday.mvp_player_id == player_id,
        ))
    history.reverse()

    partners, opponents = _pairs(matchdays, group)
    return schemas.PlayerDetailOut(
        player_id=player_id,
        name=player.name,
        summary=summary,
        history=history,
        partners=_pair_rows(partners, player_id, names, summary.win_rate, min_days),
        opponents=_pair_rows(opponents, player_id, names, summary.win_rate, min_days),
        min_days=min_days,
    )


def rotate_share_token(db: DBSession, group: models.Group) -> str:
    group.share_token = new_token(24)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group.share_token
