---
module: glossary
checked_at: 2026-10-02
expires: "none (stable vocabulary); technical rows are re-read at each release"
confidence: "definitions [RULE-owner]/[PROVEN-internal] for house terms; no volatile numbers except where a row says 'house preset'"
refresh: "n/a — add terms when a lesson introduces them; keep Hebrew and English rows in step"
---

# מילון מונחים · Glossary (עברית ↔ English)

| Field | Value |
|---|---|
| Fact set | working vocabulary of the course: Hebrew terms ↔ English, house terms, evidence tags |
| Versions / ids | none |
| `checked_at` | **2026-10-02** (research date) |
| Source | research glossary (anonymised) + terms used across the reference modules |
| Scope / plan / region | Hebrew-first course; English for implementers |
| Confidence | definitions are working definitions, not standards |
| `expires` | none; see front matter |
| Non-spending refresh | edit the file |

מספרים בטבלאות הם **פריסט בית (house preset v1)** ולא חוק פלטפורמה, אלא אם נכתב אחרת. · Numbers marked *house preset* are the course's defaults, not platform law.

## 1. Editing and delivery · עריכה והפקה
| עברית | English | Meaning |
|---|---|---|
| קאט / חיתוך | cut | a picture or sound edit point; "whole-sentence cuts in natural order" is the house rule for talk |
| רילס | Reels | vertical short video, 9:16 |
| הוק | hook | the first 1-3 seconds that make the viewer stay; works without sound |
| בי-רול | B-roll | cut-away footage or graphics over the speaker; full-bleed and meaning-matched |
| דובר / טוקינג-הד | speaker / talking head | a person speaking to camera |
| כתוביות | captions | burned-in subtitles; they animate **out** as well as in |
| תמלול | transcription | speech to text; Hebrew uses ivrit-ai models |
| מקור | source | untouched input footage (read-only; copy, never move) |
| מוכן | final / delivered | the output folder: finals plus `manifest.json` only |
| טיוטה | draft | a render shown for review; Studio preview first |
| רינדור | render | producing the video file from the composition |
| סבב הערות | notes round | one cycle of feedback and changes |
| קליטה | intake | the question loop that ends in a precise brief (no reference → ask) |
| רפרנס | reference | a video whose style is analysed and transferred |
| מושן / מושן גרפיקס | motion graphics | animated graphics/UI/type pieces |
| טיפוגרפיה קינטית | kinetic typography | animated text as the main visual |
| עדות / המלצה | testimonial | a customer or student review video |
| מודעה / פרסומת | ad | paid social video |
| ממומן / אורגני | sponsored / organic | licence and policy scope of a placement |
| השקה | launch | a product or app launch film |
| אזור בטוח / סייף זון | safe zone | areas of 9:16 free of platform UI (house numbers, to be proven on devices) |
| מאטה / חיתוך דובר | matte / cutout | alpha mask or transparent layer of the speaker |
| תיקון צבע / גריידינג | colour correction / grading | correct first (from the camera original), grade second |
| 2.5D | 2.5D | depth-layered parallax animation of a still |
| רימאקס (החלפת אודיו בלי רינדור) | remux | replace the audio without re-rendering the picture |

## 2. Process and files · תהליך וקבצים
| עברית | English | Meaning |
|---|---|---|
| פרומפט (PROMPT.md) | PROMPT.md | the frame-level spec; **approved before the first line of code** (agent drafts, human approves) |
| DESIGN.md | DESIGN.md | locked palette/type/token table of a project |
| פריסט בית | house preset | a named default (safe zones, −14 LUFS, colour targets, caption font) — a decision, not a law |
| שער איכות | gate | a check with predicate, evidence, action-if-false, owner, recheck; a gate that cannot run says `not_run` |
| נעילת רינדור | render lock | one heavy job at a time on the machine |
| רינדור קטע | segment / range render | render only a range instead of the whole film |
| מניפסט | manifest | file listing which source hash each output was rendered from |
| יומן עלויות וזמנים | ledger | per-project timing and credit record |
| רשימת חומרים (BOM) | bill of materials | file-level list of everything shipped, with licences |
| סקיל | skill | a folder with `SKILL.md` that an agent loads when triggered; procedure data, not permission |
| פרופיל | profile | an optional install bundle (e.g. `asr-vulkan`) with its own manifest |
| בדיקת תקינות (doctor) | doctor | health check that runs real tiny jobs |

