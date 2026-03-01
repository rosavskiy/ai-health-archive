from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import uuid
from datetime import datetime

from app.db.session import get_db
from app.db.models import User
from app.core.security import (
    verify_password, hash_password, create_access_token,
    generate_totp_secret, verify_totp, get_totp_qr_base64, decode_token
)
from app.core.config import settings

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    consent_accepted: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    totp_required: bool = False


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_base64: str


class TOTPVerifyRequest(BaseModel):
    code: str


@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if not req.consent_accepted:
        raise HTTPException(400, detail="Необходимо принять Политику конфиденциальности и согласие на обработку ПД (152-ФЗ)")

    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, detail="Email уже зарегистрирован")

    user = User(
        id=uuid.uuid4(),
        email=req.email,
        hashed_password=hash_password(req.password),
        consent_accepted=True,
        consent_accepted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Аккаунт создан. Рекомендуем настроить 2FA.", "user_id": str(user.id)}


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")

    # Если 2FA включена — возвращаем временный токен, фронт запросит OTP
    if user.totp_enabled:
        temp_token = create_access_token(
            {"sub": str(user.id), "purpose": "totp_verify"},
            expires_delta=timedelta(minutes=5)
        )
        return TokenResponse(access_token=temp_token, totp_required=True)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/totp/verify", response_model=TokenResponse)
def totp_verify(req: TOTPVerifyRequest, db: Session = Depends(get_db),
                token: str = Depends(lambda x: x)):
    pass  # упрощённо — полная реализация ниже


@router.post("/totp/verify-full", response_model=TokenResponse)
def totp_verify_full(
    code: str = Body(..., embed=True),
    temp_token: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    payload = decode_token(temp_token)
    if payload.get("purpose") != "totp_verify":
        raise HTTPException(401, "Неверный токен")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not verify_totp(user.totp_secret, code):
        raise HTTPException(401, "Неверный OTP-код")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/totp/setup", response_model=TOTPSetupResponse)
def totp_setup(db: Session = Depends(get_db), token: str = Depends(
    lambda req: req.headers.get("Authorization", "").replace("Bearer ", "")
)):
    payload = decode_token(token)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    secret = generate_totp_secret()
    user.totp_secret = secret
    db.commit()
    qr = get_totp_qr_base64(secret, user.email)
    return TOTPSetupResponse(secret=secret, qr_base64=qr)


@router.post("/totp/enable")
def totp_enable(code: str = Body(..., embed=True), db: Session = Depends(get_db),
                token: str = Depends(lambda req: req.headers.get("Authorization", "").replace("Bearer ", ""))):
    payload = decode_token(token)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user.totp_secret or not verify_totp(user.totp_secret, code):
        raise HTTPException(400, "Неверный код. 2FA не активирована.")
    user.totp_enabled = True
    db.commit()
    return {"message": "2FA успешно активирована"}
