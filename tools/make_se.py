# 効果音ラボ（https://soundeffect-lab.info/）の効果音を、アプリで鳴らす wav にする
#   se_src\ の mp3 → se\ の wav（22.05kHz・モノラル・16bit）。作業のじゃまにならないよう小さめにする
#   本人の希望で、リアルな音ではなく、ポップで短い音にしている
import array, glob, os, subprocess, wave
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "se_src")
OUT = os.path.join(ROOT, "se")
RATE = 22050
# 出す名前、もとのファイル、使う長さ（秒）、くり返す回数、くり返しの間隔（秒）
LIST = [
    ("se_jump", "puyon1.mp3", 0.3, 1, 0),       # ぷよん：窓へ跳ぶ
    ("se_write", "cursor7.mp3", 0.16, 3, 0.13),  # ピピピッ：絵日記を描く
    ("se_paper", "decision39.mp3", 0.5, 1, 0),   # ペチョッ：紙を丸める
    ("se_goal", "decision34.mp3", 0.6, 1, 0),    # ポン：ゴミ箱に入る
]

def ffmpeg():
    base = os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "WinGet", "Packages")
    return glob.glob(os.path.join(base, "**", "ffmpeg.exe"), recursive=True)[0]

def decode(ff, path, sec):
    raw = subprocess.run([ff, "-loglevel", "error", "-i", path, "-t", str(sec), "-af", "volume=0.5",
                          "-ar", str(RATE), "-ac", "1", "-f", "s16le", "-"], check=True, capture_output=True).stdout
    a = array.array("h"); a.frombytes(raw)
    # 終わりの 30 ミリ秒を小さくして、ぷつっと切れないようにする
    n = min(len(a), int(RATE * 0.03))
    for i in range(n):
        a[len(a) - n + i] = int(a[len(a) - n + i] * (n - i) / n)
    return a

os.makedirs(OUT, exist_ok=True)
for old in glob.glob(os.path.join(OUT, "se_*.wav")): os.remove(old)
ff = ffmpeg()
for name, src, sec, rep, gap in LIST:
    one = decode(ff, os.path.join(SRC, src), sec)
    step = int(RATE * gap) if rep > 1 else len(one)
    total = step * (rep - 1) + len(one)
    mix = [0] * total
    for r in range(rep):
        for i, v in enumerate(one):
            mix[r * step + i] = max(-32768, min(32767, mix[r * step + i] + v))
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(array.array("h", mix).tobytes())
    print(name, total / RATE, "s")
