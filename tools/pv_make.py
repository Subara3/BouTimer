# PV の場面を、画面を録画せずに作る
#   python tools/pv_make.py G H I        （場面の記号。省くと全部）
#
# 1. tools\pvstage.ax を quiet で動かす（舞台の窓は前に出さず、重なり順のいちばん後ろに置く。フォーカスを取らない）
# 2. 舞台の窓の中身を PrintWindow で写す（自分の窓なので、ほかの窓に隠れていても写る）
# 3. 本体を pvmode で動かす。足場と前面の窓を舞台の窓だけで決め、2コマごとの絵と位置を proto\pvf に書き出す
# 4. 背景・舞台の窓・棒人間（・認識の図示・はじめましての窓・偽のマウス）を重ねて 30fps の動画にし、
#    書き出した時刻に、同梱の声と効果音を重ねる
# 使っている人の画面は写さない。棒人間の窓は画面の下のほうに出るが、フォーカスは取らない
import array, ctypes, glob, os, shutil, subprocess, sys, time, wave
from ctypes import wintypes
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO = os.path.join(ROOT, "proto")
TOOLS = os.path.join(ROOT, "tools")
OUT = os.path.join(ROOT, "pv", "new")
HSP = r"C:\hsp37\hsp3utf.exe"
CMP = r"C:\hsp37\hspcmp.exe"
W, H = 1280, 720

# 記号: (ファイル名, 本体に渡すモード, 前面にする舞台の窓 1=メモ 2=YouTube 3=エディタ, 秒数の上限, カメラの寄り)
# 寄りが 1 より大きいと、棒人間を追いかけて、その倍率で寄る（舞台が広く、棒人間が小さく見えるため）
SCENES = {
    "A": ("A_いろいろな動き", "show", 1, 120, 1.8),
    "B": ("B_つつく・投げる・登る", "interact", 1, 70, 1.5),
    "C": ("C_休憩でふちに座る", "test", 3, 30, 1.4),
    "D": ("D_サボり先に札", "scold", 2, 40, 1.5),
    "G": ("G_はじめまして", "wizardtest wzauto", 1, 50, 1.0),
    "H": ("H_やることにチェック", "tdchecktest tdnoundo", 3, 20, 2.0),
    "I": ("I_認識の図示", "realtest ovl", 1, 30, 1.0),
    "J": ("J_珠音のドット絵", "show tamane", 1, 120, 2.2),
    "K": ("K_タイマーで一時停止", "clicktest", 1, 14, 1.8),
    "L": ("L_やることリストと内訳", "pvlisttest", 1, 16, 1.0),
    "R": ("R_道さがし", "pvroutetest", 1, 26, 1.0),
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


WINTITLE = {2: "今日の内訳と1週間の記録", 10: "やることリスト", 11: "はじめまして"}
_frames = {}


def framed(client, wid):
    # 中身だけを写した小さな窓に、Windows 11 ふうの枠（題名の帯と ─ □ ✕）を描き足す
    key = (wid, client.size)
    w, h = client.size
    tb = 32
    if key not in _frames:
        from PIL import ImageFont
        fr = Image.new("RGBA", (w + 2, h + tb + 1), (243, 243, 243, 255))
        d = ImageDraw.Draw(fr)
        d.rectangle([0, 0, w + 1, h + tb], outline=(200, 200, 205, 255))
        f = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 12)
        icon = Image.open(os.path.join(TOOLS, "boutimer_icon.png")).convert("RGBA").resize((16, 16), Image.LANCZOS)
        fr.alpha_composite(icon, (10, 8))
        d.text((34, 8), WINTITLE.get(wid, ""), font=f, fill=(40, 40, 48, 255))
        c = (70, 70, 80, 255)
        bx = w - 24
        d.line([(bx - 5, 11), (bx + 5, 21)], fill=c, width=1); d.line([(bx - 5, 21), (bx + 5, 11)], fill=c, width=1)
        bx -= 46
        d.rectangle([bx - 5, 11, bx + 5, 21], outline=c)
        bx -= 46
        d.line([(bx - 5, 16), (bx + 5, 16)], fill=c, width=1)
        _frames[key] = fr
    out = _frames[key].copy()
    out.paste(client, (1, tb))
    return out


