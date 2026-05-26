# 🎰 לוטו ישראל – ניתוח סטטיסטי

פרויקט Python המוריד תוצאות לוטו מה-RSS של פאיס, שומר ב-SQLite, ומציג ניתוח סטטיסטי.

## מבנה הפרויקט

```
lotto_israel/
├── fetch_lotto.py    # הורדה + פירסור RSS + שמירה ב-DB
├── analyze_lotto.py  # ניתוח סטטיסטי
├── seed_mock.py      # נתוני דוגמה (ללא אינטרנט)
├── requirements.txt
└── lotto.db          # נוצר אוטומטית
```

## התקנה

```bash
pip install -r requirements.txt
```

## שימוש

### 1. הורדה ושמירה

```bash
# הורד ושמור
python fetch_lotto.py

# בדיקה ללא שמירה
python fetch_lotto.py --dry-run
```

### 2. ניתוח סטטיסטי

```bash
# דוח מלא
python analyze_lotto.py

# 10 המספרים הנפוצים ביותר
python analyze_lotto.py --top 10

# ניתוח מתאריך מסוים + זוגות
python analyze_lotto.py --since 2023-01-01 --pairs
```

### 3. נתוני דוגמה (ללא אינטרנט)

```bash
python seed_mock.py
python analyze_lotto.py
```

## מסד הנתונים

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
| `rank` | INTEGER | דרגת הפרס |
| `winners` | INTEGER | מספר זוכים |
| `prize_ils` | REAL | סכום הפרס בש"ח |

## ניתוחים זמינים

- 📊 **שכיחות מספרים** – אילו מספרים הופיעו הכי הרבה
- 🔥 **מספרים חמים / קרים** – הנפוצים והנדירים ביותר
- 👫 **ניתוח זוגות** – אילו זוגות מספרים "אוהבים" להופיע ביחד
- ⚖️ **יחס זוגי/אי-זוגי**
- ➕ **התפלגות סכומים**
- 🔢 **מספרים עוקבים**
- 📦 **התפלגות עשורים** (1-10, 11-20, ...)
- 💪 **שכיחות המספר החזק**

## הרצה אוטומטית (Cron)

```bash
# כל יום שלישי ורביעי בשעה 22:30
30 22 * * 2,3 cd /path/to/project && python fetch_lotto.py >> lotto.log 2>&1
```
