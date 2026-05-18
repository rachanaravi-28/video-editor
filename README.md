# Video Editor

AI-assisted pipeline for producing polished portrait reels from raw iPhone footage.

---

## What's inside

```
video-editor/
├── scripts/
│   ├── color_server.py       ← local color editor (Lightroom-style, ffmpeg-accurate)
│   ├── color_editor.html     ← served by color_server.py at localhost:7788
│   └── gen_captions_generic.py  ← ASS caption generator (CLI, single clip)
├── sfx/
│   └── camera-shutter.wav    ← played on B-roll entry
├── references/
│   └── pipeline.md           ← all ffmpeg commands, step by step
└── README.md
```

> Raw footage, B-roll clips, and renders are **not** stored in this repo. Drop source clips into a local project folder and point the scripts at them.

---

## Quick start

### 1. Install dependencies

```bash
# ffmpeg with libass (required for captions)
brew install ffmpeg-full

# Python transcription engine
cd ~/Developer && git clone https://github.com/heygen-com/video-use
cd video-use && uv sync

# Node version ≥ 18 (optional, for HyperFrames outros)
node --version
```

### 2. Set up API keys

```bash
cp .env.example .env
# Fill in:
# ELEVENLABS_API_KEY=...
```

### 3. Install fonts

Copy your project fonts to the system font directory:

```bash
# macOS
cp path/to/fonts/*.ttf ~/Library/Fonts/
cp path/to/fonts/*.otf ~/Library/Fonts/
```

---

## Pipeline (summary)

1. **SDR convert** raw iPhone MOV (HLG → BT.709 via `setparams`)
2. **Transcribe** with ElevenLabs Scribe (word-level timestamps)
3. **EDL** — craft `edl.json`, remove filler words
4. **Render base** via `video-use`
5. **Generate captions** — `python3 scripts/gen_captions_generic.py transcript.json captions.ass`
6. **Assemble** — B-roll overlays, watermark, captions
7. **BGM + SFX** — music mix + camera shutter on B-roll
8. **Outro** — HyperFrames render, xfade transition
9. **Loudnorm** — two-pass to −14 LUFS
10. **Color correct** (optional) — see Color editor below

Full ffmpeg commands: [`references/pipeline.md`](references/pipeline.md)

---

## Color editor

Runs a local HTTP server with Lightroom-style controls. Preview uses actual ffmpeg-rendered frames — no canvas approximation.

### 1. Create a `project.json` in the scripts folder

```json
{
  "sdr_src":           "~/path/to/source.MOV",
  "logo":              "~/path/to/logo_watermark.png",
  "logo_x":            60,
  "logo_y":            60,
  "bgm":               "~/path/to/bgm.mp3",
  "bgm_volume":        0.22,
  "bgm_duration":      84,
  "captions":          "captions.ass",
  "sdr_out":           "sdr/out.mp4",
  "outro":             "~/path/to/outro.mp4",
  "outro_offset":      83.0,
  "speech_volume":     2.0,
  "speech_end":        83.08,
  "speech_fade_start": 82.85,
  "broll": [
    {"file": "~/path/to/clip1.mp4", "start": 12.38, "end": 18.0}
  ]
}
```

### 2. Run the server

```bash
python3 scripts/color_server.py
open http://localhost:7788
```

Controls: Temperature, Tint, Saturation, Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Gamma (master + R/G/B channels).

When satisfied, click **⚡ Render** to produce `final.mp4`.

---

## Caption generator

```bash
python3 scripts/gen_captions_generic.py transcript.json captions.ass \
  --font "Manrope ExtraBold" \
  --fontsize 78 \
  --alignment 8 \
  --marginv 340
```

| Option | Default | Notes |
|---|---|---|
| `--font` | `Manrope ExtraBold` | Must be installed on the system |
| `--fontsize` | `78` | Points |
| `--alignment` | `8` | ASS alignment (8 = top-center, 2 = bottom-center) |
| `--marginv` | `340` | Vertical margin in pixels |
| `--max-words` | `4` | Words per caption phrase |
| `--gap` | `0.35` | Pause threshold (seconds) to break a phrase |
