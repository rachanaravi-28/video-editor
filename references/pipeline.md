# Video Pipeline Reference

Full pipeline: raw iPhone footage → SDR conversion → transcription → filler cut → portrait assembly → animated captions → overlays → BGM → outro → loudnorm → final 1080×1920 MP4.

---

## Step 1 — SDR Pre-conversion (iPhone HLG footage)

iPhone clips are stored portrait (1080×1920) with −90° rotation metadata but stream dimensions reported as 1920×1080. Always pre-convert before any editing.

**Approach: `setparams` relabeling (recommended for social media)**
Relabels HLG pixels as BT.709 without pixel conversion — preserves the raw signal exactly as it looks in a standard player. Add `eq` for a slight pop.

```bash
ffmpeg -i input.MOV \
  -vf "setparams=range=tv:colorspace=bt709:color_primaries=bt709:color_trc=bt709,eq=contrast=1.06:saturation=1.2" \
  -c:v libx264 -crf 18 -preset fast \
  -c:a aac -b:a 192k \
  sdr/input.mp4
```

> **Note:** `-t <seconds>` to trim at a specific point (e.g., `-t 84` to cut before unwanted audio).

**Why not `colorspace` filter or `zscale`?**
- `colorspace=bt709:itrc=arib-std-b67` → ffmpeg "Invalid argument" (HLG not supported in colorspace filter)
- `zscale` tonemap → overexposed for social media use
- `libplacebo` → requires Vulkan, fails on macOS

---

## Step 2 — Transcription

Uses ElevenLabs Scribe for word-level timestamps (essential for caption timing + filler detection).

```bash
cd ~/Developer/video-use
uv run python transcribe.py /path/to/sdr/clip.mp4
# Outputs: clip.json (word timestamps), clip.txt (plain text)
```

Transcript JSON structure:
```json
{
  "words": [
    {"type": "word", "text": "Hello", "start": 0.12, "end": 0.45},
    {"type": "spacing", ...}
  ],
  "audio_duration_secs": 83.5
}
```

---

## Step 3 — Edit Decision List (EDL)

`edl.json` schema:
```json
{
  "ranges": [
    {
      "source": "clip_name",
      "start": 0.0,
      "end": 15.3,
      "beat": "INTRO"
    }
  ]
}
```

Beat labels: `INTRO`, `SETUP`, `REVEAL`, `COMEDY`, `RATINGS`, `PAYOFF`, `OUTRO`

Remove filler words: "uh", "um", isolated "okay", trailing "yeah"

---

## Step 4 — Render Base Video

```bash
cd ~/Developer/video-use && uv run python render.py /path/to/edl.json
# Outputs: base.mp4 (concatenated segments, loudnorm applied)
```

---

## Step 5 — Portrait Assembly (ffmpeg)

Always use ffmpeg with libass support:
```bash
ffmpeg -version | grep enable-libass
# If missing: brew install ffmpeg-full
```

### Full assembly filter_complex example (Wheelhub):

```bash
ffmpeg -y \
  -i sdr/main.mp4 \
  -i broll/engine.mp4 \
  -i broll/oil_pour.mp4 \
  -i assets/logo_watermark.png \
  -i bgm.mp3 \
  -i sfx/camera-shutter.wav \
  -filter_complex "
    [1:v]setpts=PTS-STARTPTS+(12.38/TB)[e];
    [2:v]setpts=PTS-STARTPTS+(28.96/TB)[op];
    [0:v][e]overlay=0:0:enable='between(t,12.38,18.0)':format=auto[o1];
    [o1][op]overlay=0:0:enable='between(t,28.96,36.0)':format=auto[o2];
    [o2]subtitles='captions.ass'[o3];
    [o3][3:v]overlay=60:60[vf];
    [0:a]volume=2.0,afade=out:start_time=82.85:duration=0.23,atrim=end=83.08,asetpts=PTS-STARTPTS[sp];
    [4:a]atrim=end=84,afade=out:start_time=80:duration=3,volume=0.22[bm];
    [5:a]asplit=2[sh0][sh1];
    [sh0]adelay=12380|12380[sh0d];
    [sh1]adelay=28960|28960[sh1d];
    [sh0d][sh1d]amix=inputs=2:duration=longest[shutter];
    [sp][bm][shutter]amix=inputs=3:duration=first[af]
  " \
  -map '[vf]' -map '[af]' \
  -c:v libx264 -crf 18 -preset fast -pix_fmt yuv420p \
  -c:a aac -b:a 192k main_v1.mp4
```

---

## Step 6 — Captions

Generate with `scripts/gen_captions_wheelhub.py` or `scripts/gen_captions_generic.py`.

Key parameters:
- `MAX_PHRASE = 4` — max words per caption line
- `GAP_THRESH = 0.35` — break phrase at pauses longer than this (seconds)

ASS style lines:
```
# Wheelhub
Style: Default,Manrope ExtraBold,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,3,8,60,60,340,1

# Wheelhub TeamTag popup
Style: TeamTag,Manrope ExtraBold,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,3,0,0,2,80,80,220,1
```

