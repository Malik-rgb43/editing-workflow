# Profile `nle-ae` — unmeasured

> Dated 2026-10-02 · evidence state **unmeasured** (documentation level; nothing was installed or driven) · expires 2026-12-31. **unsupported ≠ missing ≠ error.**

## Honest status
The research did not install an After Effects bridge, call a tool, or round-trip a project. This profile records routes, a known Hebrew-numbers regression family, and the safety rules; it promises no result.

## Routes
1. **File hand-off** (always available): alpha sprites / ProRes 4444 / caption data, with a **loss report**. 2. **Higgsfield plugin + MCP bridge** (`ae_*` tools; optional; executes editor operations; its generation tools spend credits → behind the paid-generation gate). 3. Student-authored scripting or panels (ExtendScript is ES3) — out of scope for v1.0. `[CONFLICT]` minimum host version: help says 2024 / 24.0+, plugin page says 2025+; untested. **Duplicate the project before any write.**

## Download size and source
`unmeasured`.

## Hardware
Requirements of the student's own After Effects version (not researched). Windows and macOS documented for the plugin; Linux not established.

## Tested-on evidence
**None.** Not tested: installation, bridge calls, Hebrew caption layers through the bridge, version compatibility.

## Hebrew numbers regression family (`[CONFLICT]`, keep as fixtures)
An internal report found numbers such as "40 000" rendering as "000 40" in right-to-left After Effects text: a normal space between digit groups is bidi class WS, and LRE/PDF embeddings were ignored in that build. Adobe documents Hebrew and mixed-number support in AE's Universal Text Engine, so "numbers always reorder in AE" is too broad — treat it as a **versioned regression fixture** (AE version, composer, font, exact string). Working fixes: merge digit groups into **one token**; use NBSP (U+00A0) or a comma as the thousands separator; LRM-fence digit runs (a regex that strips whitespace turns "40 50" into "4050" — use explicit tokens instead). Source: `agent-content/references/hebrew-rtl-captions.md` §7.

## States
| State | When |
|---|---|
| `unsupported` | host version or OS below what the bridge needs (once confirmed) |
| `missing` | After Effects or the bridge not found at the recorded version |
| `error` | a tiny read-only call fails, or a write cannot be reversed |

## Licences
After Effects: Adobe terms (the student's licence). Bridge/plugin terms were not reviewed — do not redistribute the installer.

## Uninstall
Remove the plugin with the host's own manager, delete bridge configuration entries and toolkit hand-off files in `_work/`. No global change by the toolkit.
