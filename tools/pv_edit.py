# PV を組み立てる（審査員に見せる用）
#   python tools/pv_make.py      … 場面の素材（pv\new）
#   python tools/pv_narration.py … ナレーション（pv\narr。VOICEVOX:No.7）
#   python tools/pv_edit.py      … これ。pv\PV_作業のおとも、棒人間_1.0.mp4 を作る
#
# 前半「できること」、後半「どうやって動いているか」の2部。
# 場面ごとにナレーションと字幕をつけ、場面のあいだは切り替え効果でつなぐ。章の見出しとおわりは、舞台と同じ色の札で出す。
# 並びと使う秒は下の PLAN で変えられる。字幕の文は pv_narration.py の LINES
import glob, json, os, subprocess, wave
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "pv", "new")
NARR = os.path.join(ROOT, "pv", "narr")
OUT = os.path.join(ROOT, "pv", "PV_作業のおとも、棒人間_1.0.mp4")
TMP = os.path.join(ROOT, "pv", "_edit")
W, H, FPS = 1280, 720, 30
FB = "C:/Windows/Fonts/meiryob.ttc"
FR = "C:/Windows/Fonts/meiryo.ttc"
INK = (46, 46, 54)
ACCENT = (64, 196, 164)  # アイコンのミント

TITLE = "作業のおとも、棒人間"
SUB = "作業集中用のポモドーロタイマー"

# ("clip", 素材の記号, [(はじめ, 長さ), ...], ナレーション, 左上の札, 寄り)  寄り：0 なし、正なら少しずつ寄る、負なら少しずつ引く
# ("card", 見出し, 小見出し, 秒)
PLAN = [
    ("clip", "J", [(0.0, 8.0)], "op", None, 0.0),
    ("card", "できること", "1", 2.4),
    ("clip", "C", [(5.0, 9.0)], "c", "ポモドーロタイマー", 0.10),
    ("clip", "K", [(1.0, 5.2)], "k", "タイマーで一時停止", 0.0),
    ("clip", "H", [(2.0, 7.0)], "h", "やることリスト", 0.08),
    ("clip", "L", [(0.6, 11.0)], "l", "かかった時間と1週間の記録", 0.0),
    ("clip", "D", [(5.0, 5.4)], "d", "サボり先に札", 0.10),
    ("clip", "G", [(1.0, 6.0)], "g", "はじめての起動", 0.0),
    ("clip", "B", [(11.0, 4.0), ("A", 1.5, 4.5)], "b", "つまむ・投げる・お茶", 0.0),
    ("clip", "J", [(2.0, 4.0)], "j", "着せ替え（珠音）", 0.12),
    ("card", "どうやって動いているか", "2", 2.6),
    ("clip", "I", [(2.0, 8.4)], "i", "認識の図示", -0.06),
    ("clip", "A", [(58.0, 6.0)], "r", "窓を渡る道さがし", 0.0),
    ("clip", "J", [(30.0, 7.4)], "p", "1秒に60回の描画", 0.15),
    ("mods", 6.2),
    ("end", 5.0),
]
XF = ["fade", "smoothleft", "circleopen", "smoothup", "wipeleft", "fadewhite", "smoothright", "circleclose", "smoothdown", "fade"]
XD = 0.5


def ffmpeg():
    base = os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "WinGet", "Packages")
    return glob.glob(os.path.join(base, "**", "ffmpeg.exe"), recursive=True)[0]


def wav_len(p):
    with wave.open(p) as w:
        return w.getnframes() / w.getframerate()


def bg():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        c = y * 40 // 720
        d.line([(0, y), (W - 1, y)], fill=(236 - c, 240 - c, 246 - c // 2))
    return im


def stick(d, x, y, s=1.0, pose="sit"):
    # 札のふちに腰かける棒人間（取扱説明書と同じ形）
    lw = int(5 * s)
    hx, hy = x, y - 58 * s
    d.line([(x, y - 2 * s), (x, y - 40 * s)], fill=INK, width=lw)
    d.line([(x, y - 2 * s), (x + 22 * s, y), (x + 24 * s, y + 26 * s)], fill=INK, width=lw, joint="curve")
    d.line([(x, y - 2 * s), (x + 16 * s, y + 4 * s), (x + 12 * s, y + 30 * s)], fill=INK, width=lw, joint="curve")
    if pose == "wave":
        d.line([(x, y - 34 * s), (x + 18 * s, y - 52 * s), (x + 26 * s, y - 76 * s)], fill=INK, width=lw, joint="curve")
    else:
        d.line([(x, y - 34 * s), (x + 20 * s, y - 20 * s)], fill=INK, width=lw)
    d.line([(x, y - 34 * s), (x - 16 * s, y - 16 * s)], fill=INK, width=lw)
    r = 17 * s
    d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 255, 255), outline=INK, width=lw)
    d.ellipse([hx + 2 * s, hy - 6 * s, hx + 6 * s, hy - 1 * s], fill=INK)
    d.ellipse([hx + 9 * s, hy - 6 * s, hx + 13 * s, hy - 1 * s], fill=INK)
    d.arc([hx + 1 * s, hy - 2 * s, hx + 14 * s, hy + 9 * s], 20, 160, fill=INK, width=max(2, int(2.5 * s)))


