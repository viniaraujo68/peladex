from collections import defaultdict
from collections.abc import Iterable

from slugify import slugify
from sqlalchemy.orm import selectinload
from sqlmodel import Session as DBSession
from sqlmodel import func, select

from . import models, schemas
from .parser import normalize
from .security import new_token

MIN_PAIR_DAYS = 3
RECENT_MATCHDAYS = 5


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


def active_matchdays(db: DBSession, group_id: int, date_from=None,
                     date_to=None) -> list[models.Matchday]:
    filters = [models.Matchday.group_id == group_id, models.Matchday.deleted_at == None]  # noqa: E711
    if date_from is not None:
        filters.append(models.Matchday.date >= date_from)
    if date_to is not None:
        filters.append(models.Matchday.date <= date_to)
    return list(
        db.exec(
            select(models.Matchday)
            .where(*filters)
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


def matchday_assists(matchday: models.Matchday) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for match in matchday.matches:
        for goal in match.goals:
            if goal.assist_player_id is not None:
                counts[goal.assist_player_id] += 1
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
                    assist_player_id=goal.assist_player_id,
                    assist_name=(
                        names.get(goal.assist_player_id)
                        if goal.assist_player_id is not None
                        else None
                    ),
                )
                for goal in goals_in_order(match)
            ],
        )
        for match in sorted(matchday.matches, key=lambda m: (m.sort_index, m.id))
    ]

    goals = matchday_goals(matchday)
    top = sorted(goals.items(), key=lambda kv: (-kv[1], names.get(kv[0], "")))
    assists = matchday_assists(matchday)
    top_assists = sorted(assists.items(), key=lambda kv: (-kv[1], names.get(kv[0], "")))
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
        top_assisters=[
            schemas.AssisterOut(player_id=pid, name=names.get(pid, "?"), assists=count)
            for pid, count in top_assists
        ],
        total_goals=sum(m.home_score + m.away_score for m in matchday.matches),
        total_assists=sum(assists.values()),
        goal_mismatch=_goal_mismatch(matchday),
    )


def goals_in_order(match: models.Match) -> list[models.Goal]:
    return sorted(match.goals, key=lambda g: g.id or 0)


def _aggregate(matchdays: list[models.Matchday], group: models.Group):
    agg: dict[int, dict] = defaultdict(
        lambda: {
            "matchdays": 0, "matches": 0, "wins": 0, "draws": 0, "losses": 0,
            "points": 0, "goals": 0, "own_goals": 0, "assists": 0,
            "mvp_count": 0, "titles": 0,
        }
    )
    history: dict[int, list[dict]] = defaultdict(list)

    for matchday in matchdays:
        tallies = tally(matchday, group)
        champion = champion_team_id(tallies)
        goals = matchday_goals(matchday)

        for team in matchday.teams:
            row = tallies[team.id]
            is_champion = champion is not None and team.id == champion
            for member in team.members:
                bucket = agg[member.player_id]
                bucket["matchdays"] += 1
                bucket["matches"] += row["played"]
                bucket["wins"] += row["wins"]
                bucket["draws"] += row["draws"]
                bucket["losses"] += row["losses"]
                bucket["points"] += row["points"]
                if is_champion:
                    bucket["titles"] += 1
                history[member.player_id].append({
                    "date": matchday.date,
                    "points": row["points"],
                    "played": row["played"],
                    "champion": is_champion,
                    "goals": goals.get(member.player_id, 0),
                })

        for match in matchday.matches:
            for goal in match.goals:
                key = "own_goals" if goal.own_goal else "goals"
                agg[goal.player_id][key] += 1
                if goal.assist_player_id is not None:
                    agg[goal.assist_player_id]["assists"] += 1
        if matchday.mvp_player_id:
            agg[matchday.mvp_player_id]["mvp_count"] += 1

    return agg, history


def _streaks(entries: list[dict]) -> tuple[int, int]:
    current = 0
    for entry in reversed(entries):
        if entry["champion"]:
            current += 1
        else:
            break
    best = 0
    run = 0
    for entry in entries:
        run = run + 1 if entry["champion"] else 0
        best = max(best, run)
    return current, best


def _recent_rate(entries: list[dict], group: models.Group) -> float | None:
    window = entries[-RECENT_MATCHDAYS:]
    played = sum(entry["played"] for entry in window)
    best = played * group.win_points
    if not best:
        return None
    return sum(entry["points"] for entry in window) / best


