"""Test muhiti: haqiqiy Postgres/Redis/SMTP ishlatilmaydi.

apps.models import paytida engine yaratib create_all() chaqiradi, shuning uchun
importdan OLDIN muhit o'zgaruvchilari qo'yiladi va create_engine xotiradagi
SQLite'ga yo'naltiriladi. Redis o'rnida fakeredis, email yuborish o'chirilgan.
"""
import os

# Muhit o'zgaruvchilari .env dan ustun turadi: testlar haqiqiy .env dagi
# kalitlar va SMTP parolini hech qachon o'qimaydi/ishlatmaydi.
os.environ["SECRET_KEY"] = "test-" + "x" * 40
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""

import fakeredis  # noqa: E402
import pytest  # noqa: E402
import sqlmodel  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

_real_create_engine = sqlmodel.create_engine
sqlmodel.create_engine = lambda *a, **k: _real_create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import apps.utils  # noqa: E402
import apps.views.auth  # noqa: E402
from apps.models import engine  # noqa: E402
from apps.views import app  # noqa: E402


@pytest.fixture
def redis():
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    for module in (apps.utils, apps.views.auth):
        module.redis_client = client
    return client


@pytest.fixture
def sent_codes(monkeypatch):
    """send_otp_email o'rniga: yuborilgan kodlarni yig'adi."""
    codes = {}

    async def fake_send(email, code):
        codes[email] = code

    monkeypatch.setattr(apps.views.auth, "send_otp_email", fake_send)
    return codes


@pytest.fixture
def client(redis, sent_codes):
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client
