#!/usr/bin/env python3
"""
Zmanda product walkthrough assembler.

Usage:
  python3 zmanda_assemble.py project.json

Reads project.json and produces final.mp4. See zmanda_project.template.json
for all available fields.
"""
import json, subprocess, os, sys, tempfile
from pathlib import Path

# Fixed brand assets — update these paths if assets move
BRAND_BG_PLAIN = (
    "/Users/rachanaravishankar/Library/CloudStorage/"
    "OneDrive-SharedLibraries-BETSOL/Team Marketing - Documents/"
    "2026/Thumbnail/Desktop Wallpaper/BETSOL Wallpaper - 31.png"
)
BRAND_BG_ZPRO = (
    "/Users/rachanaravishankar/Library/CloudStorage/"
    "OneDrive-SharedLibraries-BETSOL/Team Marketing - Documents/"
    "2026/Thumbnail/Desktop Wallpaper/BETSOL Wallpaper - 30.png"
)
BRAND_OUTRO = (
    "/Users/rachanaravishankar/Library/CloudStorage/"
    "OneDrive-SharedLibraries-BETSOL/Team Marketing - Documents/"
    "01. Marketing Assets/01. Zmanda/Outro/ZProOutro26.mp4"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, label=""):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        tail = r.stderr.decode()[-600:]
        raise RuntimeError(f"{label} failed:\n{tail}")
    return r


def probe_video(path):
    """Return (width, height, duration) of a video file."""
    r = subprocess.run([
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_streams', '-show_format', path
    ], capture_output=True)
    d = json.loads(r.stdout)
    v = next(s for s in d['streams'] if s['codec_type'] == 'video')
    dur = float(d['format']['duration'])
    return int(v['width']), int(v['height']), dur


def xp(val):
    """Expand user path."""
    return os.path.expanduser(str(val)) if val else ''


# ---------------------------------------------------------------------------
# Step 1: Apply cuts (and optional speed ramps) to produce trimmed video
# ---------------------------------------------------------------------------

def apply_cuts(recording, cuts, speed_ramps, out_path):
    """
    Remove cut segments, optionally speed up speed_ramp segments.
    Outputs video-only (no audio — voiceover is handled separately).

    cuts:        [{"start": 10.5, "end": 18.0}, ...]   segments to REMOVE
    speed_ramps: [{"start": 5.0, "end": 15.0, "speed": 2.0}, ...]
    """
    _, _, duration = probe_video(recording)

    # Build a timeline of segments to keep, each with a speed multiplier
    # Start from a single segment covering the whole recording
    segments = [{"start": 0.0, "end": duration, "speed": 1.0}]

    # Apply speed ramps: split any segment that overlaps a ramp
    for ramp in sorted(speed_ramps, key=lambda x: x['start']):
        rs, re, sp = float(ramp['start']), float(ramp['end']), float(ramp['speed'])
        new_segs = []
        for seg in segments:
            ss, se = seg['start'], seg['end']
            if re <= ss or rs >= se:
                new_segs.append(seg)          # no overlap
            else:
                if ss < rs:
                    new_segs.append({"start": ss, "end": rs, "speed": seg['speed']})
                new_segs.append({"start": max(ss, rs), "end": min(se, re), "speed": sp})
                if re < se:
                    new_segs.append({"start": re, "end": se, "speed": seg['speed']})
        segments = new_segs

    # Remove cut segments
    kept = []
    for seg in segments:
        ss, se = seg['start'], seg['end']
        # Drop if this segment's midpoint falls inside any cut
        mid = (ss + se) / 2
        in_cut = any(float(c['start']) <= mid <= float(c['end']) for c in cuts)
        if not in_cut and se > ss:
            kept.append(seg)

    if not kept:
        raise RuntimeError("All footage removed after applying cuts.")

    # Build filter_complex: trim + setpts (+ speed) + concat
    vparts = []
    filter_parts = []
    for i, seg in enumerate(kept):
        ss, se, sp = seg['start'], seg['end'], seg['speed']
        pts = f"PTS*{1/sp}" if sp != 1.0 else "PTS-STARTPTS"
        filter_parts.append(
            f"[0:v]trim=start={ss}:end={se},setpts={pts}[v{i}]"
        )
        vparts.append(f"[v{i}]")

    n = len(kept)
    filter_parts.append(f"{''.join(vparts)}concat=n={n}:v=1:a=0[vout]")
    fc = ';'.join(filter_parts)

    run([
        'ffmpeg', '-y', '-i', recording,
        '-filter_complex', fc,
        '-map', '[vout]',
        '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p',
        '-r', '30', out_path
    ], "apply_cuts")
    print(f"  Kept {n} segment(s) after cuts.")


