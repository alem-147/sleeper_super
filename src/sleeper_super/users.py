from dataclasses import dataclass
import sqlite3

import httpx
import pandas as pd

from sleeper_super.config import Settings

@dataclass
class User:
    id: int
    display_name: str

def init_users(settings: Settings) -> None:

    with sqlite3.connect(settings.db_name) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
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
                INSERT INTO users (id, display_name) VALUES (?, ?)
                ON CONFLICT (id)
                DO UPDATE SET display_name = excluded.display_name
                """,
                (user["user_id"], user["display_name"])
            )

def init_rosters(settings: Settings) -> None:
    with sqlite3.connect(settings.db_name) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rosters (
                league_id INTEGER NOT NULL,
                roster_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,

                PRIMARY KEY (league_id, roster_id),

                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        leagues = pd.read_csv(settings.league_ids_path)

        for league_id in leagues["id"]:
            rosters = httpx.get(f"https://api.sleeper.app/v1/league/{league_id}/rosters").json()
            for roster in rosters:
                conn.execute("""
                    INSERT INTO rosters(league_id, roster_id, user_id) VALUES (?, ?, ?)
                    ON CONFLICT (league_id, roster_id)
                    DO UPDATE SET
                        user_id = excluded.user_id
                    """,
                    (roster["league_id"], roster["roster_id"], roster["owner_id"])
                ) 

def get_users(settings: Settings) -> pd.DataFrame:
    with sqlite3.connect(settings.db_name) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM users",
            conn,
        )
    return df

def get_user_rosters(settings: Settings, user_id: int) -> pd.DataFrame:
    with sqlite3.connect(settings.db_name) as conn:
        df = pd.read_sql_query(f"""
            SELECT * FROM rosters
            WHERE user_id = {user_id}""",
            conn,
        )
    return df

