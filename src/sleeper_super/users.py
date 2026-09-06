from dataclasses import dataclass
import sqlite3

import httpx
import pandas as pd

from sleeper_super.config import Settings

@dataclass
class User:
    id: int
    display_name: str

def init_users(conn: sqlite3.Connection, settings: Settings) -> None:
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

def get_users(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM users", conn)

def init_rosters(conn: sqlite3.Connection, settings: Settings) -> None:
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

def get_rosters(conn: sqlite3.Connection, user_ids: list[int] | None = None) -> pd.DataFrame:
    query = "SELECT * from rosters"
    params: tuple[int, ...] = ()

    if user_ids:
        placeholders = ", ".join(["?" for _ in user_ids])
        query += f" WHERE user_id IN ({placeholders})"
        params = tuple(user_ids)

    return pd.read_sql_query(query, conn, params=params)
