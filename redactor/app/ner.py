"""
NER — поиск Персональных Данных (ПДн) в тексте.
Использует natasha (Russian NLP) + regex-паттерны.
Возвращает списокspan'ов {start, end, label} для маскирования.
"""
import re
from typing import List, Tuple
from natasha import (
    Segmenter, MorphVocab,
    NewsEmbedding, NewsNERTagger,
    NamesExtractor, AddrExtractor,
    Doc,
)

# Инициализируем один раз при старте
_segmenter = Segmenter()
_morph = MorphVocab()
_emb = NewsEmbedding()
_ner = NewsNERTagger(_emb)
_names_extractor = NamesExtractor(_morph)
_addr_extractor = AddrExtractor(_morph)

# Regex-паттерны для структурированных ПДн
_PATTERNS: List[Tuple[str, str]] = [
    (r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\s?\d{2}\b", "СНИЛС"),
    (r"\b\d{16}\b", "ПОЛИС"),
    (r"\b(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b", "ТЕЛЕФОН"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "EMAIL"),
    # Серия и номер паспорта РФ
    (r"\b\d{4}\s?\d{6}\b", "ПАСПОРТ"),
    # Дата рождения (ДД.ММ.ГГГГ)
    (r"\b\d{2}\.\d{2}\.(19|20)\d{2}\b", "ДАТА_РОЖДЕНИЯ"),
]

# Метка маски для вывода (█ × длина слова)
MASK_CHAR = "█"


def find_pii_spans(text: str) -> List[dict]:
    """
    Возвращает список: [{start, end, label, original}]
    Все позиции — символьные индексы в тексте.
    """
    spans = []

    # 1. Natasha NER: имена (PER) и адреса (LOC/ADR)
    doc = Doc(text)
    doc.segment(_segmenter)
    doc.tag_ner(_ner)

    for span in doc.spans:
        if span.type in ("PER", "LOC", "ORG"):
            spans.append({
                "start": span.start,
                "end": span.stop,
                "label": span.type,
                "original": text[span.start:span.stop],
            })

    # 2. Natasha NamesExtractor — ФИО с высокой точностью
    for match in _names_extractor(text).matches:
        spans.append({
            "start": match.start,
            "end": match.stop,
            "label": "ФИО",
            "original": text[match.start:match.stop],
        })

    # 3. Regex-паттерны
    for pattern, label in _PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            spans.append({
                "start": m.start(),
                "end": m.end(),
                "label": label,
                "original": m.group(),
            })

    # Сортируем и убираем дубли/перекрытия
    spans.sort(key=lambda s: s["start"])
    merged = []
    for s in spans:
        if merged and s["start"] < merged[-1]["end"]:
            # Берём более широкий span
            if s["end"] > merged[-1]["end"]:
                merged[-1]["end"] = s["end"]
        else:
            merged.append(s)

    return merged


def mask_text(text: str, spans: List[dict]) -> str:
    """Заменяет найденные ПДн на ████ той же длины."""
    result = list(text)
    for span in reversed(spans):
        length = span["end"] - span["start"]
        replacement = MASK_CHAR * max(length, 4)
        result[span["start"]:span["end"]] = list(replacement)
    return "".join(result)
