"""
AI-Shield: теперь работает как оркестратор.

Поток:
  1. Отправить файл в Redactor Service → получить masked_text + masked_image
  2. Отправить masked_text в OpenAI → извлечь медпоказатели
  3. Вернуть результат в worker

В OpenAI НИКОГДА не попадают сырые данные — только уже анонимизированный текст.
"""
import re
import json
import httpx
from openai import OpenAI

from app.core.config import settings

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


async def call_redactor_file(file_bytes: bytes, mime_type: str) -> dict:
    """
    Отправляет сырой файл в Redactor Service.
    Возвращает: {masked_text, masked_image_b64, pii_found}
    """
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.REDACTOR_URL}/redact/file",
            files={"file": ("document", file_bytes, mime_type)},
            headers={"X-Redactor-Key": settings.REDACTOR_API_KEY},
        )
        resp.raise_for_status()
    return resp.json()


async def call_redactor_text(text: str) -> dict:
    """
    Отправляет текст в Redactor Service для маскирования ПДн.
    Используется для текстовых вложений из email.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.REDACTOR_URL}/redact/text",
            json={"text": text},
            headers={"X-Redactor-Key": settings.REDACTOR_API_KEY},
        )
        resp.raise_for_status()
    return resp.json()


async def extract_metrics_from_masked_text(masked_text: str) -> dict:
    """
    Отправляет УЖЕ АНОНИМИЗИРОВАННЫЙ текст в OpenAI.
    Задача OpenAI: только структурировать данные, не получать ПДн.
    """
    system_prompt = """Ты — медицинский AI-ассистент.
Получаешь текст лабораторного анализа с уже замаскированными персональными данными (████).
Задача: извлечь медицинские показатели в JSON.

Верни ТОЛЬКО валидный JSON (без markdown-блоков):
{
  "metrics": [
    {"name": "Глюкоза", "value": 5.1, "unit": "ммоль/л", "ref_min": 3.9, "ref_max": 6.1, "date": "2026-01-15"}
  ],
  "lab_name": "Инвитро",
  "doc_date": "2026-01-15"
}

Если показатель не имеет референсных значений — ставь null.
Дату формата YYYY-MM-DD. Если даты нет — null."""

    response = openai_client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": masked_text},
        ],
        temperature=0,
        max_tokens=4096,
    )

    content = response.choices[0].message.content.strip()
    content = re.sub(r"^```json\s*|```$", "", content, flags=re.MULTILINE).strip()
    return json.loads(content)


async def process_document_pipeline(file_bytes: bytes, mime_type: str) -> dict:
    """
    Полный pipeline:
      file → [Redactor: OCR+NER+маскирование] → [OpenAI: извлечение метрик]

    Возвращает:
      {masked_text, masked_image_b64, metrics, lab_name, doc_date, pii_found}
    """
    # Шаг 1: Redactor — все ПДн удалены до того как данные уйдут куда-либо ещё
    redactor_result = await call_redactor_file(file_bytes, mime_type)
    masked_text = redactor_result.get("masked_text", "")
    masked_image_b64 = redactor_result.get("masked_image_b64")
    pii_found = redactor_result.get("pii_found", 0)

    # Шаг 2: OpenAI получает только анонимный текст
    metrics_result = {}
    if masked_text.strip():
        try:
            metrics_result = await extract_metrics_from_masked_text(masked_text)
        except Exception:
            metrics_result = {"metrics": [], "lab_name": "", "doc_date": None}

    return {
        "masked_text": masked_text,
        "masked_image_b64": masked_image_b64,
        "pii_found": pii_found,
        "metrics": metrics_result.get("metrics", []),
        "lab_name": metrics_result.get("lab_name", ""),
        "doc_date": metrics_result.get("doc_date"),
    }


    content = response.choices[0].message.content.strip()
    # Убираем markdown-обёртку если LLM всё же добавил
    content = re.sub(r"^```json\s*|```$", "", content, flags=re.MULTILINE).strip()
    return json.loads(content)


async def process_document_pipeline(file_bytes: bytes, mime_type: str) -> dict:
    """
    Полный pipeline: OCR → regex mask → LLM mask + extract.
    Возвращает: {"masked_text": ..., "metrics": [...], "lab_name": ..., "doc_date": ...}
    """
    raw_text = await ocr_document(file_bytes, mime_type)
    result = await llm_mask_and_extract(raw_text)
    return result
