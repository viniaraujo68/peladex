from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session as DBSession
from sqlmodel import select

from .. import models, schemas
from ..auth import require_owner
from ..db import get_session
from ..errors import api_error

router = APIRouter(prefix="/api/groups/{group_id}", tags=["catalog"])


@router.get("/players", response_model=list[schemas.PlayerOut])
def list_players(group_id: int, _: models.User = Depends(require_owner),
                 db: DBSession = Depends(get_session)):
    rows = db.exec(
        select(models.Player)
        .where(models.Player.group_id == group_id)
        .order_by(models.Player.name)
    ).all()
    return [schemas.PlayerOut(id=p.id, name=p.name, active=p.active) for p in rows]


@router.post("/players", response_model=schemas.PlayerOut, status_code=201)
def create_player(group_id: int, body: schemas.NamedCreate,
                  _: models.User = Depends(require_owner),
                  db: DBSession = Depends(get_session)):
    exists = db.exec(
        select(models.Player).where(
            models.Player.group_id == group_id, models.Player.name == body.name
        )
    ).first()
    if exists:
        raise api_error(status.HTTP_409_CONFLICT, "player_exists",
                        "Já existe um jogador com esse nome nesta pelada")
    player = models.Player(group_id=group_id, name=body.name)
    db.add(player)
    db.commit()
    db.refresh(player)
    return schemas.PlayerOut(id=player.id, name=player.name, active=player.active)


@router.patch("/players/{player_id}", response_model=schemas.PlayerOut)
def update_player(group_id: int, player_id: int, body: schemas.PlayerUpdate,
                  _: models.User = Depends(require_owner),
                  db: DBSession = Depends(get_session)):
    player = db.get(models.Player, player_id)
    if not player or player.group_id != group_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jogador não encontrado")
    data = body.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in data:
        player.name = data["name"]
    if "active" in data:
        player.active = data["active"]
    db.add(player)
    db.commit()
    db.refresh(player)
    return schemas.PlayerOut(id=player.id, name=player.name, active=player.active)


@router.delete("/players/{player_id}", status_code=204)
def delete_player(group_id: int, player_id: int, _: models.User = Depends(require_owner),
                  db: DBSession = Depends(get_session)):
    player = db.get(models.Player, player_id)
    if not player or player.group_id != group_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jogador não encontrado")
    has_history = db.exec(
        select(models.TeamMember).where(models.TeamMember.player_id == player_id)
    ).first()
    if has_history:
        player.active = False
        db.add(player)
    else:
        db.delete(player)
    db.commit()


def _venue_in_use(db: DBSession, venue_id: int) -> bool:
    return db.exec(
        select(models.Matchday).where(models.Matchday.venue_id == venue_id)
    ).first() is not None


@router.get("/venues", response_model=list[schemas.NamedOut])
def list_venues(group_id: int, _: models.User = Depends(require_owner),
                db: DBSession = Depends(get_session)):
    rows = db.exec(
        select(models.Venue)
        .where(models.Venue.group_id == group_id)
        .order_by(models.Venue.name)
    ).all()
    return [schemas.NamedOut(id=v.id, name=v.name) for v in rows]


@router.post("/venues", response_model=schemas.NamedOut, status_code=201)
def create_venue(group_id: int, body: schemas.NamedCreate,
                 _: models.User = Depends(require_owner),
                 db: DBSession = Depends(get_session)):
    exists = db.exec(
        select(models.Venue).where(
            models.Venue.group_id == group_id, models.Venue.name == body.name
        )
    ).first()
    if exists:
        raise api_error(status.HTTP_409_CONFLICT, "venue_exists", "Local já existe")
    venue = models.Venue(group_id=group_id, name=body.name)
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return schemas.NamedOut(id=venue.id, name=venue.name)


@router.delete("/venues/{venue_id}", status_code=204)
def delete_venue(group_id: int, venue_id: int, _: models.User = Depends(require_owner),
                 db: DBSession = Depends(get_session)):
    venue = db.get(models.Venue, venue_id)
    if not venue or venue.group_id != group_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Local não encontrado")
    if _venue_in_use(db, venue_id):
        raise api_error(status.HTTP_409_CONFLICT, "venue_in_use",
                        "Este local é usado por dias registrados e não pode ser excluído")
    db.delete(venue)
    db.commit()
