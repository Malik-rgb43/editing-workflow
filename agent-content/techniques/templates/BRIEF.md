<!--
TEMPLATE: hf/BRIEF.md  (copy into projects/<name>/hf/BRIEF.md at wf-00; delete these comments)

RULES (agent-content/playbooks/wf-00-intake.md):
 - BRIEF.md is FIVE LINES of fact + an intent paragraph. It is NOT the spec.
   The only spec is hf/PROMPT.md (its <ledger> block holds every checkable line). There is no SPEC.md.
 - Every value below must come from the person's message, the files, or a default marked (D) in the ledger.
   Never invent a brand, price, claim, logo or colour.
 - The frontmatter keys are the ones the HyperFrames skills read on the author's builds (workflow / flow / storyboard / type ...).
   Verify the key names on the installed HyperFrames skill version; keys it does not know are ignored.
 - Dates, prices and model ids do not belong here (perishable) — they go in dated reference modules.
-->
---
type: <talking-head | testimonial | ad-promo | motion-graphics | ai-generated | podcast-clip>   # the type skill that owns the work
ratios: <9:16 | 16:9 | 1:1 | 4:5 ...>    # the MASTER first; others are re-layouts (wf-variants)
fps: <30 | native fps of AI takes (usually 24)>
length: <exact seconds, e.g. 45.0>        # ledger LEN; never derived from a multiplier
flow: <automation | companion>            # how the engine skill should work: unattended build vs alongside a human
workflow: <general-video | other>         # which HyperFrames workflow owns the build; check the installed skill list
language: <he | en>                       # language of speech and on-screen text
ledger: hf/PROMPT.md#ledger               # pointer — the spec lives there
---

## Intent (3–6 lines, plain language)
What the viewer should feel or do, who the audience is, what the video is for. Quote the person's own words where they matter.

## Source and rights
- Source files: `source/<...>` (copied, never moved). Camera original present? <yes/no — from `ls`>
- Licences / consent: <see hf/SOURCES.md; consent record for any person on camera or voice>

## Guards (only if the person said "completely new" or listed forbidden things)
- Must NOT appear: <the previous version's moves, a competitor's name, an internal concept name, third-party logos, a revenue total>

## Claims allowed on screen (product facts only)
- <fact — where the person stated it (message id / file)>

## Reference
- <ref-id + the time range that is "the style", or "none">
