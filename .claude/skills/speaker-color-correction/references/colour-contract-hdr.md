# Colour contract, HDR and log sources

Load when: the source is an iPhone/HDR clip, a log or full-range file, mixed cameras, or any clip whose tags look wrong. Everything here is a CANDIDATE design from documentation and a static code audit (T12); nothing in this project was run on HDR material. Dated 2026-10-02; sources: distilled 04 colour §0, §4; T12 via that file.

## 1. What the author's tools assume
The inspected renderer assumes limited-range BT.709: it converts range and YCbCr matrix, then tags 709. It has no transfer linearisation, no BT.2020 -> 709 primary conversion, no HDR tone map and no Dolby processing. `color_scopes` probes dimensions only and decodes uint8 `yuv444p`. So a student with phone footage must handle the contract first, or the numbers in the gate describe a wrong picture.

## 2. Probe every input (and sample frames, not only the stream)
`ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,pix_fmt,color_range,color_space,color_transfer,color_primaries,side_data_list -of json <file>`. Record rotation, fps (rational), range, matrix, transfer, primaries. Mixed clips need per-segment handling. Missing or contradictory metadata -> an explicit override with provenance in the grade JSON plus a preview, never a silent 709 assumption.

## 3. Input -> route (T12 candidates; stop/review conditions)
| Input | Route | Stop and review when |
|---|---|---|
| SDR 709 limited | range/matrix decode to a named working representation; the author fit | tags disagree with the frames, or the file is full range |
| Full-range SDR | explicit full -> working range, once | double expansion |
| Camera log / raw | camera-specific documented input transform | unsupported camera or white balance |
| HLG BT.2020 | declared HLG linearisation, reference condition, tone map, gamut map to an approved SDR | no reference condition |
| Dolby Vision profile 8.4 | RPU-aware candidate AND a separately labelled HLG-base fallback | RPU decoding absent; no trusted SDR reference |
| Graphics / CG | named asset encoding and premultiplication; output view once | the output view is already baked |
Source switch to remember: a source tagged BT.2020 PQ/HLG makes HyperFrames render HEVC 10-bit HDR; use `render --sdr` for social deliverables, and the engine's realtime grade path is Rec.709/SDR only.

## 4. FFmpeg facts that matter
- `tonemap` algorithms operate on single-precision float LINEAR light; `zscale` supplies transfer/range/primary conversion and needs a build with libzimg. A commonly documented candidate chain (NOT run here; test on your own clip and view before/after): `zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p`.
- libplacebo can apply a Dolby Vision RPU when present; its documented DV output is BT.2020 + PQ, so request and validate SDR output explicitly. "FFmpeg always ignores Dolby metadata" is wrong, but side-data availability and the compiled filter must be tested.
- `waveform`, `vectorscope`, `histogram` and `signalstats` give numeric/visual diagnostics.
- Apple Dolby Vision 8.4 is HLG-compatible Main10 with BT.2020 signalling; a generic HLG-base conversion does not prove the Dolby look. Compare a trusted SDR export (Apple/Resolve) against the FFmpeg candidates under the same reference conditions; no winner is claimed.

## 5. ACES / OCIO (candidate only)
An arbitrary 709 display-rendered plate must not be called "scene-linear camera data" by naming it ACES. ACEScg and ACEScct are different working encodings. Pin the engine, config and output transform independently; record for each LUT: sha256, size/domain, interpolation, engine version, input/output encodings, scene/display referred, config hash, baked status; never apply an already-baked output transform twice. A DaVinci Resolve route has no certified Python auto-grade method: inventory the installed API before proposing it.

## 6. Colour-contract record (write it into `data/grade.json`)
`{"camera_file":"<name>","sha256":"...","range":"tv","matrix":"bt709","transfer":"bt709","primaries":"bt709","hdr_converted":false,"override":null,"override_provenance":null}`
The G2 gate is `pass` only when every field is filled from a probe or an explicit, recorded override.

## 7. Regression corpus proposed by T12 (not built; the colour tools are tested on a synthetic clip only)
Synthetic ramps/bars in full and limited 709, 8 and 10 bit; consented light/dark/mixed-lit faces with beard/occlusion and no-face controls; HLG and profile 8.4 with and without a usable RPU; exact 30, 29.97, 30.5 and variable frame rates. Acceptance: no silent input assumptions; pre-clamp clipping logged; mask rejection without a fake pass; output tags match the actual conversion.

## Sources
distilled 04 colour §0, §4, §5; T12 FINDINGS and COLOR_PIPELINE via that file; FFmpeg filter documentation as summarised there; checked 2026-10-02.
