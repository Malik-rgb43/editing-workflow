# פלט ראשון - רינדור פיקסצ'ר

> נכתב ב-2026-10-02. המטרה: להוכיח על המחשב *שלך* שהמסלול התקנה -> רינדור -> בדיקה עובד, עם מקורות סינתטיים בבעלותנו (בלי חומרי לקוח, בלי עלות). הכול מקומי וחינמי. מספרי זמנים ומהירות במאגר הזה נמדדו על מחשב אחד (one reference machine) ולא מועברים אליך. English: [docs/en/first-output.md](../en/first-output.md). קודם מתקינים: install (`claude-code-setup`, docs/he/install.md).

הפקודות משתמשות במפעיל `run` כדי להתנהג זהה ב-PowerShell, ב-CMD וב-bash: הפקודה `python install/bootstrap.py run -- <command>` רצה מתיקיית הערכה המותקנת עם סביבת ה-Python של הערכה ומחליפה את `{work_root}` בתיקיית העבודה שלך (נתיב לטיני).

<!-- step: first-output-01 -->
## first-output-01 - מה זה מוכיח
נוצר פרויקט דוגמה דו-לשוני (עברית + אנגלית) אנכי באורך 8 שניות, המנוע מרנדר אותו, והוא נבדק. הוא כולל בכוונה מלכודות של כיוון מעורב (סימן שקל עם פסיק אלפים, אחוז אחרי ספרות, תחילית עברית לפני מילה לטינית, מילים לטיניות בתוך שורה עברית). מעבר פירושו: FFmpeg מקודד, המנוע מרנדר, הגופנים מגיעים מקבצים, וקובץ ה-MP4 הסופי עובר בדיקות על כל פריים. זה **לא** מוכיח איכות מודלים, מהירות GPU או שספק כלשהו עובד.

<!-- step: first-output-02 -->
## first-output-02 - בודקים את ההתקנה ואת תיקיית העבודה
```text
python install/bootstrap.py verify
python install/bootstrap.py where
```
המצב `installed` חייב להיות `pass`. שורש העבודה (`paths.work_root` בקובץ `toolkit.local.toml`) חייב להיות באותיות לטיניות בלבד: הפקודה `npx hyperframes init` מדלגת בשקט על `index.html` תחת נתיב עם אותיות עבריות. לא משנים שמות של תיקיות מקור; מעתיקים אותן לשורש העבודה.

<!-- step: first-output-03 -->
## first-output-03 - מייצרים את מקורות הדוגמה
```text
python install/bootstrap.py run -- python fixtures/generators/make_sample_project.py --out "{work_root}/sample-project"
```
נוצר `projects/sample-he-en/` עם `source/` (קליפ ממלא מקום של 8 שניות בגודל 1080x1920 עם צליל שאינו דיבור, קליפ B-roll מופשט, רצועת מוזיקה, סמל לוגו, תסריטים בעברית ובאנגלית, כתוביות SRT, תזמון ברמת מילה, `brief.json`) וקובץ `project.json` עם הכותרת העברית לתצוגה. הכול מיוצר מתוך מקורות הבדיקה של FFmpeg בידי הסקריפט (מקור: `fixtures/generators/make_sample_project.py`, ‏`fixtures/manifest.json`). בקליפ אין דיבור אמיתי, ולכן אי אפשר לבדוק איתו זיהוי דיבור.

<!-- step: first-output-04 -->
## first-output-04 - בודקים את המקורות
```text
python install/bootstrap.py run -- python -m core probe "{work_root}/sample-project/projects/sample-he-en/source/speaker_standin_1080x1920.mp4"
```
צפוי JSON עם קודק `h264`, גודל 1080x1920, ‏30 פריימים לשנייה (קצב רציונלי, לא מעוגל), משך 8 שניות ומספר הפריימים הצפוי. קוד יציאה שאינו אפס או `INSUFFICIENT_EVIDENCE` הם כישלון, לא אזהרה.

