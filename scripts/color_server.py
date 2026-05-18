#!/usr/bin/env python3
"""Color editor — preview frames rendered by ffmpeg. http://localhost:7788

Configure your project by creating a project.json file next to this script:

{
  "sdr_src":           "~/path/to/source.MOV",
  "logo":              "~/path/to/logo_watermark.png",
  "logo_x":            60,
  "logo_y":            60,
  "bgm":               "~/path/to/bgm.mp3",
  "bgm_volume":        0.22,
  "bgm_duration":      84,
  "captions":          "captions.ass",
  "sdr_out":           "sdr/out.mp4",
  "outro":             "~/path/to/outro.mp4",
  "outro_offset":      83.0,
  "speech_volume":     2.0,
  "speech_end":        83.08,
  "speech_fade_start": 82.85,
  "broll": [
    {"file": "~/path/to/clip1.mp4", "start": 12.38, "end": 18.0},
    {"file": "~/path/to/clip2.mp4", "start": 28.96, "end": 36.0}
  ]
}
"""
import http.server, json, subprocess, threading, os

BASE = os.path.dirname(os.path.abspath(__file__))

_cfg = {}
_cfg_path = os.path.join(BASE, 'project.json')
if os.path.exists(_cfg_path):
    with open(_cfg_path) as _f:
        _cfg = json.load(_f)


def _p(key, default=''):
    val = _cfg.get(key) or os.environ.get(key.upper(), default)
    return os.path.expanduser(val) if val else default


SDR_SRC  = _p('sdr_src')
LOGO     = _p('logo')
BGM      = _p('bgm')
SHUTTER  = os.path.abspath(os.path.join(BASE, '..', 'sfx', 'camera-shutter.wav'))
CAPTIONS = _p('captions', os.path.join(BASE, 'captions.ass'))
SDR_OUT  = _p('sdr_out',  os.path.join(BASE, 'sdr_out.mp4'))
MAIN_OUT = os.path.join(BASE, 'main_preview.mp4')
OUTRO    = _p('outro')
FINAL    = os.path.join(BASE, 'final.mp4')

BROLL_CLIPS       = _cfg.get('broll', [])
SPEECH_END        = float(_cfg.get('speech_end', 0))
SPEECH_FADE_START = float(_cfg.get('speech_fade_start', max(0, SPEECH_END - 0.23)))
SPEECH_VOLUME     = float(_cfg.get('speech_volume', 2.0))
BGM_VOLUME        = float(_cfg.get('bgm_volume', 0.22))
BGM_DURATION      = float(_cfg.get('bgm_duration', 0))
LOGO_X            = _cfg.get('logo_x', 60)
LOGO_Y            = _cfg.get('logo_y', 60)
OUTRO_OFFSET      = float(_cfg.get('outro_offset', 0))

render_lock  = threading.Lock()
preview_lock = threading.Lock()

SETPARAMS = "setparams=range=tv:colorspace=bt709:color_primaries=bt709:color_trc=bt709"


