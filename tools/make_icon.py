# 配布する exe のアイコンを作る（案15：ストップウォッチ型の白い窓のふちに、ピクトグラムの棒人間が腰かける）
#   python tools/make_icon.py  → tools/boutimer.ico（と、確かめ用の tools/boutimer_icon.png）
# タスクトレイの絵は main.hsp の *make_tray_icon で同じ形を描く
import os
from PIL import Image, ImageDraw

S = 1024
K = S / 32.0
BG = (64, 196, 164, 255)
WHITE = (255, 255, 255, 255)
NAVY = (30, 38, 64, 255)

def P(x, y): return (x * K, y * K)
def B(x, y, w, h): return [x * K, y * K, (x + w) * K, (y + h) * K]

def stroke(d, pts, col, w):
    pts = [P(*p) for p in pts]
    d.line(pts, fill=col, width=int(w * K), joint="curve")
    r = w * K / 2
    for x, y in pts:
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)

im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle(B(1, 1, 30, 30), radius=6.5 * K, fill=BG)
# ストップウォッチ型の白い窓と、時計の針
d.rounded_rectangle(B(6, 18, 20, 11), radius=2.5 * K, fill=WHITE)
stroke(d, [(21, 24), (21, 21)], NAVY, 1.4)
stroke(d, [(21, 24), (23.6, 24)], NAVY, 1.4)
# 棒人間：腰は窓の上辺。手はふちの少し後ろにつき、すねを前に垂らす
x, y, w = 11, 17.4, 2.6
r = 3.0
d.ellipse(B(x - r, y - 11.5 - r, 2 * r, 2 * r), fill=NAVY)
stroke(d, [(x, y), (x, y - 7.5)], NAVY, w)
stroke(d, [(x, y - 6), (x - 2.5, y - 3), (x - 3.5, y + 0.2)], NAVY, w)
stroke(d, [(x, y), (x + 5.5, y), (x + 6, y + 5)], NAVY, w)

here = os.path.dirname(os.path.abspath(__file__))
im.resize((512, 512), Image.LANCZOS).save(os.path.join(here, "boutimer_icon.png"))
im.save(os.path.join(here, "boutimer.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(os.path.join(here, "boutimer.ico"))
