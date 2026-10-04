---
module: hyperframes-traps
checked_at: 2026-10-02
expires: "immediately on any change of the pinned HyperFrames, browser, FFmpeg, Node or OS version; otherwise 2026-12-31"
confidence: "owner-observed traps [PROVEN-internal][LOCAL-only] on CLI 0.8.79-0.8.93; vendor rows [SOURCED-unverified]; none re-tested on 0.8.98 except where marked"
refresh: "run the regression fixtures in section 4 on the pinned build (local, free, ASCII path); hyperframes doctor / --version / lint / check are non-spending"
---

# HyperFrames, headless Chrome and FFmpeg traps — dated reference

| Field | Value |
|---|---|
| Fact set | symptom → cause → fix → prevention for known engine failures; lint/check code meanings; Windows issues; privacy surfaces; regression fixtures |
| Versions / ids | research pin **HyperFrames 0.8.98** (Node ≥ 22); owner observations on CLI 0.8.79-0.8.93, 2026-09-27 to 2026-09-30; Chrome Headless Shell 152.0.7977.30 (E01); GSAP 3.14.2; FFmpeg 8.1 full build |
| `checked_at` | **2026-10-02** (= research date; **must be refreshed before use**) |
| Source | `distilled/04-…/hyperframes-traps.md`; `distilled/03-…/e09-e12-final-results.md` (E12); E01 report |
| Scope / plan / region | one reference machine / Hebrew-named folders. Many rows are `[LOCAL-only]` |
| Confidence | **every trap is a scoped historical report, not a current limitation, until a minimal reproducer passes on the pinned build** |
| `expires` | see front matter |
| Non-spending refresh | build the fixtures in section 4 in an ASCII directory (e.g. `<ASCII work root>/lab/<name>`), run on the pinned build, record settings and result; promote a trap to "current limitation" only after a reproducer; retire a workaround only after the paired fixture passes |

**Wording rule for lessons:** "reported on the author's 2026-09-28 setup; regression pending on the pinned build". Never "HyperFrames cannot …".

## 0. Never-break rules (owner) — keep them even when a trap does not reproduce
1. **ASCII work root.** `npx hyperframes init` silently skips `index.html` under a path with Hebrew characters (`lint`, `check`, `render` work there). Use the scaffold tool, which inits in an ASCII temp directory and moves the project; verify `index.html` exists. `[PROVEN-internal]` `[LOCAL-only]` (0.8.79, never reported upstream; not a general Unicode finding).
2. **No `dir="rtl"` on `<html>` or the composition root.** Use `lang="he"` on `<html>` and `direction:rtl` only on text elements; lint code `html_dir_attribute_breaks_render`. **`[CONFLICT]`: E12 could not reproduce a black render on 0.8.98.** Keep the rule (cheap to obey) and re-test per version; never teach "root RTL is invalid HTML" (W3C recommends root `dir=rtl` for RTL documents — an engine-specific workaround). `[PROVEN-internal]` `[MEASURED-lab]`
3. **Fonts from files.** `@font-face` from `hf/fonts/`; the engine's Chrome did not find fonts by installed name on the reference machine (vendor docs say supported/Google/installed fonts are embedded at build time — `[CONFLICT]`; the deterministic rule is a shipped file).
4. **`hyperframes snapshot --describe false`, ≤ 5 timestamps per call.** Otherwise frames can go to Gemini when a key exists; longer lists time out. `--describe false` disables only that branch, not remote fonts or asset URLs.
5. **One heavy job at a time** (render, check, snapshot, Blender, ASR, matte) via the render lock; a render next to another heavy job took 21.5 min instead of 11.5.
6. **Studio-first review; range renders; one full render per round; every-frame QA on the final render.**

## 1. Failure catalogue
Status: **H** historical owner report, **V** vendor documentation, **L** lint/check code, **R** vendor issue report.

