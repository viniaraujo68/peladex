from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session as DBSession
from sqlmodel import select

from .. import models, schemas, services, writes
from ..auth import require_owner
from ..db import get_session
from ..models import utcnow
from .groups import load_group

router = APIRouter(prefix="/api/groups/{group_id}", tags=["matchdays"])


def get_matchday(db: DBSession, group_id: int, matchday_id: int) -> models.Matchday:
    matchday = db.get(models.Matchday, matchday_id)
    if not matchday or matchday.group_id != group_id or matchday.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dia de pelada não encontrado")
    return matchday


def find_by_date(db: DBSession, group_id: int, day: date_type) -> models.Matchday | None:
    return db.exec(
        select(models.Matchday).where(
            models.Matchday.group_id == group_id,
            models.Matchday.date == day,
            models.Matchday.deleted_at == None,  # noqa: E711
        )
    ).first()


@router.get("/matchdays", response_model=list[schemas.MatchdayOut])
def list_matchdays(group_id: int, _: models.User = Depends(require_owner),
                   db: DBSession = Depends(get_session)):
    group = load_group(db, group_id)
    names = services.player_names(db, group_id)
    venues = services.venue_names(db, group_id)
    matchdays = services.active_matchdays(db, group_id)
    matchdays.sort(key=lambda m: (m.date, m.id), reverse=True)
    return [services.serialize_matchday(db, m, group, names, venues) for m in matchdays]


@router.post("/matchdays", response_model=schemas.MatchdayOut, status_code=201)
def create_matchday(group_id: int, body: schemas.MatchdayCreate,
                    _: models.User = Depends(require_owner),
                    db: DBSession = Depends(get_session)):
    group = load_group(db, group_id)
    writes.validate_payload(db, group_id, body)
    matchday = models.Matchday(group_id=group_id, date=body.date)
    writes.apply_payload(db, matchday, body)
    db.commit()
    db.refresh(matchday)
    return services.serialize_matchday(db, matchday, group)


@router.get("/matchdays/{matchday_id}", response_model=schemas.MatchdayOut)
def read_matchday(group_id: int, matchday_id: int, _: models.User = Depends(require_owner),
                  db: DBSession = Depends(get_session)):
    group = load_group(db, group_id)
    return services.serialize_matchday(db, get_matchday(db, group_id, matchday_id), group)


@router.put("/matchdays/{matchday_id}", response_model=schemas.MatchdayOut)
def update_matchday(group_id: int, matchday_id: int, body: schemas.MatchdayCreate,
                    _: models.User = Depends(require_owner),
                    db: DBSession = Depends(get_session)):
    group = load_group(db, group_id)
    matchday = get_matchday(db, group_id, matchday_id)
    writes.validate_payload(db, group_id, body)
    writes.clear_children(db, matchday.id)
    db.expire(matchday)
    writes.apply_payload(db, matchday, body)
    db.commit()
    db.refresh(matchday)
    return services.serialize_matchday(db, matchday, group)


@router.delete("/matchdays/{matchday_id}", status_code=204)
def delete_matchday(group_id: int, matchday_id: int, _: models.User = Depends(require_owner),
                    db: DBSession = Depends(get_session)):
    matchday = get_matchday(db, group_id, matchday_id)
    matchday.deleted_at = utcnow()
    db.add(matchday)
    db.commit()
