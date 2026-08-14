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
    # AI 引擎选择：dify（Dify CE headless）| openai_compatible（DeepSeek/通义等）
    ai_provider: str = "dify"
    openai_compatible_base_url: str = "https://api.deepseek.com"
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = "deepseek-chat"
    # 定时调度时区（单 worker 进程内 APScheduler）
    scheduler_timezone: str = "Asia/Shanghai"
    # Agent fetch_url 工具
    agent_fetch_timeout: float = 15
    agent_fetch_max_chars: int = 8000
    # 知识库 RAG（R8/R9/R10）
    rag_top_k: int = 5
    rag_chunk_chars: int = 600
    rag_scan_extensions: list[str] = ["md", "txt", "markdown"]
    rag_max_upload_mb: int = 10
    # 微信小程序订阅消息（R16）
    wechat_appid: str = ""
    wechat_secret: str = ""
    wechat_template_due: str = ""


settings = Settings()
