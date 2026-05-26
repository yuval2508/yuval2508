"""
predict_lotto.py
----------------
הצעות מספרים מבוססות ניתוח סטטיסטי + ML קל.

⚠️  חשוב: הלוטו הוא הגרלה אקראית לחלוטין.
    אין מודל שיכול "לנחש" את המספרים הבאים.
    הכלי הזה מציע מספרים על בסיס אסטרטגיות סטטיסטיות שונות —
    לא כי הן מנצחות, אלא כי הן מעניינות לנתח.

שימוש:
    python3 predict_lotto.py                  # כל האסטרטגיות
    python3 predict_lotto.py --strategy hot   # רק "מספרים חמים"
    python3 predict_lotto.py --runs 10        # 10 הגרלות מדומות
"""

import argparse
import random
import sqlite3
from collections import Counter
from pathlib import Path

import numpy as np

DB_PATH = Path(__file__).parent / "lotto.db"


# ──────────────────────────────────────────────────────────────────── #
#  Data                                                                 #
# ──────────────────────────────────────────────────────────────────── #

def load_draws(db_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM draws ORDER BY draw_date").fetchall()
    conn.close()
    return rows


def all_numbers(draws: list[sqlite3.Row]) -> list[int]:
    nums = []
    for d in draws:
        nums += [d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]]
    return nums


def last_appeared(draws: list[sqlite3.Row]) -> dict[int, int]:
    """מחזיר dict {מספר: לפני כמה הגרלות הופיע לאחרונה}."""
    last = {}
    for idx, d in enumerate(draws):
        for col in ("n1", "n2", "n3", "n4", "n5", "n6"):
            last[d[col]] = idx
    n = len(draws)
    return {num: n - 1 - last.get(num, -1) for num in range(1, 50)}


# ──────────────────────────────────────────────────────────────────── #
#  Strategies                                                           #
# ──────────────────────────────────────────────────────────────────── #

def strategy_uniform() -> list[int]:
    """אקראי טהור – baseline."""
    return sorted(random.sample(range(1, 50), 6))


def strategy_hot(draws: list[sqlite3.Row], n_recent: int = 50) -> list[int]:
    """
    'מספרים חמים' – בחירה משוקללת לפי שכיחות ב-n_recent הגרלות האחרונות.
    מספר שהופיע הרבה → סיכוי גבוה יותר להיבחר.
    """
    recent = draws[-n_recent:]
    nums = all_numbers(recent)
    c = Counter(nums)
    population = list(range(1, 50))
    weights = [c.get(n, 0) + 1 for n in population]  # +1 כדי שלכל מספר יש סיכוי מינימלי
    chosen = random.choices(population, weights=weights, k=20)
    return sorted(set(chosen))[:6]


def strategy_cold(draws: list[sqlite3.Row], n_recent: int = 50) -> list[int]:
    """
    'מספרים קרים' – בחירה לפי מספרים שלא הופיעו לאחרונה.
    תיאוריה: 'הגיע תורם'.
    """
    recent = draws[-n_recent:]
    nums = all_numbers(recent)
    c = Counter(nums)
    population = list(range(1, 50))
    weights = [1 / (c.get(n, 0) + 1) for n in population]
    chosen = random.choices(population, weights=weights, k=20)
    return sorted(set(chosen))[:6]


def strategy_balanced(draws: list[sqlite3.Row]) -> list[int]:
    """
    'מאוזן' – תמהיל: 3 חמים + 3 קרים, פריסה על עשורים שונים.
    """
    nums = all_numbers(draws)
    c = Counter(nums)
    sorted_by_freq = sorted(range(1, 50), key=lambda n: c.get(n, 0), reverse=True)
    hot = sorted_by_freq[:15]
    cold = sorted_by_freq[-15:]
    chosen = random.sample(hot, 3) + random.sample(cold, 3)
    return sorted(chosen)


def strategy_due(draws: list[sqlite3.Row]) -> list[int]:
    """
    'מספרים בפיגור' – מספרים שלא הופיעו הכי הרבה זמן.
    """
    age = last_appeared(draws)  # {מספר: לפני כמה הגרלות}
    sorted_by_age = sorted(range(1, 50), key=lambda n: age.get(n, 9999), reverse=True)
    # בחר 6 מתוך 12 הכי "בפיגור"
    return sorted(random.sample(sorted_by_age[:12], 6))


def strategy_ml_frequency(draws: list[sqlite3.Row]) -> list[int]:
    """
    'ML – ממוצע נע' (Exponential Moving Average).
    שוקל הופעות אחרונות יותר מהיסטוריות.
    """
    alpha = 0.05  # כמה להאט את ה"שכחה"
    scores = {n: 0.0 for n in range(1, 50)}
    for d in draws:
        appeared = {d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]}
        for n in range(1, 50):
            if n in appeared:
                scores[n] = scores[n] * (1 - alpha) + alpha * 1.0
            else:
                scores[n] = scores[n] * (1 - alpha)

    population = list(range(1, 50))
    weights = [scores[n] + 0.001 for n in population]
    chosen = random.choices(population, weights=weights, k=20)
    return sorted(set(chosen))[:6]


