# Question bank and round plan

Load when a ledger field is missing or you are composing a round. Shared technique file (owned elsewhere): `agent-content/techniques/question-bank.md`. Options below are course "house presets v1", not platform law (decision default Q5): they are recommended starting points the user may overrule. Source: distilled 02 workflow-end-to-end section 2.4, 2026-10-01.

## 1. How to ask
- Use the host's ask-user tool if there is one (e.g. AskUserQuestion); otherwise one numbered chat message. Either way: **3-4 questions per round**, highest impact first.
- Every option is concrete (a number, a name, a hex, a file). **First option = recommended**, labelled `(מומלץ)` / `(recommended)` with one line of why.
- Visual choice? Add a preview: an ASCII layout (safe zones, caption rail), a timeline strip, or a still from `hf/references/`. For 3+ pending visual taste choices, offer `visual-choice-board` instead of more rounds.
- After every round print one line: `נעול: <ids> | פתוח: <dims>` (locked | open) and update the ledger.
- Do not ask what is already known (read the source tree and the message first) and do not ask infrastructure questions (tools, folders): decide and say why in one line.
- "תמשיך" / "continue" / "whatever you think" = take every recommended option, mark `D`, say so in ONE line (`Defaults taken: 9:16, 45 s, silence-cut only, ...`). It counts as the user's choice. It never covers a blocking dimension the user has not seen.

## 2. Round plan
| Round | Dimensions (max 4) | Why this order |
|---|---|---|
| 1 | FMT, LEN, STR (footage), BAR | they change everything downstream; a quality bar asked after approval forced a rebuild once. COLOR: check the folder yourself first and ask only if unclear |
| 2 | HOOK, TON, LOOK, MOT | the feel |
| 3 | TYPE, 3D, BROLL, BRAND | the look of the parts (BRAND from files the user supplies, never invented) |
| 4 | CAP, MUS, SFX, CTA (+ VO) | the finish; CTA is always asked and is `D` only on "continue" |
| 5 | FILE, VAR, DUE (+ rights, consent, AI-disclosure facts) | the exact deliverable and the variant matrix |
Same plan as the shared technique `agent-content/techniques/question-bank.md` (canonical, with the full Hebrew bank and per-type questions). Stop when no blocking row is open (FMT, LEN, TON, BAR, CTA, FILE; STR and COLOR with footage; VAR with several files); skip any dimension the footage or a reference already answers. Typical total: 1-3 rounds when the user answers fully, up to 5 for a vague start.

## 3. The bank (Hebrew question | English question | options, first = recommended)
| Dim | Hebrew | English | Options |
|---|---|---|---|
| FMT | לאיזו פלטפורמה ובאיזה יחס, ומה היחס הראשי? | Which platform and ratio, and which is the master? | 9:16 Reels/TikTok/Shorts (rec.) / 16:9 YouTube or site / 1:1 / 4:5 feed / 9:16 + 16:9 (master 9:16, re-layout not crop) |
| LEN | כמה שניות בדיוק? | Exactly how many seconds? | speaker reel: full content (rec.) / 30 / 45 / 60; motion: 30 / 45. Never derive from a multiplier; "too fast" -> propose exact seconds, confirm in one line |
| STR | לחתוך רק שתיקות או לבנות מחדש? | Silence cut only, or restructure? | silence cut only, natural order, whole sentences (rec.) / restructure (show the text of the cut first) / hook moved to 0 s, rest in order |
| BAR | מה רמת האיכות? | What quality bar? | premium (B-roll or graphics beat every 3-6 s, cutout with graphics behind, measured colour, beat sync) (rec.) / clean and simple / draft or test. State the price/market claim only as the user's own target |
| TON | איזו אנרגיה? | What energy? | energetic-premium / calm-premium / luxury / humorous |
| HOOK | מה נאמר או נראה ב-0-3 שניות? | What is said or seen at 0-3 s? | the strongest result or number on frame 0 (rec.) / a question / a pattern-interrupt visual / the source's first line |
| LOOK | איזו פלטה? | Which palette? | the client's brand (rec. if it exists) / one dark ground + ONE accent / light editorial. One locked palette per project |
| TYPE | איזה פונט לכתוביות וכותרות? | Which caption/title font? | the user names one, or a brand font; no name = build a font board (`visual-choice-board` rule 8: 8 OFL Hebrew fonts with their own line), never a silent default; "you choose" = Rubik (house preset), said back as a default |
| MOT | איזו שפת תנועה? | Which motion language? | clean and smooth (one continuous camera, eased) (rec.) / snap and drift / minimal |
| 3D | באילו ביטים תלת-ממד? | Which beats get 3D? | 2-3 hero beats with a reason each (rec.) / none / heavy. Decide per beat, not per video |
| BROLL | איזה בי-רול? | Which B-roll? | real footage + motion-graphics layer (rec.) / UI rebuilt in code / stock only / none. No AI-looking stills of people |
| CAP | כתוביות? | Captions? | word-group cards that animate in AND out (rec.) / keywords only / none (default for motion launches) |
| MUS | מוזיקה? (שואלים תמיד, גם אם לרפרנס אין) | Music? (ask even if the reference has none) | a licensed bed with a SOURCE row (rec.) / trending sound (own account only) / none |
| SFX | אפקטי קול? | Sound effects? | only on visible events, quiet under speech (rec.) / rich (launch) / none |
| VO | קריינות והגייה של שמות? | Voice-over and name pronunciation? | the source voice (rec.) / TTS with a spelled lexicon / none |
| CTA | מה הצופה עושה בסוף ומה כתוב? | What does the viewer do at the end; what is written? | a proposed exact line + end card <= 3 s (rec.) / the client's own words / none. Always asked |
| FILE | איך לקרוא לקובץ הסופי? | Final file name? | `<name>_9x16.mp4` (rec.) / the user's exact name (it wins) |
| VAR | יש גרסאות? | Variants? | one (rec.) / hooks A/B/C / lengths / ratios / no-music, no-captions versions |
| DUE | יש דד-ליין? | Deadline? | none, quality first (rec.) / a date: say what scope shrinks |
| COLOR | יש קובץ מצלמה מקורי? צריך תיקון צבע? | Is there a camera original; does colour need correcting? | check yourself first (`source_inventory.py`); correct from the camera original (rec.) / footage is fine / the user's own look |
| BRAND | לוגו, צבעים, פונטים? | Logo, colours, fonts? | from the client note or site; ask, never invent; use the logo file as supplied |

## 4. Never-guess list
Platform, length, tone, CTA, structure (silence cut vs rebuild) and quality bar block the concept. Missing footage, missing subject or missing text: ask ONE concentrated question while doing independent work (read the tree, probe files); never replace a filmed speaker with slides or an AI character without consent, and never carry the reference product's claims to the user's product.
