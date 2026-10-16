# pv\下書き_ぼうタイマー.mp4 に字幕と題名を重ねて pv\PV_作業のおとも、棒人間.mp4 を作る
# 字幕の文言と時間（秒）は下の $caps で変えられる
$root = Split-Path $PSScriptRoot
$pv = Join-Path $root "pv"
$ff = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (-not $ff) { throw "ffmpeg が見つかりません" }

# 下書き版のつなぎ順：B1(0-13) B2(13-28) D(28-44) C(44-58) A(58-118)
$caps = @(
  @(3, 13, "投げると、窓の辺で跳ね返る"),
  @(13, 28, "窓の縁で離すと、よじ登る"),
  @(28, 44, "作業中にサボり先を開くと、注意しに来る"),
  @(44, 58, "25分たつと休憩。使っている窓のふちで休む"),
  @(58, 112, "作業中は、勝手にいろいろやっている")
)
$titleText = "作業のおとも、棒人間"
$font = "C\:/Windows/Fonts/meiryob.ttc"

Set-Location $pv
$enc = New-Object Text.UTF8Encoding $false
$filters = @()
# 題名（最初の3秒と、最後の6秒）
[IO.File]::WriteAllText((Join-Path $pv "cap_title.txt"), $titleText, $enc)
$filters += "drawtext=fontfile='$font':textfile=cap_title.txt:fontsize=72:fontcolor=0x2E2E36:box=1:boxcolor=white@0.85:boxborderw=24:x=(w-text_w)/2:y=(h-text_h)/2-40:enable='lt(t,3)+gte(t,112)'"
for ($i = 0; $i -lt $caps.Count; $i++) {
  $f = "cap_$i.txt"
  [IO.File]::WriteAllText((Join-Path $pv $f), $caps[$i][2], $enc)
  $filters += "drawtext=fontfile='$font':textfile=$($f):fontsize=34:fontcolor=white:box=1:boxcolor=0x2E2E36@0.75:boxborderw=14:x=(w-text_w)/2:y=h-text_h-36:enable='between(t,$($caps[$i][0]),$($caps[$i][1]))'"
}
$vf = $filters -join ","
$a = "-y -loglevel error -i `"下書き_ぼうタイマー.mp4`" -vf `"$vf`" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p `"PV_作業のおとも、棒人間.mp4`""
Start-Process $ff -ArgumentList $a -NoNewWindow -Wait
Remove-Item cap_*.txt
Get-Item (Join-Path $pv "PV_作業のおとも、棒人間.mp4") | Select-Object Name, Length
