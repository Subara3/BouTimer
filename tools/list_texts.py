# 画面に出る文言（ソースの日本語の文字列）を一覧にする
#   python tools/list_texts.py  → docs/文言一覧.csv（Excel で開ける UTF-8）
# 「書き直し」の列を埋めたら、tools/apply_texts.py で差し替える
import csv, glob, os, re

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
proto = os.path.join(root, "proto")
out = os.path.join(root, "docs", "文言一覧.csv")

def kind_of(fn, code):
    if "sea_line" in code: return "季節のセリフ"
    if "gbubble" in code: return "ゴーストのセリフ"
    if "bubble" in code: return "吹き出し（セリフ）"
    if "signtext" in code: return "札"
    if fn == "overlay.hsp": return "認識の図示"
    if fn == "draw.hsp" and ("label" in code or "hs_line" in code): return "頭の上の表示"
    if "stat_line" in code: return "右クリックのメニュー"
    if "abt" in code: return "バージョン情報"
    if "tipw" in code: return "トレイ"
    if "AppendMenu" in code: return "右クリックのメニュー"
    if "dialog" in code: return "ダイアログ"
    if fn == "diary.hsp": return "絵日記"
    if fn == "wizard.hsp": return "はじめての質問"
    if fn == "summary.hsp": return "日報用のまとめ"
    if re.search(r"\b(mes|title|button|chkbox|combox|listbox|objprm)\b", code) or "al_" in code or "wz_" in code: return "窓の文字"
    if "kotoba" in code or "ktxt" in code or "dtxt" in code or "ttxt" in code: return "ファイルの説明行"
    return "その他"

def code_part(line):
    # ; 以降のコメントを外す（文字列の中の ; は残す）
    q = False
    for i, ch in enumerate(line):
        if ch == '"' and (i == 0 or line[i - 1] != "\\"): q = not q
        if ch == ";" and not q: return line[:i]
    return line

rows = []
for path in sorted(glob.glob(os.path.join(proto, "*.hsp"))):
    fn = os.path.basename(path)
    if fn == "tests.hsp": continue
    for no, line in enumerate(open(path, encoding="utf-8").read().split("\n"), 1):
        code = code_part(line.rstrip("\r"))
        for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', code):
            s = m.group(1)
            if not re.search(r"[　-ヿ一-鿿！-｠]", s): continue
            if s in ("土日月火水木金", "日月火水木金土", "０１２３４５６７８９", "｜"): continue
            if s.endswith(".lnk"): continue
            ctx = code.strip()
            if len(ctx) > 90: ctx = ctx[:90] + "…"
            rows.append([kind_of(fn, code), fn, no, s.replace("\\n", "／"), "", ctx])

order = ["はじめての質問", "吹き出し（セリフ）", "季節のセリフ", "札", "ゴーストのセリフ", "頭の上の表示", "絵日記", "右クリックのメニュー", "窓の文字", "ダイアログ", "バージョン情報", "トレイ", "日報用のまとめ", "技術の見える化", "ファイルの説明行", "その他"]
rows.sort(key=lambda r: (order.index(r[0]), r[1], r[2]))
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["番号", "種類", "ファイル", "行", "今の文言（／は改行）", "書き直し（空欄ならそのまま）", "コード（どこで出るかの手がかり）"])
    for i, r in enumerate(rows, 1):
        w.writerow([i] + r)
print(out, len(rows))
for k in order:
    print(k, sum(1 for r in rows if r[0] == k))
