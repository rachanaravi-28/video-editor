#!/usr/bin/env python3
"""Generate ASS captions for Ragi to Raga from ElevenLabs transcript JSON."""
import json, sys

FONT = "Satoshi Black"
FONT_SIZE = 78
MARGIN_V = 700
MAX_WORDS = 4
MIN_GAP = 0.35  # seconds gap to break phrase

def ts(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    cs = int(round((sec - int(sec)) * 100))
    return f"{h}:{m:02d}:{int(sec):02d}.{cs:02d}"

with open('/Users/PrateekDarshan/Downloads/ragi-edit/transcript.json') as f:
    data = json.load(f)

words = [w for w in data.get('words', []) if w.get('type') == 'word']

# Group into phrases
phrases = []
current = []
for i, w in enumerate(words):
    current.append(w)
    next_w = words[i+1] if i+1 < len(words) else None
    gap = (next_w['start'] - w['end']) if next_w else 999
    if len(current) >= MAX_WORDS or gap >= MIN_GAP:
        phrases.append(current)
        current = []
if current:
    phrases.append(current)

# Build ASS
header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT},{FONT_SIZE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,3,2,60,60,{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

lines = [header]
for phrase in phrases:
    start = phrase[0]['start']
    end = phrase[-1]['end']
    text = ' '.join(w['text'] for w in phrase)
    lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{text}")

out = '\n'.join(lines)
with open('/Users/PrateekDarshan/Downloads/ragi-edit/captions.ass', 'w') as f:
    f.write(out)

print(f"Generated {len(phrases)} caption events")
print(f"Duration: {words[-1]['end']:.1f}s")
