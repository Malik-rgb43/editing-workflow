# Optional: the Claude Artifact variant (Claude-only; not the default)

Load only if the user asks for a hosted page or you are in a Claude client that lists an Artifact tool. The default for every client (Claude Code, Codex, any student setup) is the local `visual-choice-board.html` + `choices.json` path: no account, no upload, works offline. Status of everything below: drafted from tool descriptions and research notes, NOT tested for a board (E13: no hosted run, no readback measured; distilled 07 choice-boards sections 2.2 and 8, 2026-10-01).

## 1. Preconditions (all must hold, else use the local path)
1. The client's real tool list contains an Artifact tool (inspect it; do not assume the CLI has the app's tools).
2. A per-client privacy decision exists for every still/text shown: a hosted page is a hosted copy. Private by default is a documented default, not proof of access control; the legacy chat "Publish" creates a PUBLIC link: never use it for client material.
3. The user asked for it or agreed.

## 2. Procedure
1. Build the board locally first (same `spec.json`, same HTML); verify it works offline.
2. Publish the same self-contained HTML as a private artifact (the tool description states a 16 MB page limit; the sample board is about 38 KB). Do not strip fonts, RTL, the none slot or the export gate.
3. Check in the hosted page: fonts load, every option shows the same current text, choices survive tab switches, typing digits in the text box does not pick an option, export is refused until complete, desktop and phone widths.
4. Readback, in this order of preference:
   a. The user pastes the JSON from the page's text box (works everywhere; run `verify` against the manifest).
   b. The user downloads `choices.json` and attaches it.
   c. If and only if the client exposes a shared artifact database and the page declares that capability (load the client's artifact-capabilities skill first), the agent may read the saved selection with the data tool. `make_board.py` v0.1 does not generate that code: it is a later extension, so today (c) is "not built".
5. Reading a UI summary is not proof that the file was saved or received; always hash and `verify` the retrieved bytes.

## 3. What not to claim
- That an artifact can write to the user's local filesystem (it cannot without a tested authorised bridge).
- Any time saving (not measured).
- That the author's account has persistent storage or Ask-Claude capabilities (unverified for the course author).
