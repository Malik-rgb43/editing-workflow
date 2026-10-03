# Cutout / matte route and layering

Load when: any beat puts graphics or footage BEHIND the speaker. Measured numbers and licences live in `volatile-facts.md` (records M1-M6); this file is the method. Dated 2026-10-02; "d06-th" = distilled 06 talking-head-and-footage.

## 1. Decide first: does a beat need it?
Cut the speaker out ONLY when a beat really puts graphics or footage behind him (text behind the head, a panel with the head crossing its edge, a behind-the-speaker 3D object, a colour drain behind him). A matte of a whole 55 s A-roll took about 35 min on the owner's CPU (native u2net, historical) and sat on the critical path once for about 20 min idle. So: list the beat ranges in `edit_plan.json`, matte those ranges only (plus 2 s handles), and start the job in the background at minute 0, under `render_lock`, never beside a render or ASR.

## 2. Route (decision default Q8)
| Route | Status in the student repo | Why |
|---|---|---|
| MODNet (Apache-2.0), ONNX via CPU or DirectML | shipped, default bundled route | licence-safe; slower and flickers more than RVM in E09 |
| Native `hyperframes remove-background` (u2net_human_seg) | shipped fallback and the control | CPU only on the reference machine's host; slowest; baseline for comparisons |
| RVM MobileNet (GPL-3.0) | OPTIONAL, installed by the user themselves, never bundled or redistributed; internal use until the licence question is resolved | fastest measured route (E09) |
| MediaPipe selfie segmenter | coarse ROI / seed only | confidence mask is not calibrated alpha; hair fails |
| MatAnyone / MatAnyone2 (S-Lab, noncommercial), SAM3 (gated, CUDA), Ultralytics YOLO (AGPL-3.0) | not used for student/client work | licence |
RVM facts that matter: it keeps recurrent state, so RESET the state at every shot boundary and edit join, and run it in sequence (stateless per-frame use changes the algorithm); documented downsample ratio 0.25 for 1080p portrait. BiRefNet (MIT) is an image model: 28.5 s per frame on the owner CPU, not a route for video here.

## 2.1 Cache rule
Key the matte cache by the decoded-content hash or frame index + model + params. NOT by `-ss` packet ranges: an edit test missed 2 of 5 reuses with packet keys (E09). Cold 104.4 s vs identical request 36.1 s (ProRes assembly was 33 s of it) on the 20 s fixture.

## 3. Post-processing (the choke)
Raw alpha -> `alphaextract, erosion x4, gblur sigma=1.8, alphamerge` -> `libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 24 -row-mt 1 -an` (webm), or ProRes 4444 for the intermediate. Why: a grass-green fringe was invisible over the original plate but obvious over a new background and cost ~5 min by hand. When the plate behind is dimmed or blurred, the matte shows (halo, grass through holes): erode x2 + gblur 1.3 on alpha, blur <= 3 px, dim above the cutout only below the chest. Moving hands stay semi-transparent (u2net limit): accept, or avoid hand-heavy moments behind layers. The heavy-job lock must wrap the alpha encode too, not only the matte call.

## 4. Layering and geometry
- Order: plate -> dim/blur -> behind-layer (giant text, cards, windows) -> cutout -> captions -> front UI -> grain, ALL under the same camera rig so depth stays locked (`camera-and-zoom.md`).
- Clear zones for behind-speaker graphics: only x < 380 or x > 700 and y 300-680 at 1080x1920; below that the body swallows them. Measure the head/shoulder geometry on a 100 px grid first. Every "behind" event needs a camera pull-back (scale 0.72-0.8).
- Cutout brightness: +7 % brightness and +3 % contrast over the plate (the owner asked that the person layer be slightly brighter; the numbers are an assistant translation, not an owner quote).
- Cut the matte from the CORRECTED plate (`color-correction-speaker`), not the raw one.
- `check` reports text "occluded" by the transparent full-frame cutout: add `data-layout-allow-occlusion` to EVERY text element including nested `<b>`/`<span>` (not inherited), after the typing spans exist.
- Text-behind-person: a text-bbox vs matte-alpha overlap check was proposed (a "24/7" behind the head, a "01/02" cut at the edge): look at the peak frame of every behind-text beat.
- Matte flicker: compare rendered vs source frame-difference series (`rendered_diff > 1.35 x src_diff + 0.6` = flicker, owner heuristic). A matte updated every third frame produced a periodic face-lift flicker in the colour bake; for the colour matte use every frame + temporal smoothing.

## 5. Quality inspection before adopting a route
E09 judged speed, not quality (edge metrics were against a sparse BiRefNet PROXY, not ground truth). Before trusting a faster route on a student's footage, view keyframes for hair, hands, holes, missed people and motion blur on dark and light backgrounds; a fast run is not a passed run. Open gates: fast-motion test, shot-boundary reset test, human review.

## Sources
d06-th §1.6, §3.1-§3.4, §4 (E09 summary); distilled 03 e09-e12-final-results; blueprint OPEN_QUESTIONS Q8; all checked 2026-10-02.