def build_color_filter(v):
    temp  = float(v.get('temp',  0));  tint = float(v.get('tint',  0))
    sat   = float(v.get('sat',  20));  exp  = float(v.get('exp',   0))
    con   = float(v.get('con',   6));  hi   = float(v.get('hi',    0))
    sh    = float(v.get('sh',    0));  wh   = float(v.get('wh',    0))
    bk    = float(v.get('bk',    0));  gamma= float(v.get('gamma', 0))
    gr    = float(v.get('gr',    0));  gg   = float(v.get('gg',    0))
    gb    = float(v.get('gb',    0))

    cR = round(temp *  0.003, 4)
    cG = round(tint *  0.002, 4)
    cB = round(temp * -0.003, 4)
    colorbalance = (f"colorbalance=rs={cR}:gs={cG}:bs={cB}:"
                    f"rm={cR}:gm={cG}:bm={cB}:rh={cR}:gh={cG}:bh={cB}")

    saturation = round((sat + 100) / 100, 4)
    contrast   = round(1 + con * 0.005, 4)
    gval  = round(10 ** (-gamma / 100), 4)
    grval = round(10 ** (-gr    / 100), 4)
    ggval = round(10 ** (-gg    / 100), 4)
    gbval = round(10 ** (-gb    / 100), 4)
    eq = (f"eq=brightness=0:contrast={contrast}:saturation={saturation}:"
          f"gamma={gval}:gamma_r={grval}:gamma_g={ggval}:gamma_b={gbval}")

    S = 0.0025; CS = 0.0025; conArm = con * CS
    expF = 2 ** exp
    def cp(x, dy): return max(0, min(1, x * expF + dy))
    pts = (f"0/{cp(0, bk*S):.4f} "
           f"0.25/{cp(0.25, sh*S - conArm*0.4):.4f} "
           f"0.5/{cp(0.5, 0):.4f} "
           f"0.75/{cp(0.75, hi*S + conArm*0.4):.4f} "
           f"1/{cp(1, wh*S):.4f}")
    curves = f"curves=master='{pts}'"

    return f"{SETPARAMS},{colorbalance},{eq},{curves}"


def render_frame_jpeg(timestamp, vf, scale_w=540):
    """Extract a single frame from SDR_SRC, return JPEG bytes."""
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(timestamp), '-i', SDR_SRC,
        '-vf', f"{vf},scale={scale_w}:-2",
        '-vframes', '1',
        '-f', 'image2pipe', '-vcodec', 'mjpeg', '-q:v', '3',
        'pipe:1'
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=15)
    return r.stdout if r.returncode == 0 else None


