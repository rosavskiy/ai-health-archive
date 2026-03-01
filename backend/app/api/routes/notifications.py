from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.db.models import Notification, User
from app.core.config import settings
from app.api.routes.documents import get_current_user

router = APIRouter()


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict


@router.post("/subscribe")
def subscribe_push(
    req: PushSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Сохраняет Web Push subscription объект пользователя."""
    current_user.push_subscription = {"endpoint": req.endpoint, "keys": req.keys}
    db.commit()
    return {"message": "Push-уведомления подключены"}


@router.get("/")
def get_notifications(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "body": n.body,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]
