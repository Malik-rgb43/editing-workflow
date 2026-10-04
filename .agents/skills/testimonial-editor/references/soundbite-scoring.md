# Soundbite scoring, selection and interview technique

Load when: step 2 of the procedure (after the transcript is hand-corrected), or when briefing the client for a new recording. Source: distilled 02 video-types §4.4 (2026-10-01). The arithmetic is in `scripts/soundbite_score.py`; this file is the judgment.

## 1. Procedure
1. Transcribe locally with word timestamps (forced Hebrew); read the WHOLE transcript; hand-fix names, numbers, brand words. Do not run an LLM rewrite over it.
2. Split into sentences using the word times. A sentence is the unit: never score a fragment that changes meaning when isolated.
3. Score every sentence 0, 1 or 2 on:

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| `specific` | vague ("a lot") | a time or a rough size | a number, an amount, a time ("40K to 100K in six weeks") |
| `emotion` | flat | some warmth | the face carries it (relief, disbelief, pride) |
| `contrast` | one state only | implied before/after | explicit before to after in the line |
| `standalone` | needs the question to make sense | partly | makes sense heard cold |
| `provable` | nothing to show | a photo or partial | a screenshot/photo exists that matches the words |
Add `objection: true` (+2) if the line kills an objection (price, "another course", zero experience, "it won't work for me").
4. Run `soundbite_score.py`. Selection defaults: hook = highest `specific + standalone` (ties: provable, then total); close = highest `emotion`; body = the best of the rest by total, ordered by the editor as before, turn, result. Take the 3 hook options to the user.
5. Put the timecoded paper edit and the 3 hook options in `hf/SCRIPT.md`. Log every reorder with the reason it stays true in context.

## 2. Rules that protect meaning
- Never splice sentences so that the combined meaning differs from what the person said. Never AI-generate a client, a voice or a result.
- A reorder is allowed only when every statement stays true in its new context (for example moving the result sentence first is fine if the result statement does not refer back to "it" defined earlier).
- A cut at a word boundary with no pause is covered (J/L cut, punch-in or proof insert); the 0.40 s pause rule applies only to silence INSIDE a kept segment.
- A hook line may run to about 4.5 s if the number lands by 3 s and is on screen from frame 0.
- `specific = 2` with `provable = 0` is a flagged risk: ask the client for the matching proof; until then show the claim only as a typographic callout in quotes (the script lists these as `needs_proof`).
- A hook with no specific number is not an excuse to invent one: open on a pain or a twist.

## 3. Worked example (synthetic)
| id | line | spec | emo | contr | alone | prov | obj | total |
|---|---|---|---|---|---|---|---|---|
| S1 | "Last month I closed 500K in the store." | 2 | 0 | 0 | 2 | 2 | no | 6 |
| S2 | "I cried when I saw the number." | 0 | 2 | 1 | 1 | 0 | no | 4 |
| S3 | "I did not believe another course would work." | 1 | 1 | 2 | 2 | 0 | yes | 8 |
| S4 | "I went from 40K to 100K." | 2 | 0 | 1 | 1 | 0 | no | 4 |
Hook = S1 (specific + standalone = 4, provable 2); close = the emotion line; S3 is the best body line (objection killer); S4 gets a `needs_proof` warning. The table is the audit trail the user can read in one glance; keep it in the project.

## 4. Interview technique for the client brief (research, `[SOURCED-unverified]`, distilled 02 §4.4)
Ask the speaker to repeat the question inside the answer so each soundbite stands alone; order easy, before, why you chose it, how it was, the result, "what would you say to someone hesitating?"; a conversation, not a script; end with "anything else?". For remote selfies: vertical, face to a window, not in a moving car, 30 fps, original file. These raise `standalone` and `specific` before you ever open the editor.
