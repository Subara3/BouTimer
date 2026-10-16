# docs/文言一覧.csv の「書き直し」を、ソースに差し替える
#   python tools/apply_texts.py          … 差し替える場所を表示するだけ
#   python tools/apply_texts.py --write  … 実際に書きかえる
# 書き直しの「／」は改行（ソースでは \n）になる。行がずれていたら、同じファイルの中で同じ文字列を探す
import csv, os, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
proto = os.path.join(root, "proto")
write = "--write" in sys.argv

rows = list(csv.reader(open(os.path.join(root, "docs", "文言一覧.csv"), encoding="utf-8-sig")))[1:]
files = {}
ng = 0
done = 0
for r in rows:
    no, kind, fn, line, old, new = r[0], r[1], r[2], int(r[3]), r[4], r[5].strip()
    if new == "" or new == old: continue
    if fn not in files:
        files[fn] = open(os.path.join(proto, fn), encoding="utf-8", newline="").read().split("\r\n")
    L = files[fn]
    lit_old = '"' + old.replace("／", "\\n") + '"'
    lit_new = '"' + new.replace("／", "\\n").replace('"', "”") + '"'
    i = line - 1
    if not (0 <= i < len(L) and lit_old in L[i]):
        hits = [k for k, s in enumerate(L) if lit_old in s]
        if len(hits) != 1:
            print(f"NG {no} {fn}:{line} 見つからない（{len(hits)}か所）: {old}")
            ng += 1
            continue
        i = hits[0]
    L[i] = L[i].replace(lit_old, lit_new, 1)
    print(f"{no} {fn}:{i + 1} {old} → {new}")
    done += 1
if write:
    for fn, L in files.items():
        open(os.path.join(proto, fn), "w", encoding="utf-8", newline="").write("\r\n".join(L))
print(f"差し替え {done} 件、見つからない {ng} 件" + ("（書きこみ済み）" if write else "（まだ書きこんでいない。--write で書きこむ）"))
