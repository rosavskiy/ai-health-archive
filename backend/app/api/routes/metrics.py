from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.db.models import Metric, User
from app.core.security import decode_token
from app.api.routes.documents import get_current_user

router = APIRouter()


@router.get("/")
def get_metrics(
    name: Optional[str] = Query(None, description="Фильтр по названию показателя"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список всех метрик пользователя (для графиков динамики)."""
    query = db.query(Metric).filter(Metric.user_id == current_user.id)
    if name:
        query = query.filter(Metric.name.ilike(f"%{name}%"))
    metrics = query.order_by(Metric.measured_at.asc()).offset(skip).limit(limit).all()
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "value": m.value,
            "unit": m.unit,
            "reference_min": m.reference_min,
            "reference_max": m.reference_max,
            "is_abnormal": m.is_abnormal,
            "measured_at": m.measured_at.isoformat(),
        }
        for m in metrics
    ]


@router.get("/names")
def get_metric_names(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Уникальные названия показателей (для построения меню графиков)."""
    names = (
        db.query(Metric.name)
        .filter(Metric.user_id == current_user.id)
        .distinct()
        .all()
    )
    return [n[0] for n in names]


@router.get("/summary")
def get_metrics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Сводка: последние значения всех показателей + флаг отклонения."""
    subq = (
        db.query(Metric.name, func.max(Metric.measured_at).label("latest"))
        .filter(Metric.user_id == current_user.id)
        .group_by(Metric.name)
        .subquery()
    )
    metrics = (
        db.query(Metric)
        .join(subq, (Metric.name == subq.c.name) & (Metric.measured_at == subq.c.latest))
        .filter(Metric.user_id == current_user.id)
        .all()
    )
    return [
        {
            "name": m.name,
            "value": m.value,
            "unit": m.unit,
            "reference_min": m.reference_min,
            "reference_max": m.reference_max,
            "is_abnormal": m.is_abnormal,
            "measured_at": m.measured_at.isoformat(),
        }
        for m in metrics
    ]


@router.get("/trend/{metric_name}")
def get_metric_trend(
    metric_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """История конкретного показателя за всё время (данные для Chart.js)."""
    metrics = (
        db.query(Metric)
        .filter(Metric.user_id == current_user.id, Metric.name == metric_name)
        .order_by(Metric.measured_at.asc())
        .all()
    )
    return {
        "name": metric_name,
        "unit": metrics[0].unit if metrics else "",
        "reference_min": metrics[0].reference_min if metrics else None,
        "reference_max": metrics[0].reference_max if metrics else None,
        "data": [{"date": m.measured_at.isoformat(), "value": m.value} for m in metrics],
    }
