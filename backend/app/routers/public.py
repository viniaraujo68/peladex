from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session as DBSession
from sqlmodel import func, select

from .. import models, schemas, services
from ..config import settings
from ..db import get_session
from ..errors import api_error
from ..ratelimit import limiter

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("", response_model=list[schemas.PublicGroupSummary])
@limiter.limit(settings.rate_limit_public)
def search_public_groups(request: Request, q: str = Query("", max_length=80),
                         limit: int = Query(30, ge=1, le=100),
                         db: DBSession = Depends(get_session)):
    stmt = select(models.Group).where(models.Group.visibility == "public")
    term = q.strip()
    if term:
        like = f"%{term.lower()}%"
        stmt = stmt.where(
            func.lower(models.Group.name).like(like) | func.lower(models.Group.slug).like(like)
        )
    groups = db.exec(stmt.order_by(models.Group.name).limit(limit)).all()
    matchday_counts, player_counts = services.group_counts(db, [g.id for g in groups])
    return [
        schemas.PublicGroupSummary(
            name=g.name, slug=g.slug, description=g.description,
            matchday_count=matchday_counts.get(g.id, 0),
            player_count=player_counts.get(g.id, 0),
        )
        for g in groups
    ]


@router.get("/{slug}", response_model=schemas.PublicGroupOut)
@limiter.limit(settings.rate_limit_public)
def get_public_group(request: Request, slug: str, t: str | None = None,
                     db: DBSession = Depends(get_session)):
    group = db.exec(select(models.Group).where(models.Group.slug == slug)).first()
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pelada não encontrada")

    allowed = group.visibility == "public" or (group.share_token and t == group.share_token)
    if not allowed:
        raise api_error(status.HTTP_403_FORBIDDEN, "group_private", "Esta pelada é privada")

    names = services.player_names(db, group.id)
    venues = services.venue_names(db, group.id)
    matchdays = services.active_matchdays(db, group.id)
    matchdays.sort(key=lambda m: (m.date, m.id), reverse=True)
    return schemas.PublicGroupOut(
        name=group.name,
        slug=group.slug,
        description=group.description,
        stats=services.compute_stats(db, group),
        evolution=services.compute_evolution(db, group),
        matchdays=[services.serialize_matchday(db, m, group, names, venues) for m in matchdays],
    )


@router.get("/{slug}/players/{player_id}", response_model=schemas.PlayerDetailOut)
@limiter.limit(settings.rate_limit_public)
def get_public_player(request: Request, slug: str, player_id: int, t: str | None = None,
                      min_days: int = Query(services.MIN_PAIR_DAYS, ge=1, le=50),
                      db: DBSession = Depends(get_session)):
    group = db.exec(select(models.Group).where(models.Group.slug == slug)).first()
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pelada não encontrada")
    allowed = group.visibility == "public" or (group.share_token and t == group.share_token)
    if not allowed:
        raise api_error(status.HTTP_403_FORBIDDEN, "group_private", "Esta pelada é privada")
    detail = services.compute_player_detail(db, group, player_id, min_days)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jogador não encontrado")
    return detail
