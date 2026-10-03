# הסרה

> נכתב ב-2026-10-02. מסירה בדיוק את מה שההתקנה יצרה, לפי המניפסט שלה. English: [docs/en/uninstall.md](../en/uninstall.md). התקנה: [install](install.md).

<!-- step: uninstall-01 -->
## uninstall-01 - מה מוסר ומה נשאר
מוסרים: הסקילים שההתקנה העתיקה (בשני הסוכנים), תיקיית הערכה המשותפת (`~/.avc/toolkit`) עם `.venv` ו-`node_modules`, סביבות Python למסלולים, הבלוק המסומן האופציונלי בקובץ ההוראות של הסוכן, הקובץ `toolkit.local.toml` אם ההתקנה כתבה אותו, והחיבורים שההתקנה רשמה (`claude mcp remove ...`).
נשארים: פרויקטי הווידאו ותיקיית העבודה שלך (`~/avc-work`), הסקילים שלך (גם אם השם דומה), הגדרות ושרתים של הסוכן שאינם קשורים, **השכפול** של ערכת הכלים (מוחקים אותו בעצמך), חשבונות שנכנסת אליהם, ותיקיית הגיבויים (`~/.avc/backups`) אלא אם תבקש לנקות אותה.
קבצים שערכת בתוך סקילים מותקנים מועתקים לתיקיית הגיבויים לפני ההסרה; קובץ שהוספת בתוך תיקיית סקיל משאיר את התיקייה במקומה.

<!-- step: uninstall-02 -->
## uninstall-02 - תצוגה מקדימה
```text
python install/bootstrap.py uninstall --dry-run
```
מדפיסה את רשימת הקבצים, התיקיות והחיבורים שיוסרו. שום דבר לא משתנה.

<!-- step: uninstall-03 -->
## uninstall-03 - מריצים
```text
python install/bootstrap.py uninstall --yes
```
המניפסט משנה שם ל-`install-manifest.uninstalled-<stamp>.json` כקבלה. מוסיפים `--purge-backups` כדי למחוק גם את `~/.avc/backups`. אחר כך מריצים `python install/bootstrap.py verify`: הוא חייב לדווח "לא מותקן".

<!-- step: uninstall-04 -->
## uninstall-04 - שאריות שרק אתה יכול להסיר
* כניסות: מבטלים גישת חיבורים בהגדרות החשבון אצל כל ספק (Higgsfield, ‏ElevenLabs) ומוחקים מפתחות API שיצרת (Pexels, ‏21st.dev, ‏Gemini) - ההתקנה מעולם לא שמרה אותם.
* משתני סביבה שהגדרת בידיים (Windows: התחל -> "Edit environment variables for your account"; ‏macOS: הקובץ `~/.zshrc` שלך).
* חבילות שאישרת ממנהל חבילות (`winget uninstall <id>` / ‏`brew uninstall <name>`): ‏Node, ‏FFmpeg, ‏uv, ‏Git הם כלים כלליים - מסירים רק אם שום דבר אחר לא זקוק להם.
* תיקיית השכפול ו-`~/avc-work` כשאין צורך יותר בפרויקטים. מחיקת תיקיית עבודה מוחקת את הסרטונים שלך: מעתיקים קודם מה שרוצים.

<!-- step: uninstall-05 -->
## uninstall-05 - התקנה מחדש
מריצים `git pull` ואז פועלים לפי [install](install.md). הגיבויים מהריצות הקודמות נשארים עד שתנקה אותם.