def card_png(path, title, num):
    im = bg()
    d = ImageDraw.Draw(im)
    fb = ImageFont.truetype(FB, 64)
    fn = ImageFont.truetype(FB, 30)
    tw = d.textlength(title, font=fb)
    bx0, by0 = (W - tw) / 2 - 56, 300
    d.rounded_rectangle([bx0, by0, bx0 + tw + 112, by0 + 120], 22, fill=(255, 255, 255), outline=(220, 222, 230), width=2)
    d.text(((W - tw) / 2, by0 + 22), title, font=fb, fill=INK)
    # 章の番号（ミントの丸）
    d.ellipse([bx0 - 28, by0 - 28, bx0 + 32, by0 + 32], fill=ACCENT)
    d.text((bx0 + 2 - d.textlength(num, font=fn) / 2, by0 - 22), num, font=fn, fill=(255, 255, 255))
    stick(d, bx0 + tw + 70, by0 + 2, 1.2, "wave")
    im.save(path)


def mods_png(path):
    im = bg()
    d = ImageDraw.Draw(im)
    fh = ImageFont.truetype(FB, 34)
    fm = ImageFont.truetype(FB, 26)
    fs = ImageFont.truetype(FR, 22)
    d.text((140, 110), "技術の核は、モジュールにして同梱", font=fh, fill=INK)
    rows = [("mod_alphawin.as", "画素ごとに半透明な窓（GDI+ と UpdateLayeredWindow）"),
            ("mod_deskwin.as", "開いている窓を、手前から足場として集める（DWM の実寸）"),
            ("mod_peakmeter.as", "再生中の音の大きさと拍（Core Audio。録音はしない）")]
    for i, (a, b) in enumerate(rows):
        y = 200 + i * 112
        d.rounded_rectangle([140, y, 1140, y + 88], 16, fill=(255, 255, 255), outline=(220, 222, 230), width=2)
        d.rectangle([140, y, 150, y + 88], fill=ACCENT)
        d.text((176, y + 12), a, font=fm, fill=INK)
        d.text((176, y + 50), b, font=fs, fill=(90, 90, 100))
    d.text((140, 560), "ソース：github.com/Subara3/BouTimer", font=fm, fill=(60, 120, 110))
    stick(d, 1080, 202, 0.9)
    im.save(path)


def end_png(path):
    im = bg()
    d = ImageDraw.Draw(im)
    fb = ImageFont.truetype(FB, 64)
    fm = ImageFont.truetype(FB, 30)
    fs = ImageFont.truetype(FR, 20)
    tw = d.textlength(TITLE, font=fb)
    d.text(((W - tw) / 2, 200), TITLE, font=fb, fill=INK)
    sw = d.textlength(SUB, font=fm)
    d.text(((W - sw) / 2, 290), SUB, font=fm, fill=(90, 90, 100))
    credit = ["HSP 3.7 で作成　／　作者 subara3", "声：VOICEVOX:玄野武宏　ナレーション：VOICEVOX:No.7",
              "効果音：効果音ラボ　着せ替え：珠音（HSP3 オフィシャル素材）", "プログラムの作成に生成AI（Claude）を使用"]
    for i, t in enumerate(credit):
        cw = d.textlength(t, font=fs)
        d.text(((W - cw) / 2, 420 + i * 34), t, font=fs, fill=(110, 110, 120))
    stick(d, (W + tw) / 2 + 40, 252, 1.0, "wave")
    im.save(path)


def wrap(text, font, d, maxw):
    # 1行に入るならそのまま。入らなければ、まんなかに近い「、」「。」のあとで折り返す（語の途中で切らない）
    if d.textlength(text, font=font) <= maxw:
        return [text]
    cuts = [i + 1 for i, ch in enumerate(text[:-1]) if ch in "、。"]
    best = None
    for c in cuts:
        a, b = text[:c], text[c:]
        if d.textlength(a, font=font) <= maxw and d.textlength(b, font=font) <= maxw:
            score = abs(len(a) - len(b))
            if best is None or score < best[0]: best = (score, c)
    if best:
        return [text[:best[1]], text[best[1]:]]
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=font) > maxw and cur:
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur: lines.append(cur)
    return lines


