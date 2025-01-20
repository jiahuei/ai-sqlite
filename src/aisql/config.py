from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

CURR_DIR = Path(__file__).resolve().parent


class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="aisql_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        cli_parse_args=False,
    )
    # Config
    db_path: str = "ws://127.0.0.1:8080"  # "file:local.db"
    log_dir: str = "logs"


ENV_CONFIG = EnvConfig()
