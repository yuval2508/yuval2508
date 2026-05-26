"""
analyze_lotto.py
----------------
ניתוח סטטיסטי של תוצאות הלוטו שנשמרו ב-SQLite.

שימוש:
    python3 analyze_lotto.py                   # דוח מלא
    python3 analyze_lotto.py --top 10          # 10 המספרים הנפוצים ביותר
    python3 analyze_lotto.py --heatmap         # מטריצת שכיחות זוגות
    python3 analyze_lotto.py --since 2023-01-01
"""

import argparse
import sqlite3
from collections import Counter
from pathlib import Path

DB_PATH = Path(__file__).parent / "lotto.db"

# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def get_conn(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"לא נמצא DB ב-{db_path}. הרץ קודם fetch_lotto.py")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def all_draws(conn: sqlite3.Connection, since: str | None = None) -> list[sqlite3.Row]:
    q = "SELECT * FROM draws"
    params: list = []
    if since:
        q += " WHERE draw_date >= ?"
        params.append(since)
    q += " ORDER BY draw_date"
    return conn.execute(q, params).fetchall()


def extract_numbers(draws: list[sqlite3.Row], include_strong=False) -> list[int]:
    nums = []
    for d in draws:
        nums += [d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]]
        if include_strong and d["strong"]:
            nums.append(d["strong"])
    return nums


# ------------------------------------------------------------------ #
#  Analysis functions                                                  #
# ------------------------------------------------------------------ #

def frequency_table(nums: list[int], top_n: int = 49) -> list[tuple[int, int]]:
    c = Counter(nums)
    return c.most_common(top_n)


def pair_frequency(draws: list[sqlite3.Row]) -> Counter:
    pairs = Counter()
    for d in draws:
        row = sorted([d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]])
        for i in range(len(row)):
            for j in range(i + 1, len(row)):
                pairs[(row[i], row[j])] += 1
    return pairs


def hot_cold(nums: list[int], all_numbers=range(1, 50)):
    c = Counter(nums)
    sorted_nums = sorted(all_numbers, key=lambda n: c.get(n, 0), reverse=True)
    hot = sorted_nums[:7]
    cold = sorted_nums[-7:]
    return hot, cold


def even_odd_ratio(draws: list[sqlite3.Row]) -> dict:
    evens = odds = 0
    for d in draws:
        for col in ("n1", "n2", "n3", "n4", "n5", "n6"):
            n = d[col]
            if n % 2 == 0:
                evens += 1
            else:
                odds += 1
    total = evens + odds
    return {"even": evens, "odd": odds, "even_pct": 100 * evens / total if total else 0}


def sum_distribution(draws: list[sqlite3.Row]) -> dict:
    sums = [d["n1"] + d["n2"] + d["n3"] + d["n4"] + d["n5"] + d["n6"] for d in draws]
    if not sums:
        return {}
    avg = sum(sums) / len(sums)
    min_s = min(sums)
    max_s = max(sums)
    # חלוקה לטווחים
    buckets: Counter = Counter()
    for s in sums:
        bucket = (s // 20) * 20
        buckets[bucket] += 1
    return {"avg": avg, "min": min_s, "max": max_s, "buckets": dict(sorted(buckets.items()))}


def consecutive_numbers(draws: list[sqlite3.Row]) -> dict:
    """כמה הגרלות יש בהן לפחות שני מספרים עוקבים."""
    count = 0
    for d in draws:
        row = sorted([d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]])
        for i in range(len(row) - 1):
            if row[i + 1] - row[i] == 1:
                count += 1
                break
    pct = 100 * count / len(draws) if draws else 0
    return {"draws_with_consecutive": count, "pct": pct}


