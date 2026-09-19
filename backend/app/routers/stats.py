from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session as DBSession

from .. import models, schemas, services
from ..auth import require_owner
from ..db import get_session
from .groups import load_group

router = APIRouter(prefix="/api/groups/{group_id}", tags=["stats"])


@router.get("/stats", response_model=schemas.StatsOut)
def get_stats(group_id: int, _: models.User = Depends(require_owner),
              db: DBSession = Depends(get_session)):
    return services.compute_stats(db, load_group(db, group_id))


@router.get("/evolution", response_model=schemas.EvolutionOut)
def get_evolution(group_id: int, _: models.User = Depends(require_owner),
                  db: DBSession = Depends(get_session)):
    return services.compute_evolution(db, load_group(db, group_id))


@router.get("/players/{player_id}/detail", response_model=schemas.PlayerDetailOut)
def get_player_detail(group_id: int, player_id: int,
                      min_days: int = Query(services.MIN_PAIR_DAYS, ge=1, le=50),
                      _: models.User = Depends(require_owner),
                      db: DBSession = Depends(get_session)):
    detail = services.compute_player_detail(db, load_group(db, group_id), player_id, min_days)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jogador não encontrado")
    return detail
