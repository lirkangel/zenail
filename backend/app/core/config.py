from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://zenail:zenail@localhost:5432/zenail"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expires_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173"
    currency_code: str = "VND"

    # Notifications
    notifications_enabled: bool = True
    notification_default_lang: str = "vi"
    notification_provider_email: str = "log"   # log | smtp
    notification_provider_sms: str = "log"     # log | esms
    notification_provider_zns: str = "log"     # log | zalo

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "Zenail <noreply@zenail.local>"

    esms_api_key: str = ""
    esms_secret_key: str = ""
    esms_brandname: str = ""

    zalo_oa_access_token: str = ""
    # JSON map: {"reminder_24h.guest.zalo_zns": "<template_id>", ...}
    zalo_zns_template_ids_json: str = "{}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()

