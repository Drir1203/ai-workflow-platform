from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ProjectHub AI"
    database_url: str = "sqlite+aiosqlite:///./projecthub.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    dify_api_url: str = "http://localhost:5001/v1"
    dify_api_key: str = ""
    # 微信小程序订阅消息（R16）
    wechat_appid: str = ""
    wechat_secret: str = ""
    wechat_template_due: str = ""


settings = Settings()
