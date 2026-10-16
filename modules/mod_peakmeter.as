;============================================================
; mod_peakmeter.as
; 再生中の音の大きさを読み、拍の頭を拾う（Windows Vista 以降 / HSP3.7）
;
; Core Audio の IAudioMeterInformation を COM で使います。
; 読むのは既定の再生デバイスの「いまの音量のピーク値」だけで、録音はしません。
; COM の扱いと float の変換は、HSP 付属の common\mod_mmaudio.as と同じ方法です。
;
;   peak_open                … 初期化。成功で stat=1（出力デバイスがないと 0）
;   peak_update              … 毎フレーム呼ぶ（60fps を想定）
;   p = peak_value()         … いまのピーク値 0.0～1.0
;   e = peak_envelope()      … ならした音量
;   b = peak_beat()          … このフレームで拍の頭を拾ったら 1
;   m = peak_playing()       … しばらく鳴り続けていれば 1
;============================================================
#ifndef __MOD_PEAKMETER__
#define __MOD_PEAKMETER__

#module peakmeter

#usecom pm_IMMDeviceEnumerator "{A95664D2-9614-4F35-A746-DE8DB63617E6}" "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
#comfunc pm_GetDefaultAudioEndpoint 4 int, int, var
#usecom pm_IMMDevice "{D666063F-1587-4E43-81F1-B948E807363F}" "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
#comfunc pm_Activate 3 var, int, int, var
#usecom pm_IAudioMeterInformation "{C02216F6-8C67-4B5B-9D00-D008E73E0064}" "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
#comfunc pm_GetPeakValue 3 var


; 単精度のビット列を倍精度に（mod_mmaudio.as の todouble と同じ）
#defcfunc local pm_todouble int p_b, local d
	d = 0.0
	lpoke d, 4, (p_b & 0x80000000) | (((p_b & 0x7fffffff) >> 3) + ((p_b & 0x7fffffff) ! 0) * 0x38000000)
	lpoke d, 0, p_b << 29
	return d

#deffunc peak_open
	ok = 0 : peak = 0.0 : env = 0.0 : beat = 0 : since = 100 : play = 0
	newcom en, pm_IMMDeviceEnumerator
	if varuse(en) = 0 : return 0
	newcom dev, pm_IMMDevice, -1, 0
	newcom met, pm_IAudioMeterInformation, -1, 0
	pm_GetDefaultAudioEndpoint en, 0, 0, dev
	if varuse(dev) = 0 : return 0
	iid = 0xC02216F6, 0x4B5B8C67, 0x08D0009D, 0x64003EE7
	pm_Activate dev, iid, 1, 0, met
	if varuse(met) = 0 : return 0
	ok = 1
	return 1

#deffunc peak_update
	beat = 0
	if ok = 0 : return
	pb = 0
	pm_GetPeakValue met, pb
	peak = pm_todouble(pb)
	env = env * 0.96 + peak * 0.04
	since++
	; ならした音量よりはっきり大きく、前の拍から少し間があいていたら拍の頭
	if (peak > env * 1.35) & (peak > 0.04) & (since > 14) : beat = 1 : since = 0
	if env > 0.02 {
		if play < 600 : play++
	} else {
		if play > 0 : play -= 3
	}
	return

#defcfunc peak_value
	return peak

#defcfunc peak_envelope
	return env

#defcfunc peak_beat
	return beat

#defcfunc peak_playing
	return play >= 180

#global
#endif
