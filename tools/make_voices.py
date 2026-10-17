# 決まった文のセリフの声を、VOICEVOX（玄野武宏）で前もって作っておく
#   VOICEVOX を起動しておいてから  python tools/make_voices.py
#   → voice\v_XXXXXXXX.wav（16kHz・モノラル・IMA ADPCM）と v_XXXXXXXX.json（口パク用の audio_query）
# ファイル名の XXXXXXXX はセリフの UTF-8 から作る djb2 ハッシュ。アプリ（voice.hsp の *vv_hash）も同じ計算をする
# すでにあるものは作りなおさない。セリフが変わったら、もう一度動かせば足りない分だけ作る
import glob, json, os, re, subprocess, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "voice")
ENGINE = "http://127.0.0.1:50021"
SPEAKER = 11  # 玄野武宏（ノーマル）
SKIP = {"カタカタ", "コンコン", "せいっ", "zzz…", "♪", "z", "Z"}
# 数字の入るセリフは、決まった部分だけを声にする（voice.hsp の *vv_spoken と合わせる）
EXTRA = ["やったな", "いい調子", "やるじゃん", "水飲もうぜ", "時間だぞ！"]

def ffmpeg():
    base = os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "WinGet", "Packages")
    hits = glob.glob(os.path.join(base, "**", "ffmpeg.exe"), recursive=True)
    if not hits: raise SystemExit("ffmpeg が見つかりません")
    return hits[0]

def djb2(s):
    h = 5381
    for b in s.encode("utf-8"):
        h = (h * 33 + b) & 0xFFFFFFFF
    return "%08x" % h

def lines_from_source():
    found = []
    for path in sorted(glob.glob(os.path.join(ROOT, "proto", "*.hsp"))):
        if os.path.basename(path) == "tests.hsp": continue
        for line in open(path, encoding="utf-8"):
            code = line.split(";")[0] if not line.lstrip().startswith(";") else ""
            # bubble = "…" と sea_line = "…"。うしろに + が続くもの（文字をつなぐもの）は外す
            for m in re.finditer(r'\b(bubble|sea_line)\s*=\s*"([^"]*)"\s*(\+)?', code):
                if m.group(3): continue
                s = m.group(2)
                if re.search(r"[0-9０-９]", s): continue
                if len(s) < 2 or s in SKIP: continue
                found.append(s)
    return found

def post(url, data=None, ctype=None):
    req = urllib.request.Request(url, data=data or b"", method="POST")
    if ctype: req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def main():
    os.makedirs(OUT, exist_ok=True)
    ff = ffmpeg()
    texts = []
    for s in lines_from_source() + EXTRA:
        if s not in texts: texts.append(s)
    made = 0
    index = []
    for s in texts:
        name = "v_" + djb2(s)
        index.append(name + "|" + s)
        wav = os.path.join(OUT, name + ".wav")
        js = os.path.join(OUT, name + ".json")
        if os.path.exists(wav) and os.path.exists(js): continue
        q = post(ENGINE + "/audio_query?speaker=%d&text=%s" % (SPEAKER, urllib.parse.quote(s)))
        raw = post(ENGINE + "/synthesis?speaker=%d" % SPEAKER, q, "application/json")
        tmp = os.path.join(OUT, "_tmp.wav")
        open(tmp, "wb").write(raw)
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", tmp, "-ar", "16000", "-ac", "1", "-c:a", "adpcm_ima_wav", wav], check=True)
        os.remove(tmp)
        open(js, "w", encoding="utf-8").write(json.dumps(json.loads(q), ensure_ascii=False, separators=(",", ":")))
        made += 1
        print("made", name, s)
    open(os.path.join(OUT, "index.txt"), "w", encoding="utf-8").write("\n".join(index) + "\n")
    size = sum(os.path.getsize(p) for p in glob.glob(os.path.join(OUT, "v_*")))
    print("lines", len(texts), "made", made, "bytes", size)

main()
