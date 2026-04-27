from fastapi import APIRouter, Depends, HTTPException, Query

from app.controllers.analytics import (
    get_analytics_cost_breakdown,
    get_analytics_daily_cost,
    get_analytics_daily_latency,
    get_analytics_kpis,
    get_recent_conversations,
)
from app.db.db_connection import get_db

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


# ─────────────────────────────────────────────────────────────
@router.get("/kpis")
def analytics_kpis(
    days: int = Query(default=30, ge=1, le=365),
    db=Depends(get_db),
):
    """Devuelve los KPIs de uso del sistema."""
    try:
        return get_analytics_kpis(db=db, days=days)
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/costs/daily")
def analytics_daily_cost(
    days: int = Query(default=30, ge=1, le=365),
    db=Depends(get_db),
):
    """Devuelve el costo diario de uso del sistema."""
    try:
        return {
            "window_days": days,
            "items": get_analytics_daily_cost(db=db, days=days),
        }
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/latency/daily")
def analytics_daily_latency(
    days: int = Query(default=30, ge=1, le=365),
    db=Depends(get_db),
):
    """Devuelve la latencia diaria del sistema."""
    try:
        return {
            "window_days": days,
            "items": get_analytics_daily_latency(db=db, days=days),
        }
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/costs/by-model")
def analytics_cost_by_model(
    days: int = Query(default=30, ge=1, le=365),
    db=Depends(get_db),
):
    """Devuelve el costo por modelo de lenguaje."""
    try:
        return {
            "window_days": days,
            "items": get_analytics_cost_breakdown(db=db, days=days),
        }
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/overview")
def analytics_overview(
    days: int = Query(default=30, ge=1, le=365),
    db=Depends(get_db),
):
    """Devuelve un resumen general de analíticas."""
    try:
        return {
            "kpis": get_analytics_kpis(db=db, days=days),
            "daily_cost": get_analytics_daily_cost(db=db, days=days),
            "daily_latency": get_analytics_daily_latency(db=db, days=days),
            "cost_by_model": get_analytics_cost_breakdown(db=db, days=days),
        }
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/conversations/recent")
def analytics_recent_conversations(
    q: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=30, ge=1, le=100),
    db=Depends(get_db),
):
    """Devuelve las conversaciones recientes registradas."""
    try:
        return {
            "limit": limit,
            "items": get_recent_conversations(db=db, limit=limit, q=q),
        }
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
