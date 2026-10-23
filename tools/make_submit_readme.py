# 応募ページに上げる作品説明ファイル（pv\submit\readme.txt、Shift_JIS・20000バイトまで）を docs\readme.txt から作る
#   python tools/make_submit_readme.py
# Shift_JIS にない文字（▶）は置きかえ、作者の欄に紹介動画の URL を足す
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs", "readme.txt")
OUT = os.path.join(ROOT, "pv", "submit", "readme.txt")
PV_URL = "https://youtu.be/ljjBfBjCtJ0"

s = open(SRC, encoding="utf-8").read().replace("\r\n", "\n")
s = s.replace("▶", "＞")
k = "ソース：https://github.com/Subara3/BouTimer\n"
assert k in s
s = s.replace(k, k + "紹介動画：" + PV_URL + "\n")
b = s.replace("\n", "\r\n").encode("cp932")
assert len(b) <= 20000, len(b)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "wb").write(b)
print(OUT, len(b), "bytes")