**Never use `force_style` in ffmpeg** — it bleeds into all subtitle styles. Let the ASS file handle styling.

---

## Step 7 — B-roll

B-roll clips must match output specs:
- Resolution: 1080×1920 (portrait)
- Frame rate: same as output (30fps Wheelhub, 24fps Sketchy)
- Format: H.264 MP4 with AAC audio (or silent)

Free sources (no auth required):
- **Mixkit**: `https://assets.mixkit.co/videos/{id}/{id}-1080.mp4`

If B-roll is landscape, convert to portrait:
```bash
ffmpeg -i landscape.mp4 \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" \
  -r 30 -c:v libx264 -crf 18 portrait.mp4
```

---

## Step 8 — Thumbnail Title Card

Generate with Freepik Mystic API:
```bash
curl -X POST https://api.freepik.com/v1/ai/mystic \
  -H "x-freepik-api-key: $FREEPIK_API_KEY" \
  -d '{"prompt":"...","aspect_ratio":"social_story_9_16","image_resolution":"2k"}'
# Poll GET /v1/ai/mystic/{task_id} until "COMPLETED"
```

Animate with HyperFrames: Ken Burns zoom-out (scale 1.12→1.0), vignette, fade in/out.
Insert AFTER "Welcome to..." intro line. During thumbnail: BGM at 2.5× volume.

---

## Step 9 — BGM & SFX

Wheelhub: lofi/chill. Sketchy: goofy/upbeat.

Freepik audio:
```bash
curl "https://api.freepik.com/v1/resources?type=audio&term=lofi" \
  -H "x-freepik-api-key: $FREEPIK_API_KEY"
```

Mix levels:
- Speech: `volume=2.0` (for iPhone footage)
- BGM: `volume=0.22` (Wheelhub), lower for Sketchy
- Camera shutter SFX: in `sfx/camera-shutter.wav`, delayed to B-roll entry points

---

## Step 10 — Outro

### Wheelhub
```bash
npx hyperframes render motion-graphics/wheelhub-outro --output renders/outro.mp4 --fps 30
```
Then xfade:
```bash
ffmpeg -y -i main_v1.mp4 -i renders/outro.mp4 \
  -filter_complex \
  '[0:v][1:v]xfade=transition=fade:duration=0.5:offset=83.0[vout];
   [0:a][1:a]acrossfade=d=0.5:curve1=exp:curve2=exp[aout]' \
  -map '[vout]' -map '[aout]' \
  -c:v libx264 -crf 18 -preset fast -pix_fmt yuv420p \
  -c:a aac -b:a 192k final_v1.mp4
```

### Sketchy Studio
```bash
npx hyperframes render motion-graphics/sketchy-outro --composition outro --fps 24 --quality high
```

---

## Step 11 — Loudnorm (two-pass)

```bash
# Pass 1 — measure
ffmpeg -i final_v1.mp4 -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null - 2>&1 | tail -20

# Pass 2 — apply measured values
ffmpeg -i final_v1.mp4 -af \
  "loudnorm=I=-14:TP=-1:LRA=11:measured_I=<I>:measured_TP=<TP>:measured_LRA=<LRA>:measured_thresh=<thresh>:linear=true" \
  -c:v copy -c:a aac -b:a 192k final_v1_loud.mp4
```

---

## Step 12 — Color Correction (optional, always offer after render)

After producing any final video, always ask:
> "Would you like to color correct this video? I can spin up the live color editor."

If yes:
```bash
cd /path/to/project && python3 ~/Documents/sketchy-video-editor/scripts/color_server.py
open http://localhost:7788
```

The editor provides Lightroom-style controls (Temperature, Tint, Saturation, Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Gamma R/G/B) with real ffmpeg-rendered preview frames. Output: `final_v{N+1}.mp4`.

---

## Versioning
- `base.mp4` — raw concat from render.py
- `main_vN.mp4` — assembled with overlays + captions (before outro)
- `final_vN.mp4` — with outro + loudnorm

---

## Common Issues & Fixes

| Problem | Fix |
|---|---|
| `libass not found` | `brew install ffmpeg-full` |
| iPhone output is 1920×3414 | Missing rotation fix — add `-metadata:s:v:0 rotate=0` and explicit `scale=...,pad=...` |
| Outro concat produces ~562s video | Re-encode outro to correct fps with silent AAC before concat; use `concat` filter not demuxer |
| Font not found by libass | `fc-query --format="%{family}\n" Manrope-ExtraBold.ttf` — exact family name must match `FontName=` |
| Captions not applying | Confirm `ffmpeg -version` shows `--enable-libass`; use single quotes around subtitles path |
| Audio bleeds after trim | Use `atrim=end=<t>` + `afade=out:start_time=<t-0.2>:duration=0.2` to hard cut cleanly |
| Canvas preview ≠ ffmpeg output | Use `color_server.py` `/preview` endpoint — renders actual ffmpeg frames, not canvas approximation |
