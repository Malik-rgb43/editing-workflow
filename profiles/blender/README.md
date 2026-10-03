# Profile `blender`

> Dated 2026-10-02 · evidence state **sourced** (owner timings measured at small sizes; no controlled benchmark) · expires 2026-12-31. **unsupported ≠ missing ≠ error.**

## What it installs
Nothing by itself: this profile **records and checks** a student-installed Blender (the **exact version is written down** — the owner runs 5.2, the research's pinned manual is 4.5 LTS; engine identifiers and APIs changed between 4.2 and 5.x, so scripts read enums instead of hard-coding them and look shader nodes up by type, not by name). It enables the 3D routes of `agent-content/references/three-d-routes.md`: headless `blender -b -P script.py` for sprite sheets and plates, and an **optional** live bridge (MCP for Blender). No Python extra group is defined; Blender uses its own bundled Python (a small Pillow-based packing helper runs in system Python).

## Download size and source
Blender download size: **`unmeasured`** (not recorded). The installer shows it before downloading.

## Hardware
Official minimum (documentation, not a guarantee for a given scene): 4-core SSE4.2 CPU, 8 GB RAM, 2 GB VRAM. Planning recommendation: 8 cores, 32 GB RAM, 8 GB VRAM. Blender 5.x requires Apple Silicon (4.5 LTS is the last Intel-Mac branch). AMD on Windows: Cycles-HIP is officially supported for the RX 7000 family from driver 24.6.1 (manual 4.5), with HIP-RT and GPU denoise; **shadow caustics are not supported**; the exact one reference machine run is pending. One heavy renderer at a time; never overlap a Blender batch with browser capture or ASR (a render took 21.5 min instead of 11.5 min next to Blender).

## Tested-on evidence (the reference machine — **LOCAL-only**; small-size timings, **not a benchmark**)
EEVEE objects **1.2-2.25 s per frame** at 384-640 px; EEVEE 3D type 1.0-1.25 s per frame; Cycles-CPU plates 51 s / 79 s / 253 s (256-384 samples); every Blender launch costs **~1-1.5 min** (shader compile + camera fit) — render several assets per launch. Not tested: a fixed 1080p fixture, Cycles-HIP on the one reference machine, 4.5-vs-5.2 differences, macOS, Linux, OptiX, Metal.

## Security — the live bridge is an unauthenticated code-execution socket
The MCP add-on listens on **localhost:9876 with no authentication or encryption and executes arbitrary Python.** Rules: bind to localhost only; **never forward or expose the port**; treat `.blend` files from the internet as untrusted code; disable telemetry; no silent provider trials and no reliance on any shared trial key; the "safe mode" is not an established sandbox. For deterministic batch work prefer native headless `bpy`. See `agent-content/references/mcp-profiles.md` §6 and `docs/en/privacy-and-security.md#mcp-isolation`.

## Spending
Hosted 3D generators and Higgsfield `bl_*` generation tools **spend credits** — they are *not* part of this profile and sit behind the paid-generation gate (approval with a dated estimate first).

## States
| State | When |
|---|---|
| `unsupported` | OS/GPU below Blender's documented requirements; Intel Mac with a 5.x build |
| `missing` | Blender not found at the recorded version |
| `error` | a tiny headless render of the bundled fixture fails, or the MCP add-on and server versions do not match |

## Licences
Blender: GPL (add-ons and assets separate; rendered output is distinguished — indexed FAQ only). MCP for Blender: MIT. Assets: Poly Haven CC0; Poly Pizza mixed CC0/CC-BY (credit the creator); Sketchfab: **reject NC**, credit CC-BY, check the NoAI tag; Tripo free output is CC BY 4.0 **non-commercial**; Meshy free is CC BY 4.0, commercial with credit to Meshy. Generated meshes need the manifest in the 3D reference. Record source URL, creator, licence, date and SHA for every asset.

## Uninstall
Remove the Blender installation you made, the MCP add-on, and the toolkit's render/sprite output in `_work/`. No global change by the toolkit.
