import secrets

from fastapi import BackgroundTasks, HTTPException, status
from sqlmodel import select

from apps.forms import (
    RegisterForm, VerifyForm, ResendForm, LoginForm, Token, RefreshTokenRequest,
)
from apps.models import User
from apps.utils import (
    hash_password, verify_password, generate_otp, save_pending_user,
    get_pending_user, send_otp_email, redis_client, MAX_ATTEMPTS,
    create_access_and_refresh_tokens, verify_token,
)
from apps.views.main import app, SessionDep


@app.post('/user/register')
async def register(register_form: RegisterForm, session: SessionDep,
                   background: BackgroundTasks):
    taken = session.exec(
        select(User).where(
            (User.email == register_form.email)
            | (User.username == register_form.username)
        )
    ).first()
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Email yoki username allaqachon band")

    data = register_form.model_dump()
    data["password"] = hash_password(data["password"])

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

    if pending["attempts"] >= MAX_ATTEMPTS:
        await redis_client.delete(key)
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Urinishlar ko'p bo'ldi, qaytadan ro'yxatdan o'ting")

    if not secrets.compare_digest(pending["code"], form.code):
        await save_pending_user(form.email, pending["data"], pending["code"],
                                attempts=pending["attempts"] + 1, keep_ttl=True)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kod noto'g'ri")

    instance = User(**pending["data"])
    session.add(instance)
    session.commit()
    session.refresh(instance)

    await redis_client.delete(key)

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
    user = session.exec(
        select(User).where(User.username == login_form.username)
    ).first()
    if not user or not verify_password(login_form.password, user.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Username yoki parol xato")

    access, refresh = create_access_and_refresh_tokens(str(user.id))
    return Token(access_token=access, refresh_token=refresh, token_type="bearer")


@app.post('/refresh', response_model=Token)
async def refresh_access_token(request: RefreshTokenRequest):
    user_id = verify_token(request.refresh_token, token_type="refresh")
    access, refresh = create_access_and_refresh_tokens(user_id)
    return Token(access_token=access, refresh_token=refresh, token_type="bearer")
