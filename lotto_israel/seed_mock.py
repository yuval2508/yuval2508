"""
seed_mock.py
------------
יוצר DB לדוגמה עם נתונים מדומים כדי לאפשר בדיקה של analyze_lotto.py
ללא גישה לאינטרנט.

שימוש:
    python seed_mock.py
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from fetch_lotto import init_db, save_draws

DB_PATH = Path(__file__).parent / "lotto.db"
random.seed(42)


def random_draw(draw_number: int, draw_date: str) -> dict:
    pool = list(range(1, 50))
    numbers = sorted(random.sample(pool, 6))
    strong = random.randint(1, 7)
    return {
        "draw_number": draw_number,
        "draw_date": draw_date,
        "numbers": numbers,
        "strong": strong,
        "extra": None,
        "raw_title": f"לוטו הגרלה {draw_number}",
        "raw_description": f"מספרים: {' '.join(map(str, numbers))} | חזק: {strong}",
    }


def main():
    conn = init_db(DB_PATH)
    draws = []
    start = date(2022, 1, 4)  # יום שלישי
    for i in range(200):
        d = start + timedelta(weeks=i)
        draws.append(random_draw(1800 + i, d.isoformat()))

    saved = save_draws(conn, draws)
    conn.close()
    print(f"[✓] נשמרו {saved} הגרלות מדומות ב-{DB_PATH}")


if __name__ == "__main__":
    main()
