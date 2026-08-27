from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")

    # Database (MongoDB)
    mongodb_url: str = Field(
        default="mongodb://localhost:27017",
        alias="MONGODB_URL",
    )
    mongodb_db: str = Field(default="resumeiq", alias="MONGODB_DB")
    # Backward-compatible alias used by older env files
    database_url: str = Field(
        default="mongodb://localhost:27017",
        alias="DATABASE_URL",
    )
    embedding_dimensions: int = Field(default=768, alias="EMBEDDING_DIMENSIONS")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        alias="CORS_ORIGINS",
    )
    # Matches Vercel production + preview URLs (https://*.vercel.app)
    cors_origin_regex: str = Field(
        default=r"https://([a-z0-9-]+\.)+vercel\.app",
        alias="CORS_ORIGIN_REGEX",
    )

    # JWT / Auth (later phases)
    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    auth_rate_limit_per_minute: int = Field(default=10, alias="AUTH_RATE_LIMIT_PER_MINUTE")
    ai_rate_limit_per_minute: int = Field(default=30, alias="AI_RATE_LIMIT_PER_MINUTE")

    # AI Provider (Groq by default; OpenAI still supported)
    ai_provider: str = Field(default="groq", alias="AI_PROVIDER")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    ai_base_url: str = Field(default="", alias="AI_BASE_URL")
    ai_model: str = Field(default="openai/gpt-oss-120b", alias="AI_MODEL")
    ai_embedding_model: str = Field(
        default="nomic-embed-text-v1_5",
        alias="AI_EMBEDDING_MODEL",
    )
    ai_max_retries: int = Field(default=2, alias="AI_MAX_RETRIES")
    ai_request_timeout_seconds: int = Field(default=60, alias="AI_REQUEST_TIMEOUT_SECONDS")
    ai_mock_mode: bool = Field(default=False, alias="AI_MOCK_MODE")

    # File upload (later phases)
    upload_max_size_mb: int = Field(default=10, alias="UPLOAD_MAX_SIZE_MB")
    upload_allowed_extensions: str = Field(
        default="pdf,docx,png,jpg,jpeg,webp,gif",
        alias="UPLOAD_ALLOWED_EXTENSIONS",
    )
    file_storage_backend: str = Field(default="local", alias="FILE_STORAGE_BACKEND")
    file_storage_path: str = Field(default="./uploads", alias="FILE_STORAGE_PATH")

    # S3 (optional)
    s3_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_region: str = Field(default="", alias="S3_REGION")
    s3_access_key: str = Field(default="", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", alias="S3_SECRET_KEY")

    @property
    def resolved_mongodb_url(self) -> str:
        if self.mongodb_url.startswith("mongodb"):
            url = self.mongodb_url
        elif self.database_url.startswith("mongodb"):
            url = self.database_url
        else:
            url = "mongodb://localhost:27017"

        # Atlas database users authenticate against the admin auth DB.
        if url.startswith("mongodb+srv://") and "authSource=" not in url:
            url = f"{url}&authSource=admin" if "?" in url else f"{url}?authSource=admin"
        return url

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_max_size_bytes(self) -> int:
        return self.upload_max_size_mb * 1024 * 1024

    @property
    def upload_allowed_mime_types(self) -> set[str]:
        return {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/png",
            "image/jpeg",
            "image/jpg",
            "image/webp",
            "image/gif",
        }

    @property
    def upload_allowed_extensions_list(self) -> list[str]:
        return [
            ext.strip().lower()
            for ext in self.upload_allowed_extensions.split(",")
            if ext.strip()
        ]


settings = Settings()
