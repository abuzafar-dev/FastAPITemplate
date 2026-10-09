import asyncio

import httpx
import pytest

from apps.config import settings
from apps.views import app

EMAIL = "victim@example.com"
FORM = {"name": "Ali", "age": 20, "username": "ali", "email": EMAIL, "password": "Parol-12345"}


def wrong_code(real: str) -> str:
    return f"{(int(real) + 1) % 1_000_000:06d}"


def test_register_and_verify_success(client, sent_codes):
    assert client.post("/user/register", json=FORM).status_code == 200
    response = client.post("/user/verify", json={"email": EMAIL, "code": sent_codes[EMAIL]})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_wrong_code_attempts_are_limited(client, sent_codes):
    client.post("/user/register", json=FORM)
    bad = wrong_code(sent_codes[EMAIL])
    statuses = [client.post("/user/verify", json={"email": EMAIL, "code": bad}).status_code
                for _ in range(settings.otp_max_attempts + 1)]
    assert statuses == [400] * settings.otp_max_attempts + [429]


def test_reregister_does_not_reset_attempts(client, sent_codes, redis):
    for _ in range(3):
        client.post("/user/register", json=FORM)
        bad = wrong_code(sent_codes[EMAIL])
        for _ in range(settings.otp_max_attempts):
            client.post("/user/verify", json={"email": EMAIL, "code": bad})
        asyncio.run(redis.delete(f"register_cooldown:{EMAIL}"))  # cooldown'ni chetlab o'tamiz
    # 3 marta qayta ro'yxatdan o'tilgan bo'lsa ham, to'g'ri kod endi qabul qilinmaydi
    client.post("/user/register", json=FORM)
    response = client.post("/user/verify", json={"email": EMAIL, "code": sent_codes[EMAIL]})
    assert response.status_code == 429


def test_register_cooldown(client):
    assert client.post("/user/register", json=FORM).status_code == 200
    assert client.post("/user/register", json=FORM).status_code == 429


def test_concurrent_wrong_guesses_are_capped(client, sent_codes):
    client.post("/user/register", json=FORM)
    real = sent_codes[EMAIL]
    guesses = [f"{i:06d}" for i in range(40) if f"{i:06d}" != real][:30]

    async def attack():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            return await asyncio.gather(*[
                ac.post("/user/verify", json={"email": EMAIL, "code": code}) for code in guesses
            ])

    responses = asyncio.run(attack())
    max_attempts = settings.otp_max_attempts
    # Faqat limit ichidagi so'rovlargina kodni haqiqatan solishtiradi
    compared = [r for r in responses if r.json().get("detail") == "Kod noto'g'ri"]
    assert len(compared) <= max_attempts
    assert any(r.status_code == 429 for r in responses)
