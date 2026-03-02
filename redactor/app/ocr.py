"""
OCR через Yandex Vision.
Возвращает текст И координаты слов для графического маскирования.
"""
import base64
import httpx
from typing import List, Tuple

from app.config import settings


async def ocr_with_boxes(
    file_bytes: bytes, mime_type: str = "image/jpeg"
) -> Tuple[str, List[dict]]:
    """
    Возвращает:
      - full_text: весь текст документа
      - words: [{text, x, y, w, h}] — слова с координатами (пиксели)
    """
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    payload = {
        "folderId": settings.YANDEX_FOLDER_ID,
        "analyze_specs": [
            {
                "content": encoded,
                "features": [
                    {
                        "type": "TEXT_DETECTION",
                        "text_detection_config": {"language_codes": ["ru", "en"]},
                    }
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze",
            json=payload,
            headers={
                "Authorization": f"Api-Key {settings.YANDEX_VISION_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()

    data = resp.json()
    words = []
    lines = []

    for result in data.get("results", []):
        for feature in result.get("results", []):
            if "textDetection" not in feature:
                continue
            for page in feature["textDetection"].get("pages", []):
                for block in page.get("blocks", []):
                    for line in block.get("lines", []):
                        line_words = []
                        for word in line.get("words", []):
                            text = word.get("text", "")
                            verts = word.get("boundingBox", {}).get("vertices", [])
                            if len(verts) >= 2:
                                xs = [int(v.get("x", 0)) for v in verts]
                                ys = [int(v.get("y", 0)) for v in verts]
                                x, y = min(xs), min(ys)
                                w = max(xs) - x
                                h = max(ys) - y
                                words.append({"text": text, "x": x, "y": y, "w": w, "h": h})
                            line_words.append(text)
                        lines.append(" ".join(line_words))

    return "\n".join(lines), words
