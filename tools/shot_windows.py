# 小さな窓を確認用モードで開いて、PrintWindow で中身（部品も含む）を PNG に書き出す
#   python tools/shot_windows.py 出力フォルダ [uis15 など、本体に足す引数]
# 本体の窓は前に出さずに開くので、ほかの窓に隠れていても写る（PW_RENDERFULLCONTENT）
import ctypes, os, subprocess, sys, time
from ctypes import wintypes
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO = os.path.join(ROOT, "proto")
HSP = r"C:\hsp37\hsp3utf.exe"
u32 = ctypes.windll.user32; g32 = ctypes.windll.gdi32
u32.SetProcessDPIAware()

# (名前, 本体のモード, 窓の題名, 待つ秒)
SHOTS = [
    ("settings", "settingswin test noaudio", "作業のおとも、棒人間の設定", 2.0),
    ("todo", "todowin test noaudio", "やることリスト", 2.0),
    ("alarm", "alarmwin test noaudio", "時刻を知らせる", 2.0),
    ("about", "abouttest noaudio", "作業のおとも、棒人間について", 2.0),
    ("teach", "teachwin test noaudio", "セリフを教える", 2.0),
    ("report", "report noaudio", "今日の内訳と1週間の記録", 3.0),
    ("wizard", "wizardtest noaudio", "はじめまして", 2.5),
]


def grab(hwnd, path):
    r = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = u32.GetWindowDC(hwnd); mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h); g32.SelectObject(mdc, bmp)
    u32.PrintWindow(hwnd, mdc, 2)
    class BIH(ctypes.Structure):
        _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                    ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32), ("biSizeImage", ctypes.c_uint32),
                    ("x", ctypes.c_int32), ("y", ctypes.c_int32), ("c", ctypes.c_uint32), ("ci", ctypes.c_uint32)]
    bi = BIH(); bi.biSize = ctypes.sizeof(BIH); bi.biWidth = w; bi.biHeight = -h; bi.biPlanes = 1; bi.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(path)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(hwnd, hdc)
    return w, h


def find(ttl, pid):
    # 起動した本体の窓だけを探す（使っている本体にも同じ題名の窓があるため）
    found = []
    PROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        n = u32.GetWindowTextLengthW(h)
        b = ctypes.create_unicode_buffer(n + 1); u32.GetWindowTextW(h, b, n + 1)
        if b.value == ttl:
            q = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(q))
            if q.value == pid: found.append(h)
        return True
    u32.EnumWindows(PROC(cb), 0)
    return found[0] if found else 0


def main():
    out = sys.argv[1]; extra = " ".join(sys.argv[2:])
    os.makedirs(out, exist_ok=True)
    for name, mode, ttl, wait in SHOTS:
        p = subprocess.Popen([HSP, "main.ax"] + (mode + " " + extra).split(), cwd=PROTO)
        hwnd = 0
        t0 = time.time()
        while time.time() - t0 < 8 and not hwnd:
            time.sleep(0.3)
            hwnd = find(ttl, p.pid)
        time.sleep(wait)
        if hwnd:
            print(name, grab(hwnd, os.path.join(out, name + ".png")))
        else:
            print(name, "not found")
        p.kill(); p.wait()


main()
