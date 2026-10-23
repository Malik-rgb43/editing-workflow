# Client warehouse (מחסן העבודות)

A local page for every client video: a frame-accurate player for drafts, numbered notes with drawings, versions (V1, V2, ...), footage intake from a memory card, and an archive of approved videos. Everything runs on this computer (`127.0.0.1`), stdlib Python only, no cloud.

Written by Gabriel Gelman ([GabrielGel/video-warehouse](https://github.com/GabrielGel/video-warehouse)); this copy ships with the editing toolkit and is **off until the user turns it on**:

```
python tools/warehouse_link.py set --bundled          # turn it on (runs the page's own --self-check first)
python tools/warehouse_link.py library "<client folder>"   # optional: the user's existing client folders, shown read-only
python tools/warehouse_link.py shortcut               # optional: a Desktop launcher (Windows)
python tools/warehouse_link.py run -- serve --open    # open the page
```

Requirements: Python 3.10+, `ffmpeg` and `ffprobe` on the PATH. Full guide: `docs/en/client-warehouse.md` (Hebrew: `docs/he/client-warehouse.md`).

Commands (the toolkit runs them through `warehouse_link.py run --`): `serve`, `add PROJECT VIDEO`, `wait PROJECT`, `inbox`, `reply PROJECT NOTE_ID --text TEXT [--resolve]`, `url PROJECT`, `--self-check`.

State (page token, caches, `config.json`) lives in `~/.avc/warehouse-state` when started through the toolkit, so an update of the toolkit never wipes it. `open-warehouse.bat` starts the page from this folder directly, with the state kept here.
