# 題名と exe 名を一度に差し替えて、配布物を作り直す
#   powershell -ExecutionPolicy Bypass -File tools\set_title.ps1 -Title "題名" -ExeName "exeの名前（英数字）"
param(
  [Parameter(Mandatory = $true)][string]$Title,
  [Parameter(Mandatory = $true)][string]$ExeName
)
$ErrorActionPreference = "Stop"
if ($ExeName -notmatch '^[A-Za-z0-9_\-]+$') { throw "ExeName は英数字・_・- だけにしてください（exe の組み立てが日本語名で失敗するため）" }
$root = Split-Path $PSScriptRoot
$utf8 = New-Object Text.UTF8Encoding $false
$utf8bom = New-Object Text.UTF8Encoding $true

# 本体：#packopt name
$main = Join-Path $root "proto\main.hsp"
$t = [IO.File]::ReadAllText($main)
$t = [regex]::Replace($t, '#packopt name "[^"]*"', "#packopt name `"$ExeName`"")
[IO.File]::WriteAllText($main, $t, $utf8)

# ビルド：packfile と出力名
$build = Join-Path $PSScriptRoot "build.ps1"
$b = [IO.File]::ReadAllText($build, [Text.Encoding]::UTF8)
$b = [regex]::Replace($b, ';!name=[^`]*`r`n', ";!name=$ExeName``r``n")
$b = [regex]::Replace($b, '"[A-Za-z0-9_\-]+\.exe"', "`"$ExeName.exe`"")
[IO.File]::WriteAllText($build, $b, $utf8bom)

# 説明書：見出しと exe 名
$readme = Join-Path $root "docs\readme.txt"
$r = [IO.File]::ReadAllText($readme)
$r = [regex]::Replace($r, '(?m)^  （題名）\r?$|^  .+(?=\r?\n  デスクトップのウィンドウの上を歩きまわる)', "  $Title")
$r = [regex]::Replace($r, '\b[A-Za-z0-9_\-]+\.exe\b', "$ExeName.exe")
[IO.File]::WriteAllText($readme, $r, $utf8bom)

# 古い名前の exe を残さない
Remove-Item (Join-Path $root "dist\*.exe") -ErrorAction SilentlyContinue
& powershell -NoProfile -ExecutionPolicy Bypass -File $build
