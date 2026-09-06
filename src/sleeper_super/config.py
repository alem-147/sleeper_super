from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    league_ids_path: str
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding='utf-8')

