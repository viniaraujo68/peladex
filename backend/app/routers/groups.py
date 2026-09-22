from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sa_delete
from sqlmodel import Session as DBSession
from sqlmodel import select

from .. import models, schemas, services
from ..auth import get_current_user, require_owner
from ..db import get_session
from ..errors import api_error

router = APIRouter(prefix="/api/groups", tags=["groups"])


def _out(g: models.Group, matchday_counts: dict[int, int],
         player_counts: dict[int, int],
         venue_names: dict[int, str] | None = None) -> schemas.GroupOut:
    venue_names = venue_names or {}
    return schemas.GroupOut(
        id=g.id, name=g.name, slug=g.slug, description=g.description,
        visibility=g.visibility, share_token=g.share_token,
        win_points=g.win_points, draw_points=g.draw_points, loss_points=g.loss_points,
        track_scorers=g.track_scorers, track_assists=g.track_assists,
        show_ratings=g.show_ratings,
        default_venue_id=g.default_venue_id,
        default_venue_name=venue_names.get(g.default_venue_id) if g.default_venue_id else None,
        matchday_count=matchday_counts.get(g.id, 0),
        player_count=player_counts.get(g.id, 0),
    )


def _to_out(db: DBSession, g: models.Group) -> schemas.GroupOut:
    counts = services.group_counts(db, [g.id])
    return _out(g, counts[0], counts[1], services.venue_names(db, g.id))


def load_group(db: DBSession, group_id: int) -> models.Group:
    group = db.get(models.Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pelada não encontrada")
    return group


@router.get("", response_model=list[schemas.GroupOut])
def list_my_groups(user: models.User = Depends(get_current_user),
                   db: DBSession = Depends(get_session)):
    group_ids = db.exec(
        select(models.GroupOwner.group_id).where(models.GroupOwner.user_id == user.id)
    ).all()
    groups = db.exec(
        select(models.Group).where(models.Group.id.in_(group_ids))
    ).all() if group_ids else []
    matchday_counts, player_counts = services.group_counts(db, [g.id for g in groups])
    return [_out(g, matchday_counts, player_counts) for g in groups]


@router.post("", response_model=schemas.GroupOut, status_code=201)
def create_group(body: schemas.GroupCreate, user: models.User = Depends(get_current_user),
                 db: DBSession = Depends(get_session)):
    group = models.Group(
        name=body.name, slug=services.unique_slug(db, body.name),
        description=body.description,
        visibility=body.visibility if body.visibility in ("private", "public") else "private",
    )
    db.add(group)
    db.flush()
    db.add(models.GroupOwner(group_id=group.id, user_id=user.id))
    db.commit()
    db.refresh(group)
    return _to_out(db, group)


@router.get("/{group_id}", response_model=schemas.GroupOut)
def get_group(group_id: int, user: models.User = Depends(require_owner),
              db: DBSession = Depends(get_session)):
    return _to_out(db, load_group(db, group_id))


@router.patch("/{group_id}", response_model=schemas.GroupOut)
def update_group(group_id: int, body: schemas.GroupUpdate,
                 user: models.User = Depends(require_owner),
                 db: DBSession = Depends(get_session)):
    group = load_group(db, group_id)
    data = body.model_dump(exclude_unset=True)
    if "visibility" in data and data["visibility"] not in ("private", "public"):
        data.pop("visibility")
    if "default_venue_id" in data and data["default_venue_id"] is not None:
        venue = db.get(models.Venue, data["default_venue_id"])
        if not venue or venue.group_id != group_id:
            raise api_error(status.HTTP_400_BAD_REQUEST, "venue_in_other_group",
                            "Local não pertence a esta pelada")
    for key in [k for k, v in data.items() if v is None and k != "default_venue_id"]:
        data.pop(key)
    for key, value in data.items():
        setattr(group, key, value)
    if "name" in data:
        group.slug = services.unique_slug(db, group.name, group.id)
    db.add(group)
    db.commit()
    db.refresh(group)
    return _to_out(db, group)


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, user: models.User = Depends(require_owner),
                 db: DBSession = Depends(get_session)):
    group = load_group(db, group_id)
    if group.default_venue_id is not None:
        group.default_venue_id = None
        db.add(group)
        db.flush()
    matchday_ids = select(models.Matchday.id).where(models.Matchday.group_id == group_id)
    team_ids = select(models.Team.id).where(models.Team.matchday_id.in_(matchday_ids))
    match_ids = select(models.Match.id).where(models.Match.matchday_id.in_(matchday_ids))
    opts = {"synchronize_session": False}
    db.execute(sa_delete(models.Goal).where(models.Goal.match_id.in_(match_ids)),
               execution_options=opts)
    db.execute(sa_delete(models.Match).where(models.Match.matchday_id.in_(matchday_ids)),
               execution_options=opts)
    db.execute(sa_delete(models.TeamMember).where(models.TeamMember.team_id.in_(team_ids)),
               execution_options=opts)
    db.execute(sa_delete(models.Team).where(models.Team.matchday_id.in_(matchday_ids)),
               execution_options=opts)
    db.execute(sa_delete(models.Matchday).where(models.Matchday.group_id == group_id),
               execution_options=opts)
    db.execute(sa_delete(models.Player).where(models.Player.group_id == group_id),
               execution_options=opts)
    db.execute(sa_delete(models.Venue).where(models.Venue.group_id == group_id),
               execution_options=opts)
    db.execute(sa_delete(models.GroupOwner).where(models.GroupOwner.group_id == group_id),
               execution_options=opts)
    db.execute(sa_delete(models.Group).where(models.Group.id == group_id),
               execution_options=opts)
    db.commit()


@router.post("/{group_id}/rotate-share-token", response_model=schemas.GroupOut)
def rotate_token(group_id: int, user: models.User = Depends(require_owner),
                 db: DBSession = Depends(get_session)):
    group = load_group(db, group_id)
    services.rotate_share_token(db, group)
    return _to_out(db, group)
