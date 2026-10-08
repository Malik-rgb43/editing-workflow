# First requests - what to ask for, in an editor's words

> Written 2026-10-08. A gallery of requests you can copy, fill in and paste into your agent after the install. For each kind of video: the request, what you will be asked before anything is built, which screens open, and whether it runs on your computer or needs a paid connection. No prices here: anything paid is estimated on the day by `paid-spend-gate`, and nothing is spent before you approve a number. Hebrew: [docs/he/first-requests.md](../he/first-requests.md).

<!-- step: first-requests-01 -->
## first-requests-01 - How to use this page
Copy a request, replace every `<...>` with your own file, folder, link or words, and send it. Talk like an editor: say what the video is for, how long, which ratio, and what you want the viewer to feel or do. You do not need to name a skill or a tool.

Every new video starts with the same short round of questions (Round 0), in one message: what the video is for, who decides the concept (you, or "you decide"), the language spoken and the language of the captions (never assumed), the consent of the people on camera when it is unclear, and any facts the video needs (the offer, prices, names, dates, a link). "You decide" covers taste, never facts: the agent asks for a missing price instead of inventing one.

**Local** means it runs on your computer with free tools (a speech model is downloaded once, after you approve its size). **Paid connection** means a service you connected (for example video generation or a voice) does part of the work; each paid call is shown as a dated estimate first and runs only after your yes. Which local tool replaces which paid one: [local-vs-paid.md](local-vs-paid.md).

<!-- step: first-requests-02 -->
## first-requests-02 - The three to start with
The installer ends with these three, chosen for what your computer has (the agent reads `tools/connections.py`). The first two are the same for everyone:
1. "Here is a video I love: `<link>` - make mine like it."
2. "Here is my footage: `<folder>` - make a 30 s reel."
3. One that fits what you connected: video generation -> "Here is my product photo: `<file>` - make a 10 s ad from it."; a voice service -> "Here is my script: `<text>` - make a 30 s explainer with a voice-over."; stock media -> "Here is my voice note: `<file>` - cover it with stock B-roll and captions."; Blender installed -> "Here is my logo: `<file>` - make a 5 s 3D logo reveal."; nothing connected -> "Here is a talking-head clip: `<file>` - cut the pauses and add captions in `<language>`."
Saying "what can you do?" or "let's start" gets you the same three.

<!-- step: first-requests-03 -->
## first-requests-03 - Talking head
**Ask:** "Here is a 4-minute talking-head clip: `<file>`. Cut it to about 60 s, 9:16: drop the pauses and the false starts, keep my best take of each sentence, punch in on the key lines, captions in `<language>`."
**You will be asked:** Round 0; the length and the ratio if you did not give them; the caption look if your brand does not fix it.
**Screens:** the Studio (you watch the edit build), the caption style board (pick the font, animation and height on a frame of your own video), the storyboard page only if B-roll or graphics are planned, the notes page on the draft.
**Local or paid:** local. Paid only if you ask for generated B-roll or a new voice.

<!-- step: first-requests-04 -->
## first-requests-04 - Testimonial
**Ask:** "Here is a 12-minute customer interview: `<file>`. Pull a 45 s testimonial: the problem, what changed, the result, in her own words. A name and title lower third, captions in `<language>`, 1:1 and 9:16."
**You will be asked:** the speaker's consent to appear, the exact spelling of her name and title, which results she really said (nothing is added to her words), the ratios.
**Screens:** the Studio, the caption style board, the storyboard page if proof shots or graphics are added, the notes page.
**Local or paid:** local.

<!-- step: first-requests-05 -->
## first-requests-05 - Ad
**Ask:** "Make a 20 s ad for `<product>` from these clips and photos: `<folder>`. The offer is `<offer, exactly as written>`, the call to action is `<link>`. A hook in the first 2 seconds, three hook versions, 9:16 for Meta and TikTok."
**You will be asked:** the offer, prices and dates word for word; the audience; the music (an ad needs a track cleared for ads); the platforms and the file list.
**Screens:** three concept ideas to choose from, the moodboard + storyboard page, the caption style board, the Studio, the notes page; after approval the hook versions and ratios are made from the approved master.
**Local or paid:** local with your footage and photos. Generated shots need a paid connection: one sample shot is generated and approved before the rest are priced.

<!-- step: first-requests-06 -->
## first-requests-06 - Montage (footage + music, no voice)
**Ask:** "Here are the clips from our event: `<folder>`, and the track: `<file>`. Make a 40 s recap, 16:9: open calm, build to the best moment, hold the hero shots longest, one look across all cameras."
**You will be asked:** the track's licence, the length, the moments that must be in it, whether text or a logo goes at the end.
**Screens:** the storyboard page (the order of shots on the music), the Studio, the notes page.
**Local or paid:** local. The agent fits the track to the length (it starts on a downbeat and ends on a phrase) and grades the cameras to one look.

