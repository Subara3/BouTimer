# PV のナレーションを VOICEVOX（No.7 アナウンス）で作る
#   VOICEVOX を起動しておいてから  python tools/pv_narration.py
#   → pv\narr\<記号>.wav。文を変えたら、もう一度動かす（変わったものだけ作りなおす）
# 字幕に出す文（左）と、読み上げる文（右。読みまちがえやすい語をかなにしたもの）
import json, os, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "pv", "narr")
ENGINE = "http://127.0.0.1:50021"
SPEAKER = 30  # No.7（アナウンス）

LINES = {
    "op":  ("作業のおとも、棒人間。デスクトップの窓の上を歩く、作業集中用のポモドーロタイマーです。", None),
    "c":   ("25分の作業と5分の休憩をくり返します。休憩になると、いま使っている窓まで来て、ふちで休みます。", None),
    "k":   ("頭の上のタイマーをクリックすると、一時停止できます。", None),
    "h":   ("やることは紙にして持ち歩きます。カーソルを乗せてチェックを入れると、丸めてゴミ箱へ。", None),
    "l":   ("終わるまでにかかった時間を記録して、今日の内訳と1週間の記録で見られます。毎日のやることも登録できます。", None),
    "d":   ("動画などを長く開いていると、札を出して声をかけます。", None),
    "g":   ("はじめての起動では、窓の中であいさつをして、いくつか質問します。", None),
    "b":   ("つまんで投げると、窓のふちで跳ね返ります。作業中は、お茶を飲んだり、釣りをしたり。", None),
    "j":   ("珠音の髪型にも着せ替えられます。", "たまねの髪型にも着せ替えられます。"),
    "i":   ("窓の位置は、Windowsの画面合成から実際の大きさで読み取ります。手前の窓に隠れた辺には立ちません。", None),
    "r":   ("離れた窓へは、窓の上の辺をつないで道を探し、跳び移ります。", None),
    "p":   ("棒人間は1秒に60回、GDI+で描きなおし、画素ごとに透ける窓で表示しています。", "棒人間は1秒に60回、ジーディーアイプラスで描きなおし、画素ごとに透ける窓で表示しています。"),
    "m":   ("使った技術は3つのモジュールにまとめて、ソースと一緒に公開しています。", None),
}


def post(url, data=None, ctype=None):
    req = urllib.request.Request(url, data=data or b"", method="POST")
    if ctype: req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    os.makedirs(OUT, exist_ok=True)
    for key, (cap, read) in LINES.items():
        text = read or cap
        stamp = os.path.join(OUT, key + ".txt")
        wav = os.path.join(OUT, key + ".wav")
        if os.path.exists(wav) and os.path.exists(stamp) and open(stamp, encoding="utf-8").read() == text:
            continue
        q = json.loads(post(ENGINE + "/audio_query?speaker=%d&text=%s" % (SPEAKER, urllib.parse.quote(text))))
        q["speedScale"] = 1.08
        q["postPhonemeLength"] = 0.2
        q["outputSamplingRate"] = 48000
        raw = post(ENGINE + "/synthesis?speaker=%d" % SPEAKER, json.dumps(q).encode("utf-8"), "application/json")
        open(wav, "wb").write(raw)
        open(stamp, "w", encoding="utf-8").write(text)
        print("made", key)
    # 字幕に出す文を、まとめて書いておく（pv_edit.py が読む）
    json.dump({k: v[0] for k, v in LINES.items()}, open(os.path.join(OUT, "captions.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


main()
