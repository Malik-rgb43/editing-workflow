# עדכון, נעיצת גרסה וחזרה אחורה

> נכתב ב-2026-10-02. ההתקנה אידמפוטנטית: הרצה חוזרת עם גרסה חדשה יותר היא עדכון. כל שינוי נרשם ביומן, ולכן אפשר לבטל את העדכון האחרון. English: [docs/en/update-rollback.md](../en/update-rollback.md). התקנה: [install](install.md).

<!-- step: update-rollback-01 -->
## update-rollback-01 - לפני העדכון
```text
python install/bootstrap.py status
python install/bootstrap.py verify
```
הפקודה `status` מציגה את הגרסה המותקנת, את השלבים האחרונים ואת חותמות הגיבוי. הפקודה `verify` מציגה קבצים ששינית אחרי ההתקנה ("סטייה"): הם יגובו לפני שיוחלפו - לעולם לא יאבדו בשקט. הפרויקטים שלך, מדיית המקור, סקילים אחרים והגדרות סוכן שאינן קשורות לא נוגעים בהם.

<!-- step: update-rollback-02 -->
## update-rollback-02 - מעדכנים
```text
git -C "<toolkit clone>" fetch --tags
git -C "<toolkit clone>" pull --ff-only
python install/bootstrap.py plan
python install/bootstrap.py apply --yes
```
(משתמשים באותם `--target/--scope` של ההתקנה אם בחרת כאלה; ‏`status` מציג אותם. אינטגרציות שהוספת עם `add` נשארות רשומות.) מה קורה: קבצי סקיל וערכה ששונו מועתקים; כל קובץ שמוחלף מועתק קודם אל `~/.avc/backups/<UTC stamp>/`; קבצים שנעלמו מהגרסה החדשה מוסרים (אחרי גיבוי); סקילים שלך באותו שם עדיין מדולגים; קבצים שלא השתנו מדולגים לפי hash. גרסה היא בלתי ניתנת לשינוי - תיקון הוא גרסה חדשה.

<!-- step: update-rollback-03 -->
## update-rollback-03 - בודקים אחרי העדכון
מריצים `verify`, ואז מרנדרים שוב את הפיקסצ'ר (first-output (`docs/he/first-output.md` in the editing toolkit repository; after install: `~/.avc/toolkit/docs/he/first-output.md`)) כדי להוכיח שהמנוע והגופנים עדיין עובדים. `check` של HyperFrames שעבר **אינו** פלט זהה פריים-לפריים: רושמים בהערות את גרסת המנוע הישנה והחדשה. לעובדות על כלים, מודלים ומחירים יש בדיקה מתוארכת נפרדת; בודקים מחדש לפני כל הוצאה.

<!-- step: update-rollback-04 -->
## update-rollback-04 - חוזרים אחורה מהעדכון האחרון
```text
python install/bootstrap.py rollback --dry-run
python install/bootstrap.py rollback --yes
```
משחזר כל קובץ ש-`apply` האחרון שהשתנה החליף או הסיר, מוחק קבצים שהוא יצר, משחזר את המניפסט הקודם (התקנה ראשונה חוזרת למצב "לא מותקן") ומסיר תיקיות שהתרוקנו. הפרמטר `--to <stamp>` בוחר יומן ישן יותר (החותמות מופיעות ב-`status`). לא מוחזר: רישומי חיבורים (מסירים עם `claude mcp remove <name>`; ‏`status` מונה את אלה שההתקנה הוסיפה), סביבות שנוצרו (`.venv`, ‏`node_modules` - נבנות מחדש ב-`apply` הבא), וכל מה ששינית בידיים מחוץ לקבצים המותקנים.

<!-- step: update-rollback-05 -->
## update-rollback-05 - נשארים על גרסה (נעיצה)
`git -C "<toolkit clone>" checkout <tag>` ואז `apply`. מנוע HyperFrames נעוץ ב-`package.json` ובקובץ הנעילה (נעיצת המחקר 0.8.98; ה-"latest" ב-npm ב-2026-10-02 היה 0.8.111 - כ-100 גרסאות בחודש). שדרוג שלו הוא צעד מפורש שנבדק מחדש (`hyperframes upgrade --project <dir> --check`), לעולם לא אוטומטי. חבילות החיבורים נעוצות בדיוק ב-`integrations/catalog.toml` (למשל `@playwright/mcp@0.0.83`). ‏Node: ‏LTS הוא v24 ב-2026-10-02; ‏v26 הופך ל-LTS ב-2026-10-28 - לא עוברים בלי בדיקה חוזרת.

<!-- step: update-rollback-06 -->
## update-rollback-06 - מבקשים עזרה בלי לדלוף דבר
שולחים: מערכת הפעלה, פלט `python install/bootstrap.py verify --json`, מזהה הצעד שנכשל ושורת השגיאה האחרונה אחרי ניקוי. ההתקנה לעולם לא מדפיסה ערכי אישורים (היא מדווחת רק אם משתנה סביבה קיים). לא שולחים מפתחות, טוקנים, חומרי לקוח או תמלולים.
