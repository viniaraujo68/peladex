from fastapi import APIRouter, Depends, status
from sqlmodel import Session as DBSession
from sqlmodel import select

from .. import models, parser, schemas, services, writes
from ..auth import require_owner
from ..db import get_session
from ..errors import api_error
from .groups import load_group
from .matchdays import find_by_date

router = APIRouter(prefix="/api/groups/{group_id}", tags=["import"])


def _issues(result: parser.ParseResult) -> list[schemas.ImportIssueOut]:
    return [
        schemas.ImportIssueOut(line=i.line, severity=i.severity, code=i.code,
                               message=i.message, text=i.text)
        for i in result.issues
    ]


def _preview_standings(day: parser.ParsedMatchday, group: models.Group) -> list[dict]:
    rows = {
        team.name: {
            "name": team.name, "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0,
        }
        for team in day.teams
    }
    for match in day.matches:
        home = rows.get(match.home_team)
        away = rows.get(match.away_team)
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
    out = []
    for row in rows.values():
        row["points"] = (row["wins"] * group.win_points + row["draws"] * group.draw_points
                         + row["losses"] * group.loss_points)
        row["goal_diff"] = row["goals_for"] - row["goals_against"]
        best = row["played"] * group.win_points
        row["win_rate"] = (row["points"] / best) if best else 0.0
        out.append(row)
    out.sort(key=lambda r: (r["win_rate"], r["goal_diff"], r["goals_for"]), reverse=True)
    return out


def _known_names(db: DBSession, group_id: int) -> list[str]:
    return list(db.exec(
        select(models.Player.name).where(models.Player.group_id == group_id)
    ).all())


@router.post("/import/preview", response_model=schemas.ImportPreviewOut)
def preview_import(group_id: int, body: schemas.ImportPreviewIn,
                   _: models.User = Depends(require_owner),
                   db: DBSession = Depends(get_session)):
    group = load_group(db, group_id)
    result = parser.parse(body.text, _known_names(db, group_id))
    matchdays = [
        schemas.ImportMatchdayPreview(
            date=day.date,
            venue=day.venue,
            mvp=day.mvp,
            notes=day.notes,
            teams=[schemas.ImportTeamPreview(name=t.name, players=t.players) for t in day.teams],
            matches=[
                schemas.ImportMatchPreview(
                    home_team=m.home_team, away_team=m.away_team,
                    home_score=m.home_score, away_score=m.away_score,
                    goals=[
                        schemas.ImportGoalPreview(player=g.player, team=g.team,
                                                  own_goal=g.own_goal, assist=g.assist)
                        for g in m.goals
                    ],
                )
                for m in day.matches
            ],
            already_exists=day.date is not None and find_by_date(db, group_id, day.date) is not None,
            standings=_preview_standings(day, group),
        )
        for day in result.matchdays
    ]
    return schemas.ImportPreviewOut(
        ok=result.ok, matchdays=matchdays, issues=_issues(result),
        new_players=result.new_players,
    )


@router.post("/import", response_model=schemas.ImportCommitOut)
def commit_import(group_id: int, body: schemas.ImportCommitIn,
                  _: models.User = Depends(require_owner),
                  db: DBSession = Depends(get_session)):
    group = load_group(db, group_id)
    result = parser.parse(body.text, _known_names(db, group_id))
    if not result.ok:
        raise api_error(status.HTTP_400_BAD_REQUEST, "import_invalid",
                        "O texto tem erros que precisam ser corrigidos antes de importar.")

    if result.new_players and not body.create_missing_players:
        raise api_error(status.HTTP_400_BAD_REQUEST, "unknown_players",
                        "O texto tem jogadores que ainda não existem nesta pelada.")

    existing_dates = [
        day.date for day in result.matchdays
        if day.date and find_by_date(db, group_id, day.date) is not None
    ]
    if existing_dates and not body.replace_existing:
        listed = ", ".join(d.isoformat() for d in existing_dates)
        raise api_error(status.HTTP_409_CONFLICT, "matchday_exists",
                        f"Já existe dia registrado em: {listed}.")

    players = {
        parser.normalize(p.name): p
        for p in db.exec(select(models.Player).where(models.Player.group_id == group_id)).all()
    }
    created_players: list[str] = []
    for name in result.new_players:
        key = parser.normalize(name)
        if key in players:
            continue
        player = models.Player(group_id=group_id, name=name)
        db.add(player)
        db.flush()
        players[key] = player
        created_players.append(name)

    venues = {
        parser.normalize(v.name): v
        for v in db.exec(select(models.Venue).where(models.Venue.group_id == group_id)).all()
    }

    created_ids: list[int] = []
    replaced = 0
    for day in result.matchdays:
        venue_id = None
        if day.venue:
            key = parser.normalize(day.venue)
            venue = venues.get(key)
            if venue is None:
                venue = models.Venue(group_id=group_id, name=day.venue)
                db.add(venue)
                db.flush()
                venues[key] = venue
            venue_id = venue.id

        mvp_id = None
        if day.mvp:
            mvp = players.get(parser.normalize(day.mvp))
            mvp_id = mvp.id if mvp else None

        team_index = {team.name: index for index, team in enumerate(day.teams)}
        payload = schemas.MatchdayCreate(
            date=day.date,
            venue_id=venue_id,
            mvp_player_id=mvp_id,
            notes=day.notes,
            teams=[
                schemas.TeamIn(
                    name=team.name,
                    player_ids=[players[parser.normalize(n)].id for n in team.players],
                )
                for team in day.teams
            ],
            matches=[
                schemas.MatchIn(
                    home_team_index=team_index[match.home_team],
                    away_team_index=team_index[match.away_team],
                    home_score=match.home_score,
                    away_score=match.away_score,
                    goals=[
                        schemas.GoalIn(
                            player_id=players[parser.normalize(g.player)].id,
                            own_goal=g.own_goal,
                            assist_player_id=(
                                players[parser.normalize(g.assist)].id if g.assist else None
                            ),
                        )
                        for g in match.goals
                    ],
                )
                for match in day.matches
            ],
        )
        writes.validate_payload(db, group_id, payload)

        existing = find_by_date(db, group_id, day.date)
        if existing is not None:
            writes.clear_children(db, existing.id)
            db.expire(existing)
            writes.apply_payload(db, existing, payload)
            replaced += 1
            created_ids.append(existing.id)
        else:
            matchday = models.Matchday(group_id=group_id, date=day.date)
            writes.apply_payload(db, matchday, payload)
            created_ids.append(matchday.id)

    db.commit()
    return schemas.ImportCommitOut(
        created_matchday_ids=created_ids, replaced=replaced,
        created_players=created_players, issues=_issues(result),
    )