def cursor(img, x, y):
    d = ImageDraw.Draw(img)
    pts = [(x, y), (x, y + 18), (x + 5, y + 14), (x + 9, y + 22), (x + 12, y + 21), (x + 8, y + 13), (x + 14, y + 13)]
    d.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0))


def run_scene(key, ff):
    name, mode, fg, limit, zoom = SCENES[key]
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
        elif p[0] == "WZ": wzs.setdefault(int(p[1]), []).append((int(p[2]), int(p[3]), int(p[4]), int(p[5]), int(p[6]) if len(p) > 6 else 11))
        elif p[0].isdigit(): frames.append(tuple(int(v) for v in p[:6]))
    os.makedirs(OUT, exist_ok=True)
    silent = os.path.join(OUT, "_silent.mp4")
    enc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", "30", "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    cur_ov = None; cur_wz = {}
    camx = camy = None
    for n, fr, cx, cy, fmx, fmy in frames:
        img = base.copy()
        if n in ovs:
            vx, vy = ovs[n]
            cur_ov = (Image.open(os.path.join(pvf, "ov_%05d.png" % n)).convert("RGBA"), vx - ox, vy - oy)
        if cur_ov: put(img, cur_ov[0], cur_ov[1], cur_ov[2])
        if n in wzs:
            for x, y, w, h, wid in wzs[n]:
                cl = Image.open(os.path.join(pvf, "w%d_%05d.bmp" % (wid, n))).convert("RGBA").crop((0, 0, w, h))
                cur_wz[wid] = (framed(cl, wid), x - 1 - ox, y - 32 - oy, n)
        for wid in list(cur_wz):
            wz, x, y, seen = cur_wz[wid]
            if n - seen > 3: del cur_wz[wid]; continue
            shadow(img, x, y, wz.width, wz.height)
            put(img, wz, x, y)
        ch = Image.open(os.path.join(pvf, "%05d.png" % n)).convert("RGBA")
        put(img, ch, cx - ox, cy - oy)
        if "tdcheck" in mode or "interact" in mode or "clicktest" in mode:
            if (fmx, fmy) != (0, 0) and fmx > -9000: cursor(img, fmx - ox, fmy - oy)
        if zoom > 1.0:
            # カメラ：棒人間の体のあたりを、ゆっくり追いかける
            tx, ty = cx - ox + ch.width / 2, cy - oy + ch.height * 0.55
            if camx is None: camx, camy = tx, ty
            camx += (tx - camx) * 0.06; camy += (ty - camy) * 0.06
            cw, chh = W / zoom, H / zoom
            l = min(max(camx - cw / 2, 0), W - cw); t = min(max(camy - chh / 2, 0), H - chh)
            img = img.crop((int(l), int(t), int(l + cw), int(t + chh))).resize((W, H), Image.LANCZOS)
        enc.stdin.write(img.convert("RGB").tobytes())
    enc.stdin.close(); enc.wait()
    # 音：書き出した時刻（コマ ÷ 60 秒）に、同梱の声と効果音を重ねる。数が多いとコマンドが長すぎるので、Python の中で足し合わせる
    final = os.path.join(OUT, name + ".mp4")
    rate = 48000
    total = int(len(frames) / 30.0 * rate) * 2
    mix = array.array("i", bytes(4 * total))
    cache = {}
    used = 0
    for fr, kind, nm in events:
        f = os.path.join(PROTO, "voice" if kind == "voice" else "se", nm + ".wav")
        if not os.path.exists(f): continue
        if f not in cache:
            raw = subprocess.run([ff, "-loglevel", "error", "-i", f, "-ar", str(rate), "-ac", "2", "-f", "s16le", "-"], capture_output=True, check=True).stdout
            a16 = array.array("h"); a16.frombytes(raw); cache[f] = a16
        src = cache[f]
        at = int(fr / 60.0 * rate) * 2
        n = min(len(src), total - at)
        for i in range(max(0, n)):
            mix[at + i] += src[i]
        used += 1
    out16 = array.array("h", (max(-32768, min(32767, v)) for v in mix))
    wavp = os.path.join(OUT, "_mix.wav")
    with wave.open(wavp, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate); w.writeframes(out16.tobytes())
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", silent, "-i", wavp, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", final], check=True)
    os.remove(wavp)
    flt = range(used)
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