### 1.1 Project creation, paths, fonts
| Symptom | Cause | Fix | Prevention | Status |
|---|---|---|---|---|
| `init` makes no `index.html`, no error | Hebrew characters in the path | init in an ASCII temp dir and move | scaffold tool; verify the file; keep failed logs | H 0.8.79 `[PROVEN-internal][LOCAL-only]` |
| text in a fallback font | installed fonts not found by name | local file + `@font-face` in `hf/fonts/` (or a web-kit link) | confirm in a snapshot; lint `font_family_without_font_face` | H 2026-09-27 |
| Hebrew word misread ("לבזבז" → "לבובו") | display font with look-alike letters (ו/ז, ד/ר, ה/ח) | check at full size; change the font | keyword look-alike test per font (see `hebrew-rtl-captions.md`) | H 2026-09 |
| built-in transcription is bad Hebrew | `init` auto-transcribes with `small.en` | `--skip-transcribe`; Hebrew via ivrit-ai (see `asr-routes.md`) | — | H |
| un-bundled Google font works locally, fails on Lambda | fonts fetched at build time **fail closed** in distributed renders | embed your own `@font-face` | do not rely on local fonts for cloud | V |
| paths with non-Latin-1 characters broke preview/download/audio | older bug, fixed upstream (#3979, #3983, #1063 closed) | update CLI | — | R |

### 1.2 Renderer: layers, 3D, media
| Symptom | Cause | Fix | Prevention | Status |
|---|---|---|---|---|
| parent `visibility`/`overflow`/3D has no effect on `<video>`/`<img>` | media composited in their own layer | time them via their own `data-start`; image on a 3D card = CSS `background-image` | preflight warning | H 2026-09-29 |
| `preserve-3d` ignores `overflow` clip; opacity flattens 3D; `backface-visibility` pops at ±90° | CSS 3D semantics in capture | fade leaves, not the 3D parent | preflight | H |
| progress bar got another element's CSS | duplicate `id` | unique ids (prefix with composition id) | preflight error | H |
| logos never appear after re-timing | stale timing grid (`F(n)` literals, sub-comp START ≠ host start) | anchor tweens to cues; re-run preflight after any re-cut | preflight | H 2026-09-30 |
| graded clip's first frames ungraded | shader grade has no pre-roll | pre-roll ≥ 6 frames under the top layer, or **bake the grade in FFmpeg** | — | H |
| partial render fails "captured 0 of expected" | media outside range was parked, not removed | delete out-of-range media in the segment composition | coverage gate | H |
| `check` says text "hidden" behind a transparent cutout | cutout occludes the text box | `data-layout-allow-occlusion` on **every** text element incl. nested spans (not inherited) | — | H |
| false `content_overlap` on tilted cards | projected boxes grow | `data-layout-allow-overlap` per element (not inherited) or `data-layout-ignore` | — | H 2026-09-28 |
| `tl.set` toggles on glyph spans that are direct flex children never show | capture ordering for flex children | absolutely-positioned layers toggled by opacity, or nest spans | — | H 2026-09-28 |
| slow capture; encode killed at 600 000 ms (4.3 fps vs ~19) | many `backdrop-filter` pills alive the whole film | `visibility:hidden` outside the time window; `FFMPEG_ENCODE_TIMEOUT_MS=3600000` | avoid whole-film backdrop-filter/large blur | H 2026-09-29 |
| shader transition: dark fringes, missing thin lines | html2canvas pipeline differs from CSS | no `transparent` in gradients, none thinner than 4 px, no `var()` on captured elements, `data-no-capture` for the rest | — | V |
| banding in dark full-screen gradients | H.264 compression | radial/solid fill, localised glow | — | V |
| engine `motionBlur` does not blur video content; forces PNG (~600 ms/frame at 1080p) | by design | use the motion-blur component or a transition | — | V v0.8.45 |
| many `<video>` of one heavy source (22 clips, 60 fps) starve fonts/images; snapshot navigation timeout | browser stalls | pre-cut **one** continuous 30 fps file (trim+concat, GOP 15); convert heavy plates to JPG/WebP | — | H |
| `.mov` > 5 GB makes tools slow/crash | file size | work from a proxy | — | `[RULE-owner]` |

### 1.3 GSAP and timing (frame-exact or it is a bug)
| Symptom | Cause | Fix | Prevention |
|---|---|---|---|
| whole video 2 frames late | a **negative `data-start`** on any clip shifts every clip | `max(0, …)` | `grep -c 'data-start="-' index.html` must be 0 |
| one black frame at each scene cut | `data-start`/`data-duration` rounded to 4 decimals | write `f/30` to **6 decimals** + 0.0005 s overlap | preflight |
| state change on a cut lands 1 frame late | `f6(n/30)` rounds just above frame n | put the change at `start − 0.005` | per-cut check at c−1..c+2 (one spike = in sync; two spikes 1-2 frames apart = out of sync; `frame_qa` flags "double jumps") |
| word pops at clip end | entrance re-asserts opacity 1 after the exit | clamp the entrance to finish before the exit | — |
| element visible from clip start | `fromTo` whose from-state is opacity 1 (immediateRender) | separate `fromTo` opacity 0 → 1 | — |
| black frame at a filter tween | `filter` from `none` to `brightness(0.9)` starts at brightness(0) | `fromTo` with full values (`blur(0px) brightness(1)`) | — |
| black outside an iris/reveal | clip ended at the start of the reveal | keep the previous scene alive until its fade-out ends | overlap clips |
| JS layout wrong for a not-yet-active clip | `getBoundingClientRect` returns 0 at build time | layout without measurement | — |
| sub-comp entrance wrong after seek-back | `gsap.from()` snapshots start state at registration | `gsap.fromTo()` | V |
| layout properties stutter | compositor snaps `left/top/width/height/letterSpacing/fontSize` to pixels | transforms (`x`,`y`,`scale`) | lint `gsap_non_transform_motion` |
| camera glitch at a tween joint | overlapping tweens or stitched eases | ONE spline path per scene | `[RULE-owner]` |

**Snapshots do not prove cuts; only a render does.** `check`/`lint` passing does not prove a correct render or correct Hebrew (`check` samples 9 grid points; a lint error silently disables the layout/contrast audits; `sweep_static` fails a frozen timeline).

### 1.4 Audio
| Symptom | Cause | Fix | Prevention |
|---|---|---|---|
| render audio ~11.5 dB low (−25.5 instead of −14 LUFS), once | render attenuated a premixed `<audio>` **(not reproduced later: −14.7)** `[CONFLICT]` | mux the mix / loudnorm; measure the final file | always measure the **final** file |
| two-pass loudnorm falls back to dynamic; LRA 1.9 | raw mix peaks above 0 dBFS | pre-limit `alimiter=limit=0.56` before both passes (LRA 3.4) | — |
| final video 2-3 frames short | limiter + loudnorm shortened the mix by ~0.07 s; `-shortest` cut the picture | pad to `dur × SR` samples after loudnorm | fixed in the mix tool |
| whole render silent | `<audio>` without id | add id | lint `media_missing_id` |
| volume tween ignored | a `data-automation` lane wins | one mechanism per track | lint `audio_volume_double_automation` |

### 1.5 Output and encoding
| Symptom | Cause | Fix | Prevention | Status |
|---|---|---|---|---|
| last 8 columns black (x 1072-1079) at width 1080, all modes, also plain FFmpeg `gbrp` | encoder issue at widths not divisible by 16 | author `data-width="1088"` + `data-deliver-width="1080"`, `html,body{width:1088px!important}`, `#root{width:1080px!important}`; deliver step crops (libx264 CRF 14) and its verify fails on an edge band; in FFmpeg chains `pad=1088:1920:0:0` before gbrp, `crop=1080:1920:0:0` at the end | edge-band check in delivery; ≥ 24 px bleed under blur/scale entries | H 2026-09-28 `[LOCAL-only]`. **Re-tested on 0.8.98 (2026-10-04, a real 20.8 s talking-head, the reference machine):** at 1080 the final failed verify (`dead_edge`, ratio 0.00); with root `data-width="1088"` + `data-deliver-width="1080"` but the A-roll layer only 1080 wide, the first ~2 s still had a dark strip (the video layer was drawn short until a zoom covered it); with the full-bleed layer ALSO 1088 wide, `hf_deliver render` cropped to 1080 and verify PASSED. `hf_deliver` implements the crop since 2026-10-04 (before, the rule was only documented) |
| unwanted HEVC 10-bit HDR output | source tagged BT.2020 PQ/HLG switches the whole render | `render --sdr`; check sources with ffprobe | `[VERIFIED-external]` |
| `--gpu` (AMD) output differs/blocks | `h264_amf` with CQP; HLS rejects `--gpu`; hardware HEVC writes no HDR metadata | drafts only; master in x264 | #1079 |
| alpha lost in webm/mov | opaque page background | transparent background; check over a checkerboard | V |
| `--browser-timeout` wrong | **unit is seconds**; `--protocol-timeout` and `--player-ready-timeout` are ms | pass the right unit | V |

### 1.6 Windows / AMD environment `[LOCAL-only]` unless noted
| Symptom | Cause | Fix | Status |
|---|---|---|---|
| normal render rejected by the disk gate (~16 GB/min RGBA estimate) | #4060 (open, ~0.8.40) | `--workers 1`, `--low-memory-mode`, free disk, `HF_CAPTURE_PARALLEL_STREAM=true`, move `--frames-cache-dir` | R; unknown on 0.8.98 |
| `spawn EBUSY` | antivirus locks ffmpeg.exe; no retry (#4058) | rerun; inference: exclude `~/.cache/hyperframes` from the scanner | R / `[IDEA]` |
| transparent first frame per worker shard | #4435 (0.8.72) | `--workers 1` for transparent renders | R |
| 6+ workers on one GPU fall back to screenshot capture (~2× slower) | #4584 (Linux report) | read the render-summary second line; `--workers 4` | R |
| `check`/snapshot hang > 10 min after a stop | orphan `chrome-headless-shell` | kill **your** process tree, rerun once; `timeout 900` on check | H |
| Navigation timeout 10000 ms with `data-color-grading` preset on `<video>` (0.8.82) | grade shader hangs on this AMD stack | **bake the grade in FFmpeg**; remove the attribute; `--no-browser-gpu` if a shader remains | H `[LOCAL-only]` (later hardware-render fix noted on 0.8.86+) |
| WebGL in headless Chrome with `--browser-gpu` stalls | AMD stack | one-second segment test in delivery mode before committing a three/WebGPU scene | H |

### 1.7 CLI, privacy, updates
| Risk | Cause | Fix |
|---|---|---|
| skills updated without consent | `init` checks skills against GitHub; `--skip-skills` ignored in 0.8.98 | `HYPERFRAMES_SKIP_SKILLS=1`; pin and snapshot skills |
| client frames sent to Gemini | `snapshot` AI description when `GEMINI_API_KEY`/`GOOGLE_API_KEY` exists | `--describe false` always |
| telemetry; `feedback` posts to a **public** channel | anonymous counters | `HYPERFRAMES_NO_TELEMETRY=1` (+ `DO_NOT_TRACK=1`) or `telemetry disable`; strip paths, user and project names from feedback |
| silent upgrade changes output | unpinned `npx`; scaffolded pin never advances | `upgrade --check`, bump with `upgrade --project .`, name old/new version; a passing `check` is not frame identity |
| remote assets/fonts at render | separate network surfaces | local fonts/media; full isolation is **not verified** (no OS trace) |
| registry install fails offline | `add` fetches item files every time | freeze selected item files and hashes in the project |
| `doctor --json` exits 0 when broken | by design | gate on `jq -e '.ok'` |

Toolchain pins: `HYPERFRAMES_SKIP_SKILLS=1` · `HYPERFRAMES_NO_UPDATE_CHECK=1` · `HYPERFRAMES_NO_TELEMETRY=1` · exact browser executable · extraction cache dir. `[VERIFIED-external]`

## 2. Lint / check codes (what they mean)
| Code | Level | Meaning |
|---|---|---|
| `standalone_composition_wrapped_in_template` | error | standalone root must not be in `<template>` |
| `subcomposition_root_styled_by_class` | error | style the sub-comp root by `#root` |
| `subcomposition_blanks_before_host` | warn | full-bleed sub-comp shorter than its host goes blank |
| `gsap_css_transform_conflict` | error | CSS initial transform + GSAP tween on the same property |
| `gsap_animates_clip_element` | error | never tween `display`/`visibility`/`autoAlpha` on `.clip` |
| `gsap_timeline_registered_before_async_build` | error | register after the async build |
| `gsap_non_transform_motion`, `gsap_repeat_ceil_overshoot` | lint | layout property tweened / use floor not ceil |
| `media_missing_id`, `media_crossorigin_breaks_preview`, `video_nested_in_timed_element` | error | ids required; no `crossorigin`; time the wrapper **or** the video |
| `audio_volume_double_automation`, `duplicate_audio_track` | lint/warn | one volume mechanism; one `<audio>` per overlapping track index |
| `root_composition_missing_duration_source` | error | Three.js / infinite CSS: set root `data-duration` |
| `font_family_without_font_face` | warn | named family without an in-file `@font-face` |
| `html_dir_attribute_breaks_render` | error | `dir` on `<html>` |
| check: `content_overlap`, `escaped_container`, `panel_out_of_canvas`, `canvas_content_at_edge`, `caption_zone_collision`, `text-clipping`, `primary-offscreen` | perception | layout audits |
| check: `sweep_static` | fail | 3 s+ composition with zero geometry change: keep one element animating |
| check: `motion_*` | sidecar | appears late / out of order / off frame / frozen / selector missing |
Escape hatches change what `check` can see: `data-layout-allow-overflow` (**inherited**), `-overlap` (not inherited), `-occlusion`, `-caption-zone`, `-ignore`, `data-layout-bleed="true"`. Apply the narrowest opt-out. `[SOURCED-unverified]`

## 3. Measured render facts (E11, HyperFrames 0.8.98, the reference machine, single passes) `[MEASURED-lab][LOCAL-only]`
Heavy 40 s (1,200 frames): 1 worker 132.6 s; 2: 113.5; 4: 92.8; **8: 88.1**; auto 91.1. Average CPU use 2-3 of 16 logical cores — **capture is the bottleneck**. Browser GPU −8% to −12%; 720p CSS-scaled proxy −20%; `--gpu` AMF encode and draft quality no gain. 12 s fixture: HyperFrames 0.8.98 cold 44.262 s / warm 42.3 s, peak RSS ~1.7 GiB (E01). Preview vs render: `<video>` layers differ by ~1 frame; 3D, shader, per-glyph `tl.set` no deviation beyond baseline (MAD 2.1, SSIM 0.98). Six-note review round (E12): full render per note 430 s; range drafts + one final 240 s; audio-only note 1.8 s.

## 4. Regression fixtures (proposal; none executed on 0.8.98 except as noted)
| Fixture | Must show |
|---|---|
| Hebrew-path init | init in a Hebrew vs ASCII path; presence of `index.html`; also Hebrew username/TEMP, Unicode filenames, spaces, long paths |
| Root RTL | `<html dir="rtl">` vs element-scoped `direction:rtl`, snapshot **and** render (E12: no black render on 0.8.98) |
| Width 1080 vs 1088 | plain grey composition at each width in every quality/GPU mode; compare with a plain FFmpeg chain |
| Integer-frame cuts | intended integer frame vs actual cut; compare c−1..c+2 |
| Negative `data-start` | prove the global shift on the pinned build |
| Audio attenuation | premixed `<audio>` vs mux; duration, loudness, clipping |
| Grade hang | grade vs none, one vs many video sources |
| GPU matrix | default capture, `--browser-gpu`, `--gpu` one at a time |
| Alpha chunk boundary | multi-worker transparent render |
| Snapshot vs render | video cut, VFX canvas; first/middle/last/boundary frames |

Lesson wording rules: "lint/check passed, therefore correct" — dropped · "unversioned `npx` + auto-updating skills in reproducible fixtures" — dropped · "`--skip-skills` prevents skill changes" — dropped · "snapshot always sends frames externally" — changed (depends on an API key; `--describe false`) · "`--gpu` is always only for drafts" — changed (encoder GPU and browser GPU are independent; evaluate output). `[SOURCED-unverified]`

## 5. Conflicts
`[CONFLICT]` fonts (vendor vs owner measurement) · audio attenuation (not reproduced) · root RTL (E12) · vendor "exit animations banned except the last scene" vs owner captions that animate out (**owner rule wins for owner work**; the vendor rule belongs to its transition harness).

## 6. Generalises to students vs local-only
Generalises: timing traps (negative start, rounding, immediateRender, filter from `none`), media-layer behaviour, audio mux/loudness, lint codes, privacy opt-outs, the regression-fixture method. `[LOCAL-only]`: Hebrew-path init, the width-1080 band, the colour-grading hang on this AMD stack, AMF behaviour, the Windows issue set, scanner/EBUSY, process-kill commands.
