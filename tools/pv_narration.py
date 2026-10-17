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
    "op":  ("作業のおとも、棒人間。作業集中用のポモドーロタイマーです。", None),
    "c":   ("25分の作業と5分の休憩をくり返して、作業のペースを保ちます。休憩の時間になると、いま使っている窓まで来て知らせます。", None),
    "k":   ("席を外すときは、タイマーを一時停止できます。", None),
    "h":   ("いま取り組むことを持ち歩いて、やることを忘れないようにします。終わったら、チェックで済みにできます。", None),
    "l":   ("かかった時間を記録して、一日と一週間の作業をふり返れます。毎日のやることも登録できます。", None),
    "d":   ("動画などを長く開いていると、作業を促します。", "動画などを長く開いていると、作業をうながします。"),
    "g":   ("はじめての起動では、作業と休憩の長さなどを質問して設定します。", None),
    "b":   ("作業の合間には、つまんで投げたりして、気分転換ができます。", None),
    "j":   ("珠音の髪型にも着せ替えられます。", "たまねの髪型にも着せ替えられます。"),
    "i":   ("開いている窓の位置を読み取って、手前の窓に隠れていない辺を足場にします。", None),
    "r":   ("離れた窓へは、窓どうしをつないで道を探し、移動します。", None),
    "p":   ("1秒に60回描きなおして、デスクトップの上に、透ける窓で重ねて表示します。", None),
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