def caption_png(path, text, label):
    # 下の字幕（ナレーションの文）と、左上の札（機能の名前）
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if text:
        f = ImageFont.truetype(FB, 30)
        lines = wrap(text, f, d, 1160)
        lh = 44
        bh = lh * len(lines) + 26
        y0 = H - bh - 28
        bw = max(d.textlength(l, font=f) for l in lines) + 56
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([(W - bw) / 2, y0 + 4, (W + bw) / 2, y0 + bh + 4], 18, fill=(0, 0, 0, 60))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
        d.rounded_rectangle([(W - bw) / 2, y0, (W + bw) / 2, y0 + bh], 18, fill=(46, 46, 54, 225))
        for i, l in enumerate(lines):
            lw = d.textlength(l, font=f)
            d.text(((W - lw) / 2, y0 + 12 + i * lh), l, font=f, fill=(255, 255, 255))
    if label:
        f = ImageFont.truetype(FB, 24)
        lw = d.textlength(label, font=f)
        d.rounded_rectangle([28, 26, 28 + lw + 64, 26 + 48], 24, fill=(255, 255, 255, 235), outline=(210, 214, 222, 255), width=2)
        d.ellipse([40, 38, 64, 62], fill=ACCENT)
        d.text((76, 34), label, font=f, fill=INK)
    im.save(path)