def _player_row(pid: int, name: str, bucket: dict, group: models.Group,
                entries: list[dict], total_matchdays: int) -> schemas.PlayerRow:
    best = bucket["matches"] * group.win_points
    days = bucket["matchdays"]
    contributions = bucket["goals"] + bucket["assists"]
    current_streak, best_streak = _streaks(entries)
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
        assists=bucket["assists"],
        contributions=contributions,
        goals_per_matchday=(bucket["goals"] / days) if days else 0.0,
        contributions_per_matchday=(contributions / days) if days else 0.0,
        mvp_count=bucket["mvp_count"],
        titles=bucket["titles"],
        title_rate=(bucket["titles"] / days) if days else 0.0,
        presence=(days / total_matchdays) if total_matchdays else 0.0,
        recent_win_rate=_recent_rate(entries, group),
        title_streak=current_streak,
        best_title_streak=best_streak,
    )


def _records(matchdays: list[models.Matchday], group: models.Group,
             names: dict[int, str], agg: dict[int, dict]) -> list[schemas.Record]:
    best_rout = None
    best_day_scorer = None
    best_day_assister = None
    duos: dict[tuple[int, int], int] = defaultdict(int)

    for matchday in matchdays:
        by_id = {team.id: team.name for team in matchday.teams}
        for match in matchday.matches:
            margin = abs(match.home_score - match.away_score)
            if margin and (best_rout is None or margin > best_rout[0]):
                best_rout = (
                    margin,
                    f"{by_id.get(match.home_team_id, '?')} {match.home_score}x"
                    f"{match.away_score} {by_id.get(match.away_team_id, '?')}",
                    matchday.date,
                )
            for goal in match.goals:
                if goal.assist_player_id is not None and not goal.own_goal:
                    duos[(goal.assist_player_id, goal.player_id)] += 1
        for pid, count in sorted(matchday_goals(matchday).items(),
                                 key=lambda kv: names.get(kv[0], "")):
            if best_day_scorer is None or count > best_day_scorer[0]:
                best_day_scorer = (count, pid, matchday.date)
        for pid, count in sorted(matchday_assists(matchday).items(),
                                 key=lambda kv: names.get(kv[0], "")):
            if best_day_assister is None or count > best_day_assister[0]:
                best_day_assister = (count, pid, matchday.date)

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
    assister = top("assists")
    records.append(schemas.Record(
        code="top_assister",
        player_name=names.get(assister[1]) if assister else None,
        value=float(assister[0]) if assister else None,
        detail=tie_detail(assister),
    ))
    records.append(schemas.Record(
        code="most_goals_matchday",
        player_name=names.get(best_day_scorer[1]) if best_day_scorer else None,
        value=float(best_day_scorer[0]) if best_day_scorer else None,
        matchday_date=best_day_scorer[2] if best_day_scorer else None,
    ))
    records.append(schemas.Record(
        code="most_assists_matchday",
        player_name=names.get(best_day_assister[1]) if best_day_assister else None,
        value=float(best_day_assister[0]) if best_day_assister else None,
        matchday_date=best_day_assister[2] if best_day_assister else None,
    ))
    titles = top("titles")
    records.append(schemas.Record(
        code="most_titles",
        player_name=names.get(titles[1]) if titles else None,
        value=float(titles[0]) if titles else None,
        detail=tie_detail(titles),
    ))
    presence = top("matchdays")
    records.append(schemas.Record(
        code="most_presence",
        player_name=names.get(presence[1]) if presence else None,
        value=float(presence[0]) if presence else None,
        detail=tie_detail(presence),
    ))
    mvps = top("mvp_count")
    records.append(schemas.Record(
        code="most_mvp",
        player_name=names.get(mvps[1]) if mvps else None,
        value=float(mvps[0]) if mvps else None,
        detail=tie_detail(mvps),
    ))
    if duos:
        best_duo = max(
            duos.items(),
            key=lambda item: (item[1], -item[0][0], -item[0][1]),
        )
        (assist_id, scorer_id), count = best_duo
        records.append(schemas.Record(
            code="best_duo",
            player_name=names.get(scorer_id, "?"),
            value=float(count),
            detail=f"com passe de {names.get(assist_id, '?')}",
        ))
    else:
        records.append(schemas.Record(code="best_duo", player_name=None, value=None))
    records.append(schemas.Record(
        code="biggest_rout",
        player_name=None,
        value=float(best_rout[0]) if best_rout else None,
        detail=best_rout[1] if best_rout else "",
        matchday_date=best_rout[2] if best_rout else None,
    ))
    return records


