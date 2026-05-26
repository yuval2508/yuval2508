"""
visualize_lotto.py
------------------
גרפים ויזואליים של תוצאות הלוטו באמצעות matplotlib.

שימוש:
    python visualize_lotto.py                     # שמירת כל הגרפים לתיקיית charts/
    python visualize_lotto.py --show              # פתיחה ישירה במסך
    python visualize_lotto.py --since 2023-01-01
"""

import argparse
import io
import sqlite3
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend ללא GUI (לשרת / CI)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

DB_PATH = Path(__file__).parent / "lotto.db"
CHARTS_DIR = Path(__file__).parent / "charts"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": "#0f172a",
    "axes.facecolor":   "#1e293b",
    "axes.edgecolor":   "#334155",
    "axes.labelcolor":  "#cbd5e1",
    "xtick.color":      "#94a3b8",
    "ytick.color":      "#94a3b8",
    "text.color":       "#f1f5f9",
    "grid.color":       "#334155",
    "grid.linestyle":   "--",
    "grid.alpha":       0.5,
})

COLORS = {
    "hot":    "#f97316",
    "cold":   "#38bdf8",
    "bar":    "#6366f1",
    "accent": "#a78bfa",
    "bg":     "#0f172a",
}


# ──────────────────────────────────────────────────────────────────── #
#  Data helpers                                                         #
# ──────────────────────────────────────────────────────────────────── #

def load_draws(db_path: Path, since: str | None = None) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    q = "SELECT * FROM draws"
    params: list = []
    if since:
        q += " WHERE draw_date >= ?"
        params.append(since)
    q += " ORDER BY draw_date"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def all_numbers(draws: list[sqlite3.Row]) -> list[int]:
    nums = []
    for d in draws:
        nums += [d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]]
    return nums


# ──────────────────────────────────────────────────────────────────── #
#  Charts                                                               #
# ──────────────────────────────────────────────────────────────────── #

def chart_frequency(draws: list[sqlite3.Row]) -> plt.Figure:
    """גרף עמודות – שכיחות כל מספר (1-49)."""
    nums = all_numbers(draws)
    c = Counter(nums)
    x = list(range(1, 50))
    y = [c.get(n, 0) for n in x]
    avg = np.mean(y)

    fig, ax = plt.subplots(figsize=(14, 5))
    colors = [COLORS["hot"] if v > avg * 1.1 else COLORS["cold"] if v < avg * 0.9 else COLORS["bar"] for v in y]
    bars = ax.bar(x, y, color=colors, width=0.8, zorder=2)
    ax.axhline(avg, color="#facc15", lw=1.5, linestyle="--", label=f"ממוצע {avg:.1f}")
    ax.set_xlabel("מספר")
    ax.set_ylabel("כמות הופעות")
    ax.set_title(f"שכיחות מספרים  ({len(draws)} הגרלות)", pad=12, fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.grid(axis="y", zorder=0)
    ax.legend(loc="upper right")

    # תוויות על העמודות הגבוהות ביותר
    top5 = sorted(range(len(y)), key=lambda i: y[i], reverse=True)[:5]
    for i in top5:
        ax.text(x[i], y[i] + 0.3, str(y[i]), ha="center", va="bottom", fontsize=7, color="#facc15")

    fig.tight_layout()
    return fig


def chart_heatmap(draws: list[sqlite3.Row]) -> plt.Figure:
    """מטריצת זוגות – כמה פעמים כל זוג הופיע ביחד."""
    N = 49
    matrix = np.zeros((N, N), dtype=int)
    for d in draws:
        row = [d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]]
        for i in range(len(row)):
            for j in range(i + 1, len(row)):
                a, b = row[i] - 1, row[j] - 1
                matrix[a][b] += 1
                matrix[b][a] += 1

    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(matrix, cmap="magma", aspect="auto")
    plt.colorbar(im, ax=ax, label="כמות הופעות משותפות")
    ax.set_title("מטריצת שכיחות זוגות", pad=12, fontsize=14, fontweight="bold")
    ax.set_xlabel("מספר")
    ax.set_ylabel("מספר")
    ticks = list(range(0, 49, 5))
    ax.set_xticks(ticks)
    ax.set_xticklabels([t + 1 for t in ticks])
    ax.set_yticks(ticks)
    ax.set_yticklabels([t + 1 for t in ticks])
    fig.tight_layout()
    return fig


