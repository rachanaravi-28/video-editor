#!/usr/bin/env python3
"""
Generate ASS captions for Zmanda product walkthrough videos.

Style: Satoshi Medium, white text, dark semi-transparent pill background,
bottom-center, optimised for 1920x1080.

Usage:
  python3 zmanda_captions.py TRANSCRIPT OUTPUT [options]

Arguments:
  TRANSCRIPT   ElevenLabs word-level transcript JSON
  OUTPUT       Output .ass file path

Options:
  --font        Font name (default: Satoshi Medium)
  --fontsize    Font size in points (default: 50)
  --marginv     Bottom margin in pixels (default: 80)
  --max-words   Max words per caption phrase (default: 7)
  --gap         Pause threshold in seconds to break phrase (default: 0.4)
"""
import argparse, json
from pathlib import Path

parser = argparse.ArgumentParser(description='Generate Zmanda walkthrough captions')
parser.add_argument('transcript', help='Path to ElevenLabs transcript JSON')
parser.add_argument('output',     help='Path for output .ass file')
parser.add_argument('--font',      default='Satoshi Medium')
parser.add_argument('--fontsize',  type=int, default=50)
parser.add_argument('--marginv',   type=int, default=80)
parser.add_argument('--max-words', type=int, default=7, dest='max_words')
parser.add_argument('--gap',       type=float, default=0.4)
args = parser.parse_args()

TRANSCRIPT = Path(args.transcript)
OUTPUT     = Path(args.output)
WHITE      = r'{\c&H00FFFFFF&}'


def fmt_t(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


with open(TRANSCRIPT) as f:
    d = json.load(f)

words = [w for w in d['words'] if w['type'] == 'word' and w['text'].strip()]
print(f"Loaded {len(words)} words, {d['audio_duration_secs']:.1f}s")

# Group into phrases
phrases = []
current = []
for i, w in enumerate(words):
    current.append(w)
    nxt = words[i + 1] if i + 1 < len(words) else None
    gap = (nxt['start'] - w['end']) if nxt else 999.0
    if len(current) >= args.max_words or gap > args.gap or not nxt:
        phrases.append(current)
        current = []

print(f"Grouped into {len(phrases)} phrases")

# One dialogue event per phrase (full phrase visible at once, not word-by-word)
# This matches the style in the example video — full sentence shown, not karaoke
events = []
for phrase in phrases:
    start_t = phrase[0]['start']
    end_t   = phrase[-1]['end']
    # Add a small gap between phrases to avoid overlap
    if events:
        prev_end = events[-1][1]
        start_t  = max(start_t, prev_end + 0.02)
    text = ' '.join(w['text'].strip() for w in phrase)
    if end_t > start_t:
        events.append((start_t, end_t, text))

print(f"Generated {len(events)} caption events")

# ASS header
# BorderStyle=3: opaque box background (BackColour fills behind text)
# Outline=20: padding around text inside the box
# BackColour=&H99000000: dark background, ~60% opaque (&H99 = alpha 153 in ASS = ~40% visible)
# In ASS alpha: 0x00=fully opaque, 0xFF=fully transparent → &H66 = 102 = 60% opaque
HEADER = f"""\
[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{args.font},{args.fontsize},&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,0,0,0,0,100,100,0,0,3,20,0,2,80,80,{args.marginv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""

lines = [HEADER]
for (start, end, text) in events:
    lines.append(f"Dialogue: 0,{fmt_t(start)},{fmt_t(end)},Default,,0,0,0,,{text}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text('\n'.join(lines) + '\n')
print(f"Wrote {len(events)} events → {OUTPUT}")
