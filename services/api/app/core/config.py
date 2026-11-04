from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================
    # Application
    # =========================================================
    app_name: str = "LovetechCyber AI Forex Analyst"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"

    # =========================================================
    # Database
    # =========================================================
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "lovetech_forex"

    # =========================================================
    # Authentication
    # =========================================================
    jwt_secret_key: str = Field(min_length=32)

    access_token_expire_minutes: int = Field(
        default=10,
        ge=5,
        le=15,
    )

    refresh_token_expire_days: int = Field(
        default=30,
        ge=1,
        le=90,
    )

    login_rate_limit: str = "5/minute"
    password_reset_rate_limit: str = "3/minute"

    # =========================================================
    # Password Reset
    # =========================================================
    password_reset_url: str = (
        "http://localhost:5173/reset-password"
    )

    # =========================================================
    # Email / SMTP
    # =========================================================
    smtp_host: str = ""

    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
    )

    smtp_username: str = ""
    smtp_password: str = ""

    smtp_from_email: str = ""

    smtp_from_name: str = (
        "LovetechCyber AI Forex Analyst"
    )

    # =========================================================
    # HTTP Security
    # =========================================================
    trusted_hosts: str = (
        "localhost,127.0.0.1"
    )

    cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:4173"
    )

    max_request_bytes: int = Field(
        default=1_048_576,
        ge=1_024,
        le=10_485_760,
    )

    # =========================================================
    # Validators
    # =========================================================
    @field_validator("app_env")
    @classmethod
    def validate_environment(
        cls,
        value: str,
    ) -> str:
        value = value.strip().lower()

        if value not in {
            "development",
            "testing",
            "production",
        }:
            raise ValueError(
                "APP_ENV must be development, "
                "testing, or production"
            )

        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_signing_secret(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip().lower()

        weak_values = {
            "change-me",
            "changeme",
            "secret",
            "password",
            "replace_with_a_random_secret_of_at_least_32_characters",
        }

        if normalized in weak_values:
            raise ValueError(
                "JWT_SECRET_KEY is a placeholder or weak value. "
                "Generate a unique random secret."
            )

        if len(value.strip()) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least "
                "32 characters long."
            )

        return value
        
    # MT5 Market Data Ingestion
    mt5_ingest_api_key: str = ""
    market_data_rate_limit: str = "30/minute"
    max_market_data_candles: int = Field(
        default=500,
        ge=1,
        le=500,
    )
    @field_validator("mt5_ingest_api_key")
    @classmethod
    def validate_mt5_api_key(cls, value: str) -> str:
        value = value.strip()

        if value and len(value) < 32:
            raise ValueError(
                "MT5_INGEST_API_KEY must be at least 32 characters"
            )

        return value
    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(
        cls,
        value: str,
    ) -> str:
        value = "/" + value.strip("/")

        if value == "/":
            raise ValueError(
                "API_V1_PREFIX cannot be the root path"
            )

        return value

    @field_validator("mongodb_database")
    @classmethod
    def validate_database_name(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value or len(value) > 63:
            raise ValueError(
                "Invalid MongoDB database name"
            )

        invalid_characters = '/\\. "$*<>:|?'

        if any(
            char in value
            for char in invalid_characters
        ):
            raise ValueError(
                "MongoDB database name contains "
                "invalid characters"
            )

        return value

    @field_validator("trusted_hosts")
    @classmethod
    def validate_trusted_hosts(
        cls,
        value: str,
    ) -> str:
        hosts = [
            host.strip()
            for host in value.split(",")
            if host.strip()
        ]

        if not hosts:
            raise ValueError(
                "At least one trusted host is required"
            )

        for host in hosts:
            if (
                "/" in host
                or "://" in host
                or " " in host
            ):
                raise ValueError(
                    "TRUSTED_HOSTS must contain hostnames "
                    "only, not URLs or paths"
                )

        return ",".join(hosts)

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(
        cls,
        value: str,
    ) -> str:
        origins = [
            origin.strip().rstrip("/")
            for origin in value.split(",")
            if origin.strip()
        ]

        if not origins:
            raise ValueError(
                "At least one CORS origin is required"
            )

        for origin in origins:
            if origin == "*":
                raise ValueError(
                    "Wildcard CORS origins are not allowed"
                )

            if not origin.startswith(
                ("http://", "https://")
            ):
                raise ValueError(
                    "CORS_ORIGINS must contain "
                    "explicit HTTP(S) origins"
                )

            if any(
                char in origin
                for char in "\r\n\t "
            ):
                raise ValueError(
                    "Invalid whitespace in CORS origin"
                )

        return ",".join(origins)

    @field_validator("password_reset_url")
    @classmethod
    def validate_password_reset_url(
        cls,
        value: str,
    ) -> str:
        value = value.strip().rstrip("/")

        if not value.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "PASSWORD_RESET_URL must be an HTTP(S) URL"
            )

        if any(
            char in value
            for char in "\r\n"
        ):
            raise ValueError(
                "Invalid password reset URL"
            )

        return value

    # =========================================================
    # Helper Properties
    # =========================================================
    @property
    def allowed_hosts(self) -> list[str]:
        return [
            host.strip()
            for host in self.trusted_hosts.split(",")
            if host.strip()
        ]

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    # =========================================================
    # Production Security Validation
    # =========================================================
    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env == "production":
            uri_lower = self.mongodb_uri.lower()

            # Production must not use local MongoDB.
            if (
                "localhost" in uri_lower
                or "127.0.0.1" in uri_lower
            ):
                raise ValueError(
                    "Production must not use a localhost "
                    "MongoDB URI"
                )

            # MongoDB must use TLS in production.
            if not (
                uri_lower.startswith("mongodb+srv://")
                or "tls=true" in uri_lower
                or "ssl=true" in uri_lower
            ):
                raise ValueError(
                    "Production MongoDB connections "
                    "must use TLS"
                )

            # Frontend origins must use HTTPS.
            if any(
                origin.startswith("http://")
                for origin in self.allowed_origins
            ):
                raise ValueError(
                    "Production CORS origins must use HTTPS"
                )

            # Wildcard hosts are forbidden.
            if (
                "*" in self.allowed_hosts
                or not self.allowed_hosts
            ):
                raise ValueError(
                    "Production must define explicit "
                    "trusted hosts"
                )

            # Password reset links must use HTTPS.
            if self.password_reset_url.startswith(
                "http://"
            ):
                raise ValueError(
                    "Production password reset URLs "
                    "must use HTTPS"
                )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()