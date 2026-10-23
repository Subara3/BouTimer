# YouTube のサムネ（1280x720）を作る
#   棒人間の絵は proto で  hsp3utf main.ax posetest uis30 shot noaudio  → proto\shot\008.png を pv\thumb\stick_wave.png に写したもの
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FB = "C:/Windows/Fonts/meiryob.ttc"
FR = "C:/Windows/Fonts/meiryo.ttc"
W, H = 1280, 720
INK = (38, 42, 56)
MINT = (178, 228, 210)
MINT2 = (214, 242, 230)

im = Image.new("RGB", (W, H))
d = ImageDraw.Draw(im)
for y in range(H):
    t = y / H
    d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(MINT2, MINT)))

# 窓（棒人間が上の辺に立つ）
wx0, wy0, wx1 = 60, 410, 560
sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(sh).rectangle([wx0 + 6, wy0 + 10, wx1 + 6, H + 40], fill=(0, 0, 0, 70))
im.paste(sh.filter(ImageFilter.GaussianBlur(10)), (0, 0), sh.filter(ImageFilter.GaussianBlur(10)))
d.rectangle([wx0, wy0, wx1, H + 20], fill=(255, 255, 255), outline=(170, 180, 190), width=2)
d.rectangle([wx0 + 1, wy0 + 1, wx1 - 1, wy0 + 44], fill=(243, 245, 248))
ft = ImageFont.truetype(FR, 22)
d.text((wx0 + 18, wy0 + 9), "メモ - 今日のやること", font=ft, fill=(60, 60, 70))
for i, s in enumerate(["—", "□", "✕"]):
    d.text((wx1 - 130 + i * 44, wy0 + 7), s, font=ft, fill=(90, 90, 100))
fl = ImageFont.truetype(FR, 34)
items = [("資料を読む", False), ("企画書の続き", False), ("メールの返信", True)]
for i, (s, done) in enumerate(items):
    y = wy0 + 72 + i * 62
    d.rectangle([wx0 + 30, y + 8, wx0 + 58, y + 36], outline=(80, 90, 110), width=3)
    if done:
        d.line([(wx0 + 35, y + 22), (wx0 + 43, y + 31), (wx0 + 56, y + 10)], fill=(40, 150, 90), width=5)
    d.text((wx0 + 76, y), s, font=fl, fill=(150, 150, 160) if done else INK)

# 棒人間（足の下を窓の上の辺に合わせる）
st = Image.open(os.path.join(ROOT, "pv", "thumb", "stick_wave.png")).convert("RGBA")
a = st.getchannel("A")
# 上のタイマーの札と、下の棒人間を、間の透明な行で分ける
rows = [any(a.getpixel((x, y)) > 0 for x in range(0, st.width, 2)) for y in range(st.height)]
top = rows.index(True)
gap = rows.index(False, top)
head = rows.index(True, gap)
label = st.crop((0, top, st.width, gap)).crop(st.crop((0, top, st.width, gap)).getbbox())
body = st.crop((0, head, st.width, st.height))
body = body.crop(body.getbbox())
k = 1.45
body = body.resize((int(body.width * k), int(body.height * k)), Image.LANCZOS)
cxm = (wx0 + wx1) // 2 + 30
by = wy0 - body.height + int(7 * k)  # 影の楕円のまんなかを辺に合わせる
im.paste(body, (cxm - body.width // 2, by), body)
lk = 1.15
label = label.resize((int(label.width * lk), int(label.height * lk)), Image.LANCZOS)
im.paste(label, (cxm - label.width // 2, by - label.height - 24), label)

# 右側の文字
fb = ImageFont.truetype(FB, 92)
x = 610
d.text((x, 120), "作業のおとも、", font=fb, fill=INK)
d.text((x, 228), "棒人間", font=fb, fill=INK)
fm = ImageFont.truetype(FB, 40)
d.text((x + 4, 362), "作業集中用のポモドーロタイマー", font=fm, fill=(40, 110, 90))
fc = ImageFont.truetype(FB, 32)
cx = x
for s in ["25分作業・5分休憩", "TODOリスト"]:
    w = d.textlength(s, font=fc)
    d.rounded_rectangle([cx, 448, cx + w + 40, 506], radius=29, fill=(255, 255, 255), outline=(40, 110, 90), width=3)
    d.text((cx + 20, 455), s, font=fc, fill=INK)
    cx += w + 60
fs = ImageFont.truetype(FB, 28)
d.text((x + 4, 560), "HSPプログラムコンテスト2026 応募作品", font=fs, fill=(70, 80, 90))

out = os.path.join(ROOT, "pv", "submit", "YouTubeサムネ.png")
im.save(out)
print(out)
