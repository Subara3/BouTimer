#!/bin/sh
# 確認用モードをまとめて動かし、エラーで止まらずに debug.txt まで書けるかを見る
#   sh tools/regress.sh            （Git Bash から。proto\main.ax をビルドしてから使う）
# 声が出るもの・本番に送るもの・窓を前に出すものは入れていない
cd "$(dirname "$0")/../proto" || exit 1
HSP=/c/hsp37/hsp3utf.exe
fail=0
run() {
	mode="$1"; want="$2"; limit="$3"
	rm -f debug.txt
	timeout -s KILL "$limit" "$HSP" main.ax $mode
	code=$?
	if [ $code -ne 0 ] || [ ! -f debug.txt ]; then
		echo "NG  $mode（終わらなかった。実行時エラーのダイアログが裏に出ているかもしれない）"
		taskkill //F //IM hsp3utf.exe >/dev/null 2>&1
		fail=1
		return
	fi
	if [ -n "$want" ] && ! grep -aq "$want" debug.txt; then
		echo "NG  $mode（「$want」が debug.txt にない）"
		fail=1
		return
	fi
	echo "OK  $mode"
}
run "test" "f=1200" 60
run "todotest" "ナイスシュート" 60
run "alarmtest" "ALARM END" 60
run "copytest" "使ったアプリ" 60
run "stretchtest" "遠くを見ると" 60
run "histtest" "H 2026-10-15" 60
run "todotimetest" "TT stat n=3" 60
run "dailytest" "DD ストレッチ" 40
run "standtest noaudio" "そろそろ立って" 40
run "slacktest" "slack=1 elapsed" 40
run "phasese test noaudio" "SE se_alarm3s" 30
run "matchtest" "MATCH 1 ホーム" 40
run "posetest" "POSE 4" 40
run "todotest" "SE se_goal" 60
run "tdchecktest" "TC n=180 vis=1 d0=0" 30
run "hovertest" "HV f=420 hover=1 st=0" 30
run "midnighttest end20" "MID pending=1" 60
run "report" "" 30
run "diary" "" 30
run "weektest" "" 40
run "interact" "" 60
run "scold" "" 60
run "peektest" "" 60
run "fstest" "" 60
run "lowpow test" "" 60
run "climb" "" 60
run "throw" "" 60
run "wizardtest" "WFIRST f=1" 60
run "playtest" "DEV ヨーヨーで犬の散歩をした。" 90
run "clicktest" "CLICK f=560 paused=0" 60
run "diarytimetest" "WROTE size=" 60
run "bubbletest" "" 30
run "minetest end20" "MINEAPP myexe=hsp3utf.exe napp=1 app0=chrome.exe" 60
run "gaptest test" "GAPA" 30
run "alarm2test test" "AL2 fire 電話をかける" 60
run "matchtest" "MATCH 0 TODO / xyz" 40
run "metertest test" "METER reopen ok=1" 30
run "outsidetest test" "OUTSIDE cx=" 30
run "icontest" "ICONS n=" 40
run "pctest noaudio" "PCTALK 今日はマウスで" 30
run "animtest" "WAVE back" 50
run "ridetest" "RIDE" 30
run "typetest test" "速いな" 40
run "linetest test" "LN 7" 20
run "calltest calltray test" "CALL ok" 30
run "closetest closeclose brclose" "CTRLW to=" 60
run "starttest" "ST f=712 notyet=0 paused=0" 40
exit $fail
