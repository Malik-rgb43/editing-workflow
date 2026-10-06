# Question bank and round plan

Load when a ledger field is missing or you are composing a round. Shared technique file (owned elsewhere): `agent-content/techniques/question-bank.md`. Options below are course "house presets v1", not platform law (decision default Q5): they are recommended starting points the user may overrule. Source: distilled 02 workflow-end-to-end section 2.4, 2026-10-01.

## 1. How to ask
- Use the host's ask-user tool if there is one (e.g. AskUserQuestion); otherwise one numbered chat message. Either way: **3-4 questions per round**, highest impact first.
- Every option is concrete (a number, a name, a hex, a file). **First option = recommended**, labelled `(מומלץ)` / `(recommended)` with one line of why.
- Visual choice? Add a preview: an ASCII layout (safe zones, caption rail), a timeline strip, or a still from `hf/references/`. For 3+ pending visual taste choices, offer `visual-choice-board` instead of more rounds.
- After every round print one line: `נעול: <ids> | פתוח: <dims>` (locked | open) and update the ledger.
- Do not ask what is already known (read the source tree and the message first) and do not ask infrastructure questions (tools, folders): decide and say why in one line.
- "תמשיך" / "continue" / "whatever you think" = take every recommended option, mark `D`, say so in ONE line (`Defaults taken: 9:16, 45 s, silence-cut only, ...`). It counts as the user's choice. It never covers a blocking dimension the user has not seen.

- **Round 0, always first (owner rule 2026-10-04), ONE message:** what the video is for (one line), *who decides the concept* (`full control - you decide` / `I define it`), the **speech and caption language** (which language is spoken; captions in it / a translation, say which / no captions), **consent** of the people on camera if unclear, and the **missing facts** (offer, prices, names, dates, contact details). Never assume Hebrew: not every student speaks Hebrew or wants Hebrew captions. The answer locks CAP (a blocking row) and gives `prep.py` its `--language`.
- **Full control** ("אתה מחליט", "you decide") = decide every remaining taste dimension yourself (format, length, tone, structure, hook, look, font, music, the CTA wording, the file name), mark each `D`, say the decisions in ONE line and show them in the draft for approval. Facts are never decided: the offer, prices, names, dates, claims and contact details (a CTA's URL, phone or price) are asked in one bundled question, with rights, consent and a deadline.

## 2. Round plan
| Round | Dimensions (max 4) | Why this order |
|---|---|---|
| 1 | FMT, LEN, STR (footage), BAR | they change everything downstream; a quality bar asked after approval forced a rebuild once. COLOR: check the folder yourself first and ask only if unclear |
| 2 | HOOK, TON, LOOK, MOT | the feel |
| 3 | TYPE, 3D, BROLL, BRAND | the look of the parts (BRAND from files the user supplies, never invented) |
| 4 | MUS, SFX, CTA (+ VO) | the finish; CAP was settled in Round 0. The CTA wording is `D` on "continue" or full control; a CTA fact (URL, phone, price) is always asked |
| 5 | VAR, DUE (+ rights, AI-disclosure facts) | the variant matrix; FILE is a default name said back, never a question |
Same plan as the shared technique `agent-content/techniques/question-bank.md` (canonical, with the full Hebrew bank and per-type questions). Stop when no blocking row is open (FMT, LEN, TON, BAR, CTA, CAP; STR and COLOR with footage; VAR with several files; FILE as a said-back default); skip any dimension the footage or a reference already answers. Typical total: 1-3 rounds when the user answers fully, up to 5 for a vague start.

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
| TYPE | איזה פונט לכתוביות וכותרות? | Which caption/title font? | the user names one, or a brand font; no name = build a font board for the caption language (`visual-choice-board` rule 8: the bundled catalogue is 8 OFL **Hebrew** fonts; for another script offer 3-4 named OFL fonts with a sample line instead), never a silent default; "you choose" / full control = your pick (Rubik is the Hebrew house preset), said back as a default |
| MOT | איזו שפת תנועה? | Which motion language? | clean and smooth (one continuous camera, eased) (rec.) / snap and drift / minimal |
| 3D | באילו ביטים תלת-ממד? | Which beats get 3D? | 2-3 hero beats with a reason each (rec.) / none / heavy. Decide per beat, not per video |
| BROLL | איזה בי-רול? | Which B-roll? | real footage + motion-graphics layer (rec.) / UI rebuilt in code / stock only / none. No AI-looking stills of people |
| CAP | כתוביות? באיזו שפה? | Captions? In which language? | language first (Round 0, blocking, never assumed): the speech language / a translation (say which) / none. Style: word-group cards that animate in AND out (rec.) / keywords only / none (default for motion launches) |
| MUS | מוזיקה? (שואלים תמיד, גם אם לרפרנס אין) | Music? (ask even if the reference has none) | a licensed bed with a SOURCE row (rec.) / trending sound (own account only) / none |
| SFX | אפקטי קול? | Sound effects? | only on visible events, quiet under speech (rec.) / rich (launch) / none |
| VO | קריינות והגייה של שמות? | Voice-over and name pronunciation? | the source voice (rec.) / TTS with a spelled lexicon / none |
| CTA | מה הצופה עושה בסוף ומה כתוב? | What does the viewer do at the end; what is written? | a proposed exact line + end card <= 3 s (rec.) / the client's own words / none. The wording is yours under full control; its facts (URL, phone, price) are always asked |
| FILE | (not asked) | (not asked) | default `<name>_9x16.mp4`, said back on the defaults line, `D`; the user's exact name wins when given |
| VAR | יש גרסאות? | Variants? | one (rec.) / hooks A/B/C / lengths / ratios / no-music, no-captions versions |
| DUE | יש דד-ליין? | Deadline? | none, quality first (rec.) / a date: say what scope shrinks |
| COLOR | יש קובץ מצלמה מקורי? צריך תיקון צבע? | Is there a camera original; does colour need correcting? | check yourself first (`source_inventory.py`); correct from the camera original (rec.) / footage is fine / the user's own look |
| BRAND | לוגו, צבעים, פונטים? | Logo, colours, fonts? | from the client note or site; ask, never invent; use the logo file as supplied |

## 4. Never-guess list
Platform, length, tone, CTA, caption language, structure (silence cut vs rebuild) and quality bar block the concept (under full control they are your said-back `D` decisions, except the caption language and the facts). Missing footage, missing subject or missing text: ask ONE concentrated question while doing independent work (read the tree, probe files); never replace a filmed speaker with slides or an AI character without consent, and never carry the reference product's claims to the user's product.
