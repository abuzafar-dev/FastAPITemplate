import secrets

from fastapi import BackgroundTasks, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from apps.forms import (
    RegisterForm, VerifyForm, ResendForm, LoginForm, Token, RefreshTokenRequest,
)
from apps.models import User
from apps.config import settings
from apps.utils import (
    hash_password, verify_password, generate_otp, save_pending_user,
    get_pending_user, send_otp_email, redis_client,
    register_verify_attempt, clear_verify_attempts, within_rate_limit,
    create_access_and_refresh_tokens, verify_token,
)
from apps.views.main import app, SessionDep


# Sinxron DB va bcrypt (~0.3-0.4 s) event loop'ni to'sib qo'ymasligi uchun
# ular run_in_threadpool orqali alohida oqimda bajariladi.

def _is_taken(session: Session, email: str, username: str) -> bool:
    return session.exec(
        select(User).where((User.email == email) | (User.username == username))
    ).first() is not None


def _create_user(session: Session, data: dict) -> User:
    instance = User(**data)
    session.add(instance)
    try:
        session.commit()
    except IntegrityError:
        # Ikki kutilayotgan ro'yxat bir xil username bilan: ikkinchisi shu yerda.
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email yoki username allaqachon band")
    session.refresh(instance)
    return instance


def _authenticate(session: Session, username: str, password: str) -> User | None:
    user = session.exec(select(User).where(User.username == username)).first()
    ok = verify_password(password, user.password if user else None)
    return user if ok else None


@app.post('/user/register')
async def register(register_form: RegisterForm, session: SessionDep,
                   background: BackgroundTasks, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not await within_rate_limit(f"register_ip:{client_ip}", settings.register_ip_limit,
                                   settings.register_ip_window_seconds):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Juda ko'p urinish, keyinroq qayta urinib ko'ring")
    if not await redis_client.set(f"register_cooldown:{register_form.email}", 1,
                                  ex=settings.register_cooldown_seconds, nx=True):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "1 daqiqadan keyin qayta urinib ko'ring")

    if await run_in_threadpool(_is_taken, session, register_form.email, register_form.username):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Email yoki username allaqachon band")

    data = register_form.model_dump()
    data["password"] = await run_in_threadpool(hash_password, data["password"])

    code = generate_otp()
    await save_pending_user(register_form.email, data, code)
    background.add_task(send_otp_email, register_form.email, code)

    return {"message": "Emailingizga kod yuborildi"}


@app.post('/user/verify', response_model=Token)
async def verify(form: VerifyForm, session: SessionDep):
    key = f"register:{form.email}"
    pending = await get_pending_user(form.email)
    if not pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Kod muddati tugagan yoki topilmadi")

    if not await register_verify_attempt(form.email):
        await redis_client.delete(key)
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Urinishlar ko'p bo'ldi, keyinroq qaytadan ro'yxatdan o'ting")

    if not secrets.compare_digest(pending["code"], form.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kod noto'g'ri")

    instance = await run_in_threadpool(_create_user, session, pending["data"])

    await redis_client.delete(key)
    await clear_verify_attempts(form.email)

    access, refresh = create_access_and_refresh_tokens(str(instance.id))
    return Token(access_token=access, refresh_token=refresh, token_type="bearer")


@app.post('/user/resend')
async def resend(form: ResendForm, background: BackgroundTasks):
    if not await redis_client.set(f"resend:{form.email}", 1, ex=60, nx=True):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "1 daqiqadan keyin qayta urinib ko'ring")

    pending = await get_pending_user(form.email)
    if not pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Avval ro'yxatdan o'ting")

    code = generate_otp()
    await save_pending_user(form.email, pending["data"], code)
    background.add_task(send_otp_email, form.email, code)

    return {"message": "Yangi kod yuborildi"}


@app.post('/user/login', response_model=Token)
async def login(login_form: LoginForm, session: SessionDep):
    user = await run_in_threadpool(
        _authenticate, session, login_form.username, login_form.password
    )
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Username yoki parol xato")

    access, refresh = create_access_and_refresh_tokens(str(user.id))
    return Token(access_token=access, refresh_token=refresh, token_type="bearer")


@app.post('/refresh', response_model=Token)
async def refresh_access_token(request: RefreshTokenRequest):
    user_id = verify_token(request.refresh_token, token_type="refresh")
    access, refresh = create_access_and_refresh_tokens(user_id)
    return Token(access_token=access, refresh_token=refresh, token_type="bearer")