def chart_sum_distribution(draws: list[sqlite3.Row]) -> plt.Figure:
    """היסטוגרמה של סכום 6 המספרים לאורך כל ההגרלות."""
    sums = [d["n1"] + d["n2"] + d["n3"] + d["n4"] + d["n5"] + d["n6"] for d in draws]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(sums, bins=30, color=COLORS["bar"], edgecolor="#0f172a", zorder=2)
    ax.axvline(np.mean(sums), color="#facc15", lw=2, linestyle="--", label=f"ממוצע {np.mean(sums):.1f}")
    ax.set_xlabel("סכום 6 מספרים")
    ax.set_ylabel("מספר הגרלות")
    ax.set_title("התפלגות סכום 6 המספרים", pad=12, fontsize=14, fontweight="bold")
    ax.grid(axis="y", zorder=0)
    ax.legend()
    fig.tight_layout()
    return fig


def chart_hot_cold_timeline(draws: list[sqlite3.Row], window: int = 50) -> plt.Figure:
    """קו זמן – 5 המספרים החמים ביותר ב-window הגרלות גלגולת."""
    if len(draws) < window:
        window = max(len(draws) // 2, 10)

    # מצא את 5 המספרים הכי נפוצים בכל ה-draws
    total = Counter(all_numbers(draws))
    top5 = [n for n, _ in total.most_common(5)]

    fig, ax = plt.subplots(figsize=(12, 5))
    palette = ["#f97316", "#a78bfa", "#34d399", "#f472b6", "#38bdf8"]

    for num, color in zip(top5, palette):
        freqs = []
        for i in range(window, len(draws) + 1):
            chunk = draws[i - window: i]
            chunk_nums = all_numbers(chunk)
            freqs.append(chunk_nums.count(num))
        xs = list(range(window, len(draws) + 1))
        ax.plot(xs, freqs, label=f"מספר {num}", color=color, linewidth=1.5)

    ax.set_xlabel(f"אינדקס הגרלה")
    ax.set_ylabel(f"הופעות ב-{window} הגרלות האחרונות")
    ax.set_title(f"5 המספרים החמים – גלגולת {window} הגרלות", pad=12, fontsize=14, fontweight="bold")
    ax.grid(zorder=0)
    ax.legend(loc="upper left")
    fig.tight_layout()
    return fig


def chart_strong_number(draws: list[sqlite3.Row]) -> plt.Figure:
    """שכיחות המספר החזק (1-7)."""
    strongs = [d["strong"] for d in draws if d["strong"]]
    if not strongs:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "אין נתוני מספר חזק", ha="center", va="center", transform=ax.transAxes)
        return fig
    c = Counter(strongs)
    x = sorted(c.keys())
    y = [c[n] for n in x]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x, y, color=COLORS["accent"], width=0.6, zorder=2)
    ax.set_xticks(x)
    ax.set_xlabel("מספר חזק")
    ax.set_ylabel("כמות הופעות")
    ax.set_title("התפלגות המספר החזק", pad=12, fontsize=14, fontweight="bold")
    ax.grid(axis="y", zorder=0)
    fig.tight_layout()
    return fig


# ──────────────────────────────────────────────────────────────────── #
#  Export                                                               #
# ──────────────────────────────────────────────────────────────────── #

CHART_FUNCS = {
    "frequency":    chart_frequency,
    "heatmap":      chart_heatmap,
    "sum_dist":     chart_sum_distribution,
    "timeline":     chart_hot_cold_timeline,
    "strong":       chart_strong_number,
}


def fig_to_png_bytes(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    data = buf.read()
    plt.close(fig)
    return data


def save_all_charts(draws: list[sqlite3.Row], output_dir: Path, show: bool = False):
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, func in CHART_FUNCS.items():
        print(f"  [{name}] מייצר גרף …")
        fig = func(draws)
        path = output_dir / f"{name}.png"
        fig.savefig(path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
        if show:
            plt.show()
        else:
            plt.close(fig)
        print(f"    → נשמר: {path}")


# ──────────────────────────────────────────────────────────────────── #
#  CLI                                                                  #
# ──────────────────────────────────────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(description="גרפים ויזואליים של תוצאות הלוטו")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--since", default=None)
    parser.add_argument("--show", action="store_true", help="פתח גרפים במסך")
    parser.add_argument("--out", default=str(CHARTS_DIR), help="תיקיית פלט")
    args = parser.parse_args()

    draws = load_draws(Path(args.db), args.since)
    if not draws:
        print("אין נתונים. הרץ קודם fetch_lotto.py או seed_mock.py")
        return

    print(f"[*] מייצר גרפים עבור {len(draws)} הגרלות …")
    save_all_charts(draws, Path(args.out), show=args.show)
    print(f"[✓] כל הגרפים נשמרו ב-{args.out}/")


if __name__ == "__main__":
    main()