def compute_stats(db: DBSession, group: models.Group, date_from=None,
                  date_to=None) -> schemas.StatsOut:
    matchdays = active_matchdays(db, group.id, date_from, date_to)
    names = player_names(db, group.id)
    agg, history = _aggregate(matchdays, group)
    total = len(matchdays)

    ranking = [
        _player_row(pid, names.get(pid, "?"), bucket, group, history.get(pid, []), total)
        for pid, bucket in agg.items()
    ]
    ranking.sort(key=lambda r: (r.win_rate, r.points, r.goals), reverse=True)

    return schemas.StatsOut(
        ranking=ranking,
        records=_records(matchdays, group, names, agg),
        total_matchdays=total,
        total_matches=sum(len(m.matches) for m in matchdays),
        total_goals=sum(
            match.home_score + match.away_score for m in matchdays for match in m.matches
        ),
        total_assists=sum(
            1 for m in matchdays for match in m.matches for goal in match.goals
            if goal.assist_player_id is not None
        ),
        first_date=matchdays[0].date if matchdays else None,
        last_date=matchdays[-1].date if matchdays else None,
    )


def compute_evolution(db: DBSession, group: models.Group, date_from=None,
                      date_to=None) -> schemas.EvolutionOut:
    matchdays = active_matchdays(db, group.id, date_from, date_to)
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


def _rate_of(bucket: dict, group: models.Group) -> float | None:
    best = bucket["played"] * group.win_points
    return (bucket["points"] / best) if best else None


def _day_team_map(matchday: models.Matchday) -> dict[int, int]:
    team_of: dict[int, int] = {}
    for team in matchday.teams:
        for member in team.members:
            team_of[member.player_id] = team.id
    return team_of


def _player_pair_stats(matchdays: list[models.Matchday], group: models.Group, player_id: int):
    universe: set[int] = set()
    for matchday in matchdays:
        universe.update(_day_team_map(matchday))
    universe.discard(player_id)

    partner_with: dict[int, list[float]] = defaultdict(list)
    partner_without: dict[int, list[float]] = defaultdict(list)
    opponent_with: dict[int, list[float]] = defaultdict(list)
    opponent_without: dict[int, list[float]] = defaultdict(list)

    for matchday in matchdays:
        team_of = _day_team_map(matchday)
        my_team = team_of.get(player_id)
        if my_team is None:
            continue
        tallies = tally(matchday, group)
        row = tallies[my_team]
        if row["played"] == 0:
            continue
        day_rate = row["win_rate"]

        teammates = {pid for pid, tid in team_of.items() if tid == my_team and pid != player_id}
        for other in universe:
            target = partner_with if other in teammates else partner_without
            target[other].append(day_rate)

        per_team: dict[int, dict] = defaultdict(lambda: {"played": 0, "points": 0})
        for match in matchday.matches:
            if my_team not in (match.home_team_id, match.away_team_id):
                continue
            at_home = match.home_team_id == my_team
            foe = match.away_team_id if at_home else match.home_team_id
            mine = match.home_score if at_home else match.away_score
            theirs = match.away_score if at_home else match.home_score
            bucket = per_team[foe]
            bucket["played"] += 1
            if mine > theirs:
                bucket["points"] += group.win_points
            elif mine < theirs:
                bucket["points"] += group.loss_points
            else:
                bucket["points"] += group.draw_points

        for other in universe:
            foe_team = team_of.get(other)
            faced = foe_team is not None and foe_team != my_team and foe_team in per_team
            if faced:
                value = _rate_of(per_team[foe_team], group)
                if value is not None:
                    opponent_with[other].append(value)
            rest = {"played": 0, "points": 0}
            for team_id, bucket in per_team.items():
                if faced and team_id == foe_team:
                    continue
                rest["played"] += bucket["played"]
                rest["points"] += bucket["points"]
            value = _rate_of(rest, group)
            if value is not None:
                opponent_without[other].append(value)

    return partner_with, partner_without, opponent_with, opponent_without


def _pair_rows_with_without(with_map: dict[int, list[float]],
                            without_map: dict[int, list[float]],
                            names: dict[int, str], min_days: int) -> list[schemas.PairRow]:
    rows: list[schemas.PairRow] = []
    for other, values in with_map.items():
        if len(values) < min_days:
            continue
        rate = sum(values) / len(values)
        apart = without_map.get(other, [])
        rate_without = (sum(apart) / len(apart)) if apart else None
        rows.append(schemas.PairRow(
            player_id=other,
            name=names.get(other, "?"),
            days=len(values),
            win_rate=rate,
            days_without=len(apart),
            win_rate_without=rate_without,
            delta=(rate - rate_without) if rate_without is not None else None,
        ))
    rows.sort(key=lambda r: (r.delta if r.delta is not None else -9, r.days), reverse=True)
    return rows


