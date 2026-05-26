# 🎰 לוטו ישראל – ניתוח סטטיסטי

פרויקט Python המוריד תוצאות לוטו מה-RSS של פאיס, שומר ב-SQLite, ומציג ניתוח סטטיסטי.

## מבנה הפרויקט

```
lotto_israel/
├── fetch_lotto.py      # הורדה + פירסור RSS + שמירה ב-DB
├── analyze_lotto.py    # ניתוח סטטיסטי (טקסט/ASCII)
├── visualize_lotto.py  # גרפים ויזואליים (matplotlib)
├── predict_lotto.py    # הצעות מספרים – 6 אסטרטגיות
├── web_app.py          # ממשק Web – Flask dashboard
├── scheduler.py        # הרצה אוטומטית (APScheduler / cron / systemd)
├── seed_mock.py        # נתוני דוגמה (ללא אינטרנט)
├── requirements.txt
└── lotto.db            # נוצר אוטומטית
```

---

## 🚀 התקנה מהירה

```bash
# 1. שכפל את ה-repo
git clone https://github.com/yuval2508/yuval2508.git
cd yuval2508/lotto_israel

# 2. צור סביבה וירטואלית (מומלץ)
python3 -m venv .venv

# Windows:
.venv\Scripts\activate
# Mac / Linux:
source .venv/bin/activate

# 3. התקן תלויות
pip install -r requirements.txt
```

---

## 📥 שלב 1 – הורד נתונים

```bash
# הורד תוצאות אמיתיות מפאיס ושמור ב-DB
python3 fetch_lotto.py

# בדיקה ללא שמירה
python3 fetch_lotto.py --dry-run

# אין אינטרנט? צור 200 הגרלות מדומות לבדיקה
python3 seed_mock.py
```

---

## 📊 שלב 2 – ניתוח

### ניתוח טקסטואלי (טרמינל)

```bash
# דוח מלא
python3 analyze_lotto.py

# 10 המספרים הנפוצים ביותר
python3 analyze_lotto.py --top 10

# ניתוח מתאריך מסוים + ניתוח זוגות
python3 analyze_lotto.py --since 2023-01-01 --pairs
```

### גרפים ויזואליים (matplotlib)

```bash
# שמור כל הגרפים לתיקיית charts/
python3 visualize_lotto.py

# פתח גרפים ישירות במסך
python3 visualize_lotto.py --show

# גרפים מתאריך מסוים
python3 visualize_lotto.py --since 2023-01-01
```

גרפים שנוצרים:
| קובץ | תיאור |
|------|--------|
| `charts/frequency.png` | שכיחות כל מספר (1-49) |
| `charts/heatmap.png` | מטריצת זוגות נפוצים |
| `charts/sum_dist.png` | התפלגות סכום 6 המספרים |
| `charts/timeline.png` | קו זמן של מספרים חמים |
| `charts/strong.png` | שכיחות המספר החזק |

### הצעות מספרים (ML סטטיסטי)

```bash
# כל האסטרטגיות, 3 הצעות כל אחת
python3 predict_lotto.py --runs 3

# אסטרטגיה ספציפית + הערכה רטרואקטיבית
python3 predict_lotto.py --strategy ensemble --eval

# אסטרטגיות זמינות: uniform | hot | cold | balanced | due | ml_ema | ensemble
```

---

## 🌐 שלב 3 – ממשק Web

```bash
python3 web_app.py
```

פתח בדפדפן: **http://localhost:5000**

Dashboard כולל:
- סטטיסטיקות כלליות + מספרים חמים/קרים
- גרפים מוטמעים
- טבלת 10 הגרלות אחרונות
- הצעות מספרים לפי אסטרטגיות

### API Endpoints

| Endpoint | תיאור |
|----------|--------|
| `GET /api/draws` | כל ההגרלות (JSON) |
| `GET /api/stats` | סטטיסטיקות כלליות |
| `GET /api/suggest/hot` | הצעה – מספרים חמים |
| `GET /api/suggest/cold` | הצעה – מספרים קרים |
| `GET /api/suggest/ensemble` | הצעה – אנסמבל |
| `GET /chart/frequency` | גרף שכיחות (PNG) |
| `GET /chart/heatmap` | מטריצת זוגות (PNG) |

---

## ⏰ שלב 4 – הרצה אוטומטית

הלוטו מתקיים בדרך כלל בימי **שלישי ושישי** בשעה 21:00.
הסקריפט ירוץ ב-22:00 (אחרי פרסום התוצאות).

### APScheduler (Python – Windows / Mac / Linux)

```bash
# מריץ תהליך Python שמחכה לזמן הנכון
python3 scheduler.py

# הרץ עכשיו פעם אחת
python3 scheduler.py --now
```

### Cron (Mac / Linux)

```bash
# הצג את שורת ה-cron המוכנה
python3 scheduler.py --cron

# או הוסף ידנית (ערוך את הנתיב לפי המיקום שלך)
crontab -e
# הוסף:
0 22 * * 2,5  /path/to/.venv/bin/python3 /path/to/lotto_israel/fetch_lotto.py >> ~/lotto.log 2>&1
```

### Windows Task Scheduler

```powershell
# צור משימה מתוזמנת (PowerShell כ-Admin)
$action  = New-ScheduledTaskAction -Execute "C:\path\to\.venv\Scripts\python.exe" `
                                   -Argument "C:\path\to\lotto_israel\fetch_lotto.py"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday,Friday -At 10:00PM
Register-ScheduledTask -TaskName "LottoFetch" -Action $action -Trigger $trigger
```

### systemd (Linux – הדרך המומלצת לשרת)

```bash
# הצג קבצי service ו-timer מוכנים
python3 scheduler.py --cron

sudo systemctl daemon-reload
sudo systemctl enable --now lotto-fetch.timer
systemctl list-timers lotto-fetch.timer   # בדוק שהטיימר פעיל
```

---

## 🗄️ מסד הנתונים

### טבלת `draws`

| עמודה | סוג | תיאור |
|-------|-----|--------|
| `draw_number` | INTEGER | מספר הגרלה (ייחודי) |
| `draw_date` | TEXT | תאריך (ISO 8601) |
| `n1`–`n6` | INTEGER | 6 המספרים הזוכים |
| `strong` | INTEGER | המספר החזק |
| `extra` | INTEGER | מספר נוסף (אם קיים) |
| `fetched_at` | TEXT | זמן שליפה |

### טבלת `prizes`

| עמודה | סוג | תיאור |
|-------|-----|--------|
| `draw_number` | INTEGER | מספר הגרלה |
| `rank` | INTEGER | דרגת הפרס (1=ראשון) |
| `winners` | INTEGER | מספר זוכים |
| `prize_ils` | REAL | סכום הפרס בש"ח |

### שאילתות SQL שימושיות

```sql
-- 10 הגרלות אחרונות
SELECT * FROM draws ORDER BY draw_date DESC LIMIT 10;

-- המספרים הנפוצים ביותר
SELECT num, COUNT(*) AS cnt FROM (
  SELECT n1 AS num FROM draws UNION ALL
  SELECT n2 FROM draws UNION ALL
  SELECT n3 FROM draws UNION ALL
  SELECT n4 FROM draws UNION ALL
  SELECT n5 FROM draws UNION ALL
  SELECT n6 FROM draws
) GROUP BY num ORDER BY cnt DESC;

-- הגרלות שבהן הופיע מספר 7
SELECT draw_number, draw_date, n1,n2,n3,n4,n5,n6
FROM draws
WHERE 7 IN (n1,n2,n3,n4,n5,n6)
ORDER BY draw_date DESC;
```
