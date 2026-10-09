import json
import secrets
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Optional

import bcrypt
import jwt
import aiosmtplib
import redis.asyncio as redis
from fastapi import HTTPException, status

from apps.config import settings

# ---------- Parol ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    """hashed None bo'lsa ham (foydalanuvchi yo'q) xuddi shuncha vaqt bcrypt
    ishlaydi - javob vaqtidan username mavjudligini bilib bo'lmasin."""
    raw = password.encode()
    if len(raw) > 72:  # bcrypt 5 ValueError beradi; bunday parol baribir saqlanmaydi
        raw = raw[:72]
        hashed_ok = False
    else:
        hashed_ok = hashed is not None
    matched = bcrypt.checkpw(raw, (hashed or _DUMMY_HASH).encode())
    return matched and hashed_ok


_DUMMY_HASH = bcrypt.hashpw(b"timing-equalizer", bcrypt.gensalt()).decode()


# ---------- JWT ----------
# Settings validates these at import time: a missing or too-short SECRET_KEY
# stops the process rather than letting it run on something guessable.
SECRET_KEY = settings.secret_key.get_secret_value()
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days


def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_and_refresh_tokens(user_id: str) -> tuple[str, str]:
    access_token = create_token(
        data={"sub": user_id, "type": "access"},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_token(
        data={"sub": user_id, "type": "refresh"},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return access_token, refresh_token


def verify_token(token: str, token_type: str = "access") -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    if payload.get("type") != token_type:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"Invalid token type. Expected {token_type}",
        )

    return user_id


# ---------- OTP (email) ----------
redis_client = redis.from_url(str(settings.redis_url), decode_responses=True)

OTP_TTL = settings.otp_ttl_seconds
MAX_ATTEMPTS = settings.otp_max_attempts


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def save_pending_user(email: str, data: dict, code: str):
    payload = json.dumps({"data": data, "code": code})
    await redis_client.set(f"register:{email}", payload, ex=OTP_TTL)


async def register_verify_attempt(email: str) -> bool:
    """Tasdiqlash urinishini hisoblaydi; limitdan oshsa False.

    Hisob alohida kalitda: ro'yxatdan qayta o'tish yoki resend uni nolga
    tushirmaydi. INCR atomar - parallel so'rovlar ham bitta hisobni oshiradi,
    shuning uchun bir vaqtda yuborilgan ko'p taxmin ham MAX_ATTEMPTS dan oshmaydi.
    """
    key = f"otp_attempts:{email}"
    await redis_client.set(key, 0, ex=settings.otp_lock_seconds, nx=True)
    return await redis_client.incr(key) <= MAX_ATTEMPTS


async def within_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    """Oyna ichida limit oshmagan bo'lsa True. Atomar (SET NX EX + INCR)."""
    await redis_client.set(key, 0, ex=window_seconds, nx=True)
    return await redis_client.incr(key) <= limit


async def clear_verify_attempts(email: str):
    await redis_client.delete(f"otp_attempts:{email}")


async def get_pending_user(email: str) -> dict | None:
    raw = await redis_client.get(f"register:{email}")
    return json.loads(raw) if raw else None


async def send_otp_email(to_email: str, code: str):
    msg = EmailMessage()
    msg["From"] = settings.smtp_user
    msg["To"] = to_email
    msg["Subject"] = "Tasdiqlash kodi"
    msg.set_content(f"Sizning kodingiz: {code}\nKod 5 daqiqa amal qiladi.")

    if not settings.smtp_user or not settings.smtp_password:
        raise RuntimeError("SMTP_USER / SMTP_PASSWORD are not configured")

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password.get_secret_value(),
        start_tls=True,
    )
