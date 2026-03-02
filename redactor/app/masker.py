"""
Графическое маскирование изображений.
Рисует чёрные прямоугольники поверх слов, которые содержат ПДн.
Использует координаты bbox из OCR + список PII-спанов из NER.
"""
import io
from typing import List
from PIL import Image, ImageDraw


def _word_intersects_pii(word_text: str, word_offset: int, spans: List[dict]) -> bool:
    """Проверяет, попадает ли слово в один из PII-спанов."""
    word_end = word_offset + len(word_text)
    for span in spans:
        # Перекрытие
        if word_offset < span["end"] and word_end > span["start"]:
            return True
    return False


def mask_image(
    image_bytes: bytes,
    words: List[dict],
    text: str,
    spans: List[dict],
    padding: int = 4,
) -> bytes:
    """
    Рисует чёрные прямоугольники поверх PII-регионов.

    words: [{text, x, y, w, h}] — слова с координатами из OCR
    text: полный распознанный текст (для сопоставления offset)
    spans: [{start, end, label, original}] — PII-спаны в тексте
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Строим маппинг: ищем каждое OCR-слово в тексте по порядку
    # и проверяем, находится ли оно в PII-спане
    cursor = 0
    for word_info in words:
        word_text = word_info["text"]
        if not word_text:
            continue

        # Ищем слово в тексте начиная с текущей позиции
        pos = text.find(word_text, cursor)
        if pos == -1:
            continue
        cursor = pos  # не двигаем вперёд — слово может повторяться

        if _word_intersects_pii(word_text, pos, spans):
            x = word_info["x"] - padding
            y = word_info["y"] - padding
            x2 = x + word_info["w"] + padding * 2
            y2 = y + word_info["h"] + padding * 2
            draw.rectangle([max(0, x), max(0, y), x2, y2], fill="black")

        cursor = pos + len(word_text)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()
