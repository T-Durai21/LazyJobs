from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "sqlite:///./cv_applier.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_ttl_hours: int = 24 * 14
    frontend_origin: str = "http://localhost:8000"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    # Local single-user mode: when set, /api/auth/local/login signs in as this email
    # without Google. Leave empty anywhere the app is reachable by other people.
    local_login_email: str = ""

    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"

    upload_dir: str = "./uploads"
    tracker_csv_path: str = ""

    user_agent: str = "cv-applier/0.1 (+personal job search assistant)"
    source_request_delay: float = 1.0
    # Remotive asks for at most four fetches a day; every source is held to the same floor.
    source_min_refresh_hours: float = 6.0


settings = Settings()