# ---------------------------------------------------------------------------
# Step 2: Composite + audio → main section
# ---------------------------------------------------------------------------

def build_main_section(cfg, trimmed_video, out_path):
    """
    Composites the trimmed recording onto the Zmanda background, adds shadow,
    applies blur regions, captions, voiceover, and BGM.
    """
    # --- Recording placement ---
    rec_w     = int(cfg.get('rec_w', 1500))
    rec_x     = int(cfg.get('rec_x', 210))
    rec_y     = int(cfg.get('rec_y', 103))

    # --- Shadow ---
    shad_opacity = float(cfg.get('shadow_opacity', 0.55))
    shad_blur    = int(cfg.get('shadow_blur', 20))
    shad_dx      = int(cfg.get('shadow_dx', 0))
    shad_dy      = int(cfg.get('shadow_dy', 12))
    shad_pad     = 60   # transparent padding added before blur for soft edges

    # --- Audio ---
    voiceover  = xp(cfg['voiceover'])
    vo_offset  = float(cfg.get('voiceover_offset', 0.0))
    bgm        = xp(cfg.get('bgm', ''))
    bgm_db     = float(cfg.get('bgm_db', -35))
    bgm_vol    = round(10 ** (bgm_db / 20), 6)

    # --- Other assets ---
    captions   = xp(cfg.get('captions', ''))
    bg         = xp(cfg.get('background', BRAND_BG_PLAIN))
    blurs      = cfg.get('blurs', [])

    _, _, video_dur = probe_video(trimmed_video)

    # --- Build input list ---
    # [0] background image, [1] trimmed recording, [2] voiceover, [3?] bgm
    inputs = [
        '-loop', '1', '-i', bg,          # [0] background (loop as image)
        '-i', trimmed_video,              # [1] recording
        '-i', voiceover,                  # [2] voiceover
    ]
    bgm_stream = None
    if bgm and os.path.exists(bgm):
        inputs += ['-i', bgm]
        bgm_stream = 3

    # --- Video filter chain ---
    shadow_x = rec_x - shad_pad + shad_dx
    shadow_y = rec_y - shad_pad + shad_dy

    # Color value for colorchannelmixer to create black semi-transparent shadow
    shad_aa = round(shad_opacity, 3)

    parts = [
        # Scale recording to target width, preserve aspect ratio
        f"[1:v]scale={rec_w}:-2:flags=lanczos,setsar=1[rec]",

        # Shadow: make black + semi-transparent, pad with transparency, blur edges
        f"[rec]format=rgba,"
        f"colorchannelmixer=rr=0:gg=0:bb=0:aa={shad_aa},"
        f"pad=iw+{shad_pad*2}:ih+{shad_pad*2}:{shad_pad}:{shad_pad}:color=#00000000,"
        f"boxblur={shad_blur}:3[shadow]",

        # Layer: background → shadow → recording
        f"[0:v][shadow]overlay={shadow_x}:{shadow_y}:format=auto[bg_shadow]",
        f"[bg_shadow][rec]overlay={rec_x}:{rec_y}[bg_rec]",
    ]
    cur = 'bg_rec'

    # Blur regions (coordinates in output/1920x1080 space unless coordinate_space=recording)
    coord_space = cfg.get('coordinate_space', 'output')
    if coord_space == 'recording':
        # Need to know original recording width to compute scale factor
        orig_w, _, _ = probe_video(cfg.get('_trimmed_path', trimmed_video))
        scale_f = rec_w / orig_w
    else:
        scale_f = 1.0
        rec_ox, rec_oy = 0, 0  # no offset needed for output coords

    for i, b in enumerate(blurs):
        bx = int(b['x'] * scale_f + (rec_x if coord_space == 'recording' else 0))
        by = int(b['y'] * scale_f + (rec_y if coord_space == 'recording' else 0))
        bw = int(b['w'] * scale_f)
        bh = int(b['h'] * scale_f)
        t0, t1 = float(b['start']), float(b['end'])
        enable = f"between(t,{t0},{t1})"

        # Split cur so it feeds both crop and overlay
        parts += [
            f"[{cur}]split[{cur}_a][{cur}_b]",
            f"[{cur}_b]crop={bw}:{bh}:{bx}:{by},"
            f"boxblur=luma_radius=12:luma_power=3[blurpatch{i}]",
            f"[{cur}_a][blurpatch{i}]overlay={bx}:{by}:enable='{enable}'[blurred{i}]",
        ]
        cur = f'blurred{i}'

    # Captions
    if captions and os.path.exists(captions):
        # Escape path for libass (backslashes and colons)
        safe_cap = captions.replace('\\', '/').replace(':', '\\:')
        parts.append(f"[{cur}]subtitles='{safe_cap}'[captioned]")
        cur = 'captioned'

    # --- Audio filter chain ---
    delay_ms = int(vo_offset * 1000)
    audio_parts = [
        f"[2:a]adelay={delay_ms}|{delay_ms}[vo_delayed]"
    ]
    audio_outs = ['[vo_delayed]']

    if bgm_stream is not None:
        bgm_fade_at = max(0.0, video_dur - 2.0)
        audio_parts.append(
            f"[{bgm_stream}:a]afade=out:start_time={bgm_fade_at}:duration=2,"
            f"volume={bgm_vol}[bgm_out]"
        )
        audio_outs.append('[bgm_out]')

    if len(audio_outs) > 1:
        audio_parts.append(
            f"{''.join(audio_outs)}amix=inputs={len(audio_outs)}:duration=first[af]"
        )
        audio_out = 'af'
    else:
        audio_out = 'vo_delayed'

    # --- Assemble filter_complex ---
    fc = ';'.join(parts + audio_parts)

    duration_args = ['-t', str(video_dur)]  # trim to recording length

    run([
        'ffmpeg', '-y',
        *inputs,
        *duration_args,
        '-filter_complex', fc,
        '-map', f'[{cur}]',
        '-map', f'[{audio_out}]',
        '-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        '-r', '30', out_path
    ], "build_main_section")


