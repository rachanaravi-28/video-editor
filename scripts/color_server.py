#!/usr/bin/env python3
"""Accurate color editor — preview frames rendered by ffmpeg directly. http://localhost:7788"""
import http.server, json, subprocess, threading, os, math, urllib.parse

BASE     = os.path.dirname(os.path.abspath(__file__))
SDR_SRC  = os.path.expanduser('~/Downloads/IMG_0359.MOV')
BROLL    = os.path.join(BASE, 'broll_portrait')
LOGO     = os.path.expanduser('~/Downloads/wheelhub-edit/logo_small.png')
BGM      = os.path.join(BASE, 'bgm_lofi.mp3')
SHUTTER  = os.path.expanduser('~/Downloads/camera-shutter/camera-shutter.wav')
CAPTIONS = os.path.join(BASE, 'captions.ass')
SDR_OUT  = os.path.join(BASE, 'sdr', 'IMG_0359.mp4')
MAIN_OUT = os.path.join(BASE, 'main_preview.mp4')
OUTRO    = os.path.join(BASE, 'yellow_outro.mp4')
FINAL    = os.path.join(BASE, 'final_v7.mp4')

render_lock  = threading.Lock()
preview_lock = threading.Lock()   # separate lock so preview never blocks full render

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
    """Run ffmpeg to extract a single frame, return JPEG bytes."""
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
    r = subprocess.run([
        'ffmpeg','-y','-t','84','-i',SDR_SRC,
        '-vf', vf,
        '-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k', SDR_OUT
    ], capture_output=True)
    if r.returncode != 0: return False, r.stderr.decode()[-400:]

    fc = (
        "[1:v]setpts=PTS-STARTPTS+(12.38/TB)[e];"
        "[2:v]setpts=PTS-STARTPTS+(28.96/TB)[op];"
        "[3:v]setpts=PTS-STARTPTS+(36.46/TB)[oc];"
        "[4:v]setpts=PTS-STARTPTS+(50.44/TB)[ch];"
        "[5:v]setpts=PTS-STARTPTS+(54.52/TB)[br];"
        "[0:v][e]overlay=0:0:enable='between(t,12.38,18.0)':format=auto[o1];"
        "[o1][op]overlay=0:0:enable='between(t,28.96,36.0)':format=auto[o2];"
        "[o2][oc]overlay=0:0:enable='between(t,36.46,48.5)':format=auto[o3];"
        "[o3][ch]overlay=0:0:enable='between(t,50.44,54.5)':format=auto[o4];"
        "[o4][br]overlay=0:0:enable='between(t,54.52,56.5)':format=auto[o5];"
        f"[o5]subtitles='{CAPTIONS}'[o6];"
        "[o6][6:v]overlay=60:60[vf];"
        # Speech: boost volume, fade out just before 'and' (83.099s), hard cut at 83.08s
        "[0:a]volume=2.0,afade=out:start_time=82.85:duration=0.23,atrim=end=83.08,asetpts=PTS-STARTPTS[sp];"
        "[7:a]atrim=start=0:end=84,afade=out:start_time=80:duration=3,volume=0.22[bm];"
        # Shutter SFX: 5 delayed copies at each B-roll entry point
        "[8:a]asplit=5[sh0][sh1][sh2][sh3][sh4];"
        "[sh0]adelay=12380|12380[sh0d];"
        "[sh1]adelay=28960|28960[sh1d];"
        "[sh2]adelay=36460|36460[sh2d];"
        "[sh3]adelay=50440|50440[sh3d];"
        "[sh4]adelay=54520|54520[sh4d];"
        "[sh0d][sh1d][sh2d][sh3d][sh4d]amix=inputs=5:duration=longest[shutter];"
        "[sp][bm][shutter]amix=inputs=3:duration=first[af]"
    )
    r = subprocess.run([
        'ffmpeg','-y',
        '-i',SDR_OUT,
        '-i',os.path.join(BROLL,'engine.mp4'),'-i',os.path.join(BROLL,'oil_pour.mp4'),
        '-i',os.path.join(BROLL,'oil_change.mp4'),'-i',os.path.join(BROLL,'chain.mp4'),
        '-i',os.path.join(BROLL,'brakes.mp4'),'-i',LOGO,'-i',BGM,'-i',SHUTTER,
        '-filter_complex',fc,'-map','[vf]','-map','[af]',
        '-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k', MAIN_OUT
    ], capture_output=True)
    if r.returncode != 0: return False, r.stderr.decode()[-400:]

    r = subprocess.run([
        'ffmpeg','-y','-i',MAIN_OUT,'-i',OUTRO,
        '-filter_complex',
        '[0:v][1:v]xfade=transition=fade:duration=0.5:offset=83.0[vout];'
        '[0:a][1:a]acrossfade=d=0.5:curve1=exp:curve2=exp[aout]',
        '-map','[vout]','-map','[aout]',
        '-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k', FINAL
    ], capture_output=True)
    if r.returncode != 0: return False, r.stderr.decode()[-400:]
    return True, FINAL


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        content = open(os.path.join(BASE,'color_editor.html'),'rb').read()
        self.send_response(200); self.send_header('Content-Type','text/html')
        self.send_header('Content-Length',len(content)); self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        length = int(self.headers.get('Content-Length',0))
        body   = json.loads(self.rfile.read(length))

        if self.path == '/preview':
            timestamp = float(body.get('timestamp', 2))
            mode      = body.get('mode', 'after')   # 'before' or 'after'
            vals      = body.get('vals', {})

            vf = SETPARAMS if mode == 'before' else build_color_filter(vals)

            with preview_lock:
                jpeg = render_frame_jpeg(timestamp, vf)

            if jpeg:
                self.send_response(200)
                self.send_header('Content-Type','image/jpeg')
                self.send_header('Content-Length', len(jpeg))
                self.end_headers(); self.wfile.write(jpeg)
            else:
                self.send_json(500, {'error':'frame render failed'})

        elif self.path == '/render':
            if not render_lock.acquire(blocking=False):
                self.send_json(503, {'ok':False,'error':'Already rendering'}); return
            try:
                ok, result = full_render(body)
                self.send_json(200, {'ok':ok,'error':result if not ok else ''})
            finally:
                render_lock.release()
        else:
            self.send_response(404); self.end_headers()


if __name__ == '__main__':
    server = http.server.HTTPServer(('localhost',7788), Handler)
    print('Color editor: http://localhost:7788  (ffmpeg-accurate preview)')
    server.serve_forever()