## 3. Hebrew typography and RTL · עברית ו-RTL
| עברית | English | Meaning |
|---|---|---|
| ו/ז, ד/ר, ה/ח | look-alike letters | pairs to test at full size in every caption font |
| RTL | right-to-left | never `dir="rtl"` on the HyperFrames root (house rule; not reproduced on 0.8.98); only on text elements |
| bidi | bidirectional text | Hebrew with embedded English/numbers; isolate those spans |
| ניקוד | niqqud | vowel marks; animate words, not letters |
| Rubik | Rubik | default caption family (a default, not a law) |
| פונט מקובץ | font from file | `@font-face` from `hf/fonts/`; the engine does not find fonts by name |

## 4. Audio · אודיו
| עברית | English | Meaning |
|---|---|---|
| LUFS | LUFS | integrated loudness; house master **−14** |
| TP / dBTP | true peak | house limit ≤ −1 dBTP on the final file |
| דאקינג | ducking | lowering the music under speech (house: −10 dB, 80 ms pre, 250 ms post) |
| מיקס | mix | VO + music + SFX on three buses |
| מדידה על הקובץ הסופי | final-file measurement | loudness is measured on the delivered file, not on the mix |

## 5. AI generation and cost · יצירה ועלות
| עברית | English | Meaning |
|---|---|---|
| תמונה לווידאו | image-to-video (i2v) | animate an approved still |
| קרדיטים | credits | a vendor's wallet; never converted to dollars or client fees |
| אישור עלות | cost approval | prior approval with a **dated** estimate before any paid action |
| שער 30 דקות | 30-minute gate | local job ETA over 30 min → propose 2.5D/animatic |
| unlim | unlim | a free-trial "unlimited" flag; the user's call, never added silently |
| MCP | MCP | Model Context Protocol server exposing tools to an agent |
| שרת תיעוד מול שרת הרצה | docs-only vs execution server | the first only returns documentation; the second changes files, accounts or spend |
| נתיב (route) | route | where a job really runs and is billed (API / MCP / CLI / web / aggregator) |

## 6. Speech recognition · זיהוי דיבור
| עברית | English | Meaning |
|---|---|---|
| ASR | ASR | automatic speech recognition |
| WER / CER | word / character error rate | edits ÷ reference words / characters |
| VAD | voice activity detection | cuts non-speech before ASR; reduces hallucination, may delete soft speech |
| הזיה | hallucination | text produced from silence or noise |
| יישור כפוי | forced alignment | assigning times to known words |
| תמלול חוזר להשוואה | back-transcription | transcribe TTS output and diff against the script |

## 7. Legal and security · משפט ואבטחה
| עברית | English | Meaning |
|---|---|---|
| רישיון | licence | the permission and its conditions; installed ≠ redistributable |
| רישיון לא ידוע | unknown licence | **do not use in client work** (decision default Q2) |
| פרטיות / אימון | privacy / training | whether a vendor may use uploaded content to improve its models |
| שחרור דמות וקול | likeness / voice release | written permission to depict a person or clone a voice |
| קוד פתוח ≠ שימוש חופשי | open weights ≠ unrestricted | check checkpoint, territory, revenue terms |
| לא ייעוץ משפטי | not legal advice | every legal page says so, with date and jurisdiction |

## 8. Evidence tags · תגיות ראיות
`[VERIFIED-external]` confirmed against a primary source and re-checked · `[SOURCED-unverified]` one source, not re-checked · `[MEASURED-lab]` measured in the research (the reference machine unless stated) · `[IDEA]` untested proposal · `[RULE-owner]` a rule from the toolkit author's practice (taste; a student's own brief, `DESIGN.md` or `toolkit.toml` overrides it - see `docs/decisions/0002-universal-by-default.md`; "the owner" in these files always means the toolkit author, never the student) · `[PROVEN-internal]` worked in an owner-approved project · `[LOCAL-only]` true only on one machine · `[CONFLICT]` sources disagree.
**unsupported ≠ missing ≠ error** — a profile that cannot run on this machine is `unsupported`; a profile that is not installed is `missing`; something that tried and failed is `error`. None of them invalidates the core.