# ---------------------------------------------------------------------------
# Step 3: Concat intro + main + outro
# ---------------------------------------------------------------------------

def concat_segments(segments, out_path):
    """Re-encode all segments to the same spec and concat."""
    inputs = []
    for s in segments:
        inputs += ['-i', s]

    n = len(segments)
    v_streams = ''.join(f'[{i}:v]' for i in range(n))
    a_streams = ''.join(f'[{i}:a]' for i in range(n))

    # Scale all to 1920x1080 in case intro/outro differ slightly
    scale_parts = []
    for i in range(n):
        scale_parts.append(f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=disable,setsar=1[sv{i}]")
    scaled_v = ''.join(f'[sv{i}]' for i in range(n))
    scale_parts.append(f"{scaled_v}concat=n={n}:v=1:a=0[vout]")
    scale_parts.append(f"{a_streams}concat=n={n}:v=0:a=1[aout]")

    fc = ';'.join(scale_parts)

    run([
        'ffmpeg', '-y',
        *inputs,
        '-filter_complex', fc,
        '-map', '[vout]', '-map', '[aout]',
        '-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        '-r', '30', out_path
    ], "concat_segments")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 zmanda_assemble.py project.json")
        sys.exit(1)

    cfg_path = sys.argv[1]
    with open(cfg_path) as f:
        cfg = json.load(f)

    recording = xp(cfg['recording'])
    intro     = xp(cfg.get('intro', ''))
    outro     = xp(cfg.get('outro', BRAND_OUTRO))
    out_path  = xp(cfg.get('output', os.path.join(os.path.dirname(os.path.abspath(cfg_path)), 'final.mp4')))

    cuts        = cfg.get('cuts', [])
    speed_ramps = cfg.get('speed_ramps', [])

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        trimmed = os.path.join(tmp, 'trimmed.mp4')
        main_mp4 = os.path.join(tmp, 'main.mp4')

        print("Step 1/3: Applying cuts...")
        apply_cuts(recording, cuts, speed_ramps, trimmed)

        print("Step 2/3: Compositing and mixing audio...")
        cfg['_trimmed_path'] = trimmed
        build_main_section(cfg, trimmed, main_mp4)

        print("Step 3/3: Concatenating intro + main + outro...")
        segments = []
        if intro and os.path.exists(intro):
            segments.append(intro)
        segments.append(main_mp4)
        if outro and os.path.exists(outro):
            segments.append(outro)

        if len(segments) == 1:
            import shutil
            shutil.copy(main_mp4, out_path)
        else:
            concat_segments(segments, out_path)

    print(f"\nDone → {out_path}")


if __name__ == '__main__':
    main()
