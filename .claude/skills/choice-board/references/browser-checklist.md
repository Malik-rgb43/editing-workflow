# Browser checklist (human or browser tool; 5 minutes)

Load after `build`, before telling the user the board is ready. The unit tests prove structure, escaping, limits and the readback; only a browser proves the rest. Last run by the author: 2026-10-02 in a Chromium-based pane on the reference machine, local server on 127.0.0.1, sample board. Passed by script: items 1 (no console errors, no resource requests), 3, 4, 5, 6, 8, 9 (375 px, no overflow) and the pause switch of 7; seen in screenshots: 2, the look-alike specimen row (system fonts only) and the dark theme. NOT run: OS reduce-motion, the light theme, embedded real font files, Firefox, Safari, touch devices.

1. Open `choice-board.html` by double click (file:), or through a local static server; no console errors; no network requests (`performance.getEntriesByType('resource')` is empty).
2. Every tab shows the user's real text in every option; fonts embedded show the chip "embedded", others "system font: may fall back" (decide whether a fallback is acceptable).
3. Each tab: pick with a digit; the pick is outlined and the summary updates; keyboard focus stays on the card you used (no jump to the page start).
4. Type digits in the sample-text box and in a comment box: nothing gets selected.
5. Arrow keys on the tab row move between tabs (in a right-to-left board Left = next); Home/End work; only the active tab is in the tab order.
6. Export with a decision unanswered: refused, the tab with the gap opens, the message names it. A "none" without a comment: refused. Complete everything: the JSON appears in the box, a download is offered.
7. Pause stops every animation and shows the end state; with the OS "reduce motion" setting nothing animates.
8. Edit the sample text: every card updates, including word-by-word animations.
9. Width 375 px: no horizontal scroll, cards in two columns, buttons reachable.
10. Mixed text (Hebrew + English + digits + a currency sign): the line reads correctly in each card; the look-alike specimen letters (ו/ז, ד/ר, ה/ח) are distinguishable in every font offered; a font where they are not is dropped from the board.
11. Dark and light OS themes: contrast of labels and outlines acceptable.
Record failures as findings; a board that fails 3, 4 or 6 is not sent to the user.
