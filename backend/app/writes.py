from fastapi import status
from sqlalchemy import delete as sa_delete
from sqlmodel import Session as DBSession
from sqlmodel import select

from . import models, schemas
from .errors import api_error


def validate_payload(db: DBSession, group_id: int, body: schemas.MatchdayCreate) -> None:
    if body.venue_id is not None:
        venue = db.get(models.Venue, body.venue_id)
        if not venue or venue.group_id != group_id:
            raise api_error(status.HTTP_400_BAD_REQUEST, "venue_in_other_group",
                            "Local não pertence a esta pelada")

    referenced: set[int] = set()
    for team in body.teams:
        referenced.update(team.player_ids)
    for match in body.matches:
        for goal in match.goals:
            referenced.add(goal.player_id)
            if goal.assist_player_id is not None:
                referenced.add(goal.assist_player_id)
    if body.mvp_player_id is not None:
        referenced.add(body.mvp_player_id)

    if referenced:
        owned = set(db.exec(
            select(models.Player.id).where(
                models.Player.group_id == group_id, models.Player.id.in_(referenced)
            )
        ).all())
        if owned != referenced:
            raise api_error(status.HTTP_400_BAD_REQUEST, "player_in_other_group",
                            "Jogador não pertence a esta pelada")

    seen: dict[int, int] = {}
    for index, team in enumerate(body.teams):
        if len(set(team.player_ids)) != len(team.player_ids):
            raise api_error(status.HTTP_400_BAD_REQUEST, "duplicate_player",
                            f"Jogador repetido no time {team.name}")
        for player_id in team.player_ids:
            if player_id in seen:
                raise api_error(status.HTTP_400_BAD_REQUEST, "player_in_two_teams",
                                "O mesmo jogador está em dois times no mesmo dia")
            seen[player_id] = index

    names = [team.name.strip().lower() for team in body.teams]
    if len(set(names)) != len(names):
        raise api_error(status.HTTP_400_BAD_REQUEST, "duplicate_team",
                        "Dois times com o mesmo nome no mesmo dia")

    for match in body.matches:
        if match.home_team_index >= len(body.teams) or match.away_team_index >= len(body.teams):
            raise api_error(status.HTTP_400_BAD_REQUEST, "unknown_team",
                            "Partida aponta para um time que não existe neste dia")
        if match.home_team_index == match.away_team_index:
            raise api_error(status.HTTP_400_BAD_REQUEST, "same_team_twice",
                            "Um time não pode jogar contra ele mesmo")
        for goal in match.goals:
            if goal.player_id not in seen:
                raise api_error(status.HTTP_400_BAD_REQUEST, "scorer_not_playing",
                                "Um artilheiro não está escalado neste dia")
            if goal.assist_player_id is None:
                continue
            if goal.own_goal:
                raise api_error(status.HTTP_400_BAD_REQUEST, "own_goal_assist",
                                "Gol contra não pode ter assistência")
            if goal.assist_player_id == goal.player_id:
                raise api_error(status.HTTP_400_BAD_REQUEST, "self_assist",
                                "Um jogador não pode dar assistência para si mesmo")
            if seen.get(goal.assist_player_id) != seen[goal.player_id]:
                raise api_error(status.HTTP_400_BAD_REQUEST, "assist_other_team",
                                "A assistência tem que ser de alguém do mesmo time")


def clear_children(db: DBSession, matchday_id: int) -> None:
    team_ids = select(models.Team.id).where(models.Team.matchday_id == matchday_id)
    match_ids = select(models.Match.id).where(models.Match.matchday_id == matchday_id)
    opts = {"synchronize_session": False}
    db.execute(sa_delete(models.Goal).where(models.Goal.match_id.in_(match_ids)),
               execution_options=opts)
    db.execute(sa_delete(models.Match).where(models.Match.matchday_id == matchday_id),
               execution_options=opts)
    db.execute(sa_delete(models.TeamMember).where(models.TeamMember.team_id.in_(team_ids)),
               execution_options=opts)
    db.execute(sa_delete(models.Team).where(models.Team.matchday_id == matchday_id),
               execution_options=opts)
    db.flush()


def apply_payload(db: DBSession, matchday: models.Matchday,
                  body: schemas.MatchdayCreate) -> None:
    matchday.date = body.date
    matchday.venue_id = body.venue_id
    matchday.mvp_player_id = body.mvp_player_id
    matchday.notes = body.notes
    db.add(matchday)
    db.flush()

    team_ids: list[int] = []
    team_of_player: dict[int, int] = {}
    for index, team_in in enumerate(body.teams):
        team = models.Team(matchday_id=matchday.id, name=team_in.name.strip(),
                           color=team_in.color, sort_index=index)
        db.add(team)
        db.flush()
        team_ids.append(team.id)
        for player_id in team_in.player_ids:
            db.add(models.TeamMember(team_id=team.id, player_id=player_id))
            team_of_player[player_id] = team.id

    for index, match_in in enumerate(body.matches):
        home_id = team_ids[match_in.home_team_index]
        away_id = team_ids[match_in.away_team_index]
        match = models.Match(
            matchday_id=matchday.id, sort_index=index,
            home_team_id=home_id, away_team_id=away_id,
            home_score=match_in.home_score, away_score=match_in.away_score,
        )
        db.add(match)
        db.flush()
        for goal_in in match_in.goals:
            scorer_team = team_of_player[goal_in.player_id]
            if goal_in.own_goal and scorer_team == home_id:
                credited = away_id
            elif goal_in.own_goal and scorer_team == away_id:
                credited = home_id
            else:
                credited = scorer_team
            db.add(models.Goal(match_id=match.id, player_id=goal_in.player_id,
                               team_id=credited, own_goal=goal_in.own_goal,
                               assist_player_id=goal_in.assist_player_id))
