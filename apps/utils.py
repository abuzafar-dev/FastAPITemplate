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


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ---------- JWT ----------
# Settings validates these at import time: a missing or too-short SECRET_KEY
# stops the process rather than letting it run on something guessable.
SECRET_KEY = settings.secret_key
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


async def save_pending_user(email: str, data: dict, code: str,
                            attempts: int = 0, keep_ttl: bool = False):
    payload = json.dumps({"data": data, "code": code, "attempts": attempts})
    key = f"register:{email}"
    if keep_ttl:
        await redis_client.set(key, payload, keepttl=True)
    else:
        await redis_client.set(key, payload, ex=OTP_TTL)


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
        password=settings.smtp_password,
        start_tls=True,
    )