def title_png(path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fb = ImageFont.truetype(FB, 66)
    fm = ImageFont.truetype(FB, 30)
    tw = d.textlength(TITLE, font=fb)
    d.rounded_rectangle([(W - tw) / 2 - 50, 220, (W + tw) / 2 + 50, 400], 26, fill=(255, 255, 255, 235))
    d.text(((W - tw) / 2, 242), TITLE, font=fb, fill=INK)
    sw = d.textlength(SUB, font=fm)
    d.text(((W - sw) / 2, 336), SUB, font=fm, fill=(60, 140, 120))
    im.save(path)


def run(ff, args):
    subprocess.run([ff, "-y", "-loglevel", "error"] + args, check=True)


def main():
    ff = ffmpeg()
    os.makedirs(TMP, exist_ok=True)
    caps = json.load(open(os.path.join(NARR, "captions.json"), encoding="utf-8"))
    parts, durs = [], []
    venc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS)]
    aenc = ["-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k"]
    for i, seg in enumerate(PLAN):
        out = os.path.join(TMP, "s%02d.mp4" % i)
        if seg[0] == "clip":
            _, key, ranges, nk, label, zoom = seg
            src = glob.glob(os.path.join(SRC, key + "_*.mp4"))[0]
            nwav = os.path.join(NARR, nk + ".wav")
            nl = wav_len(nwav)
            # 範囲は (はじめ, 長さ) か、ほかの素材からなら (記号, はじめ, 長さ)
            ranges = [r if len(r) == 3 else (key, r[0], r[1]) for r in ranges]
            total = sum(r[2] for r in ranges)
            # ナレーションが入りきらなければ、最後の範囲をのばす
            if nl + 1.0 > total:
                ranges = ranges[:-1] + [(ranges[-1][0], ranges[-1][1], ranges[-1][2] + nl + 1.0 - total)]
                total = nl + 1.0
            capp = os.path.join(TMP, "c%02d.png" % i)
            caption_png(capp, caps.get(nk, ""), label)
            ins, fc = [], []
            for k, (rk, ss, dd) in enumerate(ranges):
                rsrc = glob.glob(os.path.join(SRC, rk + "_*.mp4"))[0]
                ins += ["-ss", "%.2f" % ss, "-t", "%.2f" % dd, "-i", rsrc]
                fc.append("[%d:v]setpts=PTS-STARTPTS,fps=%d[v%d];[%d:a]asetpts=PTS-STARTPTS,aresample=48000[a%d]" % (k, FPS, k, k, k))
            n = len(ranges)
            if n > 1:
                fc.append("".join("[v%d][a%d]" % (k, k) for k in range(n)) + "concat=n=%d:v=1:a=1[vc][ac]" % n)
            else:
                fc.append("[v0]null[vc];[a0]anull[ac]")
            if zoom:
                z0, z1 = (1.0, 1.0 + zoom) if zoom > 0 else (1.0 - zoom, 1.0)
                fc.append("[vc]scale=w='trunc(%d*(%f+(%f)*t/%f)/2)*2':h=-2:eval=frame,crop=%d:%d,setsar=1[vz]" % (W, z0, z1 - z0, total, W, H))
            else:
                fc.append("[vc]null[vz]")
            ci = n; ni = n + 1
            ins += ["-loop", "1", "-t", "%.2f" % total, "-i", capp, "-i", nwav]
            if i == 0:
                tp = os.path.join(TMP, "title.png"); title_png(tp)
                ins += ["-loop", "1", "-t", "%.2f" % total, "-i", tp]
            # 最初の場面は、題名を出してから字幕に切りかえる
            cap_on = 3.6 if i == 0 else 0.3
            fc.append("[%d:v]format=rgba,fade=t=in:st=%.2f:d=0.35:alpha=1[cap]" % (ci, cap_on))
            fc.append("[vz][cap]overlay=0:0[vcap]")
            if i == 0:
                fc.append("[%d:v]format=rgba,fade=t=in:st=0.3:d=0.5:alpha=1,fade=t=out:st=3.2:d=0.4:alpha=1[tt]" % (n + 2))
                fc.append("[vcap][tt]overlay=0:0[vout]")
            else:
                fc.append("[vcap]null[vout]")
            nd = int((cap_on + 0.1) * 1000) if i == 0 else 350
            fc.append("[ac]volume=0.45[sa];[%d:a]aresample=48000,aformat=channel_layouts=stereo,adelay=%d|%d,apad[na];[sa][na]amix=inputs=2:normalize=0:duration=first[aout]" % (ni, nd, nd))
            run(ff, ins + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", "%.2f" % total] + venc + aenc + [out])
            durs.append(total)
        else:
            if seg[0] == "card":
                _, title, num, dur = seg
                png = os.path.join(TMP, "k%02d.png" % i); card_png(png, title, num)
                nwav = None
            elif seg[0] == "mods":
                dur = max(seg[1], wav_len(os.path.join(NARR, "m.wav")) + 1.2)
                png = os.path.join(TMP, "k%02d.png" % i); mods_png(png)
                nwav = os.path.join(NARR, "m.wav")
            else:
                dur = seg[1]
                png = os.path.join(TMP, "k%02d.png" % i); end_png(png)
                nwav = None
            # 札はゆっくり寄る
            vf = "scale=w='trunc(%d*(1+0.04*t/%f)/2)*2':h=-2:eval=frame,crop=%d:%d,setsar=1" % (W, dur, W, H)
            if nwav:
                run(ff, ["-loop", "1", "-t", "%.2f" % dur, "-i", png, "-i", nwav, "-filter_complex",
                         "[0:v]%s[v];[1:a]aresample=48000,aformat=channel_layouts=stereo,adelay=400|400,apad[a]" % vf,
                         "-map", "[v]", "-map", "[a]", "-t", "%.2f" % dur] + venc + aenc + [out])
            else:
                run(ff, ["-loop", "1", "-t", "%.2f" % dur, "-i", png, "-f", "lavfi", "-t", "%.2f" % dur, "-i", "anullsrc=r=48000:cl=stereo",
                         "-filter_complex", "[0:v]%s[v]" % vf, "-map", "[v]", "-map", "1:a", "-t", "%.2f" % dur] + venc + aenc + [out])
            durs.append(dur)
        parts.append(out)
        print("part", i, "%.1fs" % durs[-1])
    # 切り替え効果でつなぐ（映像は xfade、音は acrossfade）
    ins = []
    for p in parts: ins += ["-i", p]
    fc = []
    vprev, aprev, acc = "[0:v]", "[0:a]", durs[0]
    for k in range(1, len(parts)):
        tr = XF[(k - 1) % len(XF)]
        off = acc - XD
        fc.append("%s[%d:v]xfade=transition=%s:duration=%.2f:offset=%.3f[vx%d]" % (vprev, k, tr, XD, off, k))
        fc.append("%s[%d:a]acrossfade=d=%.2f[ax%d]" % (aprev, k, XD, k))
        vprev, aprev = "[vx%d]" % k, "[ax%d]" % k
        acc = off + durs[k]
    fc.append("%sloudnorm=I=-16:TP=-1.5:LRA=11[af]" % aprev)
    run(ff, ins + ["-filter_complex", ";".join(fc), "-map", vprev, "-map", "[af]"] + venc + aenc + ["-movflags", "+faststart", OUT])
    for f in glob.glob(os.path.join(TMP, "*")): os.remove(f)
    os.rmdir(TMP)
    print("PV:", OUT, "%.1fs" % acc, "%.1f MB" % (os.path.getsize(OUT) / 1e6))


main()
