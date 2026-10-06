# Handoff note

Load when writing the note. The note and `<project>/_work/connections.json` are the only files the router writes; the owner skill reads both before its first step and must not depend on earlier conversation.

## Format (all fields mandatory; use `unknown`, never blank)
```
ROUTE:     <owner skill>   next: <skill or none>
WHY:       <route-table row id> | user said: "<verbatim quote>"
PROJECT:   projects/<name>/  |  none yet
STATE:     intake=<none|open|locked> prompt=<none|drafted|approved|unknown> render=<none|draft|final> (source: project_state.py | ls | user)
LOCKED:    <decisions the user already made, each quoted>
ENGINE:    HyperFrames (default, Q14)  |  <user-named engine> (gate: licence/scope check)
OVERLAYS:  paid-spend-gate=<needed|not needed>  video-brief-intake=<needed|done>
OPEN:      <at most ONE question that blocks the author, or none>
SCOPE:     <user restrictions: no spend, planning only, read-only source, ...>
CONNECTIONS: <one line per relevant job: use / not needed / fallback>
EVIDENCE:  <listing or JSON the decision rests on>
```

## Rules
- `LOCKED` carries the user's words, not a paraphrase; Hebrew stays Hebrew.
- `STATE.prompt`: `none` (no frame-by-frame spec yet; a `<ledger>`-only PROMPT.md is still intake), `drafted` (`<structure>` exists), `approved` only with a `PROMPT_APPROVED` line in `hf/CHANGELOG.md` or the user's own statement; otherwise `unknown`.
- `OPEN` holds at most one question; more questions belong to `video-brief-intake` (Step 0 of `pro-video-editor`).
- Path: `<project>/_work/handoff.md`, overwritten per handoff, never in `hf/`. No project yet: the note goes in chat, and `pro-video-editor` saves it there right after `new_project.py`.
- `CONNECTIONS` lines come from `<project>/_work/connections.json` (or the presence run, when there is no project yet).

## Example A: resume a locked project
```
ROUTE:     revision-notes-handler   next: render-qa-delivery
WHY:       row "notes on a draft" | user said: "the hook feels slow"
PROJECT:   projects/clinic_reel/
STATE:     intake=locked prompt=approved render=draft (source: project_state.py)
LOCKED:    "45 seconds", "9:16", "no music in the first 3 s"
ENGINE:    HyperFrames (default, Q14)
OVERLAYS:  paid-spend-gate=not needed  video-brief-intake=done
OPEN:      none
SCOPE:     none stated
CONNECTIONS: none needed for notes (from _work/connections.json)
EVIDENCE:  hf/PROMPT.md, hf/CHANGELOG.md (PROMPT_APPROVED 2026-10-01), _work/drafts/clinic_reel_v2.mp4
```

## Example B: explicit engine
```
ROUTE:     pro-video-editor   next: render-qa-delivery
WHY:       row "any production" | user said: "use Remotion for this one"
PROJECT:   none yet
STATE:     intake=none prompt=none render=none (source: ls)
LOCKED:    "use Remotion for this one"
ENGINE:    Remotion (user-named; gate: licence/company-size terms must be checked; not the v1.0 default)
OVERLAYS:  paid-spend-gate=not needed  video-brief-intake=needed (Step 0)
OPEN:      none
SCOPE:     none stated
CONNECTIONS: stock (Pexels) not connected -> own footage; generation not needed
EVIDENCE:  user message
```

## Example C: ambiguous, one question
```
ROUTE:     (pending)   next: video-analysis OR pro-video-editor
WHY:       raw 90 s clip + "תעבור על הסרטון הזה" | user said: "תעבור על הסרטון הזה"
OPEN:      "Do you want a breakdown of this video (cuts, transcript, sound), or an edited version of it?"
```
(The router stops after sending the question; it builds nothing.)
