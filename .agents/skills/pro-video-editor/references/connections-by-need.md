# Connections by need

Load when Step 0 decides which connection to use for a job (stock, logos, UI pieces, 3D, generation, music, reference capture).

Presence comes from Step 0 (`_work/connections.json` + your own tool list); a listed integration is not a working one. Free and local come first; anything that can cost money goes through `paid-spend-gate` with a dated estimate.

| Need | Connected route (if the student has it) | Free / local fallback |
|---|---|---|
| Stock footage and photos | Pexels API (free tier; licence row per file) | the student's own footage, `assets/` |
| Icons and real logos | Iconify MCP (brand logos only with permission for ads) | hand-drawn SVG |
| UI components, cards, effects | shadcn registries (free); 21st.dev Magic MCP (account) | toolkit blocks, hand-built |
| 3D objects and scenes | Blender (CLI headless or Blender MCP). Blender missing and the video needs 3D: ask ONE yes/no, "Blender is where the 3D is built; about 350 MB, free; install it?", then `install/bootstrap.py add blender --yes --install-missing` | a 2.5D move on a still |
| Generated stills, video, voice | Higgsfield MCP/CLI, ElevenLabs MCP: paid, through the gate | plan + stills, the source voice |
| Music | ElevenLabs: paid, through the gate | a licensed library track (licence row per placement) or silence |
| Reference capture, preview QA | Playwright MCP | `hyperframes snapshot` |
| A reference the student may analyse | yt-dlp | the file the student sends |
| A screen recording (demo, tutorial) | none needed: no recorder is installed for it | the student's own recording, made with what their computer already has (`agent-content/playbooks/wf-screen-demo.md`) |
A connection that is missing is never a reason to stop: say what it would add, use the fallback, and offer the connection once.

**Stock search, whichever library is connected:** query subject first in 2-4 words plus one point-of-view word; score each candidate 1-5 against its beat and accept 3 or more; a wrong point of view costs more than a wrong colour; when nothing reaches 3, go in this order: rephrase, a second library, own footage or a photo with a move, a graphic or UI beat, a generated shot (paid, through the gate). The table and the reasons: `references/visual-beats.md` section 4b.
