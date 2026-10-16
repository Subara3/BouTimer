# PV の場面を、画面を録画せずに作る
#   python tools/pv_make.py G H I        （場面の記号。省くと全部）
#
# 1. tools\pvstage.ax を quiet で動かす（舞台の窓は前に出さず、重なり順のいちばん後ろに置く。フォーカスを取らない）
# 2. 舞台の窓の中身を PrintWindow で写す（自分の窓なので、ほかの窓に隠れていても写る）
# 3. 本体を pvmode で動かす。足場と前面の窓を舞台の窓だけで決め、2コマごとの絵と位置を proto\pvf に書き出す
# 4. 背景・舞台の窓・棒人間（・認識の図示・はじめましての窓・偽のマウス）を重ねて 30fps の動画にし、
#    書き出した時刻に、同梱の声と効果音を重ねる
# 使っている人の画面は写さない。棒人間の窓は画面の下のほうに出るが、フォーカスは取らない
import ctypes, glob, os, shutil, subprocess, sys, time
from ctypes import wintypes
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO = os.path.join(ROOT, "proto")
TOOLS = os.path.join(ROOT, "tools")
OUT = os.path.join(ROOT, "pv", "new")
HSP = r"C:\hsp37\hsp3utf.exe"
CMP = r"C:\hsp37\hspcmp.exe"
W, H = 1280, 720

# 記号: (ファイル名, 本体に渡すモード, 前面にする舞台の窓 1=メモ 2=YouTube 3=エディタ, 秒数の上限)
SCENES = {
    "A": ("A_いろいろな動き", "show", 1, 120),
    "B": ("B_つつく・投げる・登る", "interact", 1, 70),
    "C": ("C_休憩でふちに座る", "test", 3, 30),
    "D": ("D_サボり先に札", "scold", 2, 40),
    "G": ("G_はじめまして", "wizardtest wzauto", 1, 50),
    "H": ("H_やることにチェック", "tdchecktest tdnoundo", 3, 20),
    "I": ("I_認識の図示", "realtest ovl", 1, 30),
    "J": ("J_珠音の髪型", "show tamane", 1, 120),
}

u32 = ctypes.windll.user32
u32.SetProcessDPIAware()
dwm = ctypes.windll.dwmapi


class RECT(ctypes.Structure):
    _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]


def ffmpeg():
    base = os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "WinGet", "Packages")
    return glob.glob(os.path.join(base, "**", "ffmpeg.exe"), recursive=True)[0]


def workarea():
    r = RECT()
    u32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)
    return r


def rects(h):
    r = RECT(); u32.GetWindowRect(h, ctypes.byref(r))
    d = RECT(); dwm.DwmGetWindowAttribute(wintypes.HWND(h), 9, ctypes.byref(d), ctypes.sizeof(d))
    return r, d


def printwindow(h, w, hh):
    # 窓の中身をメモリの DC に写して、PIL の画像にする（PW_RENDERFULLCONTENT）
    g32 = ctypes.windll.gdi32
    hdc = u32.GetDC(0)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, hh)
    g32.SelectObject(mdc, bmp)
    u32.PrintWindow(h, mdc, 2)

    class BIH(ctypes.Structure):
        _fields_ = [("size", ctypes.c_uint32), ("w", ctypes.c_int32), ("h", ctypes.c_int32), ("planes", ctypes.c_uint16),
                    ("bits", ctypes.c_uint16), ("comp", ctypes.c_uint32), ("isz", ctypes.c_uint32), ("x", ctypes.c_int32),
                    ("y", ctypes.c_int32), ("cu", ctypes.c_uint32), ("ci", ctypes.c_uint32)]
    bi = BIH(40, w, -hh, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * hh * 4)
    g32.GetDIBits(mdc, bmp, 0, hh, buf, ctypes.byref(bi), 0)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(0, hdc)
    return Image.frombuffer("RGBA", (w, hh), buf.raw, "raw", "BGRA", 0, 1).convert("RGB")


