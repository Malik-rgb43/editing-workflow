# פתרון תקלות

> נכתב ב-2026-10-02. תסמין -> סיבה -> פתרון, לפי הסדר שבו סטודנטים נתקלים בהם. הפקודות רצות מתיקיית השכפול של הערכה. תגיות ראיה: **[נמדד]** על one reference machine של הבעלים, **[מתועד]** בדף רשמי שנקרא ב-2026-10-02, **[לא נמדד]** נימוק שלא הורץ. English: [docs/en/troubleshooting.md](../en/troubleshooting.md). התקנה: [install](install.md).

<!-- step: troubleshooting-01 -->
## troubleshooting-01 - "python is not recognized" / נפתחת חנות Microsoft / Python ישן מדי
סיבה: ב-Windows ה-`python` יכול להיות מחליף של החנות (קוד יציאה 9009); ב-macOS ‏`python3` יכול להיות 3.9. ההתקנה *מתחילה* לרוץ על 3.9 ומעלה אבל צריכה 3.11 ומעלה כדי לקרוא את `integrations/catalog.toml`. פתרון, לפי הסדר: ‏`py -3 --version`; ‏`python3 --version`; אם יש `uv` מריצים `uv run --python 3.12 --no-project python install/bootstrap.py plan` (‏uv מוריד Python משלו ולא נוגע במערכת); אחרת מתקינים uv (`winget install --id astral-sh.uv -e --source winget` / ‏`brew install uv`) או Python 3.12 מ-python.org. אחר כך פותחים טרמינל חדש. [מתועד: מסמכי uv]

<!-- step: troubleshooting-02 -->
## troubleshooting-02 - PowerShell, ‏CMD ו-Git Bash מתנהגים אחרת
* ב-PowerShell 5.1 אין `&&`: שולחים פקודה אחת בכל שורה. עוטפים כל נתיב במרכאות כפולות (עובד ב-PowerShell, ב-CMD וב-bash). ב-bash על Windows נתיבים כמו `/c` עלולים להפוך ל-`C:/`; שומרים נתיבים לטיניים ומשתמשים ב-`MSYS_NO_PATHCONV=1` אם ערך של דגל התעוות. [נמדד אצל הבעלים]
* "running scripts is disabled on this system" כש-`npx` רץ: ‏PowerShell חוסם את ה-`npx.ps1`. אפשר לקרוא ל-`npx.cmd`, או ש**אתה** מרשה זאת לחשבון שלך (`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`). זו הגדרת אבטחה של המערכת: הסוכן לעולם לא משנה אותה בשבילך.
* לפקודות של הערכה משתמשים ב-`python install/bootstrap.py run -- ...`: הוא קובע `PYTHONPATH`, ‏UTF-8 ושורש עבודה באותו אופן בכל מעטפת.

