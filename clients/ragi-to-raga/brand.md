# Ragi to Raga — Brand Guidelines

## Client
Ragi to Raga is a restaurant in Bengaluru on Kanakapura Road, next to Doddakalsandra metro station. Known for traditional, natural food (ragi-based, no maida/baking soda/artificial colors), North Karnataka specialties, and a lush green ambience.

## Video Style
- **Caption font**: Satoshi Black, 78pt, all-white, no highlight
- **Caption alignment**: Alignment=2 (bottom-center), MarginV=700
- **Caption ordering**: Apply `subtitles` filter AFTER B-roll overlay, BEFORE food image overlays — so captions show on B-roll but are hidden under food images
- **BGM**: Classical Indian / ambient Indian instrumental (`assets/bgm_indian_meditations.mp3`)
- **Logo watermark**: `assets/Logo.png` scaled to ~200px wide, placed top-left at (60, 60)
- **Outro**: `assets/outro.mp4` — 12.3s branded outro, append with 0.5s xfade cross dissolve

## iPhone HLG → SDR Conversion (Hable tone map — use for ALL iPhone footage)
```
zscale=t=linear:npl=203:m=bt2020nc:r=tv,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv:p=bt709,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p
```
**Do NOT use `setparams` — it's a no-op relabel that doesn't change pixels.**

## Audio Levels
- Speech: `volume=2.0`
- BGM: `volume=0.22`, fade out last 3s

## Food Image Assets
- `assets/pizza_portrait.jpg` — Ragi pizza on golden yellow bg (#C1921D), padded to 1080×1920
- `assets/halbai_portrait.jpg` — Ragi Halbai, padded to 1080×1920 with black bg
- When displaying food images, use `loop=loop=-1:size=1:start=0` to hold the still image
- For rotating pizza: `rotate='t*0.05':ow=iw:oh=ih:fillcolor=0xC1921D` (fillcolor must match image bg)
- To sample exact background color: `ffmpeg -i img.png -vf "crop=50:50:10:10,scale=1:1:flags=area" -frames:v 1 -f rawvideo -pix_fmt rgb24 pipe:1 | python3 -c "import sys; d=sys.stdin.buffer.read(3); print(f'#{d[0]:02X}{d[1]:02X}{d[2]:02X}')"`
- When padding images, use the sampled color: `pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0xC1921D`

## B-Roll
- Metro clip: show when speaker mentions metro (~17s in edited timeline)
- PTS offset for overlay: `setpts=PTS-STARTPTS+(START_TIME/TB)` — critical, without this B-roll is exhausted before the overlay window
- Add camera shutter SFX at B-roll entry: `sfx/camera-shutter.wav`

## Whip Transitions Between Cuts
```
[v1][v2]xfade=transition=slideleft:duration=0.15:offset=(dur_v1-0.15)
[a1][a2]acrossfade=d=0.15
```
- Add whip SFX at each xfade offset: `sfx/whip-woosh.mp3` via `adelay=<ms>|<ms>`
- Segment timing: recalculate after each xfade (subtract 0.15s per transition)

## Caption Text Fixes (ElevenLabs transcription artifacts)
Add to `FIXES` dict in `scripts/gen_captions_ragi.py`:
```python
FIXES = {
    'Ragi 2 Raga': 'Ragi to Raga',
    'Doddaballapalem': 'Doddakalsandra',
    'Girmir': 'Girmit',
}
```

## ffmpeg Critical Notes
- `xfade` and all filters after it require `fps=30,format=yuv420p` to prevent "Error reinitializing filters"
- Apply `fps=30,format=yuv420p` after every `concat` and after every overlay chain before xfade
- Always use absolute path in `subtitles=` filter (single-quoted)
- B-roll overlay: `enable='between(t,START,END)'` uses output timeline time
- When trimming from non-zero start: adjust all downstream timestamps accordingly
  - `new_time = (t_orig - start_trim) - sum(cut_durations_before_t)`
- Per-segment xfade shifts: captions in seg N → subtract `N * xfade_dur` from timestamps

## Full Pipeline Order (filter_complex)
```
1. trim + HLG tone map per segment → [v1][v2][v3]...
2. xfade between segments → [vcat]
3. B-roll overlay (with PTS offset) → [vbroll]
4. subtitles filter → [vsub]         ← MUST be here (after broll, before food)
5. Food image overlays (loop+rotate) → [vfood]
6. Logo overlay → [vmain]
7. xfade to outro → [vfinal]
```
