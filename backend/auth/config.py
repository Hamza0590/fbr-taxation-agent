from pydantic_settings import BaseSettings
from functools import lru_cache


class AuthSettings(BaseSettings):
    # Password reset
    reset_token_expire_minutes: int = 30

    # SMTP — env vars: SMTP_HOST, SMTP_PORT, etc.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Tax Sathi"

    # Frontend base URL — env var: FRONTEND_BASE_URL
    frontend_base_url: str = "http://localhost:3000"

    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
