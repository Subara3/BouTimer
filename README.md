# 作業のおとも、棒人間

作業集中用のポモドーロタイマー。棒人間が、デスクトップに開いているウィンドウの上の辺を足場にして歩きまわります。

HSPプログラムコンテスト2026の応募作品です。HSP 3.7で書いていて、WindowsのAPIを直接呼んでいます。

- 25分の作業と5分の休憩をくり返します。休憩になると、いま使っているウィンドウのふちに飛んできて座ります
- 作業中は、窓から窓へ飛び移ったり、お茶を飲んだり、釣りをしたり、勝手にすごします
- やることリスト、時刻のお知らせ、今日の内訳と1週間の記録、日報用のまとめがあります
- つまんで投げると、ウィンドウの辺で跳ね返り、縁につかまって登ります

使い方は [docs/readme.txt](docs/readme.txt) と [docs/manual.html](docs/manual.html) にあります。

## 動かす

配布用の zip（BouTimer.exe と、同梱の声・効果音）は、コンテストのページからダウンロードできます。

ソースから動かすときは、HSP 3.7（C:\hsp37）を入れて、`proto` フォルダで次のようにします。

```powershell
cd proto
& C:\hsp37\hspcmp.exe "--compath=C:\hsp37\common\" -i -u -d "-omain.ax" main.hsp
& C:\hsp37\hsp3utf.exe main.ax
```

- ソースは UTF-8 です。`#include "hsp3utf.as"` で hsp3utf.exe を使います
- 声のファイル（voice フォルダ）は、このリポジトリには入れていません。VOICEVOX を起動してから `python tools/make_voices.py` で作れます。なくても、声が出ないだけで動きます
- 効果音のファイル（se フォルダ）も入れていません。効果音ラボ（https://soundeffect-lab.info/）から `tools/make_se.py` に書いてあるファイルを `se_src` に置いて、`python tools/make_se.py` で作れます
- `powershell -ExecutionPolicy Bypass -File tools\build.ps1` で `dist\BouTimer.exe` を組み立てます
- `sh tools/regress.sh`（Git Bash）で、確認用モードをまとめて動かします

## フォルダ

| フォルダ | 中身 |
|---|---|
| proto | 本体。main.hsp が初期化とメインループで、機能ごとのファイルを `#include` しています |
| modules | ほかの HSP スクリプトからも使えるようにしたモジュールと、単体で動くサンプル |
| server | ゴースト機能とフレンド機能のサーバー（Cloudflare Workers + KV） |
| tools | 組み立て、アイコン、声と効果音の作成、PV の撮影、回帰テスト |
| docs | 説明書（readme.txt）と取扱説明書（manual.html） |

## モジュール

| ファイル | できること |
|---|---|
| mod_alphawin.as | 画素ごとに半透明なウィンドウ（GDI+ で描いて UpdateLayeredWindow で出す）。描いた形どおりにクリックが当たる |
| mod_deskwin.as | 開いているウィンドウを手前から「足場」として集める。DWM の実寸を使い、手前の窓に隠れた辺かどうかも調べられる |
| mod_peakmeter.as | 再生中の音の大きさを Core Audio で読み、拍の頭を拾う。録音はしない |

使い方は、それぞれのファイルの先頭と modules/readme_modules.txt にあります。

## クレジット

- 声：VOICEVOX:玄野武宏
- 効果音：効果音ラボ
- 着せ替えの髪型：珠音（HSP3 オフィシャル素材。著作権はオガワコウサク（チームグリグリ）氏、修正BSDライセンス）
- プログラムの作成に生成AI（Claude）を使用しています

## ライセンス

自由に再配布・改変してかまいません。modules フォルダのモジュールも、自由に使ってかまいません。

ただし、同梱の声（VOICEVOX:玄野武宏）と効果音（効果音ラボ）は、それぞれの利用規約にしたがいます。取り出して使わないでください。

## 作者

subara3（https://subara3.com/）
