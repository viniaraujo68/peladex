from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PELADEX_", extra="ignore")

    database_url: str = "sqlite:///./peladex.db"

    session_cookie_name: str = "peladex_session"
    session_ttl_days: int = 30
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    cors_origins: str = "http://localhost:5173"

    allow_registration: bool = True

    rate_limit_enabled: bool = True
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "3/minute"
    rate_limit_public: str = "30/minute"


settings = Settings()
