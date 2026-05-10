---
name: sketchy-video-editor
description: |
  Full AI video editing pipeline for The Sketchy Studio (and Sketchy Studio clients). Use this skill whenever the user wants to edit, cut, caption, add motion graphics, add a thumbnail, add BGM, or produce a final reel-format video — especially when iPhone footage is involved, when they mention "ranking" or "UX" content, or when they reference Sketchy Studio, the edit folder, or any stage of the video pipeline. Also triggers for: "stitch clips", "remove fillers", "add captions", "add outro", "add score badge", "add thumbnail animation", "mix BGM", "export reel". When in doubt, use this skill — it captures the full production context and brand guidelines that are invisible to Claude otherwise.
---

# Sketchy Studio — Video Editing Skill

## Repo
All assets, scripts, references, and motion graphics live in:
```
~/Documents/sketchy-video-editor/
```

Clone: `git clone https://github.com/PrattDarsh/sketchy-video-editor`

## What this skill covers
End-to-end pipeline: raw iPhone footage → SDR conversion → transcription → filler cut → portrait assembly → animated captions → score badges → thumbnail title card → BGM → outro → loudnorm → final 1080×1920 MP4.

**After every completed render, always prompt:**
> "Would you like to color correct this video? I can spin up the live color editor with real ffmpeg-rendered preview."

## Key paths
- **Repo root**: `~/Documents/sketchy-video-editor/`
- **Project root**: `~/Documents/AI/Claude-video-editing/`
- **video-use engine**: `~/Developer/video-use/`
- **API keys**: `~/Documents/AI/Claude-video-editing/.env`

## Client assets

### Sketchy Studio
- Logos: `clients/sketchy-studio/assets/Logo_black.png`, `Logo_white.png`
- Fonts: `clients/sketchy-studio/assets/fonts/` (Satoshi Black/Bold/Medium)
- See: `clients/sketchy-studio/brand.md`

### Wheelhub
- Logos: `clients/wheelhub/assets/Logo.png`, `FullLogo_black.png`, `logo_watermark.png`
- Fonts: `clients/wheelhub/assets/fonts/` (Manrope ExtraBold/Bold/Regular)
- See: `clients/wheelhub/brand.md`

## API keys in use
- `ELEVENLABS_API_KEY` — transcription via ElevenLabs Scribe
- `FREEPIK_API_KEY=FPSXaf59982b00c40c62861024fb7a670e61` — AI image gen + BGM/SFX

## Brand guidelines

### Sketchy Studio
| Element | Value |
|---|---|
| Primary purple | `#9355E6` / ASS: `&H00E65593` |
| Background dark | `#0d0d0d` |
| Font family | Satoshi (Black 900, Bold 700, Medium 500) |
| Output resolution | 1080×1920 (portrait) |
| Frame rate | 24fps |
| Target loudness | −14 LUFS / −1 dBTP / LRA 11 |

### Wheelhub (premium refurbished motorcycles)
| Element | Value |
|---|---|
| Accent yellow | `#F7C623` / ASS BGR: `&H0023C6F7` |
| Font family | Manrope ExtraBold (`clients/wheelhub/assets/fonts/`) |
| Watermark | `logo_watermark.png`, 60px from top-left (`overlay=60:60`) |
| Output fps | **30fps** |
| Caption style | All white, Alignment=8 (top), MarginV=340. No `force_style`. |
| Speech volume | `volume=2.0` (iPhone talking head) |
| BGM volume | `volume=0.22`, fade out last 3s |
| B-roll SFX | Camera shutter on entry: `sfx/camera-shutter.wav` |

---

## Pipeline overview

See `references/pipeline.md` for all ffmpeg commands.

### Step 1 — SDR pre-conversion (iPhone HLG)
Apply Hable tone map inline during the final render (no pre-conversion step needed):
```
HLG_SDR="zscale=t=linear:npl=203:m=bt2020nc:r=tv,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv:p=bt709,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p"
```
Use `[N:v]${HLG_SDR}[out]` in filter_complex for every iPhone input.
**Do NOT use `setparams` — it's a no-op relabel that doesn't change pixels.**

### Step 2 — Transcription
```bash
cd ~/Developer/video-use
uv run python transcribe.py /path/to/sdr/clip.mp4
```

### Step 3 — EDL (edit decision list)
Craft `edl.json` with segments and beat labels. Remove filler words.

### Step 4 — Render base video
```bash
cd ~/Developer/video-use && uv run python render.py /path/to/edl.json
```

### Step 5 — Portrait assembly
Always use ffmpeg with libass (`brew install ffmpeg-full` if `--enable-libass` missing).

