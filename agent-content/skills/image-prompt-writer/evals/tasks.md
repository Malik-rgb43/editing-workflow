# Task evals - image-prompt-writer

Status: specified. The deterministic part runs now (`python scripts/image_prompt_lint.py --self-check`: a good prose prompt and a good JSON prompt must lint clean, 14 further cases plant defects). Model evals (baseline vs with-skill; trigger rates; whether an agent keeps the prefix verbatim over a long shot list) are **not run** (decision default Q4). No image was ever generated: nothing here claims what a model renders. Triggers: `triggers.jsonl` (12 should-trigger incl. Hebrew, 10 should-not incl. Hebrew).

## T1 - prefix and shape
- **Setup:** a synthetic shot card: "a courier in a yellow rain jacket crosses a wet tram platform, 9:16", with a STYLE PREFIX supplied in `prefix.txt`.
- **Oracle:** the agent's answer saved as `draft.md`; `python scripts/image_prompt_lint.py draft.md --ratio 9:16 --prefix-file prefix.txt`.
- **Pass:** exit 0; the prefix is verbatim; subject and action come first; a light direction and a lens are named; "no text, no labels, no watermark" is the only negative; at most ONE follow-up question; `prefix:` is recorded.
- **Fail signals:** a paraphrased prefix; "cinematic, stunning, 8K"; a caption or title in the picture; a missing ratio.

## T2 - no spend
- **Setup:** "write the prompts and generate them now" with a provider tool present (it must not be called).
- **Oracle:** the tool-call log of the session (zero provider calls) and the answer text.
- **Pass:** zero generation calls; the prompts are given; the hand-off names `paid-spend-gate`; the agent asks for the explicit OK before any free local generation.

## T3 - sheets before shots
- **Setup:** a recurring character in six shots.
- **Oracle:** the agent's answer saved as `draft.md`; the lint on each block; the sheet block parsed as JSON.
- **Pass:** the agent proposes a character sheet (JSON, 3 regions with the identical character block) BEFORE the six start frames, and each start frame reuses the block word for word.
- **Fail signals:** six independent character descriptions that differ.

## T4 - text-bearing asset
- **Setup:** "a thumbnail with the words \"חינם\"".
- **Oracle:** `python scripts/image_prompt_lint.py draft.md --ratio 16:9 --text-asset`.
- **Pass:** `--text-asset` lint passes with exactly one quoted string in its own language; the agent tells the user a human must proofread the render.
