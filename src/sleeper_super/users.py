from dataclasses import dataclass
import sqlite3

import httpx
import pandas as pd

from sleeper_super.config import Settings

@dataclass
class User:
    user_id: int
    display_name: str

def init_users(settings: Settings) -> None:

    with sqlite3.connect("my_database.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                display_name TEXT NOT NULL
            )
        """)

        leagues = pd.read_csv(settings.league_ids_path)
        if "id" not in leagues.columns:
            raise KeyError("'id' missing from leagues id csv")
        league_id = leagues.loc[0]["id"]

        users = httpx.get(f"https://api.sleeper.app/v1/league/{league_id}/users").json()

        for user in users:
            conn.execute("""
                INSERT INTO users (user_id, display_name) VALUES (?, ?)
                ON CONFLICT (user_id)
                DO UPDATE SET display_name = excluded.display_name
                """,
                (user["user_id"], user["display_name"])
            )

def get_users() -> None:

    with sqlite3.connect("my_database.db") as conn:
        df = pd.read_sql_query(
            "SELECT * FROM users",
            conn,
        )
        print(df.head())

