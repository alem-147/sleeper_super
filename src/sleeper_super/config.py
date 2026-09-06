from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    league_ids_path: Path

    @computed_field
    @property
    def db_name(self) -> str:
        return f"{self.league_ids_path.stem}.db"

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding='utf-8')

