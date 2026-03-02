"""
Шифрованное S3-хранилище (AES-256 на стороне клиента + server-side encryption).
Совместимо с Yandex Object Storage и Selectel S3.
"""
import io
import base64
import boto3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

from app.core.config import settings


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name="us-east-1",  # MinIO и Yandex принимают этот регион
    )


def _get_aes_key() -> bytes:
    key_b64 = settings.S3_ENCRYPTION_KEY
    if not key_b64:
        raise ValueError("S3_ENCRYPTION_KEY не задан в настройках")
    return base64.b64decode(key_b64)


def encrypt_file(data: bytes) -> bytes:
    """AES-256-GCM шифрование. Возвращает: nonce(12) + ciphertext."""
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext


def decrypt_file(encrypted_data: bytes) -> bytes:
    """Расшифровка AES-256-GCM."""
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    return aesgcm.decrypt(nonce, ciphertext, None)


def upload_document(user_id: str, doc_id: str, file_bytes: bytes) -> str:
    """Шифрует и загружает файл в S3. Возвращает s3_key."""
    encrypted = encrypt_file(file_bytes)
    s3_key = f"users/{user_id}/docs/{doc_id}.enc"
    _get_s3_client().put_object(
        Bucket=settings.S3_BUCKET,
        Key=s3_key,
        Body=encrypted,
    )
    return s3_key


def download_document(s3_key: str) -> bytes:
    """Загружает и расшифровывает документ из S3."""
    resp = _get_s3_client().get_object(Bucket=settings.S3_BUCKET, Key=s3_key)
    encrypted_data = resp["Body"].read()
    return decrypt_file(encrypted_data)


def delete_document(s3_key: str) -> None:
    _get_s3_client().delete_object(Bucket=settings.S3_BUCKET, Key=s3_key)