<!-- step: first-requests-07 -->
## first-requests-07 - Screen tutorial
**Ask:** "Here is my screen recording with narration: `<file>`. Make a 90 s tutorial: zoom in where the action is, cut the dead time where nothing moves and nobody talks, keep every menu readable, captions in `<language>`."
**You will be asked:** the length, the ratio (16:9 for YouTube, 9:16 for a short), the steps the viewer must not miss.
**Screens:** the Studio, the caption style board, the notes page. The agent also lists narration lines where nothing on screen changes, so you can fix them before the draft.
**Local or paid:** local. Use your own recording; the agent does not install a screen recorder.

<!-- step: first-requests-08 -->
## first-requests-08 - Podcast clip
**Ask:** "Here is a 50-minute podcast: `<file>`, with one mic track per speaker: `<a.wav>`, `<b.wav>`. Find the three strongest 45 s moments and cut each to 9:16 with the speaker's name and captions in `<language>`."
**You will be asked:** the speakers' names and their consent, the language, how many clips, which topics to avoid.
**Screens:** the candidate moments with their times (you pick which ones), the caption style board, the Studio, the notes page per clip.
**Local or paid:** local. With one track per speaker (or a stereo file with one speaker per channel) each word is labelled with who said it, without a model.

<!-- step: first-requests-09 -->
## first-requests-09 - Launch or motion piece
**Ask:** "Make a 15 s launch video for our app `<name>` from these screenshots and the logo: `<folder>`. Kinetic type on the three key benefits, the logo at the end, 16:9 and 9:16, in the feel of `<a brand or a link you like>`."
**You will be asked:** the exact benefit lines, the brand colours and fonts, the music, whether 3D is wanted.
**Screens:** the moodboard + storyboard page (every beat as a frame before any code), choice boards for fonts, palettes and easing when there are options, the Studio, the notes page.
**Local or paid:** local (HyperFrames; Blender for 3D if installed). AI 3D models or generated shots need a paid connection.

<!-- step: first-requests-10 -->
## first-requests-10 - Captions only
**Ask:** "Add captions to this finished video: `<file>`. The speech is `<language>`; captions in `<language>`, burned in, word by word, plus an SRT file." Or translated: "Translate the captions of `<file>` from `<language>` to `<language>`, keep the brand and people's names as they are, and give me both a burned-in version and an SRT."
**You will be asked:** the speech language and the caption language; for a translation, the words that must never be translated (names, brands, product terms) and your approval of the translated text before it is placed, with every claim, price and legal line checked by you again.
**Screens:** the caption style board, the Studio, the notes page. A change of reading direction (Hebrew or Arabic <-> English) also mirrors the layout: alignment, the caption side, arrows and progress bars.
**Local or paid:** local. A dub (a new voice in another language) needs a paid voice connection and the consent of the person whose voice it is.

<!-- step: first-requests-11 -->
## first-requests-11 - A reference you love
**Ask:** "Here is a reel I love: `<link>`. Make my `<topic or footage>` in its style: the same pacing, the same kind of captions and transitions, 30 s, 9:16. Tell me what you can do here and what would need a paid service."
**You will be asked:** which part of the reference is THE style (when it has several looks), the length and ratio, the facts of your video. Its music, footage and logos are never reused: only its grammar (pacing, devices, type, camera rhythm).
**Screens:** the reference's contact sheets, a choice board with three ways to apply it (Faithful, Elevated, Twist) as stills, each borrowed device marked local, needs a connection (paid gate) or not reproducible; then the storyboard page, the Studio and the notes page.
**Local or paid:** usually local. The analysis tells real footage from photos with a slow zoom: those are local work on a still, not a paid video generation. A project estimate from a reference is a range (the reference's cuts per minute x your length, never below a few shots) with its assumptions written out.

<!-- step: first-requests-12 -->
## first-requests-12 - The screens you will see
| Screen | When it opens | What you do there |
|---|---|---|
| The Studio | whenever work on a project starts or resumes | watch the video and its timeline fill in while the agent works |
| Caption style board | before the first caption is built | pick the font, animation and height on a frame of your own video |
| Choice board | any visual choice with two or more options (fonts, palettes, hooks, the three ways to apply a reference) | click the option you want |
| Moodboard + storyboard | before any composition code, when the video has beats beyond footage, captions, music and cuts | approve, or write a note on any frame |
| Notes page | after every draft render | write notes on the timeline (a point or a range), or press "approved" |
Each screen opens in the agent's browser pane without you asking. A path or a description in chat is not a substitute; if you only see a path, ask the agent to open it.