<!-- step: troubleshooting-03 -->
## troubleshooting-03 - אותיות עבריות בנתיבים
* הפקודה `npx hyperframes init` **מדלגת בשקט על `index.html`** תחת נתיב עם אותיות עבריות (‏`lint`, ‏`check`, ‏`render` ממשיכים לעבוד). תמיד יוצרים פרויקטים תחת שורש עבודה לטיני; לעולם לא משנים שמות של תיקיות מקור. [נמדד: דיווח הבעלים על HyperFrames 0.8.79; לא נמדד מחדש על הגרסה הנעוצה]
* שם משתמש עברי ב-Windows (`C:\Users\<שם בעברית>\`) תקין ל-Python ול-FFmpeg אבל לא לפרויקטים של המנוע: ההתקנה מזהירה וקובעת כברירת מחדל שורש עבודה ב-`C:\avc-work`; אפשר להעביר `--work-root "C:\avc-work"` (לטיני בלבד; ערך לא לטיני נדחה) ו-`--home "C:\avc\toolkit"` לתיקיית הערכה.
* עברית בשם *קובץ* של חומרי הגלם שלך תקינה ל-FFmpeg; מעתיקים אותו לשורש העבודה לפני שהמנוע משתמש בו.
* בקונסולה מופיע `????`: ב-CMD מריצים `chcp 65001`, או משתמשים ב-Windows Terminal. ההתקנה כותבת UTF-8 (בלי BOM) בכל מקום; הבעיה היא בתצוגה, לא בקבצים.

<!-- step: troubleshooting-04 -->
## troubleshooting-04 - FFmpeg חסר, "נמצא אבל הקידוד האמיתי נכשל", ה-PATH לא התרענן
* חסר: משתמשים בפקודה המדויקת שב-`plan` (ב-Windows ‏`winget install --id Gyan.FFmpeg -e --source winget`, ב-macOS ‏`brew install ffmpeg`, ב-Linux מנהל החבילות שלך) - [מתועד 2026-10-02; האתר ffmpeg.org עצמו מספק קוד מקור בלבד]. אחר כך פותחים **טרמינל חדש** (ה-PATH נקרא בהפעלה).
* נמצא אבל `ffmpeg mini-encode: fail`: בבנייה חסר `libx264` או `aac` (יש בניות מינימליות). מריצים `ffmpeg -hide_banner -encoders` ומחפשים `libx264` ו-`aac`; מתקינים בנייה מלאה. כל בדיקה אחרת חסרת משמעות עד שזו עוברת.
* כמה FFmpeg: ‏`where ffmpeg` (Windows) / ‏`which -a ffmpeg` מראה מי מנצח; מגדירים `[binaries] ffmpeg` ב-`toolkit.local.toml` כדי לנעוץ אחד.

<!-- step: troubleshooting-05 -->
## troubleshooting-05 - ‏NVENC / QSV ברשימה אבל לא עובדים
מקודד חומרה ברשימת `ffmpeg -encoders` רק אומר שהוא קומפל פנימה. במחשב ה-AMD של הבעלים ‏NVENC ו-QSV **הופיעו ברשימה אבל נכשלו באתחול**; ‏AMF ל-H.264/HEVC עבד [נמדד]. הערכה בוחרת מקודדים לפי **קידוד אמיתי קצר**, לעולם לא לפי הרשימה, וחוזרת ל-`libx264` על ה-CPU. מקודדי NVIDIA ו-Apple **לא נמדדו**. לא "מתקנים" בהתקנת דרייברים רק כדי לרצות את הסוכן: מדווחים את פלט `doctor`.

<!-- step: troubleshooting-06 -->
## troubleshooting-06 - זיהוי דיבור על ה-GPU ‏(Vulkan) קורס
המסלול המהיר האופציונלי שאפשר להוסיף עם `add whisper-cpp` (‏whisper.cpp + Vulkan, כ-9.8 פעמים מהר מהרצת ה-CPU שלו, על מחשב הבעלים בלבד) דורש את משתנה הסביבה `GGML_VK_DISABLE_COOPMAT=1` על הדרייבר של הבעלים, אחרת קרס [נמדד, מקומי בלבד; ייתכן שהדרייבר שלך שונה]. ב-PowerShell: ‏`$env:GGML_VK_DISABLE_COOPMAT = "1"`; ב-bash: ‏`export GGML_VK_DISABLE_COOPMAT=1`. משתמשים ב-8 תהליכונים (16 היה איטי יותר). אם עדיין נכשל, משתמשים במסלול ה-CPU (מותקן אוטומטית): איטי יותר אבל זה בסיס התמיכה שעובד על כל מחשב. מסלולי CUDA ו-Apple לא נמדדו. ה-`transcribe` של HyperFrames עצמו משתמש כברירת מחדל במודל אנגלי: לעברית משתמשים במסלול התמלול של הערכה עם משקלות ivrit-ai.

<!-- step: troubleshooting-07 -->
## troubleshooting-07 - הסקילים לא מתגלים
1. מפעילים מחדש את הסוכן אחרי ההתקנה (סקילים נקראים בהפעלה).
2. במקום הנכון? ‏Claude Code: ‏`~/.claude/skills/<name>/SKILL.md` (משתמש) או `<project>/.claude/skills/` (פרויקט). ‏Codex: ‏`~/.agents/skills/` או `<repo>/.agents/skills/`; ‏`~/.codex/skills` אינו בשימוש [מתועד]. מריצים `python install/bootstrap.py verify`: הוא מונה קבצי סקיל חסרים או ששונו.
3. התקנת עם `--scope project`? אז רק הפעלות שנפתחו בתוך תיקיית הפרויקט רואות אותם.
4. שם התיקייה חייב להיות זהה ל-`name:` בראש `SKILL.md` (התוכנית של ההתקנה בודקת זאת). סקיל שלך באותו שם מנצח - ראו "conflicts" ב-`plan`; משתמשים ב-`--force` רק אחרי שקראת מה מגובה.
5. שואלים את הסוכן "אילו סקילים יש לך על עריכת וידאו?"; ‏`course-router` אמור להופיע. עדיין כלום: שולחים את `verify --json`.

<!-- step: troubleshooting-08 -->
## troubleshooting-08 - חיבור (שרת MCP) לא מתחבר
* בודקים מה הלקוח חושב: ‏`claude mcp list`, ‏`claude mcp get <name>` או `/mcp` בתוך הפעלה. ב-Codex: ‏`codex mcp list`.
* ‏Windows מקומי: שרתי `npx`/`uvx` צריכים את העטיפה `cmd /c` - ההתקנה מוסיפה אותה ל-Claude Code [מתועד]; ל-Codex על Windows זה [לא נמדד].
* ‏Node ישן מדי: המנוע ורוב שרתי npx צריכים Node 22+ (‏LTS הוא v24 ב-2026-10-02). בודקים `node --version` באותו טרמינל שהסוכן משתמש בו.
* שרתי היקף-פרויקט (קובץ `.mcp.json` בתיקייה) מבקשים אישור שלך בשימוש הראשון; שרתי היקף-משתמש נמצאים בהגדרות המשתמש שלך.
* ‏Playwright אומר שהדפדפן חסר: מאשרים את התקנת הדפדפן שלו, או משתמשים בדפדפן מותקן (`--browser msedge`); נשארים ב-`--isolated`. הפעלה ראשונה איטית: מגדילים את פסק הזמן של ההפעלה בלקוח (ב-Codex ‏`startup_timeout_sec`, ברירת מחדל 10 שניות; התבנית משתמשת ב-30) [מתועד].
* "already exists": ההתקנה מדלגת על שרת באותו שם או כינוי (למשל `playwright` שלך). שני שרתי דפדפן מכפילים את סכמת הכלים; נשארים עם אחד.
* עדיין נכשל: מסירים ורושמים מחדש בידיים עם הפקודה המדויקת שב-`plan` (‏`argv`), ואז מפעילים מחדש את הסוכן. שרת שלא מתחבר לא פוגע בהתקנה הבסיסית.

<!-- step: troubleshooting-09 -->
## troubleshooting-09 - הכניסה (OAuth) נכשלה
רלוונטי ל-Higgsfield, ‏ElevenLabs. בסוכן מריצים `/mcp`, בוחרים שרת ומתחברים; או בטרמינל `claude mcp login <name>` / ‏`codex mcp login <name>` [מתועד]. חשבון או סביבת עבודה לא נכונים? מתנתקים קודם בדפדפן. חלון קופץ נחסם או מדיניות SSO של החברה? מתירים את החלון או פונים למנהל. לעולם לא מדביקים קודים או טוקנים בצ'אט. כניסה מוצלחת לא עולה כלום ואינה אישור הוצאה. אם כתובת ה-MCP של הספק בקטלוג מסומנת `unverified` (‏Higgsfield, ‏Unsplash), משתמשים במסלול המתועד של הספק עצמו (‏Higgsfield: ה-CLI שלו).

<!-- step: troubleshooting-10 -->
## troubleshooting-10 - התנגשות פורטים
החיבור של Blender מאזין ב-`localhost:9876` ו**אין לו אימות**: אם הפורט תפוס, מוצאים מי משתמש בו (ב-Windows ‏`netstat -ano | findstr 9876`, ב-macOS/Linux ‏`lsof -i :9876`) וסוגרים אותו; לעולם לא מעבירים את הפורט הלאה ולא חושפים אותו לרשת. שרת התצוגה המקדימה של המנוע מדפיס את הכתובת שבה הוא משתמש; אם פורט תפוס, עוצרים את התצוגה הישנה לפני שמתחילים אחרת (משימה כבדה אחת בכל רגע).

<!-- step: troubleshooting-11 -->
## troubleshooting-11 - ‏`npm ci` או המנוע נכשלים
* בלי רשת או מאחורי פרוקסי: מריצים `apply --offline`, מתקנים את הרשת ומריצים `apply` שוב (שלבים שהסתיימו מדולגים).
* ‏`--ignore-scripts` אומר שהדפדפן **לא** יורד ב-`npm ci`; שלב הדפדפן נפרד ומפורש (`hyperframes browser ensure`, הגודל לא נמדד על מחשבי סטודנטים).
* גרסת המנוע שונה מנעיצת המחקר (0.8.98)? לא משדרגים כדי "לתקן" בעיה; הנעיצה זזה רק אחרי בדיקה חוזרת.
* לעולם לא מריצים `npm install -g` למנוע; הוא נעוץ לפרויקט.

<!-- step: troubleshooting-12 -->
## troubleshooting-12 - ‏`claude doctor` ירוק אבל וידאו לא עובד
הפקודה `claude doctor` מאבחנת רק את התקנת Claude Code וההגדרות שלו [מתועד]. מוכנות וידאו, גופנים ו-GPU מגיעה מ-`python install/bootstrap.py verify` (קידוד FFmpeg אמיתי, ‏hash של קבצים, בדיקת קישורים) ומ-`doctor` של הערכה. מדווחים את חמשת המצבים; מצב שלא רץ הוא `not_run`.

<!-- step: troubleshooting-13 -->
## troubleshooting-13 - ‏`uv sync` נכשל
הערכה צריכה Python 3.12 או 3.13 (‏`requires-python`); ‏`uv` מוריד עותק משלו אם צריך (ייתכנו רשת ומאות מגה-בייט; לא נמדד). שגיאות בנוגע לקובץ נעילה: מריצים שוב בלי עריכות (ההתקנה משתמשת ב-`--locked` רק כש-`uv.lock` קיים). אנטי-וירוס או לקוח סנכרון (OneDrive, ‏Dropbox) שנועל את תיקיית הערכה עלול לשבור את הסביבה: שומרים את תיקיית הערכה ושורש העבודה מחוץ לתיקיות מסונכרנות [עצה לא נמדדה]. הליבה עדיין עובדת בלי סביבת Python למשימות FFmpeg פשוטות; המפעיל `run -- python ...` יגיד מה חסר.

<!-- step: troubleshooting-14 -->
## troubleshooting-14 - התקנה חלקית, "another install is running", התנגשויות
* קוד יציאה 4 (חלקי): קוראים את השורה היחידה שנכשלה, מתקנים ומריצים שוב את אותה פקודה.
* "another install is running": קיים קובץ נעילה ב-`~/.avc/install.lock`. ממתינים; אם בטוחים ששום דבר לא רץ (קריסה), ‏`--break-lock`.
* ‏`conflict-foreign` בתוכנית: כבר יש לך סקיל בשם הזה. הוא מדולג ולא נוגעים בו. משנים את השם שלך, או `--force` (התיקייה שלך מועתקת קודם לגיבויים).
* משהו הועתק חלקית אחרי הפסקת חשמל: קבצים מוחלפים באופן אטומי, ולכן הרצה חוזרת מתכנסת; ‏`verify` מראה כל מה שחסר.

<!-- step: troubleshooting-15 -->
## troubleshooting-15 - מה לשלוח כשמבקשים עזרה
מערכת הפעלה וגרסה, מעטפת, הפלט של `python install/bootstrap.py verify --json`, מזהה הצעד, שורת השגיאה האחרונה אחרי ניקוי, ומה ציפית. לעולם לא מפתחות, טוקנים, חומרי לקוח או תמלולים. ההתקנה מדפיסה רק אם משתנה אישורים קיים, לעולם לא את ערכו.
