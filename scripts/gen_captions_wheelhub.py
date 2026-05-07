#!/usr/bin/env python3
"""
Regenerate Wheelhub captions.ass
- Clean non-overlapping phrase events (no double-lines)
- Current word yellow, context words white
- Team name pop-up tags when first mentioned
- Proper ASS v4.00+ format
"""
import json
from pathlib import Path

EDL_PATH   = Path('/Users/PrateekDarshan/Downloads/wheelhub-edit/edl.json')
TRANS_DIR  = Path('/Users/PrateekDarshan/Downloads/wheelhub-edit/sdr/edit/transcripts')
OUTPUT     = Path('/Users/PrateekDarshan/Downloads/wheelhub-edit/captions.ass')

YELLOW = r'{\c&H0023C6F7&}'   # #F7C623 yellow
WHITE  = r'{\c&H00FFFFFF&}'   # white

# Team name → bike answer
TEAM_ANSWERS = {
    'CSK': 'Triumph Street Triple 765',
    'DC': 'Splendor',
    'KKR': 'R15',
    'RCB': 'RX100',
    'MI': 'TVS XL',
}

def fmt_t(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def load_words(clip):
    p = TRANS_DIR / f"{clip}.json"
    with open(p) as f:
        d = json.load(f)
    return [w for w in d['words'] if w['type'] == 'word']

# ── 1. Load EDL and map words to output timeline ─────────────────────────────
with open(EDL_PATH) as f:
    edl = json.load(f)

all_words = []   # [{text, start_out, end_out}, ...]
cursor = 0.0

for rng in edl['ranges']:
    src = rng['source']
    s0, s1 = rng['start'], rng['end']
    dur = s1 - s0
    out_s = cursor
    cursor += dur

    words = load_words(src)
    for w in words:
        if s0 <= w['start'] < s1:
            out_start = out_s + (w['start'] - s0)
            out_end   = out_s + min(w['end'] - s0, dur)
            txt = w['text'].strip()
            if txt:
                all_words.append({
                    'text': txt,
                    'start': out_start,
                    'end': out_end,
                    'src': src,
                })

# ── 2. Group into phrases ─────────────────────────────────────────────────────
# Break phrase when: gap > 0.35s OR phrase length >= 4 words
MAX_PHRASE = 4
GAP_THRESH = 0.35

phrases = []
current = []
for i, w in enumerate(all_words):
    current.append(w)
    nxt = all_words[i+1] if i+1 < len(all_words) else None
    gap = (nxt['start'] - w['end']) if nxt else 999.0
    if len(current) >= MAX_PHRASE or gap > GAP_THRESH or not nxt:
        phrases.append(current)
        current = []

# ── 3. Generate caption events (no overlaps) ─────────────────────────────────
caption_events = []

for phrase in phrases:
    for i, word in enumerate(phrase):
        start_t = word['start']
        # End exactly when next word (or next phrase) starts — no overlap
        end_t   = phrase[i+1]['start'] if i+1 < len(phrase) else word['end']

        # Build text: white context + yellow current word
        parts = []
        for j in range(i+1):
            w_text = phrase[j]['text']
            if j < i:
                parts.append(f"{WHITE}{w_text}")
            else:
                parts.append(f"{YELLOW}{w_text}{WHITE}")

        text = ' '.join(parts)
        caption_events.append((start_t, end_t, text, 'Default'))

# ── 4. Team name pop-up events ───────────────────────────────────────────────
team_events = []
mentioned = set()

# Map team name spellings in transcript to canonical
TEAM_ALIASES = {
    'CSK': 'CSK', 'CSK?': 'CSK', 'CSK,': 'CSK',
    'DC': 'DC', 'DC?': 'DC', 'DC,': 'DC',
    'KKR': 'KKR', 'KKR?': 'KKR', 'KKR.': 'KKR', 'KKR,': 'KKR',
    'RCB': 'RCB', 'RCB?': 'RCB', 'RCB.': 'RCB', 'RCB,': 'RCB',
    'MI': 'MI', 'MI?': 'MI', 'MI,': 'MI', 'MI.': 'MI',
}

for w in all_words:
    key = TEAM_ALIASES.get(w['text'].strip())
    if key and key not in mentioned and key in TEAM_ANSWERS:
        mentioned.add(key)
        t_start = w['start']
        t_end   = t_start + 2.2
        answer  = TEAM_ANSWERS[key]
        pop_text = f"{WHITE}{key}  {YELLOW}→  {WHITE}{answer}"
        team_events.append((t_start, t_end, pop_text, 'TeamTag'))
        print(f"  Team pop: {key} at {t_start:.2f}s → '{answer}'")

# KKR and MI asked off-screen — hardcode at their segment start times
# Compute segment start times from EDL
seg_cursor = 0.0
seg_times = {}
for rng in edl['ranges']:
    seg_times[rng['beat']] = seg_cursor
    seg_cursor += rng['end'] - rng['start']

for team, beat, answer in [('KKR', 'MANISH_KKR', 'R15'), ('MI', 'SANTOSH_MI', 'TVS XL')]:
    if team not in mentioned and beat in seg_times:
        mentioned.add(team)
        t_start = seg_times[beat]
        t_end   = t_start + 2.2
        pop_text = f"{WHITE}{team}  {YELLOW}→  {WHITE}{answer}"
        team_events.append((t_start, t_end, pop_text, 'TeamTag'))
        print(f"  Team pop (hardcoded): {team} at {t_start:.2f}s → '{answer}'")

# ── 5. Write ASS file ─────────────────────────────────────────────────────────
HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Manrope ExtraBold,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,3,8,60,60,340,1
Style: TeamTag,Manrope ExtraBold,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,3,0,0,2,80,80,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

all_events = sorted(caption_events + team_events, key=lambda x: x[0])

lines = [HEADER.rstrip()]
for (start, end, text, style) in all_events:
    if end > start:
        lines.append(f"Dialogue: 0,{fmt_t(start)},{fmt_t(end)},{style},,0,0,0,,{text}")

OUTPUT.write_text('\n'.join(lines) + '\n')
print(f"\nWrote {len(caption_events)} caption events + {len(team_events)} team tags")
print(f"Output: {OUTPUT}")
