# 小さな窓（設定・やること・時刻・フレンド・バージョン情報・内訳・はじめまして）の座標と字の大きさを、
# 画面の拡大率（uis）に合わせる UI() でくるむ。一度だけ流す変換（すでに UI( があるところは触らない）
#   python tools/ui_scale_transform.py [--write]
import re, sys

FILES = ["alarm.hsp", "friend.hsp", "kotoba.hsp", "report.hsp", "todo.hsp", "ui_settings.hsp", "wizard.hsp"]
# 命令ごとに、何番目の引数（0始まり）を拡大するか
RULES = {
    "pos": [0, 1], "objsize": [0, 1, 2], "font": [1], "boxf": [0, 1, 2, 3], "line": [0, 1, 2, 3],
    "circle": [0, 1, 2, 3], "combox": [1], "listbox": [1], "input": [1, 2], "mesbox": [1, 2],
}


def split_top(s, sep):
    # 文字列と括弧の外にある sep で分ける
    out, cur, depth, q = [], "", 0, False
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            cur += c
            if c == "\\" and i + 1 < len(s):
                cur += s[i + 1]; i += 2; continue
            if c == '"': q = False
        elif c == '"':
            q = True; cur += c
        elif c in "([{":
            depth += 1; cur += c
        elif c in ")]}":
            depth -= 1; cur += c
        elif c == sep and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += c
        i += 1
    out.append(cur)
    return out


def wrap(a):
    t = a.strip()
    if t == "" or t.startswith("UI(") or t == "0": return a
    lead = a[: len(a) - len(a.lstrip())]
    trail = a[len(a.rstrip()):]
    return lead + "UI(" + t + ")" + trail


def conv_stmt(st):
    m = re.match(r"^(\s*)([a-z]+)(\s+)(.*)$", st, re.S)
    if not m: return st
    ind, cmd, sp, rest = m.groups()
    if cmd not in RULES: return st
    # 文末の ; コメントは触らない（文字列の外の ; から）
    args = split_top(rest, ",")
    # 引数がない boxf などはそのまま
    if len(args) == 1 and args[0].strip() == "": return st
    for k in RULES[cmd]:
        if k < len(args): args[k] = wrap(args[k])
    return ind + cmd + sp + ",".join(args)


def conv_screen(line):
    # screen id, W, H, mode, (wa..)/2 - K, (wa..)/2 - K
    m = re.match(r"^(\s*screen\s+)(.*)$", line)
    if not m or "UI(" in line: return line
    args = split_top(m.group(2), ",")
    if len(args) < 6: return line
    args[1] = wrap(args[1]); args[2] = wrap(args[2])
    for k in (4, 5):
        args[k] = re.sub(r"-\s*(.+)$", lambda mm: "- UI(" + mm.group(1).strip() + ")", args[k])
    return m.group(1) + ",".join(args)


def conv_line(line):
    body = line.rstrip("\r\n"); nl = line[len(body):]
    if body.lstrip().startswith(";") or body.strip() == "": return line
    if re.match(r"^\s*screen\s", body): return conv_screen(body) + nl
    # 行末コメントを分ける（文字列の外の ;）
    parts = split_top(body, ";")
    code = parts[0]; comment = ";" + ";".join(parts[1:]) if len(parts) > 1 else ""
    stmts = split_top(code, ":")
    new = ":".join(conv_stmt(s) for s in stmts)
    return new + comment + nl


def main():
    write = "--write" in sys.argv
    import os
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "proto")
    for f in FILES:
        p = os.path.join(base, f)
        src = open(p, "rb").read().decode("utf-8")
        lines = src.splitlines(keepends=True)
        out = [conv_line(l) for l in lines]
        n = sum(1 for a, b in zip(lines, out) if a != b)
        print(f, n, "lines")
        if not write:
            for a, b in zip(lines, out):
                if a != b: print("  -", a.rstrip()); print("  +", b.rstrip())
        else:
            open(p, "wb").write("".join(out).encode("utf-8"))


main()
