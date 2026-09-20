from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session as DBSession

from .. import models, schemas, services
from ..auth import require_owner
from ..db import get_session
from .groups import load_group

router = APIRouter(prefix="/api/groups/{group_id}", tags=["stats"])


@router.get("/stats", response_model=schemas.StatsOut)
def get_stats(group_id: int, date_from: date | None = None, date_to: date | None = None,
              _: models.User = Depends(require_owner),
              db: DBSession = Depends(get_session)):
    return services.compute_stats(db, load_group(db, group_id), date_from, date_to)


@router.get("/evolution", response_model=schemas.EvolutionOut)
def get_evolution(group_id: int, date_from: date | None = None, date_to: date | None = None,
                  _: models.User = Depends(require_owner),
                  db: DBSession = Depends(get_session)):
    return services.compute_evolution(db, load_group(db, group_id), date_from, date_to)


@router.get("/players/{player_id}/detail", response_model=schemas.PlayerDetailOut)
def get_player_detail(group_id: int, player_id: int,
                      min_days: int = Query(services.MIN_PAIR_DAYS, ge=1, le=50),
                      date_from: date | None = None, date_to: date | None = None,
                      _: models.User = Depends(require_owner),
                      db: DBSession = Depends(get_session)):
    detail = services.compute_player_detail(
        db, load_group(db, group_id), player_id, min_days, date_from, date_to
    )
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jogador não encontrado")
    return detail


@router.get("/pairs", response_model=schemas.PairLeaderboard)
def get_pairs(group_id: int, min_days: int = Query(services.MIN_PAIR_DAYS, ge=1, le=50),
              limit: int = Query(10, ge=1, le=50),
              date_from: date | None = None, date_to: date | None = None,
              _: models.User = Depends(require_owner),
              db: DBSession = Depends(get_session)):
    return services.compute_pair_leaderboard(
        db, load_group(db, group_id), min_days, limit, date_from, date_to
    )


@router.post("/combo", response_model=schemas.ComboOut)
def post_combo(group_id: int, body: schemas.ComboIn,
               _: models.User = Depends(require_owner),
               db: DBSession = Depends(get_session)):
    return services.compute_combo(db, load_group(db, group_id), body)


@router.get("/assist-network", response_model=schemas.AssistNetwork)
def get_assist_network(group_id: int, limit: int = Query(12, ge=1, le=60),
                       date_from: date | None = None, date_to: date | None = None,
                       _: models.User = Depends(require_owner),
                       db: DBSession = Depends(get_session)):
    return services.compute_assist_network(
        db, load_group(db, group_id), limit, date_from, date_to
    )
