# Wheelhub — Brand Guidelines

## Identity
Premium refurbished motorcycles. Tone: confident, energetic, trustworthy.

## Colors
| Element        | Hex       | ASS BGR          |
|----------------|-----------|------------------|
| Accent yellow  | `#F7C623` | `&H0023C6F7`     |
| Background dark| `#0A0A0A` |                  |
| White text     | `#FFFFFF` | `&H00FFFFFF`     |

## Typography
| Weight       | File                          |
|--------------|-------------------------------|
| ExtraBold    | `assets/fonts/Manrope-ExtraBold.ttf` |
| Bold         | `assets/fonts/Manrope-Bold.ttf`      |
| Regular      | `assets/fonts/Manrope-Regular.ttf`   |

## Assets
| File                        | Use                                          |
|-----------------------------|----------------------------------------------|
| `assets/Logo.png`           | Square icon logo (1229×973, yellow bg)       |
| `assets/FullLogo_black.png` | Full wordmark for outro (2914×448, RGBA)     |
| `assets/logo_watermark.png` | Pre-scaled watermark for top-left (140×110)  |

## Output Specs
- Resolution: 1080×1920 (portrait)
- Frame rate: **30fps**
- Target loudness: −14 LUFS / −1 dBTP / LRA 11

## Watermark
- File: `assets/logo_watermark.png`
- Position: `overlay=60:60` (top-left, 60px from each edge)

## Caption Style (ASS v4.00+)
- Font: Manrope ExtraBold, 78pt
- Color: all white — NO yellow word highlighting
- Alignment: `8` = top-center, or `2` = bottom-center
- MarginV: `340` (top) / `700` (center)
- No `force_style` in ffmpeg — let ASS file handle all styling
- Non-overlapping phrase events (max 4 words, break at >0.35s gap)
- Black outline (Outline=2), small shadow (Shadow=3)

```
Style: Default,Manrope ExtraBold,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,3,8,60,60,340,1
```

## Yellow Card Transition (brand signature)
Solid yellow frame (~2.5s) used as segment separator between major sections.

```bash
ffmpeg -y -f lavfi -i color=c=0xF7C623:size=1080x1920:rate=30:duration=2.5 \
  -f lavfi -i anullsrc=r=48000:cl=stereo \
  -shortest -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac yellow_card.mp4
```

## Outro (HyperFrames)
- Location: `motion-graphics/wheelhub-outro/`
- Duration: 4.5s, dark bg (#0A0A0A), yellow accents, FullLogo_black.png centered
- Render: `npx hyperframes render wheelhub-outro --output renders/outro.mp4 --fps 30`

## Speech Volume
- `volume=2.0` for iPhone talking head clips

## BGM
- Style: lofi/chill for talking heads (e.g. Mixkit "Sleepy Cat" ID 135)
- Mix at ~22% volume (`volume=0.22`)
- Fade out last 3s before video ends

## SFX
- Camera shutter on B-roll entry: `sfx/camera-shutter.wav`
