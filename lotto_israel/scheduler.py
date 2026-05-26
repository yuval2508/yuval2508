"""
scheduler.py
------------
הרצה אוטומטית של fetch_lotto.py בימי ההגרלה.

הלוטו מתקיים בדרך כלל:
  • יום שלישי  – 21:00
  • יום שישי   – 21:00
  (התוצאות מתפרסמות באתר כ-30-60 דקות לאחר מכן)

שימוש:
    python3 scheduler.py              # מריץ scheduler רציף (blocking)
    python3 scheduler.py --now        # מריץ פעם אחת עכשיו ויוצא
    python3 scheduler.py --cron       # מדפיס הוראת crontab ויוצא
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

LOG_PATH = Path(__file__).parent / "lotto_scheduler.log"
FETCH_SCRIPT = Path(__file__).parent / "fetch_lotto.py"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────── #
#  Job                                                                  #
# ──────────────────────────────────────────────────────────────────── #

def run_fetch():
    log.info("▶ מריץ fetch_lotto.py …")
    try:
        result = subprocess.run(
            [sys.executable, str(FETCH_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            log.info("✓ fetch הסתיים בהצלחה")
            for line in result.stdout.splitlines():
                log.info("  " + line)
        else:
            log.error("✗ fetch נכשל (returncode=%d)", result.returncode)
            log.error(result.stderr)
    except subprocess.TimeoutExpired:
        log.error("✗ timeout — fetch לקח יותר מ-120 שניות")
    except Exception as e:
        log.exception("✗ שגיאה בלתי צפויה: %s", e)


# ──────────────────────────────────────────────────────────────────── #
#  Cron instruction                                                     #
# ──────────────────────────────────────────────────────────────────── #

CRONTAB_LINE = (
    "# לוטו – שלישי ושישי ב-22:00 (אחרי שהתוצאות מתפרסמות)\n"
    f"0 22 * * 2,5  {sys.executable} {FETCH_SCRIPT} >> {LOG_PATH} 2>&1"
)

SYSTEMD_SERVICE = f"""\
[Unit]
Description=Lotto Israel Fetcher
After=network.target

[Service]
Type=oneshot
ExecStart={sys.executable} {FETCH_SCRIPT}
StandardOutput=append:{LOG_PATH}
StandardError=append:{LOG_PATH}

[Install]
WantedBy=multi-user.target
"""

SYSTEMD_TIMER = """\
[Unit]
Description=Run Lotto Fetcher on draw days
Requires=lotto-fetch.service

[Timer]
# שלישי ושישי ב-22:00
OnCalendar=Tue,Fri 22:00:00
Persistent=true

[Install]
WantedBy=timers.target
"""


# ──────────────────────────────────────────────────────────────────── #
#  APScheduler                                                          #
# ──────────────────────────────────────────────────────────────────── #

def start_scheduler():
    if not HAS_APSCHEDULER:
        log.error(
            "APScheduler לא מותקן.\n"
            "הרץ:  pip install apscheduler\n"
            "או השתמש ב:  python3 scheduler.py --cron"
        )
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="Asia/Jerusalem")

    # יום שלישי ושישי בשעה 22:00
    scheduler.add_job(
        run_fetch,
        CronTrigger(day_of_week="tue,fri", hour=22, minute=0,
                    timezone="Asia/Jerusalem"),
        id="lotto_fetch",
        name="Lotto RSS Fetch",
        misfire_grace_time=3600,
        coalesce=True,
    )

    log.info("=" * 50)
    log.info("  🗓  Lotto Scheduler מופעל")
    log.info("  הגרלות: שלישי + שישי בשעה 22:00 (ישראל)")
    log.info("  לוג: %s", LOG_PATH)
    log.info("  עצור עם Ctrl+C")
    log.info("=" * 50)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler נעצר.")


# ──────────────────────────────────────────────────────────────────── #
#  CLI                                                                  #
# ──────────────────────────────────────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(description="Scheduler להורדת תוצאות לוטו")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--now",     action="store_true", help="הרץ פעם אחת עכשיו")
    group.add_argument("--cron",    action="store_true", help="הדפס הוראות crontab/systemd")
    args = parser.parse_args()

    if args.now:
        run_fetch()
        return

    if args.cron:
        print("\n── Crontab ──────────────────────────────────")
        print(CRONTAB_LINE)
        print("\nהוספה אוטומטית לcrontab (הרץ על ubuntu01):")
        print(f'  (crontab -l 2>/dev/null; echo "{CRONTAB_LINE}") | crontab -')

        print("\n── systemd (מומלץ יותר) ───────────────────")
        print("שמור ב-/etc/systemd/system/lotto-fetch.service :")
        print(SYSTEMD_SERVICE)
        print("שמור ב-/etc/systemd/system/lotto-fetch.timer :")
        print(SYSTEMD_TIMER)
        print("הפעלה:")
        print("  sudo systemctl daemon-reload")
        print("  sudo systemctl enable --now lotto-fetch.timer")
        print("  systemctl list-timers lotto-fetch.timer")
        return

    start_scheduler()


if __name__ == "__main__":
    main()
