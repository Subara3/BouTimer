# 時刻を知らせるときの音を3種類、計算で作る（素材は使わない）
# 「ピンポーン」は高→低の2音、「ピンポンパンポーン」は上がる4音（ドミソド）
#   前の版は、上がる2音に長い余韻をつけていて、緊急地震速報のチャイムに聞こえると本人の指摘があった
#   python tools/make_alarm_se.py  → se\se_alarm1.wav（電子音）、se_alarm2.wav（玄関チャイム）、se_alarm3.wav（放送チャイム）
#   どれも「ピピピ」のひとまとまりを3回くり返したものにしてある（1回鳴らすと3回聞こえる）
#   se_alarm1s〜3s は、ひとまとまりを1回だけ（作業と休憩が切りかわるときの音）
import array, math, os, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "se")
RATE = 22050
PEAK = 0.4


def tone(freq, sec, decay=0.0, harm=()):
    # decay は 1 秒あたりの減衰（0 で減衰なし）。harm は倍音の (倍率, 強さ)
    n = int(RATE * sec)
    out = []
    for i in range(n):
        t = i / RATE
        v = math.sin(2 * math.pi * freq * t)
        for m, a in harm:
            v += a * math.sin(2 * math.pi * freq * m * t)
        env = math.exp(-decay * t) if decay else 1.0
        # 立ち上がりと終わりの 3ms は滑らかに（プチッという音を防ぐ）
        edge = min(1.0, i / (RATE * 0.003), (n - 1 - i) / (RATE * 0.003))
        out.append(v * env * max(0.0, edge))
    return out


def silence(sec):
    return [0.0] * int(RATE * sec)


def join(parts):
    s = []
    for p in parts: s += p
    return s


def repeat3(unit, gap):
    return join([unit, silence(gap), unit, silence(gap), unit])


# 1 電子音：ピッピッピッピッ（2kHz の短い音を4つ）
beep = join([tone(2000, 0.07), silence(0.07)] * 4)
alarm1 = repeat3(beep, 0.5)
alarm1s = beep

def overlay(notes):
    # notes は (開始秒, 波形) の並び。重ねて1つの波形にする（鉄琴のように、前の音が残っているうちに次を鳴らす）
    n = max(int(RATE * t0) + len(w) for t0, w in notes)
    s = [0.0] * n
    for t0, w in notes:
        off = int(RATE * t0)
        for i, v in enumerate(w): s[off + i] += v
    return s


# 玄関チャイムと放送チャイムの音色：鉄琴（ヴィブラフォン）のように、基音に少しの倍音を足して、なめらかに消える
def bar(freq, sec, decay):
    return tone(freq, sec, decay=decay, harm=((2, 0.12), (3, 0.05)))


# 2 玄関チャイム：ピンポーン。高い音から低い音へ下がる2音（玄関の呼び鈴は短い鉄板→長い鉄板の順に叩く）
#   ミ(659Hz)→ド(523Hz)。「ピン」は短く消え、「ポーン」は長く残る
def door_chime():
    return overlay([(0.0, bar(659, 0.7, 5.0)), (0.38, bar(523, 1.3, 2.2))])
alarm2 = repeat3(door_chime(), 0.6)
alarm2s = door_chime()

# 3 放送チャイム：ピンポンパンポーン。店や学校の放送の前に鳴る、上がっていく4音（ドミソド）
#   音の高さは、チャイム付きマイク（なんず MCH-500）の仕様にある 440・554・659・880Hz（ラ・ド#・ミ・ラ）に合わせた
def announce_chime():
    return overlay([(0.0, bar(440, 0.8, 3.5)), (0.36, bar(554, 0.8, 3.5)), (0.72, bar(659, 0.8, 3.5)), (1.08, bar(880, 1.1, 2.5))])
alarm3 = repeat3(announce_chime(), 0.5)
alarm3s = announce_chime()

os.makedirs(OUT, exist_ok=True)
for name, s in (("se_alarm1", alarm1), ("se_alarm2", alarm2), ("se_alarm3", alarm3),
                ("se_alarm1s", alarm1s), ("se_alarm2s", alarm2s), ("se_alarm3s", alarm3s)):
    m = max(abs(v) for v in s) or 1.0
    pcm = array.array("h", [int(v / m * PEAK * 32767) for v in s])
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    print(name, round(len(s) / RATE, 2), "s")
