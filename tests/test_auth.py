import asyncio
import time
from unittest import mock

import httpx
import pytest
from pydantic import ValidationError

import apps.utils
import apps.views.auth
from apps.config import Settings, settings
from apps.views import app

FORM = {"name": "Ali", "age": 20, "username": "ali", "email": "ali@example.com", "password": "Parol-12345"}


def register_and_verify(client, sent_codes, **overrides):
    form = {**FORM, **overrides}
    assert client.post("/user/register", json=form).status_code == 200
    return client.post("/user/verify", json={"email": form["email"], "code": sent_codes[form["email"]]})


def test_settings_error_does_not_leak_secrets(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")  # majburiy maydon yo'q -> ValidationError
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, secret_key="FAKE-SECRET-" + "x" * 30, smtp_password="FAKE-SMTP")
    assert "FAKE-" not in str(excinfo.value)
    shown = Settings(_env_file=None, secret_key="FAKE-SECRET-" + "x" * 30, smtp_password="FAKE-SMTP",
                     database_url="postgresql://a:b@h/d")
    assert "FAKE-" not in repr(shown)


def test_password_over_72_bytes_is_rejected_cleanly(client):
    response = client.post("/user/register", json={**FORM, "password": "пароль" * 12})  # 72 belgi, 144 bayt
    assert response.status_code == 422


def test_login_with_huge_password_is_401_not_500(client, sent_codes):
    register_and_verify(client, sent_codes)
    response = client.post("/user/login", json={"username": "ali", "password": "a" * 200})
    assert response.status_code == 401


def test_login_success_and_wrong_password(client, sent_codes):
    register_and_verify(client, sent_codes)
    assert client.post("/user/login", json={"username": "ali", "password": FORM["password"]}).status_code == 200
    assert client.post("/user/login", json={"username": "ali", "password": "boshqa-parol"}).status_code == 401


def test_two_pending_registrations_same_username_second_gets_409(client, sent_codes):
    client.post("/user/register", json={**FORM, "email": "a@example.com"})
    client.post("/user/register", json={**FORM, "email": "b@example.com"})
    first = client.post("/user/verify", json={"email": "a@example.com", "code": sent_codes["a@example.com"]})
    second = client.post("/user/verify", json={"email": "b@example.com", "code": sent_codes["b@example.com"]})
    assert (first.status_code, second.status_code) == (200, 409)


def test_register_is_rate_limited_per_ip(client, monkeypatch):
    monkeypatch.setattr(settings, "register_ip_limit", 3)
    statuses = [client.post("/user/register", json={**FORM, "email": f"u{i}@example.com",
                                                    "username": f"u{i}"}).status_code for i in range(5)]
    assert statuses == [200, 200, 200, 429, 429]


def test_unknown_user_still_runs_bcrypt():
    with mock.patch.object(apps.utils.bcrypt, "checkpw", wraps=apps.utils.bcrypt.checkpw) as checkpw:
        assert apps.utils.verify_password("whatever", None) is False
    assert checkpw.call_count == 1


def test_hashing_does_not_block_event_loop(client, monkeypatch):
    def slow_hash(password):
        time.sleep(0.6)
        return "hashed"

    monkeypatch.setattr(apps.views.auth, "hash_password", slow_hash)

    async def scenario():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            started = time.monotonic()
            register = asyncio.create_task(ac.post("/user/register", json=FORM))
            await asyncio.sleep(0.05)  # register hash_password ichiga kirib olsin
            await ac.post("/refresh", json={"refresh_token": "invalid"})  # tez endpoint
            # Loop bloklansa, bu so'rov hash tugaguncha (0.6 s) kutib qoladi
            fast_latency = time.monotonic() - started
            await register
            return fast_latency

    assert asyncio.run(scenario()) < 0.4