def full_render(v):
    vf = build_color_filter(v)

    # Step 1: color-correct to SDR
    r = subprocess.run([
        'ffmpeg', '-y', '-i', SDR_SRC,
        '-vf', vf,
        '-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', SDR_OUT
    ], capture_output=True)
    if r.returncode != 0:
        return False, r.stderr.decode()[-400:]

    # Step 2: assemble — B-roll overlays, captions, logo watermark, audio mix
    n_broll = len(BROLL_CLIPS)
    inputs = ['-i', SDR_OUT]
    for clip in BROLL_CLIPS:
        inputs += ['-i', os.path.expanduser(clip['file'])]
    if LOGO:
        inputs += ['-i', LOGO]
    if BGM:
        inputs += ['-i', BGM]
    inputs += ['-i', SHUTTER]

    logo_idx    = 1 + n_broll
    bgm_idx     = logo_idx + (1 if LOGO else 0)
    shutter_idx = bgm_idx  + (1 if BGM  else 0)

    video_parts = []
    audio_parts = []

    # B-roll: offset each clip to its timeline position, then overlay in sequence
    for i, c in enumerate(BROLL_CLIPS):
        video_parts.append(f"[{i+1}:v]setpts=PTS-STARTPTS+({c['start']}/TB)[b{i}]")

    cur = '0:v'
    for i, c in enumerate(BROLL_CLIPS):
        nxt = f"ov{i}"
        video_parts.append(
            f"[{cur}][b{i}]overlay=0:0:enable='between(t,{c['start']},{c['end']})':format=auto[{nxt}]"
        )
        cur = nxt

    if os.path.exists(CAPTIONS):
        video_parts.append(f"[{cur}]subtitles='{CAPTIONS}'[cap]")
        cur = 'cap'

    if LOGO:
        video_parts.append(f"[{cur}][{logo_idx}:v]overlay={LOGO_X}:{LOGO_Y}[vf_out]")
        cur = 'vf_out'

    # Speech: boost, fade, trim
    audio_parts.append(
        f"[0:a]volume={SPEECH_VOLUME},"
        f"afade=out:start_time={SPEECH_FADE_START}:duration=0.23,"
        f"atrim=end={SPEECH_END},asetpts=PTS-STARTPTS[sp]"
    )

    # BGM: trim, fade out last 3s
    if BGM and BGM_DURATION:
        bgm_fade = max(0.0, BGM_DURATION - 3)
        audio_parts.append(
            f"[{bgm_idx}:a]atrim=start=0:end={BGM_DURATION},"
            f"afade=out:start_time={bgm_fade}:duration=3,"
            f"volume={BGM_VOLUME}[bm]"
        )

    # Shutter SFX: one delayed copy per B-roll entry point
    if n_broll:
        splits = ''.join(f'[sh{i}]' for i in range(n_broll))
        audio_parts.append(f"[{shutter_idx}:a]asplit={n_broll}{splits}")
        for i, c in enumerate(BROLL_CLIPS):
            ms = int(c['start'] * 1000)
            audio_parts.append(f"[sh{i}]adelay={ms}|{ms}[sh{i}d]")
        mixed = ''.join(f'[sh{i}d]' for i in range(n_broll))
        audio_parts.append(f"{mixed}amix=inputs={n_broll}:duration=longest[shutter]")

    # Mix all audio streams
    audio_streams = ['[sp]']
    if BGM and BGM_DURATION:
        audio_streams.append('[bm]')
    if n_broll:
        audio_streams.append('[shutter]')

    if len(audio_streams) > 1:
        audio_parts.append(
            f"{''.join(audio_streams)}amix=inputs={len(audio_streams)}:duration=first[af]"
        )
        audio_out = 'af'
    else:
        audio_out = 'sp'

    fc = ';'.join(video_parts + audio_parts)
    video_map = ['-map', f'[{cur}]'] if video_parts else ['-map', '0:v']

    r = subprocess.run([
        'ffmpeg', '-y',
        *inputs,
        '-filter_complex', fc,
        *video_map,
        '-map', f'[{audio_out}]',
        '-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', MAIN_OUT
    ], capture_output=True)
    if r.returncode != 0:
        return False, r.stderr.decode()[-400:]

    # Step 3: append outro with xfade transition
    if OUTRO and os.path.exists(OUTRO):
        r = subprocess.run([
            'ffmpeg', '-y', '-i', MAIN_OUT, '-i', OUTRO,
            '-filter_complex',
            f'[0:v][1:v]xfade=transition=fade:duration=0.5:offset={OUTRO_OFFSET}[vout];'
            '[0:a][1:a]acrossfade=d=0.5:curve1=exp:curve2=exp[aout]',
            '-map', '[vout]', '-map', '[aout]',
            '-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k', FINAL
        ], capture_output=True)
        if r.returncode != 0:
            return False, r.stderr.decode()[-400:]
        return True, FINAL

    return True, MAIN_OUT


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        content = open(os.path.join(BASE, 'color_editor.html'), 'rb').read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = json.loads(self.rfile.read(length))

        if self.path == '/preview':
            timestamp = float(body.get('timestamp', 2))
            mode      = body.get('mode', 'after')
            vals      = body.get('vals', {})
            vf = SETPARAMS if mode == 'before' else build_color_filter(vals)
            with preview_lock:
                jpeg = render_frame_jpeg(timestamp, vf)
            if jpeg:
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', len(jpeg))
                self.end_headers()
                self.wfile.write(jpeg)
            else:
                self.send_json(500, {'error': 'frame render failed'})

        elif self.path == '/render':
            if not render_lock.acquire(blocking=False):
                self.send_json(503, {'ok': False, 'error': 'Already rendering'})
                return
            try:
                ok, result = full_render(body)
                self.send_json(200, {'ok': ok, 'error': result if not ok else ''})
            finally:
                render_lock.release()
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    if not SDR_SRC:
        print('Warning: sdr_src not set. Create a project.json or set SDR_SRC env var.')
    server = http.server.HTTPServer(('localhost', 7788), Handler)
    print('Color editor: http://localhost:7788  (ffmpeg-accurate preview)')
    server.serve_forever()
