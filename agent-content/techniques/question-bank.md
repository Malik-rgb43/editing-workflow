# Technique: the question bank (בנק שאלות לקליטה)

> Status: specified, deterministic checks only; model eval not run (decision default Q4). Written 2026-10-02 from distilled/02 workflow-end-to-end §2.4 (the author's `video-concept-intake` bank), distilled/01 rules-and-gates A1–A14. Hebrew is kept where the Hebrew itself is the knowledge: ask a Hebrew-speaking person in Hebrew; ask others in their language and keep the same structure.
> Tags: `[RULE-owner]` · `[PROVEN-internal]` · `[IDEA]`.
> Companion: [concept-ledger.md](concept-ledger.md) (where the answers go), `agent-content/playbooks/wf-00-intake.md` (when to ask).

## 0. Round discipline `[RULE-owner]`

The author's wording (O0305, 2026-09-29): *"אם אין סרטון רפרנס אתה שואל שאלות עד שאתה מדייק הכל"* — with no reference video, ask until everything is precise.

1. **3–4 questions per round**, highest impact first (use the host's multiple-choice question tool when there is one; otherwise a numbered list with lettered options).
2. **Every option is concrete** (numbers, names, a real track, a hex), never "something modern".
3. **The first option is the recommended default**, labelled `(מומלץ)` / "(recommended)" with **one line why**.
4. **A visual choice gets a preview** (an ASCII layout with safe zones and caption rail, a timeline strip, a still from `hf/references/`). When the person hesitates between fonts, caption animations, easings, palettes or transitions, build a **choice board** instead of arguing in chat (skill `visual-choice-board`; an owner idea, desk-tested only `[IDEA]`).
5. **Never guess the four blockers:** platform/ratio, length, tone, CTA. Everything else may default and is marked `D`.
6. **The quality bar (BAR) is asked in round 1** — never after the spec is approved (a bar asked late forced a ~40 min rebuild).
7. After each round print one line: `נעול: … | פתוח: …`.
8. **Stop** when nothing material is open — typically 1–3 rounds. Do not ask infrastructure questions (tools, folders, models): decide and say why in one line.
9. **"תמשיך"** (or "continue", "whatever you think") = take every recommended default, mark them `D`, and say so in ONE line. That counts as the person's choice, not a guess.
10. **Round 0 first** (owner rule 2026-10-04): what the video is for, who decides the concept (full control / the person), and the caption language (never assume Hebrew). Full control = you decide every taste dimension, mark `D`, show the decisions in the draft.
10. **Before asking, look**: `ls` the whole source folder, `ffprobe` the files, read the message. Never ask what is already known.

## 1. Round plan (default order)

| Round | Dimensions (max 4) | Notes |
|---|---|---|
| 1 | FMT · LEN · STR (footage) · **BAR** | COLOR is checked by the agent first (camera original? scopes) and asked only if unclear |
| 2 | HOOK · TON · LOOK · MOT | with previews |
| 3 | TYPE · 3D · BROLL · BRAND | BRAND: from files the person supplies; never invented |
| 4 | CAP · MUS · SFX · CTA (+ VO) | CTA is always asked; `D` only on "תמשיך" |
| 5 | FILE · VAR · DUE (+ RIGHTS/CONSENT/AIDISC) | the variant matrix is written into `<inputs>` |

Type-specific blocks (§4) replace or join the round where they belong. With a **reference video**, run the reference procedure first (§3) and ask only what a reference never answers: length, ratios, structure, CTA, file name, bar, music licence, deadline.

## 2. The bank (core dimensions)

Format of each cell: the Hebrew question · the English gloss · options (**first = default**).

| dim | שאלה (Hebrew) | Question (English) | אפשרויות / Options |
|---|---|---|---|
| FMT | לאיזו פלטפורמה ובאיזה יחס? ומה היחס הראשי? | which platform and ratio, which is primary? | 9:16 ריילס/טיקטוק (מומלץ: רוב הצפייה בנייד) · 16:9 יוטיוב · 1:1 פיד · 9:16 + 16:9 (מאסטר 9:16, עיצוב מחדש ליחס השני) |
| LEN | כמה שניות בדיוק? | exactly how many seconds? | דובר: התוכן המלא (מומלץ) · 30 · 45 · 60. מושן: 30 · 45. **אף פעם לא לפי מכפיל** |
| STR | להשאיר את כל התוכן ולחתוך רק שתיקות, או לבנות מחדש? | full length with silences cut only, or rebuild? | חיתוך שתיקות בלבד, סדר טבעי, משפטים שלמים (מומלץ) · בנייה מחדש (אראה קודם את **טקסט החיתוך**, בלי רינדור) · ההוק עובר לשנייה 0 והשאר לפי הסדר |
| BAR | מה רמת האיכות? (למשל: "עריכה פרימיום בשווי ₪500–700 לסרטון עד דקה") | quality level | פרימיום: ביט של B-roll/גרפיקה כל 3–6 שניות, גזירה וגרפיקה מאחור, תיקון צבע מדוד, סנכרון לביט, DESIGN.md (מומלץ) · נקי ופשוט · טיוטה/בדיקה |
| TON | איזו אנרגיה? | energy | אנרגטי-פרימיום · רגוע-פרימיום · יוקרתי · הומוריסטי |
| HOOK | מה נאמר ומה נראה בשניות 0–3? | what is said/seen at 0–3 s | השורה החזקה ביותר (תוצאה/מספר) בפריים 0 (מומלץ) · שאלה · ויזואל שובר-דפוס · המשפט הראשון של המקור |
| LOOK | איזו פלטת צבעים? | palette | פלטה אחת נעולה: רקע כהה אחד + צבע בולט אחד (מומלץ; "בלי ורוד" היא העדפה של הבעלים, לא חוק) · צבעי המותג · בהיר-עריכתי |
| TYPE | באיזה פונט לכתוביות וכותרות? | caption/title font | Rubik Regular/600 לקטנות + Black/900 למילות מפתח (מומלץ: ברירת מחדל, לא חוק) · פונט תצוגה שמתאים לרפרנס, **נבדק בגודל מלא על ו/ז, ד/ר, ה/ח** · פונט המותג |
| MOT | איזו שפת תנועה? | motion language | נקי וחלק: קאמרה רציפה, עקומות רכות (מומלץ) · snap-ואז-drift בסגנון השקות · מינימלי |
| 3D | באילו ביטים יש תלת-ממד, ובאיזה כלי? | which beats get 3D and with which tool | 2–3 ביטים מרכזיים עם נימוק לכל ביט: Blender לאובייקט פוטוריאליסטי, Three.js לפרוצדורלי/נתונים/מופעים רבים (מומלץ) · בלי · הרבה |
| BROLL | איזה B-roll? | kind of B-roll | צילום אמיתי + שכבת גרפיקה, UI לפי המשמעות, מונע-נתונים (מומלץ) · סטוק בלבד · בלי. **אף פעם לא תמונות AI של אנשים** |
| CAP | כתוביות? באיזו שפה? | captions + their language (Round 0, never assumed) | שפת הדיבור · תרגום (לאיזו שפה) · בלי. סגנון: קבוצות של 1–3 מילים, אנימציית כניסה **וגם יציאה**, פס כתוביות שתחתיתו לא מתחת ל-y 1450 (מומלץ לדובר) · מילות מפתח בלבד · בלי (ברירת מחדל להשקות מושן) |
| MUS | איזו מוזיקה? | music | רצועה מהספרייה עם שורת רישיון, נגמרת ברינג-אאוט עד הפריים האחרון (מומלץ) · סאונד טרנדי (אורגני בלבד) · בלי. **נשאל גם כשלרפרנס אין מוזיקה** |
| SFX | אפקטי סאונד? | sound effects | רק על אירועים נראים, 18–26 dB מתחת לקול (מומלץ) · עשיר (השקה) · בלי |
| VO | קריינות? איך מבטאים שמות מותג? | voice-over and brand pronunciation | הקול של המקור (מומלץ) · TTS עם לקסיקון (שם מותג מאוית באותיות) · בלי |
| CTA | מה הצופה עושה בסוף ומה בדיוק כתוב? | what the viewer does at the end | ניסוח מדויק שאציע + כרטיס סיום עד 3 שניות (מומלץ) · במילים של הלקוח · בלי |
| FILE | איך קוראים לקובץ הסופי? | final file name | `<name>_9x16.mp4` (מומלץ) · שם מדויק שתכתבו |
| VAR | צריך וריאנטים? | variants | אחד (מומלץ) · הוקים A/B/C · אורכים · יחסים · "בלי מוזיקה"/"בלי כתוביות" |
| DUE | יש דדליין? | deadline | אין, איכות קודם (מומלץ) · תאריך (יקטין היקף; אגיד במה) |
| BRAND | יש לוגו, צבעים, פונטים? | logo, colours, fonts | מקבצים שתשלחו או מאתר הלקוח (מומלץ) · אשלח · אין. **לא ממציאים** |
| COLOR | יש קובץ מצלמה מקורי (4K)? צריך תיקון צבע? | camera original / colour correction | תיקון מהמקור עם סקופים (מומלץ) · הצילום בסדר · מראה משלי |

Notes: *TYPE* — a font that reads one word as another is a failure, e.g. a condensed display face made ז look like ו and "לבזבז" read as "לבובו"; test every keyword at final size (the look-alike test). *LOOK* — "one palette through the whole video with clear rules per role" is the author's rule; "no pink" is his taste. *CAP* — word-pop vs sentence mode differ in timing (1–3 words, 0.35–0.7 s per card vs up to 6 words and ≥ 5/6 s); `pro-video-editor` says which.

## 3. When a reference exists

| שאלה (Hebrew) | Question (English) | Why |
|---|---|---|
| הרפרנס כולל כמה מראות (לפני/אחרי, פתיח מול גוף). איזה קטע הוא "הסגנון"? (עם תמונות לבחירה) | the reference has several looks; which time range is "the style"? | a test copied the before/after look when the author wanted the FINAL look `[PROVEN-internal]` |
| מה התפקיד של כל רפרנס? (A = כתוביות וטיפוגרפיה, B = קצב ומעברים) | role of each reference | one DNA card per reference |
| אני לוקח דקדוק (קצב, מעברים, טיפוגרפיה, מבנה סאונד) ולא חומרים (צילומים, מוזיקה, לוגו). מאושר? | grammar yes, assets no | rights |
| רפרנס מוסיקה/אורך/מבנה — האם גם הם חלק מהסגנון, או רק מה שמופיע במקטע שבחרת? | do length/structure/"no music" of the reference apply? | the reference's flaws and its absence of music are not copied; a speaker video gets music by default |

## 4. Type-specific questions (added to the round plan)

| Type | Questions (HE · EN) |
|---|---|
| talking-head | האם יש קובץ מקורי באיכות גבוהה לצד הגרסה הדחוסה? · is a camera original in the folder? — **the agent checks first** (`ls`), then confirms. האם מותר לשנות סדר משפטים? (ברירת מחדל: לא) |
| testimonial | יש הסכמה כתובה לשימוש (פרסום)? · written consent? מה השם/גיל/תפקיד לשורת-שם? · name/role for the lower-third? אילו מספרים נאמרים ויש צילום מסך שמתאים **לכל** מספר? · is there a matching proof for every spoken number? (אם לא: מספר = כיתוב ציטוט, לא "הוכחה") |
| ad-promo | מה ההצעה המדויקת (מספר, תנאי, דדליין, הסתייגות)? · exact offer; ערוץ הפעולה (וואטסאפ / טלפון / כפתור)? · CTA channel; אילו טענות מותר לומר, ואיפה ההוכחה? · which claims are allowed and where is the proof?; פלטפורמות: מטא / טיקטוק? · music licence must allow ads |
| motion-graphics | מה האובייקט הראשי שחוזר לאורך הסרטון? · hero object; מה הפרטים (מחיר/שם) שמגיעים להתקרבות של ≥ 0.9 שניות? · which details get a close-up?; יש קריינות? אם כן: לקסיקון הגייה |
| ai-generated | מה תקרת התקציב (קרדיטים) ומספר הניסיונות המרבי לשוט? · budget ceiling and retry cap (💲 `paid-spend-gate`); דמות חוזרת? פנים/ידיים/טקסט חייבים להופיע? · design around model weaknesses; האם התוכן ריאליסטי (גילוי AI לפי הפלטפורמה)? |
| podcast-clip | כמה קליפים ובאיזה אורך? · how many clips, what length; סגנון יבש (שיחה) או מעוצב? · dry vs graphic profile; כמה דוברים (TRACK / SPLIT / GRID)? · layout; אני אציג טבלת בחירת קטעים — אתה בוחר לפני עריכה |

## 5. Visual and clarifying questions

- **Ambiguous revision note** ("לא טוב" with no detail): only if the diagnosis is not decisive, ask ONE question with 2–3 concrete options and the frame. `[RULE-owner]`
- **Beat replacement** ("משעמם", "נראה AI"): do not ask; replace the beat from the type's beat menu and explain in one line what you chose and why.
- **Choice-board trigger:** the person says "אני לא בטוח בין…" about fonts/animations/palettes/layouts → one interactive board with their real text and colours instead of chat rounds.

## 6. What NOT to ask

Tools, folders, models, which ASR route, whether to run QA, how to name internal files, anything answered by `ls`/`ffprobe`/the message; creative decisions the person delegated ("מה שאתה חושב" → decide, explain in one line, mark `D`). (src: distilled/01 A10)

## 7. Worked exercise (synthetic): a messy brief → ledger rows

Message (invented): *"היי, אני רוצה סרטון קצר על הסדנה שלי לצילום בנייד. בערך חצי דקה, משהו אנרגטי, שייראה מקצועי כזה. יש לי סרטון שצילמתי איך שאני מסביר — תעשה ממנו משהו חזק עם כתוביות. אני אוהב את הסגנון של הסרטון שצירפתי. תוסיף מוזיקה, ושיהיה סוף עם הרשמה."*

| Statement | Row | State after parsing | What the agent asks (round) |
|---|---|---|---|
| "קצר… בערך חצי דקה" | LEN | `default` 30.0 s proposed, not locked | exact seconds (R1) |
| "אנרגטי" | TON | `locked` U (energetic) — spec: an event ≤ 0.7 s | confirm the number (R2) |
| "שייראה מקצועי כזה" | BAR | vague → open | the premium-bar question (R1) |
| "יש לי סרטון שצילמתי" | STR, COLOR | open | silence-cut vs rebuild; the agent runs `ls` and looks for a camera original first (R1) |
| "כתוביות" | CAP | `locked` U (captions on); style open | mode and font (R4/R3) |
| "הסגנון של הסרטון שצירפתי" | REF | open | which time range is the style (wf-01) |
| "מוזיקה" | MUS | `locked` U; track open | licence row; ring-out (R4) |
| "סוף עם הרשמה" | CTA | `locked` U (a sign-up end card); line open | the exact line (R4) |
| (nothing) | FMT, FILE, VAR | open | R1 / R5 |

A good result of round 1: FMT, LEN, STR, BAR answered; ledger shows `נעול: FMT LEN STR BAR TON CAP MUS | פתוח: HOOK LOOK TYPE REF CTA FILE VAR`.

## 8. Failure modes

| Symptom | Cause | Remedy | Prevention |
|---|---|---|---|
| the person answers "מה שאתה חושב" five times | too many creative/infrastructure questions | decide, explain in one line | §6 |
| rebuild after approval | BAR/MOT/3D asked late | add rows, re-plan | round 1 |
| the person says "I told you" | an already-known fact was asked | read the message and files first | rule 10 |
| a wrong platform assumed | FMT guessed | ask | rule 5 |
| answers lost | no ledger row | write the row immediately | [concept-ledger.md](concept-ledger.md) |

(src: distilled/02 workflow §2.4–§2.5; distilled/01 A1–A14 — read 2026-10-02. The Hebrew phrasings are this repo's; the structure is the author's.)
