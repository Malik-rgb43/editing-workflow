# Board spec, manifest and choices.json

Load when writing `spec.json`, building the board, or reading a `choices.json` back. Engine: `scripts/make_board.py` (stdlib). Working example: `references/sample-spec.json`.

## 1. Commands
```
python scripts/make_board.py build spec.json --out <dir>     # -> <dir>/visual-choice-board.html + board_manifest.json
python scripts/make_board.py serve <dir> [--port 0] [--timeout 3600] [--open]   # default readback: exits with the verified picks
python scripts/make_board.py verify <dir>/board_manifest.json choices.json [--json]
python scripts/test_make_board.py                             # 13 tests, no network, no browser
```
Build is deterministic: the same spec gives the same `board_id` (the build time is stored but not part of the id). Measured on the reference machine, 2026-10-02: the sample spec (6 decisions, 20 options, no embedded fonts) builds to 37,753 bytes in about 17 ms. Embedded fonts or a still make the file larger (E13's research board with 8 embedded fonts was 2.1 MB; unmeasured for yours).

## 2. Spec (schema_version 1)
| Key | Rule |
|---|---|
| `project`, `title`, `text` | required; `text` is the user's REAL line (placeholder text such as "lorem ipsum" is refused); `title` is shown in the page |
| `lang` | `he` (UI right-to-left) or `en`; the page chrome follows it, each sample text uses `dir="auto"` so mixed Hebrew/English/numbers shape correctly |
| `keyword` | optional; a word from the real text for the look-alike specimen; default: the longest Hebrew word that contains ו/ז, ד/ר or ה/ח |
| `still` | optional path (relative to the spec) to a JPG/PNG/WebP frame, embedded as a data URI (limit 2.5 MB); private client stills stay on this machine; never upload |
| `banned` | animation/transition names refused for this project; default `["bounce","crossfade"]` (owner banned list); set it from the project's DESIGN.md |
| `safe_zone` | `{top,bottom,left,right,canvas:[W,H],rail_bottom,label}`; default is "house preset v1" (300/672/140/192 on 1080x1920, caption rail <= y 1450): unverified pixels, shown as a preset not a platform law |
| `decisions[]` | 1 or more; ids `[a-z][a-z0-9_]*`, unique |
| `decisions[].kind` | `font`, `caption_anim`, `easing`, `palette`, `transition`, `layout`, `text` |
| `decisions[].options[]` | 2-12 per decision (8-12 is the target; fewer than 3 prints a warning that chat may be faster); option `id` `[A-Za-z0-9_-]{1,20}`, not `none`; `label` required |

Option fields by kind:
| kind | fields | preview shows |
|---|---|---|
| `font` | `family` (plain name), `weight`, `fallback` (`sans-serif`/`serif`/...), optional `font_file` + `license` (embedded as base64; `license` is mandatory with a file; <= 3 MB) | the real text in the face, a large keyword specimen, the six look-alike letters, a chip "embedded" or "system font: may fall back" |
| `caption_anim` | `anim` in `rise slide_up blur_in scale_in word_rise karaoke mask_wipe` (`bounce` exists only so it can be refused) | the real text animating in, holding, and out (exit mirrors entrance) |
| `easing` | `bezier` [x1,y1,x2,y2] (x in 0..1), `duration_ms` 100-4000 | the real text sliding in with that curve, the curve drawn, the CSS string |
| `palette` | `colors` {bg,text,accent} as hex | the real text on the palette, swatches, text/background contrast ratio (flag below 3:1) and accent ratio |
| `transition` | `trans` in `wipe push iris slide_up` (`crossfade` refused by default), optional `color_b` | A to B on a loop (still or dark plate as A) |
| `layout` | `caption_y_pct` 0-100 | the caption on the phone frame with the safe zone (green dashed) and the caption rail limit (red dashed); a warning chip when the caption would sit under the rail |
| `text` | `text` | a hook or headline variant in the phone frame |

## 3. What the page does (and what it refuses)
- Self-contained: no remote font, script, image or request (the builder scans its own output and aborts if it finds one); works offline by double click; fonts and the still are data URIs.
- Per decision: tab (arrow keys, Home/End, direction-aware in RTL), option cards (radio buttons; digits 1-9, 0, q, w pick; `n` = none), a reject toggle, a comment box, and a "none of these" slot that requires a comment.
- Typing in the text box or a comment never triggers a shortcut. Selection does not rebuild the DOM, so keyboard focus stays where it was.
- Pause switch and `prefers-reduced-motion` stop every animation; the page shows the final state.
- The confirm button ("אישור הבחירה ✓" / "Confirm my picks ✓") is refused until every decision has a pick or a commented "none". Served by `serve`, it POSTs the picks to the server (same origin, per-run token, Origin check, 1 MB cap, a Content-Security-Policy that blocks any other request) and shows "sent"; the file on disk never contains that network code. Opened as a plain file, it saves `choices.json` and shows the JSON in a text box (copy button) for hosts that block downloads.
- User text is written with `textContent`; HTML-looking text stays inert.
- Not included in v0.1: ranking, a hosted-page readback adapter.

## 4. choices.json (written by the page)
```json
{"schema_version": 1, "board_id": "964f986e7a255061", "project": "sample_reel", "exported_utc": "...Z",
 "session_elapsed_ms": 17806, "sample_text": "...",
 "decisions": {"font": {"choice": "A", "none": false, "comment": "", "rejected": ["C"]},
               "anim": {"choice": null, "none": true, "comment": "something calmer", "rejected": []}},
 "assets": {"fonts": [{"option": "font/A", "file": "...", "sha256": "...", "bytes": 0, "license": "..."}], "still": null}}
```
`verify` checks: schema version, board id equals the manifest's (a wrong or rebuilt board is refused), every decision answered and none unknown, choices are real option ids, `none` has a comment, a choice is not also rejected, embedded asset hashes match. It prints one decision line each, e.g. `font = Arial 800 (option A)`; the agent states these lines to the user.

## 5. After the readback
1. Quote the decision lines to the user in one message.
2. Add ledger rows (`src` U; `said` = the board pick; `spec` = the measurable value: font file and weight, easing control points and duration, hex palette, caption y in px) and write the palette/fonts/motion tokens into DESIGN.md and PROMPT.md before any code. A reject becomes a banned-list candidate.
3. A browser preview is not the final engine render: re-render one still or sample frame in the real engine, and for fonts check the keyword's look-alike letters at full size in that render.
