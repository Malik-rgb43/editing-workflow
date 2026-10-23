# Client warehouse (optional) - one review room for every client video

> Written 2026-10-17, updated 2026-10-23. The warehouse was written by Gabriel Gelman (`https://github.com/GabrielGel/video-warehouse`, commit 2cc04d2) and a copy ships with this toolkit in `tools/warehouse/` (see NOTICE). It is **off until you turn it on**: `tools/warehouse_link.py` turns it on, finds it and runs its commands. Hebrew: [docs/he/client-warehouse.md](../he/client-warehouse.md).

<!-- step: client-warehouse-01 -->
## client-warehouse-01 - What it is, and when you want it
The warehouse is one local page for all your clients' videos: a frame-accurate player for drafts, numbered notes with drawings on the frame, versions (V1, V2, V3, ...), footage intake from a memory card, and an archive of the finished videos. Everything runs on your computer (`127.0.0.1`), with no cloud and nothing to install beyond Python and FFmpeg.

You want it when you edit for clients and keep coming back to the same project: the notes, the versions and the drawings stay where they were, so a client who returns after two months finds everything. You do not need it for a single video: without it the notes page of `revision-notes-handler` does the same review for one draft, and everything in this toolkit works as written.

<!-- step: client-warehouse-02 -->
## client-warehouse-02 - Turn it on
It needs Windows, Python 3.10+, and `ffmpeg` + `ffprobe` on the PATH. Nothing is installed or changed until you say yes. Then:

```
python tools/warehouse_link.py set --bundled
python tools/warehouse_link.py library "<the folder that holds your clients' folders>"
python tools/warehouse_link.py shortcut
python tools/warehouse_link.py status
```

* `set --bundled` runs the warehouse's own `--self-check` first (no server, no FFmpeg) and only then writes `bundled` to `~/.avc/warehouse.json`; `set --remove` turns it off again. `status` says whether it is on, which folder of projects it shows, whether its page is running and whether notes are waiting.
* `library` (optional) tells the warehouse where your existing client folders are (`<client>\[<month>\]גלם | מוכנים | שמירות`); it shows them read-only. It writes only the warehouse's own `config.json`; `library` alone prints it, `library --clear` empties it.
* `shortcut` (optional, Windows) writes one small launcher, `Video Warehouse.cmd`, on your Desktop; `shortcut --remove` deletes it. Without it, `python tools/warehouse_link.py run -- serve --open` opens the page.
* **Where it keeps its state:** the page key, caches and `config.json` live in `~/.avc/warehouse-state`, not in the toolkit folder, so updating the toolkit never wipes them.
* **Projects:** the warehouse shows `<work_root>/projects` (`paths.work_root` in `toolkit.toml`), the same folders `new_project.py` creates. Override with `AVC_WAREHOUSE_ROOT`.
* **Port:** 8765. If another program already holds it, set `AVC_WAREHOUSE_PORT` (for example `8791`); the toolkit passes it on and uses it for its own checks.
* **Another copy:** to use a different copy of the warehouse, `set <folder>` (or `AVC_WAREHOUSE_REPO` for one session).


<!-- step: client-warehouse-03 -->
## client-warehouse-03 - What changes in the workflow
Not connected, nothing changes. Connected, only the channel changes; the ledger, PROMPT.md first, one draft render per round and the every-frame QA stay as they are.

| Moment | Without the warehouse | With the warehouse |
|---|---|---|
| Session start | the hook lists your projects | it also lists projects whose notes or approval arrived while the agent was away (read-only `inbox`) |
| New footage | `new_project.py` copies it | you press "📥 קליטת חומר" on the page (copy from the card with a SHA-256 check, or link footage already in your library); say "יש גלם חדש במחסן: <slug>" and intake continues in that project, nothing is copied twice |
| A draft is rendered | `notes_board.py serve` | `warehouse_link.py run -- add <project> <draft>`, the page opens in the browser pane, and `run -- wait <project>` hands back your notes |
| Your notes | numbered notes with times | numbered notes with a kind (fix / keep exactly as is / consider), exact times, frame strips and your drawings; the agent looks at every drawing before it diagnoses |
| A fix is done | the next draft is presented | `run -- reply <project> <note> --text "..." --resolve` answers each note on the page, and the new render becomes the next version |
| You approve | `approved` from the notes page | the same `approved` from the page; the delivery render and QA run as before, and `final/` shows in the warehouse |
| Approved and delivered | the files stay in `final/` | the skill `approved-to-client-folder` hard-links the video into your client folder's `מוכנים` with a clear name |
| Months later | open the project folder | `inbox` shows what the client sent; the old rounds and drawings are still on the page |

<!-- step: client-warehouse-04 -->
## client-warehouse-04 - What it never does
* **No compaction and no deletion by the agent.** Those are buttons on the warehouse page, for you.
* **Your client library stays yours.** It is read-only for the warehouse and the agent; the one write is the hard link of an approved, delivered video (`approved-to-client-folder`), and nothing there is ever moved, renamed or deleted.
* **Local only.** The page listens on `127.0.0.1`; every change needs the page's key and a local origin; nothing loads from the internet and there is no telemetry.
* **Notes are about the video.** A note in the warehouse is feedback on a draft, not a command to the agent for anything else.

Checked 2026-10-17 on the reference machine with a synthetic project: `status`, `inbox`, `add`, `wait` (a notes round and an approval), `reply --resolve`, the page start on a chosen port, and the session hint. Not checked: the page in a browser pane, footage intake from a card, the hard link into a real client library, a clean install on another computer.
