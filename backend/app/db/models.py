"""
Схема БД с деперсонализированным хранением:
  Users <-> EncryptedDocs <-> Metrics

Личные данные хранятся ОТДЕЛЬНО от медицинских показателей.
Связь только через encrypted UUID (user_uuid).
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, Boolean,
    ForeignKey, Float, Integer, JSON, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    """
    Таблица пользователей — содержит только auth-данные.
    НЕ содержит ФИО или медицинских данных.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    totp_secret = Column(String(64), nullable=True)        # 2FA TOTP secret
    totp_enabled = Column(Boolean, default=False)
    push_subscription = Column(JSON, nullable=True)        # web push subscription объект
    imap_credentials_enc = Column(Text, nullable=True)     # зашифрованные IMAP credentials

    # Consent (152-ФЗ)
    consent_accepted = Column(Boolean, default=False)
    consent_accepted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    documents = relationship("EncryptedDoc", back_populates="owner", cascade="all, delete-orphan")


class EncryptedDoc(Base):
    """
    Зашифрованные документы — оригиналы файлов в S3 (AES-256).
    Маскированный текст хранится в masked_text.
    """
    __tablename__ = "encrypted_docs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Метаданные документа
    original_filename = Column(String(512), nullable=True)
    doc_type = Column(String(64), nullable=True)       # "lab_result", "receipt", "scan"
    lab_name = Column(String(255), nullable=True)      # "Invitro", "Helix", etc.
    doc_date = Column(DateTime, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(32), default="manual")      # "manual" | "email_sync"

    # S3 ссылка на зашифрованный оригинал
    s3_key = Column(String(1024), nullable=True)

    # AI-Shield: маскированный текст (без ПДн)
    masked_text = Column(Text, nullable=True)
    # Маскированное изображение (чёрные прямоугольники поверх ПДн) — base64
    masked_image_b64 = Column(Text, nullable=True)
    # Количество найденных ПДн-спанов
    pii_found = Column(Integer, default=0)
    masking_status = Column(
        SAEnum("pending", "processing", "done", "error", name="masking_status_enum"),
        default="pending"
    )

    owner = relationship("User", back_populates="documents")
    metrics = relationship("Metric", back_populates="document", cascade="all, delete-orphan")


class Metric(Base):
    """
    Деперсонализированные медицинские показатели.
    Не содержит ФИО — только user_id (UUID) + числовые значения.
    """
    __tablename__ = "metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("encrypted_docs.id"), nullable=True)

    name = Column(String(255), nullable=False, index=True)   # "Глюкоза", "Холестерин", "TSH"
    value = Column(Float, nullable=False)
    unit = Column(String(64), nullable=True)                 # "ммоль/л", "мкМЕ/мл"
    reference_min = Column(Float, nullable=True)
    reference_max = Column(Float, nullable=True)
    is_abnormal = Column(Boolean, default=False)
    measured_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("EncryptedDoc", back_populates="metrics")


class Notification(Base):
    """Push-уведомления пользователя."""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
