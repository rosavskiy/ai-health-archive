import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.db.session import get_db
from app.db.models import EncryptedDoc, User
from app.core.security import decode_token
from app.core.config import settings
from app.services.storage import upload_document, download_document, delete_document
from app.tasks.worker import process_uploaded_document

router = APIRouter()

ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png", "image/heic"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def get_current_user(db: Session = Depends(get_db),
                     token: str = Depends(lambda req: req.headers.get("Authorization", "").replace("Bearer ", ""))):
    payload = decode_token(token)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(401, "Не авторизован")
    return user


@router.post("/upload", status_code=201)
async def upload_document_route(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, f"Неподдерживаемый тип файла: {file.content_type}")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, "Файл превышает 20 МБ")

    doc_id = str(uuid.uuid4())
    s3_key = upload_document(str(current_user.id), doc_id, file_bytes)

    doc = EncryptedDoc(
        id=doc_id,
        user_id=current_user.id,
        original_filename=file.filename,
        s3_key=s3_key,
        source="manual",
        masking_status="pending",
        doc_type="lab_result",
    )
    db.add(doc)
    db.commit()

    # Запускаем фоновую обработку (Celery)
    process_uploaded_document.delay(doc_id, file_bytes.hex(), file.content_type)

    return {"doc_id": doc_id, "status": "pending", "message": "Файл загружен, идёт обработка AI-Shield"}


@router.get("/")
def list_documents(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(EncryptedDoc).filter(EncryptedDoc.user_id == current_user.id)
    if search:
        query = query.filter(
            EncryptedDoc.original_filename.ilike(f"%{search}%") |
            EncryptedDoc.lab_name.ilike(f"%{search}%")
        )
    docs = query.order_by(EncryptedDoc.uploaded_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": str(d.id),
            "filename": d.original_filename,
            "lab_name": d.lab_name,
            "doc_date": d.doc_date.isoformat() if d.doc_date else None,
            "uploaded_at": d.uploaded_at.isoformat(),
            "status": d.masking_status,
            "source": d.source,
        }
        for d in docs
    ]


@router.get("/{doc_id}/download")
def download_doc(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(EncryptedDoc).filter(
        EncryptedDoc.id == doc_id, EncryptedDoc.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(404, "Документ не найден")

    file_bytes = download_document(doc.s3_key)
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={doc.original_filename}"},
    )


@router.delete("/{doc_id}")
def delete_doc(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(EncryptedDoc).filter(
        EncryptedDoc.id == doc_id, EncryptedDoc.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(404, "Документ не найден")

    if doc.s3_key:
        delete_document(doc.s3_key)
    db.delete(doc)
    db.commit()
    return {"message": "Документ удалён"}
