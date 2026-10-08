# Rubric: screen demo / tutorial (a screen recording turned into a short tutorial)

> Status: **provisional, derived, unmeasured.** Written 2026-10-08 from `agent-content/playbooks/wf-screen-demo.md` and `tools/screen_zoom.py`. No delivered screen-demo project is behind it yet; its numbers are house defaults, labelled as such.
> Companion files: [critic-brief.md](critic-brief.md) · [visual-review-4-axis.md](visual-review-4-axis.md) · `agent-content/playbooks/wf-screen-demo.md`.

## 1. How to score
Same rules as every rubric (README). Watch it the way a learner would: on a phone, muted first (can you follow from the picture alone?), then with sound (does every spoken step show on screen when it is said?).

## 2. Dimensions (1 / 3 / 5)

| Dimension | 1 - material failure | 3 - usable with repair | 5 - strong |
|---|---|---|---|
| **Meaning / story** | opens on the desktop or on setup; steps in recording order with detours; no visible result | the steps are in order, but it starts slowly or the result comes only at the end | opens on the result or the problem it solves; steps joined by "but / therefore"; nothing a learner does not need |
| **Caption / language** | UI text unreadable on a phone; captions covering the control being shown | readable on desktop only; captions sometimes near the active area | every UI word the voice names is at least 40 px at 1080 width; captions and callouts never over the area in action |
| **Composition / brand** | the whole screen for the whole video; zooms that crop the clicked control out | zooms on the main actions but late, or held too short to read | the active area fills about 60-80 % of the width when it matters; zoom out only when the place changes; every zoom held long enough to read |
| **Motion / edit** | waits and dead time left at real speed; jerky in-out-in zooms | most dead time cut; some zoom moves too fast or too frequent | every dead range of 1 s or more cut or sped (sound off, last 0.5 s at real speed); single eased moves; reversals follow the camera rules |
| **Audio** | voice level jumping between takes; keyboard and mouse noise louder than the voice | voice even, with some noise or long silences | voice levelled and cleaned, silences shortened, no music fighting the explanation (a soft bed at most) |
| **Integrity / continuity** | private data visible (email, tokens, names, other tabs); a step that does not work as shown | private data blurred late or partly | no private data in any frame (checked on the contact sheet); every step shown is the real result |

## 3. Hard gates
| Gate | Predicate | Evidence |
|---|---|---|
| **SD-G1 cue match** | every action the voice names is visible within ±1.5 s, or has a written reason | `_work/zoom_cut.json` `cue_misses` |
| **SD-G2 readable** | every zoom key passes the readability rule (text >= 40 px at 1080 width, magnification <= 2x) | the readability table in PROMPT.md |
| **SD-G3 no dead time** | no dead range of 1 s or more left uncut or unsped | `_work/zoom_cut.json` `dead` list |
| **SD-G4 private data** | no private data in any frame | a contact sheet of the final file, looked at frame by frame |

## 4. Severe failures (block alone)
A password, token, key or personal message visible in any frame; a tutorial step that does not produce the shown result; a zoom that hides the control being clicked.