<!-- step: first-output-05 -->
## first-output-05 - מרנדרים עם המנוע
מבקשים מהסוכן: "תהפוך את פרויקט הדוגמה לסרטון אנכי קצר עם כתוביות בעברית" - הסקיל `video-request-router` מנתב. המסלול הצפוי הוא התהליך המבוקר של הערכה, בלי אילתורים: האינטייק כבר נענה ב-`brief.json`; הסוכן מנסח `PROMPT.md` ו**אתה מאשר אותו לפני כל שורת קוד**; אחר כך פיגום הפרויקט תחת שורש העבודה (`new_project`), בדיקה סטטית (`hf_preflight`), הפקודה `hyperframes check`, רינדורי טווח, רינדור מלא אחד תחת נעילת הרינדור, ומדידת עוצמת שמע על הקובץ שנשלח (`hf_deliver`). לפקודות מנוע משתמשים ב-`python install/bootstrap.py run --cwd "<project hf folder>" -- npx hyperframes ...`. הכללים שהסוכן מקיים: בלי `dir="rtl"` על שורש הקומפוזיציה, גופנים מקבצי `@font-face` בתיקייה `hf/fonts/`, הפקודה `hyperframes snapshot --describe false` עם עד 5 חותמות זמן, משימה כבדה אחת בכל רגע.
זמינות (נבדק 2026-10-02): כלי שלב 1 קיימים ב-`tools/` - ‏`doctor`, ‏`new_project`, ‏`hf_preflight`, ‏`hf_segment`, ‏`hf_deliver`, ‏`frame_qa`, ‏`caption_qa`, ‏`sheet`, ‏`transcribe`, ‏`render_lock`, ‏`ledger`, ‏`join_diff`, ‏`qa_delivery` (לכל אחד שורת `Usage:` - ‏`python tools/<name>.py --help`). שלב ה-render עצמו דורש Node ואת מנוע HyperFrames; את `hf_segment` ואת חלק ה-render של `hf_deliver` לא הרצנו מקצה לקצה מול render חי של HyperFrames בריפו הזה (נבדקו רק התכנון, ה-mux והאימות), ולכן ה-render הראשון במנוע הוא המבחן האמיתי - דווחו על כל הבדל. הריצו קודם `python tools/doctor.py smoke`: הוא מוכיח ש-FFmpeg, נתיבים עם עברית/רווחים/אימוג'י וכלי ה-QA עובדים במחשב הזה, בלי צורך במנוע.

<!-- step: first-output-06 -->
## first-output-06 - בודקים את התוצאה (מכונה + אדם)
* מכונה: בדיקת כל הפריימים על הקובץ הסופי (`frame_qa`, ‏`caption_qa`, עוצמת שמע) כותבת מעטפת JSON ‏`{status, decoded_frames, expected_frames, ...}`; רק `PASS` עם decoded = expected נחשב. כלי חסר, פסק זמן או מדגם ריק הם `not_run` / `INSUFFICIENT_EVIDENCE`, לעולם לא מעבר. לצבירה: `python tools/qa_delivery.py run <final.mp4> --captions` (שער הביקורת האנושית נוסף רק אם אתם אישרתם את הקובץ המדויק: `--human-approved "<המילים שלכם>"`).
* אדם: מנגנים את ה-MP4. בודקים: האותיות העבריות הן עברית אמיתית (לא ריבועים), סימני פיסוק ומספרים יושבים בצד הנכון בשורות מעורבות, כתובית לא נעלמת אפילו לפריים אחד, השמע לא חתוך, הפריים האחרון לא שחור.
אחר כך רושמים את העובדות (ההתקנה מאמתת אותן, היא לא מאמינה למילה שלך):
```text
python install/bootstrap.py mark first_render --evidence "<path to the final .mp4>"
python install/bootstrap.py mark inspection_passed --evidence "<path to the QA json>"
```

<!-- step: first-output-07 -->
## first-output-07 - שומרים את הזמנים
רושמים דקות של הקמה, טעינה, רינדור, בדיקה וסקירה (הרשומה הראשונה ביומן הזמנים שלך; מודול `ledger` של הערכה מסכם אותם: `python install/bootstrap.py run -- python -m core ledger summarize <file>`). אלה המספרים שלך; לא משווים אותם לשום דבר אחר. אם רינדור בודד לוקח יותר מהצפוי, לא מנסים שוב באופן עיוור: קוראים את `troubleshooting` (in the `claude-code-setup` repository, docs/he/troubleshooting.md).
