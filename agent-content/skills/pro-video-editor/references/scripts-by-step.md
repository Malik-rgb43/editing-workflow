# Which script, when

Load when you are about to check a plan, a composition or a claim in Steps 3-5, or when a step names one of the scripts in `scripts/`.

Stdlib, `--self-check`, Usage in each docstring. They check numbers and text, never appearance.

| Step | Script | What it checks |
|---|---|---|
| 3 (speaker edit) | `plan_lint.py` | the edit plan: cut and zoom cadence, cover margins, a scale change on A-to-A joins, overlay width |
| 3 (testimonial) | `soundbite_score.py` | ranks your scored soundbites into the hook, the close and the body |
| 3 and 5 (testimonial, claims) | `claims_check.py` | the consent record and every quote against the source words, hedges and numbers |
| 3 (before a spend) | `check_route_freshness.py` | a dated reference is still fresh before a price or route decision |
| 3 (local generation) | `route_gate.py` | the local ETA per shot against the 30-minute limit |
| 3b | `storyboard_board.py` | the board: check, grab real frames, serve, read the answer (it shows images, it does not judge them) |
| 4 (AI takes) | `probe_takes.py`, then `cutlist_check.py` | fps, colour tags and VFR/HDR flags of each take; then clean windows, no reverse, artifacts covered, native fps |
| 4 (every patch) | `seek_safe_scan.py` | composition state that cannot be seeked (clocks, random, rAF, loops, transitions) |
| 4 and 5 | `palette_audit.py` | every colour in the composition against the one locked DESIGN.md palette |
| 5 (text, CTA, price, logo) | `safe_zone_check.py` | each box against the safe-zone preset; passes only with an overlay snapshot you looked at |
