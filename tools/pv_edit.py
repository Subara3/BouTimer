# pv\new の場面（tools/pv_make.py で作ったもの）を切り出してつなぎ、機能名だけの字幕と題名を重ねて PV にする
#   python tools/pv_edit.py   → pv\PV_作業のおとも、棒人間_1.0.mp4
# 字幕の文言と、使う秒（はじめ・長さ）は下の CUTS で変えられる
import glob, os, subprocess
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "pv", "new")
OUT = os.path.join(ROOT, "pv", "PV_作業のおとも、棒人間_1.0.mp4")
TITLE = "作業のおとも、棒人間"
SUB = "作業集中用のポモドーロタイマー"
END2 = "HSP 3.7　／　subara3"
FONT = "C\\:/Windows/Fonts/meiryob.ttc"

# 場面のファイル（記号）、はじめ（秒）、長さ（秒）、字幕
CUTS = [
    ("G", 1.0, 20.0, "はじめての質問"),
    ("H", 2.0, 10.0, "やることリスト"),
    ("C", 5.0, 15.0, "ポモドーロ（休憩）"),
    ("D", 4.0, 12.0, "サボり先の札"),
    ("B", 2.0, 28.0, "つつく・なでる・投げる"),
    ("I", 2.0, 12.0, "認識の図示"),
    ("J", 10.0, 12.0, "着せ替え（珠音）"),
    ("A", 20.0, 24.0, "いろいろな動き"),
]


def ffmpeg():
    base = os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "WinGet", "Packages")
    return glob.glob(os.path.join(base, "**", "ffmpeg.exe"), recursive=True)[0]


def esc(s):
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def main():
    ff = ffmpeg()
    tmp = os.path.join(SRC, "_edit")
    os.makedirs(tmp, exist_ok=True)
    parts = []
    for i, (key, ss, dur, cap) in enumerate(CUTS):
        src = glob.glob(os.path.join(SRC, key + "_*.mp4"))[0]
        vf = ["drawtext=fontfile='%s':text='%s':fontsize=34:fontcolor=white:box=1:boxcolor=0x2E2E36@0.75:boxborderw=14:x=(w-text_w)/2:y=h-text_h-36" % (FONT, esc(cap))]
        if i == 0:
            # 最初の3.5秒は題名
            vf.append("drawtext=fontfile='%s':text='%s':fontsize=64:fontcolor=0x2E2E36:box=1:boxcolor=white@0.88:boxborderw=22:x=(w-text_w)/2:y=(h-text_h)/2-60:enable='lt(t,3.5)'" % (FONT, esc(TITLE)))
            vf.append("drawtext=fontfile='%s':text='%s':fontsize=30:fontcolor=0x2E2E36:box=1:boxcolor=white@0.88:boxborderw=12:x=(w-text_w)/2:y=(h-text_h)/2+20:enable='lt(t,3.5)'" % (FONT, esc(SUB)))
        vf.append("fade=t=in:st=0:d=0.3,fade=t=out:st=%.2f:d=0.3" % (dur - 0.3))
        part = os.path.join(tmp, "p%02d.mp4" % i)
        subprocess.run([ff, "-y", "-loglevel", "error", "-ss", str(ss), "-t", str(dur), "-i", src, "-vf", ",".join(vf),
                        "-af", "afade=t=in:st=0:d=0.3,afade=t=out:st=%.2f:d=0.3" % (dur - 0.3),
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
                        "-c:a", "aac", "-ar", "48000", "-ac", "2", part], check=True)
        parts.append(part)
    # おわりの題名（舞台と同じ背景の色で4秒）
    bg = Image.new("RGB", (1280, 720))
    d = ImageDraw.Draw(bg)
    for y in range(720):
        c = y * 40 // 720
        d.line([(0, y), (1279, y)], fill=(236 - c, 240 - c, 246 - c // 2))
    bgp = os.path.join(tmp, "end.png"); bg.save(bgp)
    endp = os.path.join(tmp, "p99.mp4")
    vf = ",".join([
        "drawtext=fontfile='%s':text='%s':fontsize=64:fontcolor=0x2E2E36:x=(w-text_w)/2:y=(h-text_h)/2-70" % (FONT, esc(TITLE)),
        "drawtext=fontfile='%s':text='%s':fontsize=30:fontcolor=0x505060:x=(w-text_w)/2:y=(h-text_h)/2+10" % (FONT, esc(SUB)),
        "drawtext=fontfile='%s':text='%s':fontsize=24:fontcolor=0x707080:x=(w-text_w)/2:y=(h-text_h)/2+70" % (FONT, esc(END2)),
        "fade=t=in:st=0:d=0.4"])
    subprocess.run([ff, "-y", "-loglevel", "error", "-loop", "1", "-t", "4", "-i", bgp, "-f", "lavfi", "-t", "4", "-i", "anullsrc=r=48000:cl=stereo",
                    "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "aac", "-shortest", endp], check=True)
    parts.append(endp)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in parts: f.write("file '%s'\n" % p.replace("\\", "/"))
    # つないでから、音の大きさをネットの動画の目安（-16 LUFS）にそろえる
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "copy",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", OUT], check=True)
    for p in parts: os.remove(p)
    os.remove(lst); os.remove(bgp); os.rmdir(tmp)
    print("PV:", OUT, "%.1f MB" % (os.path.getsize(OUT) / 1e6))


main()
