# PV 用の素材を撮る（舞台の上でキャラを動かし、1280x720 の範囲だけを録画する）
#   powershell -ExecutionPolicy Bypass -File tools\pv_record.ps1 [-Only "C,D"]
param([string]$Only = "A,B1,B2,C,D")
$Only = $Only -split ","
$root = Split-Path $PSScriptRoot
$proto = Join-Path $root "proto"
$out = Join-Path $root "pv"
$ff = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (-not $ff) { throw "ffmpeg が見つかりません" }
New-Item -ItemType Directory -Force $out | Out-Null

Add-Type -AssemblyName System.Windows.Forms
Add-Type -Name M -Namespace PV -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
[DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
[DllImport("user32.dll")] public static extern void mouse_event(int f, int dx, int dy, int d, int e);
[DllImport("user32.dll")] public static extern void keybd_event(byte v, byte s, int f, int e);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
public delegate bool EnumProc(IntPtr h, IntPtr l);
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
[DllImport("user32.dll")] public static extern IntPtr WindowFromPoint(POINT p);
[DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr h, uint f);
[StructLayout(LayoutKind.Sequential)] public struct POINT { public int X; public int Y; public POINT(int x, int y) { X = x; Y = y; } }
'@
[PV.M]::SetProcessDPIAware() | Out-Null
$gy = [Windows.Forms.Screen]::PrimaryScreen.WorkingArea.Bottom
$oy = $gy - 720

# HSP ランタイムで .ax を動かす
Push-Location $proto
& "C:\hsp37\hspcmp.exe" "--compath=C:\hsp37\common\" -i -u -d "-omain.ax" main.hsp | Out-Null
Pop-Location
Push-Location $PSScriptRoot
& "C:\hsp37\hspcmp.exe" "--compath=C:\hsp37\common\" -i -u "-opvstage.ax" pvstage.hsp | Out-Null
Pop-Location
# 初回の案内が出ないよう設定ファイルを置く
if (-not (Test-Path (Join-Path $proto "settings.txt"))) { "work_min=25`r`nbreak_min=5`r`n" | Set-Content -Encoding UTF8 (Join-Path $proto "settings.txt") }

# 舞台の fg 番目のウィンドウ（1=メモ 2=YouTube 3=エディタ）を確実に前面へ
function FocusStage([int]$procId, [int]$fg) {
  $prefix = @("", "メモ", "YouTube", "エディタ")[$fg]
  $script:target = [IntPtr]::Zero
  [PV.M]::EnumWindows({ param($h, $l)
    $p = 0; [PV.M]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
    if ($p -eq $procId) { $sb = New-Object System.Text.StringBuilder 256; [PV.M]::GetWindowText($h, $sb, 256) | Out-Null; if ($sb.ToString().StartsWith($prefix)) { $script:target = $h; return $false } }
    return $true }, [IntPtr]::Zero) | Out-Null
  if ($script:target -ne [IntPtr]::Zero) { [PV.M]::keybd_event(0x12, 0, 0, 0); [PV.M]::keybd_event(0x12, 0, 2, 0); [PV.M]::SetForegroundWindow($script:target) | Out-Null }
}
function Shot([string]$name, [int]$secs, [string]$mode, [int]$fg, [scriptblock]$action) {
  $st = Start-Process C:\hsp37\hsp3utf.exe -ArgumentList "pvstage.ax $($secs + 8) 0 $oy $fg" -WorkingDirectory $PSScriptRoot -PassThru
  Start-Sleep 2
  if ($fg) { FocusStage $st.Id $fg }
  $ch = Start-Process C:\hsp37\hsp3utf.exe -ArgumentList "main.ax $mode noidle" -WorkingDirectory $proto -PassThru
  Start-Sleep -Milliseconds 300
  $file = Join-Path $out "$name.mp4"
  $a = "-y -loglevel error -f lavfi -i `"ddagrab=output_idx=0:framerate=30:draw_mouse=1:offset_x=0:offset_y=${oy}:video_size=1280x720,hwdownload,format=bgra`" -t $secs -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p `"$file`""
  $rec = Start-Process $ff -ArgumentList $a -PassThru -WindowStyle Hidden
  if ($action) { & $action }
  $rec.WaitForExit(($secs + 30) * 1000) | Out-Null
  $ch | Stop-Process -Force -ErrorAction SilentlyContinue
  $st | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep 1
  "{0}: {1:N1} MB" -f $name, ((Get-Item $file).Length / 1MB)
}
# ddagrab が止まってしまう場面用：CopyFromScreen で 12fps のコマを撮って動画にする
function ShotFrames([string]$name, [int]$secs, [string]$mode, [int]$fg) {
  Add-Type -AssemblyName System.Drawing
  $st = Start-Process C:\hsp37\hsp3utf.exe -ArgumentList "pvstage.ax $($secs + 8) 0 $oy $fg" -WorkingDirectory $PSScriptRoot -PassThru
  Start-Sleep 2
  if ($fg) { FocusStage $st.Id $fg }
  $ch = Start-Process C:\hsp37\hsp3utf.exe -ArgumentList "main.ax $mode noidle" -WorkingDirectory $proto -PassThru
  $tmp = Join-Path $env:TEMP "boutimer_frames"
  Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue; New-Item -ItemType Directory $tmp | Out-Null
  $bmp = New-Object Drawing.Bitmap 1280, 720
  $g = [Drawing.Graphics]::FromImage($bmp)
  $enc = [Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
  $ep = New-Object Drawing.Imaging.EncoderParameters 1
  $ep.Param[0] = New-Object Drawing.Imaging.EncoderParameter ([Drawing.Imaging.Encoder]::Quality, [long]92)
  # 写り込み防止：録画範囲の格子点で、いちばん手前の窓が舞台か本体のプロセスのものかを確かめる
  $ok = { param($pids)
    for ($yy = 20; $yy -lt 720; $yy += 70) { for ($xx = 20; $xx -lt 1280; $xx += 90) {
      $h = [PV.M]::GetAncestor([PV.M]::WindowFromPoint(([PV.M+POINT]::new($xx, $oy + $yy))), 2)
      $wp = 0; [PV.M]::GetWindowThreadProcessId($h, [ref]$wp) | Out-Null
      if (-not ($pids -contains [int]$wp)) { return $false } } }
    return $true }
  $sw = [Diagnostics.Stopwatch]::StartNew(); $n = 0; $bad = 0; $saved = 0
  $pids = @($st.Id, $ch.Id)
  while ($sw.Elapsed.TotalSeconds -lt $secs) {
    $target = $n / 12.0
    while ($sw.Elapsed.TotalSeconds -lt $target) { Start-Sleep -Milliseconds 5 }
    if (-not (& $ok $pids)) { $bad++; if ($bad -gt 24) { break }; $n++; continue }
    $g.CopyFromScreen(0, $oy, 0, 0, $bmp.Size)
    $bmp.Save((Join-Path $tmp ("f{0:D5}.jpg" -f $saved)), $enc, $ep)
    $n++; $saved++
  }
  $ch | Stop-Process -Force -ErrorAction SilentlyContinue
  $st | Stop-Process -Force -ErrorAction SilentlyContinue
  $file = Join-Path $out "$name.mp4"
  & $ff -y -loglevel error -framerate 12 -i (Join-Path $tmp "f%05d.jpg") -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -r 30 $file
  Remove-Item $tmp -Recurse -Force
  if ($bad -gt 24) { Remove-Item $file -ErrorAction SilentlyContinue; "{0}: 他の窓が重なったので中止（{1}コマ）" -f $name, $bad; return }
  "{0}: {1} frames saved, {2} skipped, {3:N1} MB" -f $name, $saved, $bad, ((Get-Item $file).Length / 1MB)
}
function Press { [PV.M]::mouse_event(2, 0, 0, 0, 0) }
function Release { [PV.M]::mouse_event(4, 0, 0, 0, 0) }
function MoveTo([int]$x, [int]$y) { [PV.M]::SetCursorPos($x, $y) | Out-Null }

$hy = $gy - 53   # realtest で x=800 に立たせたときの頭の位置

if ($Only -contains "A") { Shot "A_いろいろな動き" 110 "show" 0 $null }

if ($Only -contains "B1") {
  Shot "B1_投げて跳ね返る" 16 "realtest" 0 {
    Start-Sleep 4
    MoveTo 800 $hy; Start-Sleep -Milliseconds 150; Press
    for ($i = 1; $i -le 30; $i++) { MoveTo (800 - $i * 6) ($hy - $i * 5); Start-Sleep -Milliseconds 30 }
    Start-Sleep -Milliseconds 500
    for ($i = 1; $i -le 5; $i++) { MoveTo (620 + $i * 40) ($hy - 150); Start-Sleep -Milliseconds 16 }
    Release; MoveTo 1260 ($oy + 20)
  }
}

if ($Only -contains "B2") {
  Shot "B2_縁を登る" 18 "realtest" 0 {
    Start-Sleep 4
    MoveTo 800 $hy; Start-Sleep -Milliseconds 150; Press
    for ($i = 1; $i -le 40; $i++) { MoveTo (800 - [int]((800 - 524) * $i / 40)) ($hy - [int](($hy - ($oy + 338)) * $i / 40)); Start-Sleep -Milliseconds 30 }
    Start-Sleep -Milliseconds 600
    Release; MoveTo 1260 ($oy + 20)
  }
}

if ($Only -contains "C") { Shot "C_休憩でふちに座る" 20 "test" 3 $null }
if ($Only -contains "D") { Shot "D_サボり先を注意" 22 "scold" 2 $null }
if ($Only -contains "F") { ShotFrames "F_ゴーストが来る" 24 "show ghostdemo" 0 }