def _blank_split(key: str, label: str) -> dict:
    return {"key": key, "label": label, "days": 0, "matches": 0, "wins": 0,
            "draws": 0, "losses": 0, "points": 0, "goals": 0, "assists": 0}


def _player_splits(matchdays: list[models.Matchday], group: models.Group, player_id: int,
                   venues: dict[int, str]):
    by_venue: dict[str, dict] = {}
    by_team: dict[str, dict] = {}

    for matchday in matchdays:
        team = next(
            (t for t in matchday.teams if any(m.player_id == player_id for m in t.members)),
            None,
        )
        if team is None:
            continue
        row = tally(matchday, group)[team.id]
        if row["played"] == 0:
            continue
        goals = matchday_goals(matchday).get(player_id, 0)
        assists = matchday_assists(matchday).get(player_id, 0)

        venue_key = str(matchday.venue_id) if matchday.venue_id else ""
        venue_label = venues.get(matchday.venue_id, "") if matchday.venue_id else ""
        for store, key, label in (
            (by_venue, venue_key, venue_label),
            (by_team, normalize(team.name), team.name),
        ):
            bucket = store.setdefault(key, _blank_split(key, label))
            bucket["days"] += 1
            bucket["matches"] += row["played"]
            bucket["wins"] += row["wins"]
            bucket["draws"] += row["draws"]
            bucket["losses"] += row["losses"]
            bucket["points"] += row["points"]
            bucket["goals"] += goals
            bucket["assists"] += assists

    def finish(store: dict[str, dict]) -> list[schemas.SplitRow]:
        rows = []
        for bucket in store.values():
            best = bucket["matches"] * group.win_points
            rows.append(schemas.SplitRow(
                key=bucket["key"], label=bucket["label"], days=bucket["days"],
                matches=bucket["matches"], wins=bucket["wins"], draws=bucket["draws"],
                losses=bucket["losses"],
                win_rate=(bucket["points"] / best) if best else 0.0,
                goals=bucket["goals"], assists=bucket["assists"],
            ))
        rows.sort(key=lambda r: (r.days, r.win_rate), reverse=True)
        return rows

    return finish(by_venue), finish(by_team)


def compute_player_detail(db: DBSession, group: models.Group, player_id: int,
                          min_days: int = MIN_PAIR_DAYS, date_from=None,
                          date_to=None) -> schemas.PlayerDetailOut | None:
    player = db.get(models.Player, player_id)
    if not player or player.group_id != group.id:
        return None

    matchdays = active_matchdays(db, group.id, date_from, date_to)
    names = player_names(db, group.id)
    agg, history = _aggregate(matchdays, group)
    summary = _player_row(player_id, player.name, agg[player_id], group,
                          history.get(player_id, []), len(matchdays))

    rows: list[schemas.PlayerMatchdayRow] = []
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
        rows.append(schemas.PlayerMatchdayRow(
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
            assists=matchday_assists(matchday).get(player_id, 0),
            champion=champion_team_id(tallies) == team.id,
            mvp=matchday.mvp_player_id == player_id,
        ))
    rows.reverse()

    partner_with, partner_without, opponent_with, opponent_without = _player_pair_stats(
        matchdays, group, player_id
    )
    by_venue, by_team = _player_splits(
        matchdays, group, player_id, venue_names(db, group.id)
    )
    return schemas.PlayerDetailOut(
        player_id=player_id,
        name=player.name,
        summary=summary,
        history=rows,
        partners=_pair_rows_with_without(partner_with, partner_without, names, min_days),
        opponents=_pair_rows_with_without(opponent_with, opponent_without, names, min_days),
        by_venue=by_venue,
        by_team=by_team,
        min_days=min_days,
    )


def compute_pair_leaderboard(db: DBSession, group: models.Group, min_days: int = MIN_PAIR_DAYS,
                             limit: int = 10, date_from=None,
                             date_to=None) -> schemas.PairLeaderboard:
    matchdays = active_matchdays(db, group.id, date_from, date_to)
    names = player_names(db, group.id)
    agg, history = _aggregate(matchdays, group)
    total = len(matchdays)
    baseline = {
        pid: _player_row(pid, names.get(pid, "?"), bucket, group,
                         history.get(pid, []), total).win_rate
        for pid, bucket in agg.items()
    }

    partners, _ = _pairs(matchdays, group)
    rows: list[schemas.PairLeaderRow] = []
    for (a, b), values in partners.items():
        if a >= b or len(values) < min_days:
            continue
        rate = sum(values) / len(values)
        expected = (baseline.get(a, 0.0) + baseline.get(b, 0.0)) / 2
        rows.append(schemas.PairLeaderRow(
            player_a_id=a, player_a=names.get(a, "?"),
            player_b_id=b, player_b=names.get(b, "?"),
            days=len(values), win_rate=rate, delta=rate - expected,
        ))
    rows.sort(key=lambda r: (r.delta, r.days), reverse=True)
    return schemas.PairLeaderboard(
        together=rows[:limit],
        apart=list(reversed(rows[-limit:])) if rows else [],
        min_days=min_days,
    )


