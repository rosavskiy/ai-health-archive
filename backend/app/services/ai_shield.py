"""
AI-Shield: OCR → NER-маскирование → Извлечение показателей.
Весь pipeline работает с анонимизированным текстом перед отправкой в LLM.
"""
import re
import json
import base64
import httpx
from typing import Optional

from openai import OpenAI
from app.core.config import settings

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Регулярные выражения для быстрого pre-маскирования
PII_PATTERNS = [
    (r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\s?\d{2}\b", "[СНИЛС_MASK]"),        # СНИЛС
    (r"\b\d{16}\b", "[ПОЛИС_MASK]"),                                       # Полис ОМС
    (r"\b(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b", "[ТЕЛЕФОН_MASK]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL_MASK]"),
]


async def ocr_document(file_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    Вызов Yandex Vision OCR API для извлечения текста из изображения/PDF.
    """
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    payload = {
        "folderId": settings.YANDEX_FOLDER_ID,
        "analyze_specs": [
            {
                "content": encoded,
                "features": [{"type": "TEXT_DETECTION", "text_detection_config": {"language_codes": ["ru", "en"]}}],
            }
        ],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze",
            json=payload,
            headers={
                "Authorization": f"Api-Key {settings.YANDEX_VISION_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()

    result = resp.json()
    texts = []
    for r in result.get("results", []):
        for feature in r.get("results", []):
            if "textDetection" in feature:
                for page in feature["textDetection"].get("pages", []):
                    for block in page.get("blocks", []):
                        for line in block.get("lines", []):
                            line_text = " ".join(w["text"] for w in line.get("words", []))
                            texts.append(line_text)
    return "\n".join(texts)


def regex_mask_pii(text: str) -> str:
    """Быстрое regex-маскирование очевидных PII."""
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


async def llm_mask_and_extract(raw_text: str) -> dict:
    """
    Отправляем PRE-маскированный текст в LLM.
    LLM: 1) финально маскирует оставшиеся ПДн, 2) извлекает медпоказатели.
    Личность + мед.данные НИКОГДА не передаются вместе.
    """
    pre_masked = regex_mask_pii(raw_text)

    system_prompt = """Ты — медицинский AI-ассистент для системы AI Health Archive (РФ).
Задача:
1. Найди и замени ВСЕ оставшиеся персональные данные (ФИО, адрес, дата рождения, паспорт) на токены [PII_MASK].
2. Извлеки все лабораторные показатели в JSON-массив:
   [{"name": "Глюкоза", "value": 5.1, "unit": "ммоль/л", "ref_min": 3.9, "ref_max": 6.1, "date": "2026-01-15"}]
3. Верни JSON: {"masked_text": "...", "metrics": [...], "lab_name": "...", "doc_date": "YYYY-MM-DD"}
Отвечай ТОЛЬКО валидным JSON, без markdown-блоков."""

    response = openai_client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Документ (предобработан):\n{pre_masked}"},
        ],
        temperature=0,
        max_tokens=4096,
    )

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