def strategy_ensemble(draws: list[sqlite3.Row]) -> list[int]:
    """
    'אנסמבל' – משקלל הצבעות מכמה אסטרטגיות.
    המספרים שקיבלו הכי הרבה הצבעות נבחרים.
    """
    votes: Counter = Counter()
    for _ in range(10):
        votes.update(strategy_hot(draws))
        votes.update(strategy_cold(draws))
        votes.update(strategy_due(draws))
        votes.update(strategy_ml_frequency(draws))
    return sorted([n for n, _ in votes.most_common(6)])


STRATEGIES = {
    "uniform":   ("🎲 אקראי טהור (Baseline)",          lambda d: strategy_uniform()),
    "hot":       ("🔥 מספרים חמים",                    strategy_hot),
    "cold":      ("🧊 מספרים קרים",                    strategy_cold),
    "balanced":  ("⚖️  מאוזן (חמים + קרים)",            strategy_balanced),
    "due":       ("⏳ מספרים בפיגור",                   strategy_due),
    "ml_ema":    ("🤖 EMA (Exponential Moving Avg)",    strategy_ml_frequency),
    "ensemble":  ("🧠 אנסמבל (כל האסטרטגיות)",         strategy_ensemble),
}


# ──────────────────────────────────────────────────────────────────── #
#  Evaluation                                                           #
# ──────────────────────────────────────────────────────────────────── #

def simulate_accuracy(
    draws: list[sqlite3.Row],
    strategy_fn,
    test_size: int = 50,
    runs: int = 200,
) -> dict:
    """
    בודק רטרואקטיבית: אם היינו בוחרים לפי האסטרטגיה לפני test_size הגרלות,
    כמה מספרים היינו מנחשים נכון בממוצע?
    """
    if len(draws) <= test_size:
        return {"avg_hits": 0, "max_hits": 0, "exact6": 0}

    train = draws[:-test_size]
    test = draws[-test_size:]
    total_hits = []
    exact6 = 0

    for _ in range(runs):
        prediction = set(strategy_fn(train))
        for d in test:
            actual = {d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]}
            hits = len(prediction & actual)
            total_hits.append(hits)
            if hits == 6:
                exact6 += 1

    return {
        "avg_hits": np.mean(total_hits),
        "max_hits": max(total_hits),
        "exact6":   exact6,
    }


# ──────────────────────────────────────────────────────────────────── #
#  CLI                                                                  #
# ──────────────────────────────────────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(description="הצעות מספרים לוטו")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument(
        "--strategy",
        choices=list(STRATEGIES.keys()) + ["all"],
        default="all",
        help="איזו אסטרטגיה להשתמש",
    )
    parser.add_argument("--runs", type=int, default=5, help="כמה ניסויים לכל אסטרטגיה")
    parser.add_argument("--eval", action="store_true", help="הרץ הערכה רטרואקטיבית")
    args = parser.parse_args()

    draws = load_draws(Path(args.db))
    if not draws:
        print("אין נתונים. הרץ קודם fetch_lotto.py או seed_mock.py")
        return

    print()
    print("=" * 60)
    print("  🎰  הצעות מספרים לוטו")
    print(f"  (מבוסס על {len(draws)} הגרלות היסטוריות)")
    print("=" * 60)
    print()
    print("  ⚠️  תזכורת: הלוטו הוא אקראי לחלוטין.")
    print("      הכלי הזה הוא לניתוח סטטיסטי בלבד.")
    print()

    strategies_to_run = (
        list(STRATEGIES.items()) if args.strategy == "all"
        else [(args.strategy, STRATEGIES[args.strategy])]
    )

    for key, (label, fn) in strategies_to_run:
        print(f"  {label}")
        for i in range(args.runs):
            nums = fn(draws) if key != "uniform" else strategy_uniform()
            nums_str = "  ".join(f"{n:2d}" for n in nums)
            print(f"    גרלה {i+1}:  [ {nums_str} ]")

        if args.eval and key != "uniform":
            print(f"    ── הערכה רטרואקטיבית (50 הגרלות האחרונות, 200 ניסויים) ──")
            ev = simulate_accuracy(draws, fn)
            print(f"    ממוצע נכונות: {ev['avg_hits']:.2f}/6   "
                  f"מקסימום: {ev['max_hits']}   "
                  f"6/6 מדויק: {ev['exact6']}")
        print()


if __name__ == "__main__":
    main()
