#!/usr/bin/env python3
"""
Generate captions for IMG_0359 — full video, all words captioned.
Wheelhub style: all white text, Manrope ExtraBold, top-aligned, non-overlapping phrases.
"""
import json
from pathlib import Path

TRANSCRIPT = Path('/Users/PrateekDarshan/Downloads/edit/transcripts/IMG_0359.json')
OUTPUT     = Path('/Users/PrateekDarshan/Downloads/img0359-edit/captions.ass')

WHITE  = r'{\c&H00FFFFFF&}'
YELLOW = r'{\c&H0023C6F7&}'   # Wheelhub yellow (for future use)

MAX_PHRASE = 4      # words per phrase
GAP_THRESH = 0.35   # seconds — break phrase at pauses longer than this

def fmt_t(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

# Load words
with open(TRANSCRIPT) as f:
    d = json.load(f)

words = [w for w in d['words'] if w['type'] == 'word' and w['text'].strip()]
print(f"Loaded {len(words)} words, {d['audio_duration_secs']:.1f}s")

# Group into phrases
phrases = []
current = []
for i, w in enumerate(words):
    current.append(w)
    nxt = words[i+1] if i+1 < len(words) else None
    gap = (nxt['start'] - w['end']) if nxt else 999.0
    if len(current) >= MAX_PHRASE or gap > GAP_THRESH or not nxt:
        phrases.append(current)
        current = []

print(f"Grouped into {len(phrases)} phrases")

# Generate events — one per word, non-overlapping, white text
events = []
for phrase in phrases:
    for i, word in enumerate(phrase):
        start_t = word['start']
        end_t = phrase[i+1]['start'] if i+1 < len(phrase) else word['end']

        # Build: previous words white, current word white (all white style)
        parts = []
        for j in range(i+1):
            parts.append(f"{WHITE}{phrase[j]['text'].strip()}")

        text = ' '.join(parts)
        events.append((start_t, end_t, text))

# Write ASS — proper v4.00+ format, all 23 style fields
HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Manrope ExtraBold,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,3,8,60,60,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

lines = [HEADER.rstrip()]
for (start, end, text) in events:
    if end > start:
        lines.append(f"Dialogue: 0,{fmt_t(start)},{fmt_t(end)},Default,,0,0,0,,{text}")

OUTPUT.write_text('\n'.join(lines) + '\n')
print(f"Wrote {len(events)} events → {OUTPUT}")
