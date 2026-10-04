# Patch discipline and the cheap-verification ladder

Load when you are about to change project files for a round, or choose how to verify a fix. Tool names are the course tools in `blueprint/TOOLS_SPEC.md`; flags below come from the author's originals, so check `--help` on the student port before relying on one. Machine-specific numbers: the reference machine, HyperFrames 0.8.98 where stated; other machines unmeasured.

## 1. Patch discipline (G5)
1. Write the patch to a FILE with the editor tool (`projects/<name>/tools/patch_r<N>.json`). Never inline Python with Hebrew or quotes in a shell heredoc (five failed heredocs in one project; 15-20 min of friction).
2. Format and engine: `scripts/apply_patch.py` (see its docstring). `{"file":"hf/index.html","strip_hf_ids":true,"edits":[{"anchor":"<exact old text>","replace":"<new>","expect":1}]}`.
3. Before: close Studio; `grep -n` every anchor; strip `data-hf-id` (the script does it); take the backup (the script does it).
4. Anchors are unique (`expect: 1`) or the whole patch fails with nothing written; overlapping anchors fail.
5. Anchor timing to word cues (`cue("word")`), not frame literals; whole frames only; `max(0, start)`; no negative `data-start` (`grep -c 'data-start="-' index.html` must print 0).
6. After: re-read the file, `hf_preflight --strict` must print 0 errors; warnings fixed or the reason written in CHANGELOG.
7. All of a round's notes go into one patch (or one patch per note, all applied) before any render.

## 2. Verification ladder (cheapest first; stop at the first rung that proves the fix)
| Rung | Tool | Time (order of magnitude) | Proves |
|---|---|---|---|
| 1 static | `hf_preflight` | 2-5 s | structure, timing grid, ids, safe zone |
| 2 look | Studio preview (`python tools/hf_studio.py <project>/hf`); hot reload measured 0.04-0.9 s on 0.8.98 | seconds | position, timing, copy, motion feel |
| 3 stills | `snapshot --at t1,t2,... --describe false` (<= 5 timestamps per call; `--describe false` always) | 1-2 min per pack | a single moment: first frame of a scene, an effect at peak, a keyword at full size. Does not prove cuts or motion |
| 4 segment | `hf_segment --from A --to B --qa` (range snapped outward to whole scenes, picture only) | 2-4 min | render-only risks: `<video>` layers (about 1 frame off in Studio), 3D, filters, cuts |
| 5 critic | the SAME critic continued by message with only the fix list ("verify on the frames, re-score <= 250 words") | minutes | independent reading of the fixes |
| 6 full | ONE full render under the lock, then `frame_qa`, `caption_qa`, `motion_qa`, `face_center`, `color_check` as relevant on the NEW file | 8-13 min observed (4-21) | everything |
A global rule is verified at every occurrence (a segment or a snapshot each). Modelled machine time for a six-note round: about 240 s with Studio-first review vs about 430 s without (E12 model; not a measured saving for you).

## 3. One full render per round
- Collect first ("collecting notes 5 more minutes, then I fix and render"): diagnose and patch while the user types, render segments only.
- Before the render: all reviewers returned, lock free (`render_lock status`), no heavy agent running, Studio closed or ids stripped, assets in.
- Long job (> 3 min): benchmark one unit, one-line ETA in chat, `timeout` (3 x ETA), background with a log and a `STATE` line, heartbeat every ~5 min, watchdog (0 frames after 3 min or no progress for 10 min: kill your own process tree, check the lock, one snapshot, retry once). The user must never have to ask "what about the render?".
- Stale-file guard: QA runs only on a file newer than the render start (`[ "$V" -nt _work/.render_start ]`); never `check | tail && render` (the pipe hides the failure; use `set -o pipefail`).
- Draft files go to `_work/drafts/`; the final folder holds finals and the manifest only.

## 4. Audio-only branch
```
python tools/hf_mix.py "projects/<name>/hf" --report
python tools/hf_deliver.py "projects/<name>/hf" --name <name> --skip-render
```
Fix the cue file (SFX gain, ducking, bed), remix, remux onto the existing raw render: about 1-2 min instead of 10+. `--skip-render` skips the freshness and preflight guards in the original tool: confirm the picture did not change since the raw render was made. Measure length, onset and loudness on the new file (no step above +3 LU at a cut unless asked).

## 5. Traps
| Trap | Cause | Fix |
|---|---|---|
| anchors miss | Studio added `data-hf-id` | strip first |
| killed a render for a late note | no batching | batch; first half stop, second half finish |
| "clean" QA on a failed render | QA ran on the old file | mtime guard |
| a fix verified by a still, broken in motion | a still cannot prove motion | segment render rung 4 |
| unrelated frames changed | a patch touched more than intended | compare outside the fixed range (`seg_diff` when available) |
