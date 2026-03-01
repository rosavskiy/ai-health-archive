"""
IMAP Email Sync: подключение к Gmail/Yandex Mail для автоматического
обнаружения писем от лабораторий (Invitro, Helix, CMD, Гемотест и др.)
и извлечения PDF-вложений.
"""
import imaplib
import email
import email.header
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Лаборатории — ключевые слова в теме/отправителе для фильтрации
LAB_SENDERS = [
    "invitro", "helix", "cmd", "гемотест", "kdl", "citylab",
    "dnkom", "сдэл", "медси", "результат", "анализ", "лаборатор",
]


def _is_lab_email(msg: email.message.Message) -> bool:
    """Проверяет, является ли письмо результатом анализов."""
    subject_raw = msg.get("Subject", "")
    sender_raw = msg.get("From", "")

    # Декодируем subject
    subject_parts = email.header.decode_header(subject_raw)
    subject = ""
    for part, enc in subject_parts:
        if isinstance(part, bytes):
            subject += part.decode(enc or "utf-8", errors="ignore")
        else:
            subject += str(part)

    combined = (subject + sender_raw).lower()
    return any(kw in combined for kw in LAB_SENDERS)


def fetch_lab_attachments(
    imap_host: str,
    imap_port: int,
    username: str,
    password: str,
    max_emails: int = 50,
) -> List[Tuple[str, bytes, str]]:
    """
    Подключается к IMAP, ищет письма от лабораторий и возвращает вложения.

    Returns:
        List of (filename, file_bytes, subject)
    """
    attachments = []

    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(username, password)
        mail.select("INBOX")

        # Поиск всех непрочитанных писем (или за последние 90 дней)
        _, data = mail.search(None, "UNSEEN")
        email_ids = data[0].split()

        # Берём последние max_emails
        for eid in email_ids[-max_emails:]:
            _, msg_data = mail.fetch(eid, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            if not _is_lab_email(msg):
                continue

            subject = str(msg.get("Subject", ""))
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                is_pdf = content_type == "application/pdf"
                is_attachment = "attachment" in content_disposition
                has_pdf_name = part.get_filename("").lower().endswith(".pdf")

                if (is_pdf or is_attachment) and (has_pdf_name or is_pdf):
                    filename = part.get_filename("document.pdf")
                    file_bytes = part.get_payload(decode=True)
                    if file_bytes:
                        attachments.append((filename, file_bytes, subject))
                        logger.info(f"Найдено вложение: {filename} из письма: {subject}")

        mail.logout()

    except Exception as e:
        logger.error(f"IMAP sync error: {e}")

    return attachments