def compute_combo(db: DBSession, group: models.Group,
                  body: schemas.ComboIn) -> schemas.ComboOut:
    matchdays = active_matchdays(db, group.id, body.date_from, body.date_to)
    names = player_names(db, group.id)
    together = [pid for pid in body.together if pid in names]
    against = [pid for pid in body.against if pid in names]

    totals = {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
              "points": 0, "goals_for": 0, "goals_against": 0}
    dates: list = []

    for matchday in matchdays:
        team_of: dict[int, int] = {}
        for team in matchday.teams:
            for member in team.members:
                team_of[member.player_id] = team.id

        if together:
            if any(pid not in team_of for pid in together):
                continue
            our_teams = {team_of[pid] for pid in together}
            if len(our_teams) != 1:
                continue
            our_team = our_teams.pop()
        else:
            our_team = None

        their_team = None
        if against:
            if any(pid not in team_of for pid in against):
                continue
            their_teams = {team_of[pid] for pid in against}
            if len(their_teams) != 1:
                continue
            their_team = their_teams.pop()
            if our_team is not None and their_team == our_team:
                continue
            if our_team is None:
                continue

        counted = False
        for match in matchday.matches:
            sides = (match.home_team_id, match.away_team_id)
            if our_team not in sides:
                continue
            if their_team is not None and their_team not in sides:
                continue
            our_goals = match.home_score if match.home_team_id == our_team else match.away_score
            their_goals = match.away_score if match.home_team_id == our_team else match.home_score
            totals["matches"] += 1
            totals["goals_for"] += our_goals
            totals["goals_against"] += their_goals
            if our_goals > their_goals:
                totals["wins"] += 1
                totals["points"] += group.win_points
            elif our_goals < their_goals:
                totals["losses"] += 1
                totals["points"] += group.loss_points
            else:
                totals["draws"] += 1
                totals["points"] += group.draw_points
            counted = True
        if counted:
            dates.append(matchday.date)

    agg, history = _aggregate(matchdays, group)
    rates = []
    for pid in together or against:
        bucket = agg.get(pid)
        if not bucket:
            continue
        rates.append(
            _player_row(pid, names.get(pid, "?"), bucket, group,
                        history.get(pid, []), len(matchdays)).win_rate
        )
    baseline = sum(rates) / len(rates) if rates else 0.0
    best = totals["matches"] * group.win_points
    win_rate = (totals["points"] / best) if best else 0.0

    return schemas.ComboOut(
        days=len(dates),
        matches=totals["matches"],
        wins=totals["wins"],
        draws=totals["draws"],
        losses=totals["losses"],
        points=totals["points"],
        goals_for=totals["goals_for"],
        goals_against=totals["goals_against"],
        win_rate=win_rate,
        baseline=baseline,
        delta=win_rate - baseline,
        dates=dates,
        together_names=[names.get(pid, "?") for pid in together],
        against_names=[names.get(pid, "?") for pid in against],
    )


def compute_assist_network(db: DBSession, group: models.Group, limit: int = 12,
                           date_from=None, date_to=None) -> schemas.AssistNetwork:
    matchdays = active_matchdays(db, group.id, date_from, date_to)
    names = player_names(db, group.id)
    links: dict[tuple[int, int], int] = defaultdict(int)
    total = 0
    for matchday in matchdays:
        for match in matchday.matches:
            for goal in match.goals:
                if goal.assist_player_id is None or goal.own_goal:
                    continue
                links[(goal.assist_player_id, goal.player_id)] += 1
                total += 1

    rows = [
        schemas.AssistLink(
            assist_player_id=assist_id, assist_name=names.get(assist_id, "?"),
            scorer_player_id=scorer_id, scorer_name=names.get(scorer_id, "?"),
            goals=count,
        )
        for (assist_id, scorer_id), count in links.items()
    ]
    rows.sort(key=lambda r: (r.goals, r.assist_name), reverse=True)
    return schemas.AssistNetwork(links=rows[:limit], total_assisted_goals=total)


def rotate_share_token(db: DBSession, group: models.Group) -> str:
    group.share_token = new_token(24)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group.share_token
