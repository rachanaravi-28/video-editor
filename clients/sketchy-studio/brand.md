# Sketchy Studio — Brand Guidelines

## Identity
Social media content studio. Tone: goofy, funny, engaging, fast-paced.

## Colors
| Element        | Hex       | ASS BGR          |
|----------------|-----------|------------------|
| Primary purple | `#9355E6` | `&H00E65593`     |
| Background dark| `#0d0d0d` |                  |
| White text     | `#FFFFFF` | `&H00FFFFFF`     |

## Typography
| Weight  | File                                    |
|---------|-----------------------------------------|
| Black   | `assets/fonts/Satoshi-Black.otf`        |
| Bold    | `assets/fonts/Satoshi-Bold.otf`         |
| Medium  | `assets/fonts/Satoshi-Medium.otf`       |

## Assets
| File                       | Use                           |
|----------------------------|-------------------------------|
| `assets/Logo_black.png`    | Logo on light backgrounds     |
| `assets/Logo_white.png`    | Logo on dark backgrounds      |

## Output Specs
- Resolution: 1080×1920 (portrait)
- Frame rate: **24fps**
- Target loudness: −14 LUFS / −1 dBTP / LRA 11

## Caption Style
- Font: Satoshi Black, word-by-word pop animation with blur
- Current word: purple highlight (`#9355E6`)
- Context words: white
- Plain text over video — no background box
- Centered in frame, high MarginV to avoid Instagram UI overlap

## Outro (HyperFrames)
- Location: `motion-graphics/sketchy-outro/`
- White background (#ffffff), 4s
- Logo_black.png pops in center with GSAP `back.out(1.8)`, scale 0→1 in 0.7s
- Render: `npx hyperframes render motion-graphics/ --composition outro --fps 24 --quality high`

## Score Badges (for ranking content)
- Small pill overlay: dark bg, large purple rating number, white "/10", grey name
- Center-screen, above captions
- Slide-in 0.35s ease_out, hold 3s
- Bell/ting SFX on appearance
- Generated as solid MP4 clips via PIL, overlaid with ffmpeg

## BGM
- Style: goofy, funny, upbeat — NOT cinematic
- Mix low so speech is clearly audible
- Source: Freepik API (`GET https://api.freepik.com/v1/resources?type=audio`)
