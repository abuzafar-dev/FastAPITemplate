"""Typed settings, read from the environment.

Everything the app needs is declared here once, validated at startup, instead
of `os.getenv` scattered across modules where a typo silently becomes None and
a missing value only surfaces when some request finally needs it.

Nothing security-relevant has a usable default: the signing key and the
database URL are required, so a misconfigured deployment refuses to start
rather than coming up with a weak or shared value.
"""

from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Sozlama xato bo'lsa ValidationError kiruvchi qiymatlarni (.env dagi
        # kalitlar, SMTP paroli) logga yozib yubormasin.
        hide_input_in_errors=True,
    )

    # --- required -----------------------------------------------------------
    # Generate with:  openssl rand -hex 32
    # min_length guards against a short placeholder being pasted in: a 10-char
    # key would still "work" while being trivially brute-forceable.
    # SecretStr: repr/log/traceback'da '**********' bo'lib ko'rinadi.
    secret_key: SecretStr = Field(min_length=32)
    database_url: PostgresDsn

    # --- JWT ----------------------------------------------------------------
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Redis: holds the pending-registration OTPs -------------------------
    redis_url: RedisDsn = "redis://localhost:6379/0"
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    # Noto'g'ri urinishlar hisobi shu muddat saqlanadi. Qayta ro'yxatdan o'tish
    # uni nolga tushirmaydi - aks holda kodni cheksiz taxmin qilish mumkin.
    otp_lock_seconds: int = 3600
    register_cooldown_seconds: int = 60
    register_ip_limit: int = 10            # bitta IP dan ...
    register_ip_window_seconds: int = 3600  # ... shuncha soniya ichida

    # --- SMTP: sends the OTP ------------------------------------------------
    # Optional so the app still starts without mail configured; sending then
    # fails loudly at the point of use instead of blocking every other route.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """Cached, so the environment is read and validated once and every importer
    sees the same object."""
    return Settings()


settings = get_settings()
