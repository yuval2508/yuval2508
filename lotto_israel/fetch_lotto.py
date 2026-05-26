"""
fetch_lotto.py
--------------
מוריד את עדכון ה-RSS של הלוטו מאתר פאיס ושומר את התוצאות ב-SQLite.

שימוש:
    python3 fetch_lotto.py              # טעינה ושמירה
    python3 fetch_lotto.py --dry-run    # הדפסה בלבד ללא שמירה
"""

import argparse
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

RSS_URL = "https://www.pais.co.il/rssfeed.ashx?lottery=lotto"
DB_PATH = Path(__file__).parent / "lotto.db"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# ------------------------------------------------------------------ #
#  Schema                                                              #
# ------------------------------------------------------------------ #

DDL = """
CREATE TABLE IF NOT EXISTS draws (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_number     INTEGER UNIQUE NOT NULL,   -- מספר הגרלה
    draw_date       TEXT NOT NULL,             -- תאריך (ISO 8601: YYYY-MM-DD)
    n1 INTEGER NOT NULL,
    n2 INTEGER NOT NULL,
    n3 INTEGER NOT NULL,
    n4 INTEGER NOT NULL,
    n5 INTEGER NOT NULL,
    n6 INTEGER NOT NULL,
    strong          INTEGER,                   -- מספר חזק (אם קיים)
    extra           INTEGER,                   -- מספר נוסף / כוכב (אם קיים)
    raw_title       TEXT,
    raw_description TEXT,
    fetched_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prizes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    draw_number INTEGER NOT NULL REFERENCES draws(draw_number),
    rank        INTEGER NOT NULL,              -- 1 = ראשון, 2 = שני, ...
    winners     INTEGER,                       -- מספר זוכים
    prize_ils   REAL,                          -- סכום פרס בשקלים
    description TEXT
);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    conn.commit()
    return conn


# ------------------------------------------------------------------ #
#  Parsing                                                             #
# ------------------------------------------------------------------ #

def parse_numbers_from_text(text: str):
    """
    מחלץ מספרים מטקסט חופשי כגון:
      "מספרים: 3, 14, 22, 31, 38, 45 | חזק: 6"
      "3 14 22 31 38 45 [6]"
    מחזיר (list_of_6, strong_or_None, extra_or_None)
    """
    # נסה לזהות "חזק" / "strong" / "כוכב"
    strong = None
    extra = None

    strong_match = re.search(
        r"(?:חזק|strong|חזקה)[^\d]*(\d+)", text, re.IGNORECASE
    )
    if strong_match:
        strong = int(strong_match.group(1))

    extra_match = re.search(
        r"(?:נוסף|extra|כוכב|\*)[^\d]*(\d+)", text, re.IGNORECASE
    )
    if extra_match:
        extra = int(extra_match.group(1))

    # כל המספרים בטקסט
    all_nums = list(map(int, re.findall(r"\b(\d{1,2})\b", text)))
    # סנן ערכים שכבר זיהינו כחזק/נוסף ומספרים מחוץ לטווח 1-49
    main = [n for n in all_nums if 1 <= n <= 49 and n != strong and n != extra]
    # קח את 6 הראשונים (ממוינים לרוב)
    main = sorted(set(main))[:6]

    return main, strong, extra


def parse_date(text: str) -> str:
    """מנסה להמיר תאריכים שונים ל-ISO 8601."""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",   # RFC 822
        "%a, %d %b %Y %H:%M:%S GMT",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # נסה לחלץ תאריך עם regex
    m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", text)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return text[:10]  # fallback


def parse_draw_number(text: str) -> int | None:
    """מחלץ מספר הגרלה מהכותרת / תיאור."""
    m = re.search(r"(?:הגרלה|draw|#|גרלה מספר)[^\d]*(\d{3,5})", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # אולי רק מספר בודד בתחילת הכותרת
    m = re.search(r"^\D*(\d{3,5})", text)
    if m:
        return int(m.group(1))
    return None


def parse_rss(xml_bytes: bytes) -> list[dict]:
    """מפרסר XML של RSS ומחזיר רשימת מילונים."""
    root = ET.fromstring(xml_bytes)
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    items = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date = item.findtext("pubDate") or item.findtext("dc:date", namespaces=ns) or ""
        link = (item.findtext("link") or "").strip()

        # חלץ מספרים מהכותרת ואז מהתיאור
        combined = title + " " + description
        numbers, strong, extra = parse_numbers_from_text(combined)

        if len(numbers) < 6:
            # אם לא הצלחנו לחלץ 6 מספרים, דלג
            print(f"[WARN] לא הצלחתי לחלץ 6 מספרים מ: {title!r}")
            continue

        draw_number = parse_draw_number(combined) or parse_draw_number(link)

        items.append(
            {
                "draw_number": draw_number,
                "draw_date": parse_date(pub_date) if pub_date else None,
                "numbers": numbers,
                "strong": strong,
                "extra": extra,
                "raw_title": title,
                "raw_description": description,
            }
        )

    return items


# ------------------------------------------------------------------ #
#  Persistence                                                         #
# ------------------------------------------------------------------ #

def save_draws(conn: sqlite3.Connection, draws: list[dict]) -> int:
    saved = 0
    cur = conn.cursor()
    for d in draws:
        nums = d["numbers"]
        if len(nums) < 6:
            continue
        try:
            cur.execute(
                """
                INSERT OR IGNORE INTO draws
                  (draw_number, draw_date, n1, n2, n3, n4, n5, n6,
                   strong, extra, raw_title, raw_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d["draw_number"],
                    d["draw_date"],
                    nums[0], nums[1], nums[2], nums[3], nums[4], nums[5],
                    d["strong"],
                    d["extra"],
                    d["raw_title"],
                    d["raw_description"],
                ),
            )
            if cur.rowcount:
                saved += 1
        except sqlite3.IntegrityError as e:
            print(f"[SKIP] {d['draw_number']}: {e}")
    conn.commit()
    return saved


# ------------------------------------------------------------------ #
#  Main                                                                #
# ------------------------------------------------------------------ #

def fetch_rss() -> bytes:
    resp = requests.get(RSS_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.content


def main():
    parser = argparse.ArgumentParser(description="מוריד תוצאות לוטו ושומר ב-SQLite")
    parser.add_argument("--dry-run", action="store_true", help="הדפס בלבד, אל תשמור")
    parser.add_argument("--db", default=str(DB_PATH), help="נתיב לקובץ DB")
    args = parser.parse_args()

    print(f"[*] מוריד RSS מ-{RSS_URL} …")
    raw = fetch_rss()
    print(f"[*] קיבלתי {len(raw):,} בייטים")

    draws = parse_rss(raw)
    print(f"[*] פורסרו {len(draws)} הגרלות")

    for d in draws:
        nums_str = " ".join(map(str, d["numbers"]))
        strong_str = f" | חזק: {d['strong']}" if d["strong"] else ""
        extra_str = f" | נוסף: {d['extra']}" if d["extra"] else ""
        print(f"  #{d['draw_number']}  {d['draw_date']}  [{nums_str}]{strong_str}{extra_str}")

    if args.dry_run:
        print("[!] dry-run – לא נשמר")
        return

    db_path = Path(args.db)
    conn = init_db(db_path)
    saved = save_draws(conn, draws)
    conn.close()
    print(f"[✓] נשמרו {saved} הגרלות חדשות ב-{db_path}")


if __name__ == "__main__":
    main()
