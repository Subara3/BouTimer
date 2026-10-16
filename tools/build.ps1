# proto\main.hsp から dist\start.exe を作る
#   powershell -ExecutionPolicy Bypass -File tools\build.ps1
# hsc3_make（exeの組み立て）は日本語を含むパスで失敗するので、ASCII だけのフォルダで組み立ててからコピーする
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot
$proto = Join-Path $root "proto"
$dist = Join-Path $root "dist"
$work = "D:\hsptest_tmp"
$hsp = "C:\hsp37"

New-Item -ItemType Directory -Force $work, $dist | Out-Null
# 配る前の状態にする（テストで作られた記録は消す）
foreach ($f in "debug.txt", "settings.txt", "distract.txt", "history.txt", "todo.txt", "alarm.txt", "kotoba.txt") { Remove-Item (Join-Path $dist $f) -ErrorAction SilentlyContinue }
Remove-Item (Join-Path $dist "diary") -Recurse -ErrorAction SilentlyContinue

Set-Location $PSScriptRoot
& "$hsp\hspcmp.exe" "--compath=$hsp\common\" -i "-obuild.ax" build.hsp | Out-Null

# 本体：UTF-8 のソースを読み、文字列も UTF-8 で出す
Set-Location $proto
$out = & "$hsp\hspcmp.exe" "--compath=$hsp\common\" -i -u "-ostart.ax" main.hsp 2>&1 | Out-String
if ($out -notmatch "No error detected") { $out; throw "compile failed" }
Move-Item -Force start.ax (Join-Path $work "start.ax")
Remove-Item packfile -ErrorAction SilentlyContinue

# #packopt と同じ内容の packfile
";!runtime=hsp3utf.hrt`r`n;!name=BouTimer`r`n;!hide=1`r`n+>start.ax`r`n" | Set-Content -NoNewline -Encoding Default (Join-Path $work "packfile")
& "$hsp\hsp3cl.exe" (Join-Path $PSScriptRoot "build.ax") $work | Out-Null
if ($LASTEXITCODE -ne 0) { throw "make failed" }

# exe のアイコンを棒人間の顔にする（tools\make_icon.py で作った boutimer.ico を、HSP 付属の iconins.exe で埋めこむ）
# iconins は引数の "" をそのまま読むので、cmd のバッチから呼ぶ。最後に Enter を待つので nul を渡す
Copy-Item -Force (Join-Path $PSScriptRoot "boutimer.ico") (Join-Path $work "boutimer.ico")
# バージョン情報（exe のプロパティに出る。iconins が読むので Shift-JIS で書いてある）
Copy-Item -Force (Join-Path $PSScriptRoot "version.txt") (Join-Path $work "version.txt")
$bat = Join-Path $work "icon.bat"
"@echo off`r`ncd /d $work`r`n$hsp\iconins.exe -e`"$work\BouTimer.exe`" -i`"$work\boutimer.ico`" -v`"$work\version.txt`" < nul`r`n" | Set-Content -NoNewline -Encoding Default $bat
$iconout = cmd /c $bat | Out-String
if ($iconout -notmatch "Kpan") { $iconout; throw "icon failed" }

Copy-Item -Force (Join-Path $work "BouTimer.exe") (Join-Path $dist "BouTimer.exe")
Copy-Item -Force (Join-Path $root "docs\readme.txt") (Join-Path $dist "readme.txt")
# 取扱説明書（HTML。外のファイルを読まないので、オフラインでも見られる）
Copy-Item -Force (Join-Path $root "docs\manual.html") (Join-Path $dist "manual.html")
Copy-Item -Force (Join-Path $root "docs\tech_*.html") $dist
# 通信に使う hspinet プラグインは exe に入らないので横に置く（HSP 付属のプラグインは再配布可）
Copy-Item -Force "$hsp\hspinet.dll" (Join-Path $dist "hspinet.dll")
New-Item -ItemType Directory -Force (Join-Path $dist "modules") | Out-Null
Copy-Item -Force (Join-Path $root "modules\*") (Join-Path $dist "modules")
# 同梱の声（tools\make_voices.py で作った玄野武宏の声と、口パク用の情報）
Remove-Item (Join-Path $dist "voice") -Recurse -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force (Join-Path $dist "voice") | Out-Null
Copy-Item -Force (Join-Path $root "voice\v_*") (Join-Path $dist "voice")
# 効果音（効果音ラボ。tools\make_se.py で wav にしたもの）
Remove-Item (Join-Path $dist "se") -Recurse -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force (Join-Path $dist "se") | Out-Null
Copy-Item -Force (Join-Path $root "se\se_*.wav") (Join-Path $dist "se")
Remove-Item (Join-Path $work "start.ax"), (Join-Path $work "packfile"), (Join-Path $work "BouTimer.exe"), (Join-Path $work "boutimer.ico"), (Join-Path $work "version.txt"), $bat -ErrorAction SilentlyContinue
Get-Item (Join-Path $dist "BouTimer.exe") | Select-Object FullName, Length, LastWriteTime
