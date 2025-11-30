from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SaaS Risk Scanner"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "postgres"
    database_password: str = ""
    database_name: str = "saas_risk_scanner"
    database_pool_min_size: int = 1
    database_pool_max_size: int = 10

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_seconds: int = 3600
    refresh_token_expire_seconds: int = 604800

    encryption_key: str = ""

    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    allowed_redirect_uris: str = (
        "http://localhost:5173/auth/callback,"
        "http://localhost:8000/api/v1/integrations/google/callback"
    )

    @property
    def allowed_redirect_uri_list(self) -> list[str]:
        return [uri.strip() for uri in self.allowed_redirect_uris.split(",")]


settings = Settings()
