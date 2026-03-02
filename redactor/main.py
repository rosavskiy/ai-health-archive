"""
Redactor Service — изолированный шлюз маскирования ПДн.

Правила:
  - Stateless: ничего не сохраняется на диск, нет БД
  - Без логов содержимого файлов или текста
  - Доступен только из внутренней сети (не публичный порт)
  - Защищён API-ключом в заголовке X-Redactor-Key
"""
import base64
import io
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.ocr import ocr_with_boxes
from app.ner import find_pii_spans, mask_text
from app.masker import mask_image

# Логгер — никогда не логирует содержимое файлов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("redactor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Redactor service started. Content logging: DISABLED")
    yield
    logger.info("Redactor service stopped.")


app = FastAPI(
    title="Redactor Service",
    version="1.0.0",
    docs_url=None,   # Документация отключена — сервис не публичный
    redoc_url=None,
    lifespan=lifespan,
)


def verify_key(x_redactor_key: str = Header(...)):
    """Проверяет API-ключ. Без ключа — 403."""
    if x_redactor_key != settings.REDACTOR_API_KEY:
        logger.warning("Redactor: unauthorized access attempt")
        raise HTTPException(status_code=403, detail="Forbidden")


class RedactTextRequest(BaseModel):
    text: str


class RedactResponse(BaseModel):
    masked_text: str
    masked_image_b64: str | None = None  # None если входные данные были текстом
    pii_found: int                        # количество найденных ПДн-спанов


@app.get("/health")
def health():
    return {"status": "ok", "service": "redactor"}


@app.post("/redact/file", response_model=RedactResponse, dependencies=[Depends(verify_key)])
async def redact_file(file: UploadFile = File(...)):
    """
    Принимает файл (JPEG/PNG/PDF).
    1. OCR → текст + координаты слов
    2. NER → находит ПДн-спаны
    3. Маскирует текст (████) и изображение (чёрные прямоугольники)
    4. Возвращает результат и сразу забывает — ничего не сохраняет
    """
    file_bytes = await file.read()
    mime = file.content_type or "image/jpeg"

    logger.info(f"Redacting file: mime={mime}, size={len(file_bytes)} bytes")
    # НЕ логируем имя файла и содержимое намеренно

    # Если PDF — конвертируем первую страницу в изображение
    image_bytes = file_bytes
    if mime == "application/pdf":
        image_bytes = _pdf_to_image(file_bytes)
        mime = "image/jpeg"

    # OCR
    try:
        raw_text, words = await ocr_with_boxes(image_bytes, mime)
    except Exception as e:
        logger.error(f"OCR failed: {type(e).__name__}")
        raise HTTPException(502, "OCR service unavailable")

    # NER — ищем ПДн
    spans = find_pii_spans(raw_text)
    logger.info(f"PII spans found: {len(spans)}")

    # Маскируем текст
    masked_txt = mask_text(raw_text, spans)

    # Маскируем изображение
    masked_img_bytes = mask_image(image_bytes, words, raw_text, spans)
    masked_img_b64 = base64.b64encode(masked_img_bytes).decode("utf-8")

    # Явно обнуляем переменные с сырыми данными
    del raw_text
    del file_bytes
    del image_bytes
    del words

    return RedactResponse(
        masked_text=masked_txt,
        masked_image_b64=masked_img_b64,
        pii_found=len(spans),
    )


@app.post("/redact/text", response_model=RedactResponse, dependencies=[Depends(verify_key)])
async def redact_text(req: RedactTextRequest):
    """
    Принимает чистый текст.
    Маскирует ПДн, возвращает очищенную версию.
    """
    logger.info(f"Redacting text: length={len(req.text)} chars")

    spans = find_pii_spans(req.text)
    logger.info(f"PII spans found: {len(spans)}")

    masked_txt = mask_text(req.text, spans)

    del req  # убираем оригинал из памяти

    return RedactResponse(
        masked_text=masked_txt,
        masked_image_b64=None,
        pii_found=len(spans),
    )


def _pdf_to_image(pdf_bytes: bytes) -> bytes:
    """Конвертирует первую страницу PDF в JPEG через PyPDF2 + Pillow."""
    try:
        import pypdf2
        import PIL.Image

        # Простой способ: рендерим через pypdf как изображение
        # Для полноценного рендера используем pdf2image если доступен
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=200)
            buf = io.BytesIO()
            images[0].save(buf, format="JPEG", quality=92)
            return buf.getvalue()
        except ImportError:
            # Fallback: пробуем открыть PDF напрямую через Pillow
            img = PIL.Image.open(io.BytesIO(pdf_bytes))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92)
            return buf.getvalue()
    except Exception:
        # Если совсем не получилось — возвращаем как есть
        return pdf_bytes
