"""
AI-Консультант: чат-интерфейс на основе анонимизированных медданных.
ФИО НИКОГДА не попадают в запросы к LLM — только показатели и даты.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from openai import OpenAI

from app.db.session import get_db
from app.db.models import Metric, User
from app.core.config import settings
from app.api.routes.documents import get_current_user

router = APIRouter()
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


def build_health_context(user_id: str, db: Session) -> str:
    """Формирует анонимный контекст из метрик пользователя для LLM."""
    metrics = (
        db.query(Metric)
        .filter(Metric.user_id == user_id)
        .order_by(Metric.measured_at.desc())
        .limit(200)
        .all()
    )
    if not metrics:
        return "Данные анализов отсутствуют."

    lines = ["Медицинские показатели пользователя (без ПДн):"]
    for m in metrics:
        status = "⚠ ОТКЛОНЕНИЕ" if m.is_abnormal else "норма"
        lines.append(
            f"- {m.measured_at.strftime('%Y-%m-%d')} | {m.name}: {m.value} {m.unit or ''} "
            f"[ref: {m.reference_min}–{m.reference_max}] [{status}]"
        )
    return "\n".join(lines)


@router.post("/")
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    health_context = build_health_context(str(current_user.id), db)

    system_prompt = f"""Ты — персональный AI-ассистент по здоровью в сервисе AI Health Archive.
Ты помогаешь пользователю понять его лабораторные анализы, динамику показателей и потенциальные риски.
Ты НЕ ставишь диагнозы и НЕ назначаешь лечение. Рекомендуй обращаться к врачу при отклонениях.
Работаешь только с анонимизированными данными — никаких ФИО в ответах.
Отвечай на русском языке, кратко и понятно.

=== ДАННЫЕ ПОЛЬЗОВАТЕЛЯ (анонимизированы) ===
{health_context}
=============================================="""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in req.messages[-20:]:  # последние 20 сообщений
        messages.append({"role": msg.role, "content": msg.content})

    response = openai_client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )

    return {"reply": response.choices[0].message.content}
