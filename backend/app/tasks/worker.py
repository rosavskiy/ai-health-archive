"""
Celery tasks для фоновой обработки:
- process_uploaded_document: OCR + маскирование + извлечение метрик
- sync_email_for_user: IMAP синхронизация
"""
import asyncio
import uuid
from datetime import datetime
from celery import Celery

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models import EncryptedDoc, Metric, Notification

celery_app = Celery("healthsafe", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "Europe/Moscow"

# Периодическая задача IMAP каждые 15 минут
celery_app.conf.beat_schedule = {
    "imap-sync-all-users": {
        "task": "app.tasks.worker.sync_all_users_email",
        "schedule": 900.0,  # 15 минут
    }
}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_uploaded_document(self, doc_id: str, file_bytes_hex: str, mime_type: str):
    """
    Фоновая обработка документа:
    1. Декодируем байты
    2. OCR + AI-Shield masking
    3. Извлекаем метрики → сохраняем в БД
    """
    from app.services.ai_shield import process_document_pipeline

    db = SessionLocal()
    try:
        doc = db.query(EncryptedDoc).filter(EncryptedDoc.id == doc_id).first()
        if not doc:
            return

        doc.masking_status = "processing"
        db.commit()

        file_bytes = bytes.fromhex(file_bytes_hex)
        result = asyncio.get_event_loop().run_until_complete(
            process_document_pipeline(file_bytes, mime_type)
        )

        doc.masked_text = result.get("masked_text", "")
        doc.lab_name = result.get("lab_name", "")
        if result.get("doc_date"):
            try:
                doc.doc_date = datetime.strptime(result["doc_date"], "%Y-%m-%d")
            except Exception:
                pass
        doc.masking_status = "done"
        db.commit()

        # Сохраняем метрики
        for m in result.get("metrics", []):
            try:
                measured_at = datetime.strptime(m.get("date", ""), "%Y-%m-%d") if m.get("date") else datetime.utcnow()
            except Exception:
                measured_at = datetime.utcnow()

            val = float(m.get("value", 0))
            ref_min = m.get("ref_min")
            ref_max = m.get("ref_max")
            is_abnormal = False
            if ref_min is not None and ref_max is not None:
                is_abnormal = not (float(ref_min) <= val <= float(ref_max))

            metric = Metric(
                id=uuid.uuid4(),
                user_id=doc.user_id,
                document_id=doc.id,
                name=m.get("name", ""),
                value=val,
                unit=m.get("unit", ""),
                reference_min=ref_min,
                reference_max=ref_max,
                is_abnormal=is_abnormal,
                measured_at=measured_at,
            )
            db.add(metric)

        # Push-уведомление
        notif = Notification(
            id=uuid.uuid4(),
            user_id=doc.user_id,
            title="Анализы обработаны",
            body=f"Документ '{doc.original_filename}' успешно распознан и добавлен в архив.",
        )
        db.add(notif)
        db.commit()

    except Exception as exc:
        db.rollback()
        doc = db.query(EncryptedDoc).filter(EncryptedDoc.id == doc_id).first()
        if doc:
            doc.masking_status = "error"
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task
def sync_email_for_user(user_id: str, imap_host: str, imap_port: int, username: str, password: str):
    """Синхронизирует почту конкретного пользователя."""
    from app.services.email_sync import fetch_lab_attachments
    from app.services.storage import upload_document

    db = SessionLocal()
    try:
        attachments = fetch_lab_attachments(imap_host, imap_port, username, password)
        for filename, file_bytes, subject in attachments:
            doc_id = str(uuid.uuid4())
            s3_key = upload_document(user_id, doc_id, file_bytes)

            doc = EncryptedDoc(
                id=doc_id,
                user_id=user_id,
                original_filename=filename,
                s3_key=s3_key,
                source="email_sync",
                masking_status="pending",
            )
            db.add(doc)
            db.commit()

            process_uploaded_document.delay(doc_id, file_bytes.hex(), "application/pdf")
    finally:
        db.close()


@celery_app.task
def sync_all_users_email():
    """Периодическая задача — синхронизирует почту всех пользователей с IMAP."""
    import json
    from cryptography.fernet import Fernet
    from app.core.config import settings

    db = SessionLocal()
    try:
        from app.db.models import User
        users = db.query(User).filter(User.imap_credentials_enc.isnot(None), User.is_active == True).all()
        for user in users:
            try:
                # Расшифровываем IMAP credentials
                f = Fernet(settings.SECRET_KEY.encode()[:44].ljust(44, b"="))
                creds = json.loads(f.decrypt(user.imap_credentials_enc.encode()).decode())
                sync_email_for_user.delay(
                    str(user.id),
                    creds["host"],
                    creds.get("port", 993),
                    creds["username"],
                    creds["password"],
                )
            except Exception as e:
                pass
    finally:
        db.close()