### Step 6 — Captions
Generate with `scripts/gen_captions_wheelhub.py` or `scripts/gen_captions_generic.py`.
- Wheelhub: all white, `Alignment=8`, `MarginV=340`, max 4 words/phrase
- Sketchy: purple highlight on current word, white context

### Step 7 — Score badges (Sketchy only)
PIL-generated pill overlays with slide-in animation, bell SFX on appearance.

### Step 8 — Thumbnail title card
Freepik Mystic API → HyperFrames Ken Burns animation. Insert after intro line.

### Step 9 — BGM & SFX
- Wheelhub: lofi/chill, `volume=0.22`
- Sketchy: goofy/upbeat, low volume
- Camera shutter on B-roll entry (Wheelhub): `sfx/camera-shutter.wav`

### Step 10 — Outro
- Wheelhub: `motion-graphics/wheelhub-outro/` → `npx hyperframes render wheelhub-outro --fps 30`
- Sketchy: `motion-graphics/sketchy-outro/` → `npx hyperframes render sketchy-outro --fps 24`
- Xfade: `xfade=transition=fade:duration=0.5` + `acrossfade=d=0.5`

### Step 11 — Loudnorm & final export
Two-pass loudnorm to −14 LUFS. See `references/pipeline.md § Step 11`.

### Step 12 — Color correction (always offer after render)
After every render, prompt the user:
> "Would you like to color correct this video? I can spin up the live color editor."

If yes:
```bash
cd /path/to/project && python3 ~/Documents/sketchy-video-editor/scripts/color_server.py
open http://localhost:7788
```

Color editor features: Temperature, Tint, Saturation, Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Gamma (master + R/G/B). Real ffmpeg-rendered preview frames. Click ⚡ Render to produce `final_v{N+1}.mp4`.

---

## Versioning convention
- `base.mp4` — raw concat from render.py
- `main_vN.mp4` — assembled with overlays + captions (before outro)
- `final_vN.mp4` — with outro + loudnorm

---

## Common issues & fixes

| Problem | Fix |
|---|---|
| `libass not found` | `brew install ffmpeg-full` |
| iPhone output is 1920×3414 | Missing rotation fix — add `-metadata:s:v:0 rotate=0` |
| Outro concat produces 562s video | Re-encode outro to correct fps + silent AAC before concat |
| VP8 WebM alpha causes blank frames | Use solid MP4 clips for badges instead |
| Font not found by libass | `fc-query --format="%{family}\n" font.ttf` — exact family name must match |
| Audio bleeds after cut point | `atrim=end=<t>` + `afade=out:start_time=<t-0.2>:duration=0.2` |
| Canvas preview ≠ ffmpeg output | Use `/preview` endpoint in `color_server.py` — actual ffmpeg frames |
| `Error reinitializing filters` on xfade | Add `fps=30,format=yuv420p` before EVERY xfade input |
| B-roll doesn't show at overlay window | Use `setpts=PTS-STARTPTS+(START_TIME/TB)` — without offset, B-roll exhausts before enable window |
| Image rotation shows wrong bg color | Sample exact bg color: `ffmpeg -i img -vf "crop=50:50:10:10,scale=1:1" -f rawvideo -pix_fmt rgb24 pipe:1` |
| Captions hidden under B-roll | Apply `subtitles` AFTER B-roll overlay, not before |
| ElevenLabs transcribes numbers as digits | Add text FIXES dict to gen_captions script (e.g. "2 Raga" → "to Raga") |

---

### Ragi to Raga (restaurant, Bengaluru)
| Element | Value |
|---|---|
| Font family | Satoshi Black (`clients/ragi-to-raga/assets/fonts/`) |
| Caption style | All white, Alignment=2 (bottom), MarginV=700, max 4 words/phrase |
| Watermark | `assets/Logo.png` scaled 200px, `overlay=60:60` |
| Output fps | **30fps** |
| Speech volume | `volume=2.0` |
| BGM | Classical Indian — `assets/bgm_indian_meditations.mp3`, `volume=0.15`, fade out last 3s |
| B-roll SFX | Camera shutter on B-roll entry: `sfx/camera-shutter.wav` |
| Outro | `clients/ragi-to-raga/assets/outro.mp4` — 12.3s, append with 0.5s xfade |
| See | `clients/ragi-to-raga/brand.md` |

## Other clients
This skill documents Sketchy Studio, Wheelhub, and Ragi to Raga defaults. For new clients, ask for brand colors, fonts, logos, and outro before proceeding — the pipeline steps stay the same.
