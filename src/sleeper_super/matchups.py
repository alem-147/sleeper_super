from collections import defaultdict
import argparse
import sqlite3

import httpx
import pandas as pd

from sleeper_super.leagues import get_leagues
from sleeper_super.users import roster2user

def init_matchups(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS matchups(
            matchup_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            league_id INTEGER NOT NULL,
            home TEXT NOT NULL,
            away TEXT NOT NULL,
            home_score REAL NOT NULL,
            away_score REAL NOT NULL,

            PRIMARY KEY (matchup_id, week, league_id),

            FOREIGN KEY (home) REFERENCES users(id),
            FOREIGN KEY (away) REFERENCES users(id),
            FOREIGN KEY (league_id) REFERENCES leagues(id)
        )""")

def init_results(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results(
            week INTEGER NOT NULL,
            home TEXT NOT NULL,
            away TEXT NOT NULL,
            home_wins INTEGER NOT NULL,
            away_wins INTEGER NOT NULL,

            PRIMARY KEY (week, home, away),

            FOREIGN KEY (home) REFERENCES users(id),
            FOREIGN KEY (away) REFERENCES users(id)
        )""")

def update_matchups(conn: sqlite3.Connection, week: int) -> None:
    leagues = get_leagues(conn)
    for league in leagues.itertuples():
        league_id = int(league.id)
        response = httpx.get(
            f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
        )
        response.raise_for_status()
        matchups_dump = response.json()

        by_matchup: defaultdict[int, list[dict]] = defaultdict(list)
        for roster_matchup in matchups_dump:
            matchup_id = roster_matchup.get("matchup_id")
            if matchup_id is not None:
                by_matchup[int(matchup_id)].append(roster_matchup)

        for matchup_id, teams in by_matchup.items():
            if len(teams) != 2:
                continue

            resolved = []
            for team in teams:
                user = roster2user(conn, league_id, int(team["roster_id"]))
                if user.empty:
                    raise ValueError(
                        f"No user found for league {league_id}, "
                        f"roster {team['roster_id']}"
                    )
                resolved.append((
                    str(user.iloc[0]["display_name"]),
                    int(user.iloc[0]["id"]),
                    float(team.get("custom_points")
                          if team.get("custom_points") is not None
                          else team["points"]),
                ))

            resolved.sort(key=lambda team: (team[0].casefold(), team[1]))
            home, away = resolved
            conn.execute(
                """
                INSERT INTO matchups (
                    matchup_id, week, league_id, home, away,
                    home_score, away_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (matchup_id, week, league_id)
                DO UPDATE SET
                    home = excluded.home,
                    away = excluded.away,
                    home_score = excluded.home_score,
                    away_score = excluded.away_score
                """,
                (matchup_id, week, league_id, home[0], away[0], home[2], away[2]),
            )

def get_matchups(conn: sqlite3.Connection, week: int | None) -> pd.DataFrame:
    query = "SELECT * FROM matchups"
    params: tuple[int, ...] = ()
    if week is not None:
        query += " WHERE week = ?"
        params = (week,)
    query += " ORDER BY week, league_id, matchup_id"
    return pd.read_sql_query(query, conn, params=params)

def update_results(conn: sqlite3.Connection, week: int) -> None:
    conn.execute("DELETE FROM results WHERE week = ?", (week,))
    conn.execute(
        """
        INSERT INTO results (week, home, away, home_wins, away_wins)
        SELECT
            week,
            home,
            away,
            SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END),
            SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END)
        FROM matchups
        WHERE week = ?
        GROUP BY week, home, away
        """,
        (week,),
    )

def get_results(conn: sqlite3.Connection, week: int | None) -> pd.DataFrame:
    query = "SELECT * FROM results"
    params: tuple[int, ...] = ()
    if week is not None:
        query += " WHERE week = ?"
        params = (week,)
    query += " ORDER BY week, home, away"
    return pd.read_sql_query(query, conn, params=params)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update matchups for a week")
    parser.add_argument("week", type=int, help="NFL fantasy week to update")
    args = parser.parse_args()

    from sleeper_super.config import Settings
    from sleeper_super.leagues import init_leagues
    from sleeper_super.users import init_rosters, init_users

    settings = Settings()
    with sqlite3.connect(settings.db_name) as conn:
        init_leagues(conn, settings)
        init_users(conn, settings)
        init_rosters(conn, settings)
        init_matchups(conn)
        init_results(conn)
        update_matchups(conn, args.week)
        update_results(conn, args.week)
        print(get_matchups(conn, args.week))
        print(get_results(conn, args.week))
