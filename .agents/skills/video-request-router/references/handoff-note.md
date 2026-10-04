# Handoff note

Load when writing the note. The note is the only artifact the router produces; the owner skill must not depend on earlier conversation.

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
EVIDENCE:  <listing or JSON the decision rests on>
```

## Rules
- `LOCKED` carries the user's words, not a paraphrase; Hebrew stays Hebrew.
- `STATE.prompt`: `none` (no frame-by-frame spec yet; a `<ledger>`-only PROMPT.md is still intake), `drafted` (`<structure>` exists), `approved` only with a `PROMPT_APPROVED` line in `hf/CHANGELOG.md` or the user's own statement; otherwise `unknown`.
- `OPEN` holds at most one question; more questions belong to `video-brief-intake`.
- Saving the note is optional; if saved: `projects/<name>/_work/handoff.md`, overwrite per handoff, never in `hf/`.

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
EVIDENCE:  hf/PROMPT.md, hf/CHANGELOG.md (PROMPT_APPROVED 2026-10-01), _work/drafts/clinic_reel_v2.mp4
```

## Example B: explicit engine
```
ROUTE:     video-brief-intake   next: pro-video-editor
WHY:       row "launch" | user said: "use Remotion for this one"
PROJECT:   none yet
STATE:     intake=none prompt=none render=none (source: ls)
LOCKED:    "use Remotion for this one"
ENGINE:    Remotion (user-named; gate: licence/company-size terms must be checked; not the v1.0 default)
OVERLAYS:  paid-spend-gate=not needed  video-brief-intake=needed
OPEN:      none
SCOPE:     none stated
EVIDENCE:  user message
```

## Example C: ambiguous, one question
```
ROUTE:     (pending)   next: pro-video-editor OR pro-video-editor
WHY:       raw 90 s clip + "make this better" | user said: "make this better"
OPEN:      "Is this a speaker reel (keep the person talking, add B-roll and captions) or an ad (offer, CTA, hook variants)?"
```
(The router stops after sending the question; it builds nothing.)
