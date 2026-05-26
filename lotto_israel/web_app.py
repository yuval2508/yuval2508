"""
web_app.py
----------
ממשק Web לניתוח תוצאות הלוטו — Flask + Bootstrap 5.

שימוש:
    python web_app.py               # http://localhost:5000
    python web_app.py --port 8080
    python web_app.py --debug
"""

import argparse
import base64
import io
import sqlite3
from collections import Counter
from pathlib import Path

from flask import Flask, jsonify, render_template

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from visualize_lotto import (
    chart_frequency, chart_heatmap,
    chart_sum_distribution, chart_strong_number,
    chart_hot_cold_timeline, fig_to_png_bytes, load_draws,
)
from predict_lotto import (
    STRATEGIES, load_draws as load_draws_pred,
    strategy_hot, strategy_cold, strategy_ensemble,
)

DB_PATH = Path(__file__).parent / "lotto.db"

app = Flask(__name__)


# ──────────────────────────────────────────────────────────────────── #
#  Helpers                                                              #
# ──────────────────────────────────────────────────────────────────── #

def png_b64(fig) -> str:
    data = fig_to_png_bytes(fig)
    return base64.b64encode(data).decode()


def get_stats(draws):
    from collections import Counter as C
    nums = []
    for d in draws:
        nums += [d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]]
    c = C(nums)
    hot = [n for n, _ in c.most_common(7)]
    cold = sorted(range(1, 50), key=lambda n: c.get(n, 0))[:7]
    avg_sum = sum(d["n1"]+d["n2"]+d["n3"]+d["n4"]+d["n5"]+d["n6"] for d in draws) / len(draws)
    return {
        "total_draws": len(draws),
        "date_from":   draws[0]["draw_date"],
        "date_to":     draws[-1]["draw_date"],
        "hot":         hot,
        "cold":        cold,
        "avg_sum":     round(avg_sum, 1),
    }


# ──────────────────────────────────────────────────────────────────── #
#  Routes                                                               #
# ──────────────────────────────────────────────────────────────────── #

@app.route("/")
def index():
    draws = load_draws(DB_PATH)
    if not draws:
        return "<h2>אין נתונים — הרץ קודם fetch_lotto.py או seed_mock.py</h2>", 503

    stats = get_stats(draws)

    # גרפים
    charts = {
        "frequency": png_b64(chart_frequency(draws)),
        "sum_dist":  png_b64(chart_sum_distribution(draws)),
        "strong":    png_b64(chart_strong_number(draws)),
        "timeline":  png_b64(chart_hot_cold_timeline(draws)),
    }

    # 10 הגרלות אחרונות
    last_draws = [
        {
            "draw_number": d["draw_number"],
            "draw_date":   d["draw_date"],
            "numbers":     [d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]],
            "strong":      d["strong"],
        }
        for d in draws[-10:][::-1]
    ]

    # הצעות
    suggestions = {
        "🔥 מספרים חמים":  strategy_hot(draws),
        "🧠 אנסמבל":        strategy_ensemble(draws),
        "🧊 מספרים קרים":  strategy_cold(draws),
    }

    return render_template(
        "index.html",
        stats=stats,
        charts=charts,
        last_draws=last_draws,
        suggestions=suggestions,
    )


@app.route("/api/draws")
def api_draws():
    draws = load_draws(DB_PATH)
    return jsonify([
        {
            "draw_number": d["draw_number"],
            "draw_date":   d["draw_date"],
            "numbers":     [d["n1"], d["n2"], d["n3"], d["n4"], d["n5"], d["n6"]],
            "strong":      d["strong"],
            "extra":       d["extra"],
        }
        for d in draws
    ])


@app.route("/api/stats")
def api_stats():
    draws = load_draws(DB_PATH)
    return jsonify(get_stats(draws))


@app.route("/api/suggest/<strategy>")
def api_suggest(strategy):
    draws = load_draws_pred(DB_PATH)
    if strategy not in STRATEGIES:
        return jsonify({"error": f"אסטרטגיה לא מוכרת: {strategy}"}), 400
    _, fn = STRATEGIES[strategy]
    nums = fn(draws) if strategy != "uniform" else __import__("predict_lotto").strategy_uniform()
    return jsonify({"strategy": strategy, "numbers": nums})


@app.route("/chart/<name>")
def chart_image(name):
    from flask import Response
    draws = load_draws(DB_PATH)
    chart_map = {
        "frequency": chart_frequency,
        "heatmap":   chart_heatmap,
        "sum_dist":  chart_sum_distribution,
        "strong":    chart_strong_number,
        "timeline":  chart_hot_cold_timeline,
    }
    if name not in chart_map:
        return "לא נמצא", 404
    data = fig_to_png_bytes(chart_map[name](draws))
    return Response(data, mimetype="image/png")


# ──────────────────────────────────────────────────────────────────── #
#  Main                                                                 #
# ──────────────────────────────────────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(description="Web app ניתוח לוטו")
    parser.add_argument("--port",  type=int, default=5000)
    parser.add_argument("--host",  default="0.0.0.0")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    print(f"[*] מפעיל שרת על http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
