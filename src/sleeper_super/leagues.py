import sqlite3

import httpx
import pandas as pd

from sleeper_super.config import Settings

def init_leagues(conn: sqlite3.Connection, settings: Settings) -> None:
    conn.execute("""
            CREATE TABLE IF NOT EXISTS leagues (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                season INTEGER NOT NULL
            )
        """)


    leagues = pd.read_csv(settings.league_ids_path)
        
    for league_id in leagues["id"]:
        league = httpx.get(f"https://api.sleeper.app/v1/league/{league_id}").json()

        conn.execute("""
                INSERT INTO leagues(id, name, season) VALUES (?, ?, ?)
                ON CONFLICT (id)
                DO UPDATE SET
                    name = excluded.name,
                    season = excluded.season
                """,
            (league["league_id"], league["name"], league["season"])
        )

def get_leagues(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM leagues", conn)

if __name__ == "__main__":
    settings = Settings()
    with sqlite3.connect(settings.db_name) as conn:
        init_leagues(conn, settings)
        print(get_leagues(conn).head())