def background():
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        c = y * 40 // 720
        d.line([(0, y), (W - 1, y)], fill=(236 - c, 240 - c, 246 - c // 2))
    return bg


def shadow(base, x, y, w, h):
    sh = Image.new("RGBA", (w + 24, h + 24), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([12, 14, w + 12, h + 14], 8, fill=(0, 0, 0, 40))
    base.alpha_composite(sh, (x - 12, y - 12))


def put(img, src, x, y):
    # はみ出す部分を切ってから重ねる
    l, t = max(0, -x), max(0, -y)
    r, b = min(src.width, W - x), min(src.height, H - y)
    if r <= l or b <= t: return
    img.alpha_composite(src.crop((l, t, r, b)), (x + l, y + t))


def cursor(img, x, y):
    d = ImageDraw.Draw(img)
    pts = [(x, y), (x, y + 18), (x + 5, y + 14), (x + 9, y + 22), (x + 12, y + 21), (x + 8, y + 13), (x + 14, y + 13)]
    d.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0))


def run_scene(key, ff):
    name, mode, fg, limit = SCENES[key]
    wa = workarea()
    ox, oy = 0, wa.b - H
    hwfile = os.path.join(TOOLS, "pvstage_hwnd.txt")
    if os.path.exists(hwfile): os.remove(hwfile)
    stage = subprocess.Popen([HSP, "pvstage.ax", "%d 0 %d %d quiet" % (limit + 20, oy, fg)], cwd=TOOLS)
    for _ in range(50):
        if os.path.exists(hwfile) and os.path.getsize(hwfile) > 0: break
        time.sleep(0.2)
    time.sleep(0.8)
    wins = []
    for line in open(hwfile, encoding="utf-8"):
        p = line.split()
        if len(p) < 2: continue
        h = int(p[1]); r, d = rects(h)
        img = printwindow(h, r.r - r.l, r.b - r.t)
        img = img.crop((d.l - r.l, d.t - r.t, d.r - r.l, d.b - r.t))
        wins.append((int(p[0]), img, d.l - ox, d.t - oy))
    # 舞台の土台：背景と窓（前面の窓をいちばん上に）
    base = background().convert("RGBA")
    for num, img, x, y in sorted(wins, key=lambda w: (w[0] == fg, -w[0])):
        shadow(base, x, y, img.width, img.height)
        base.paste(img, (x, y))
    mx, my = d.l - r.l, d.t - r.t  # 見えない枠の幅（PrintWindow の絵の切りとりに使う）
    # 本体を動かす
    pvf = os.path.join(PROTO, "pvf")
    shutil.rmtree(pvf, ignore_errors=True)
    t0 = time.time()
    subprocess.run([HSP, "main.ax", "%s pvmode pvfg%d pvframes pvvoice pvsec%d" % (mode, fg, limit)], cwd=PROTO, timeout=limit + 60)
    stage.kill()
    print(key, "ran %.1fs" % (time.time() - t0))
    # 書き出しを読む
    frames, events, ovs, wzs = [], [], {}, {}
    for line in open(os.path.join(pvf, "frames.txt"), encoding="utf-8", errors="replace"):
        p = line.split()
        if not p: continue
        if p[0] == "EV": events.append((int(p[1]), p[2], p[3]))
        elif p[0] == "OV": ovs[int(p[1])] = (int(p[2]), int(p[3]))
        elif p[0] == "WZ": wzs[int(p[1])] = (int(p[2]), int(p[3]), int(p[4]), int(p[5]))
        elif p[0].isdigit(): frames.append(tuple(int(v) for v in p[:6]))
    os.makedirs(OUT, exist_ok=True)
    silent = os.path.join(OUT, "_silent.mp4")
    enc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", "30", "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    cur_ov = None; cur_wz = None; last_wz = -99
    for n, fr, cx, cy, fmx, fmy in frames:
        img = base.copy()
        if n in ovs:
            vx, vy = ovs[n]
            cur_ov = (Image.open(os.path.join(pvf, "ov_%05d.png" % n)).convert("RGBA"), vx - ox, vy - oy)
        if cur_ov: put(img, cur_ov[0], cur_ov[1], cur_ov[2])
        if n in wzs:
            x, y, w, h = wzs[n]
            wz = Image.open(os.path.join(pvf, "wz_%05d.bmp" % n)).convert("RGBA").crop((mx, my, w - mx, h - mx))
            cur_wz = (wz, x + mx - ox, y + my - oy); last_wz = n
        if cur_wz and n - last_wz <= 3:
            shadow(img, cur_wz[1], cur_wz[2], cur_wz[0].width, cur_wz[0].height)
            put(img, cur_wz[0], cur_wz[1], cur_wz[2])
        ch = Image.open(os.path.join(pvf, "%05d.png" % n)).convert("RGBA")
        put(img, ch, cx - ox, cy - oy)
        if "tdcheck" in mode or "interact" in mode:
            if (fmx, fmy) != (0, 0) and fmx > -9000: cursor(img, fmx - ox, fmy - oy)
        enc.stdin.write(img.convert("RGB").tobytes())
    enc.stdin.close(); enc.wait()
    # 音：書き出した時刻（コマ ÷ 60 秒）に、同梱の声と効果音を重ねる
    final = os.path.join(OUT, name + ".mp4")
    ins, flt = [], []
    for fr, kind, nm in events:
        f = os.path.join(PROTO, "voice" if kind == "voice" else "se", nm + ".wav")
        if not os.path.exists(f): continue
        ins += ["-i", f]
        k = len(ins) // 2
        ms = int(fr * 1000 / 60)
        flt.append("[%d:a]aresample=48000,aformat=channel_layouts=stereo,adelay=%d|%d[a%d]" % (k, ms, ms, k))
    if flt:
        mix = "".join("[a%d]" % (i + 1) for i in range(len(flt)))
        fc = ";".join(flt) + ";%samix=inputs=%d:normalize=0,apad[aout]" % (mix, len(flt))
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", silent] + ins + ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", final], check=True)
    else:
        shutil.move(silent, final)
    if os.path.exists(silent): os.remove(silent)
    shutil.rmtree(pvf, ignore_errors=True)
    print(key, name, "%d frames, %d sounds" % (len(frames), len(flt)))


def main():
    ff = ffmpeg()
    subprocess.run([CMP, r"--compath=C:\hsp37\common" + "\\", "-i", "-u", "-d", "-omain.ax", "main.hsp"], cwd=PROTO, capture_output=True)
    subprocess.run([CMP, r"--compath=C:\hsp37\common" + "\\", "-i", "-u", "-opvstage.ax", "pvstage.hsp"], cwd=TOOLS, capture_output=True)
    keys = sys.argv[1:] or list(SCENES)
    for k in keys:
        run_scene(k, ff)


main()
