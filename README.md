# Sketchy Video Editor

AI-assisted video editing pipeline for The Sketchy Studio and its clients. Clone this repo and you have everything needed to produce polished portrait reels from raw iPhone footage.

---

## What's inside

```
sketchy-video-editor/
├── clients/
│   ├── wheelhub/
│   │   ├── brand.md          ← colors, fonts, specs, caption style
│   │   └── assets/           ← logos, watermark, fonts
│   └── sketchy-studio/
│       ├── brand.md
│       └── assets/           ← logos, fonts
├── scripts/
│   ├── color_server.py       ← local color editor (Lightroom-style, ffmpeg-accurate)
│   ├── color_editor.html     ← served by color_server.py at localhost:7788
│   ├── gen_captions_wheelhub.py   ← ASS caption generator (EDL-aware, team tags)
│   └── gen_captions_generic.py    ← ASS caption generator (single clip)
├── sfx/
│   └── camera-shutter.wav    ← played on B-roll entry
├── motion-graphics/
│   ├── wheelhub-outro/       ← HyperFrames outro (dark bg, yellow accents, 4.5s, 30fps)
│   └── sketchy-outro/        ← HyperFrames outro (white bg, logo pop, 4s, 24fps)
├── references/
│   └── pipeline.md           ← all ffmpeg commands, step by step
└── SKILL.md                  ← Claude AI skill (load into ~/.claude/skills/)
```

> Raw footage, B-roll clips, and project renders are **not** stored in this repo. Drop source clips into a local project folder and point the scripts at them.

---

## Quick start

### 1. Install dependencies

```bash
# ffmpeg with libass (required for captions)
brew install ffmpeg-full

# HyperFrames (for outros)
npm install -g hyperframes

# Python transcription engine
cd ~/Developer && git clone https://github.com/heygen-com/video-use
cd video-use && uv sync

# Node version ≥ 18
node --version
```

### 2. Set up API keys

```bash
cp .env.example .env
# Fill in:
# ELEVENLABS_API_KEY=...
# FREEPIK_API_KEY=...
```

### 3. Install fonts

Copy fonts to system:
```bash
# macOS
cp clients/wheelhub/assets/fonts/*.ttf ~/Library/Fonts/
cp clients/sketchy-studio/assets/fonts/*.otf ~/Library/Fonts/
```

### 4. Install the Claude skill (optional, for AI-assisted editing)

```bash
cp SKILL.md ~/.claude/skills/sketchy-video-editor/SKILL.md
```

---

## Pipeline (summary)

1. **SDR convert** raw iPhone MOV (HLG → BT.709 via `setparams`)
2. **Transcribe** with ElevenLabs Scribe (word-level timestamps)
3. **EDL** — craft `edl.json`, remove filler words
4. **Render base** via `video-use`
5. **Assemble** — B-roll overlays, watermark, captions
6. **BGM + SFX** — lofi mix + camera shutter on B-roll
7. **Outro** — HyperFrames render, xfade transition
8. **Loudnorm** — two-pass to −14 LUFS
9. **Color correct** (optional) — `python3 scripts/color_server.py` → `open http://localhost:7788`

Full ffmpeg commands: [`references/pipeline.md`](references/pipeline.md)

---

## Clients

| Client | FPS | Font | Accent | Details |
|---|---|---|---|---|
| Sketchy Studio | 24 | Satoshi | `#9355E6` purple | [`clients/sketchy-studio/brand.md`](clients/sketchy-studio/brand.md) |
| Wheelhub | 30 | Manrope ExtraBold | `#F7C623` yellow | [`clients/wheelhub/brand.md`](clients/wheelhub/brand.md) |

---

## Color editor

Runs a local server with Lightroom-style controls. Preview uses actual ffmpeg-rendered frames — no canvas approximation.

```bash
cd /your/project/folder
python3 ~/Documents/sketchy-video-editor/scripts/color_server.py
open http://localhost:7788
```

Controls: Temperature, Tint, Saturation, Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Gamma (master + R/G/B channels).

When satisfied, click **⚡ Render** to produce `final_v{N+1}.mp4`.

> The color server is hardcoded with source/output paths at the top of `color_server.py` — update `SDR_SRC`, `BROLL`, `CAPTIONS`, etc. for each project.

---

## Adding a new client

1. Create `clients/<client-name>/brand.md` with colors, fonts, output specs
2. Add logos and fonts to `clients/<client-name>/assets/`
3. Build a HyperFrames outro in `motion-graphics/<client-name>-outro/`
4. Add any custom caption style to brand.md

Pipeline steps are the same across all clients — only visual parameters change.