def decade_distribution(draws: list[sqlite3.Row]) -> Counter:
    """איזה עשור (1-10, 11-20, ...) מופיע הכי הרבה."""
    c: Counter = Counter()
    for d in draws:
        for col in ("n1", "n2", "n3", "n4", "n5", "n6"):
            n = d[col]
            decade = ((n - 1) // 10) * 10 + 1
            c[f"{decade:02d}-{decade+9:02d}"] += 1
    return c


# ------------------------------------------------------------------ #
#  Printing                                                            #
# ------------------------------------------------------------------ #

BAR = "█"

def print_bar(label: str, value: int, max_val: int, width: int = 30):
    filled = int(width * value / max_val) if max_val else 0
    bar = BAR * filled + "░" * (width - filled)
    print(f"  {label:>4}  {bar}  {value}")


def print_section(title: str):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ------------------------------------------------------------------ #
#  Main report                                                         #
# ------------------------------------------------------------------ #

def run_report(args):
    conn = get_conn(Path(args.db))
    draws = all_draws(conn, since=args.since)

    if not draws:
        print("אין נתונים ב-DB. הרץ קודם fetch_lotto.py")
        return

    print_section(f"סיכום כללי  ({len(draws)} הגרלות)")
    print(f"  מ-{draws[0]['draw_date']}  עד  {draws[-1]['draw_date']}")

    # ── שכיחות מספרים ──────────────────────────────────────────────
    nums = extract_numbers(draws)
    freq = frequency_table(nums, top_n=args.top)

    print_section(f"שכיחות מספרים (Top {args.top})")
    max_freq = freq[0][1] if freq else 1
    for num, cnt in freq:
        print_bar(str(num), cnt, max_freq)

    # ── חם / קר ────────────────────────────────────────────────────
    hot, cold = hot_cold(nums)
    print_section("מספרים חמים ❤️  (הנפוצים ביותר)")
    print(" ", "  ".join(str(n) for n in hot))
    print_section("מספרים קרים 🧊  (הנדירים ביותר)")
    print(" ", "  ".join(str(n) for n in cold))

    # ── זוגות ──────────────────────────────────────────────────────
    if args.pairs:
        pairs = pair_frequency(draws)
        print_section("זוגות המספרים הנפוצים ביותר (Top 15)")
        for (a, b), cnt in pairs.most_common(15):
            print(f"  ({a:2d}, {b:2d})  הופיע {cnt} פעמים")

    # ── זוגי / אי-זוגי ─────────────────────────────────────────────
    eo = even_odd_ratio(draws)
    print_section("יחס זוגי / אי-זוגי")
    print(f"  זוגיים:    {eo['even']:>5}  ({eo['even_pct']:.1f}%)")
    print(f"  אי-זוגיים: {eo['odd']:>5}  ({100 - eo['even_pct']:.1f}%)")

    # ── סכום ──────────────────────────────────────────────────────
    sd = sum_distribution(draws)
    print_section("התפלגות סכום 6 המספרים")
    print(f"  ממוצע: {sd['avg']:.1f}   מינימום: {sd['min']}   מקסימום: {sd['max']}")
    print("  התפלגות לפי טווחים:")
    max_b = max(sd["buckets"].values()) if sd["buckets"] else 1
    for bucket, cnt in sd["buckets"].items():
        print_bar(f"{bucket}-{bucket+19}", cnt, max_b)

    # ── מספרים עוקבים ─────────────────────────────────────────────
    cons = consecutive_numbers(draws)
    print_section("מספרים עוקבים")
    print(f"  הגרלות עם לפחות שני מספרים עוקבים: "
          f"{cons['draws_with_consecutive']} ({cons['pct']:.1f}%)")

    # ── עשורים ───────────────────────────────────────────────────
    dec = decade_distribution(draws)
    print_section("התפלגות לפי עשורים")
    max_d = max(dec.values()) if dec else 1
    for label, cnt in sorted(dec.items()):
        print_bar(label, cnt, max_d)

    # ── מספר חזק ─────────────────────────────────────────────────
    strongs = [d["strong"] for d in draws if d["strong"]]
    if strongs:
        print_section("מספר חזק – שכיחות")
        sc = Counter(strongs)
        max_sc = sc.most_common(1)[0][1]
        for num, cnt in sorted(sc.most_common()):
            print_bar(str(num), cnt, max_sc)

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="ניתוח סטטיסטי של תוצאות הלוטו")
    parser.add_argument("--db", default=str(DB_PATH), help="נתיב לקובץ DB")
    parser.add_argument("--since", default=None, help="סינון מתאריך (YYYY-MM-DD)")
    parser.add_argument("--top", type=int, default=20, help="כמה מספרים להציג בטבלת שכיחות")
    parser.add_argument("--pairs", action="store_true", help="הצג ניתוח זוגות")
    args = parser.parse_args()
    run_report(args)


if __name__ == "__main__":
    main()
