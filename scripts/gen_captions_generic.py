#!/usr/bin/env python3
"""Generate ASS captions from an ElevenLabs word-level transcript JSON.

Usage:
  python3 gen_captions_generic.py TRANSCRIPT OUTPUT [options]

Arguments:
  TRANSCRIPT   Path to ElevenLabs transcript JSON (word-level timestamps)
  OUTPUT       Path for the output .ass file

Options:
  --font       Font name (default: Manrope ExtraBold)
  --fontsize   Font size in points (default: 78)
  --alignment  ASS alignment (1-9, default: 8 = top-center)
  --marginv    Vertical margin in pixels (default: 340)
  --max-words  Max words per phrase (default: 4)
  --gap        Pause threshold in seconds to break a phrase (default: 0.35)
"""
import argparse, json
from pathlib import Path

parser = argparse.ArgumentParser(description='Generate ASS captions from ElevenLabs transcript')
parser.add_argument('transcript', help='Path to transcript JSON')
parser.add_argument('output',     help='Path for output .ass file')
parser.add_argument('--font',      default='Manrope ExtraBold')
parser.add_argument('--fontsize',  type=int, default=78)
parser.add_argument('--alignment', type=int, default=8)
parser.add_argument('--marginv',   type=int, default=340)
parser.add_argument('--max-words', type=int, default=4, dest='max_words')
parser.add_argument('--gap',       type=float, default=0.35)
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

# Group words into phrases based on pause length and max word count
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

# One event per word within each phrase; show all words up to and including current
events = []
for phrase in phrases:
    for i, word in enumerate(phrase):
        start_t = word['start']
        end_t   = phrase[i + 1]['start'] if i + 1 < len(phrase) else word['end']
        text    = ' '.join(f"{WHITE}{phrase[j]['text'].strip()}" for j in range(i + 1))
        events.append((start_t, end_t, text))

HEADER = f"""\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{args.font},{args.fontsize},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,3,{args.alignment},60,60,{args.marginv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""

lines = [HEADER]
for (start, end, text) in events:
    if end > start:
        lines.append(f"Dialogue: 0,{fmt_t(start)},{fmt_t(end)},Default,,0,0,0,,{text}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text('\n'.join(lines) + '\n')
print(f"Wrote {len(events)} events → {OUTPUT}")
