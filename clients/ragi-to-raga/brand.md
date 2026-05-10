# Ragi to Raga — Brand Guidelines

## Client
Ragi to Raga is a restaurant in Bengaluru on Kanakapura Road, next to Doddaballapalem metro station. Known for traditional, natural food (ragi-based, no maida/baking soda/artificial colors), North Karnataka specialties, and a lush green ambience.

## Video Style
- **Caption font**: Satoshi Black, 78pt, all-white, no highlight
- **Caption alignment**: Alignment=2 (bottom-center), MarginV=700
- **BGM**: Classical Indian / ambient Indian instrumental (Mixkit "Indian Meditations" ID 21 included)
- **Logo watermark**: `assets/Logo.png` scaled to ~200px wide, placed top-left at (60, 60)
- **Outro**: `assets/outro.mp4` — 12.3s branded outro, append with 0.5s xfade cross dissolve

## Source Footage
- iPhone HLG (arib-std-b67, bt2020nc) — use `setparams` relabeling approach for SDR conversion
- Typical resolution: 3840x2160 (4K), auto-rotated to 1080x1920 portrait by ffmpeg
- Conversion filter (Hable tone map — preferred, produces natural iPhone look):
  `zscale=t=linear:npl=203:m=bt2020nc:r=tv,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv:p=bt709,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p`

## Audio Levels
- Speech: volume=2.0
- BGM: volume=0.15

## B-Roll
- When speaker mentions metro: insert metro B-roll clip at that timestamp
- Use `setpts=PTS-STARTPTS` on B-roll + `overlay=0:0:enable='between(t,START,END)'`
- Add camera shutter SFX at B-roll start (see `sfx/camera-shutter.wav` in repo root)

## ffmpeg Notes
- Always add `fps=30,format=yuv420p` before `xfade` to prevent "Error reinitializing filters"
- Subtitles filter must use absolute path in single quotes

## Transcription
- Use ElevenLabs Scribe v1 with `timestamps_granularity=word`
- Script: `scripts/gen_captions_ragi.py`
