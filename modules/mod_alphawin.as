;============================================================
; mod_alphawin.as
; 画素ごとに半透明なウィンドウを作る（HSP3.7 / hsp3utf 想定）
;
; GDI+ で 32bit の画像（アルファ付き）に描き、UpdateLayeredWindow で表示します。
; カラーキー方式と違い、アンチエイリアスの縁がにじみません。
; ウィンドウはフォーカスを取らず、常に最前面にいます。
;
;   alphawin_init id, w, h, x, y   … ウィンドウと描画先を作る
;   g = alphawin_graphics()        … GDI+ の Graphics ハンドル（Gdip～ 関数で描く）
;   alphawin_clear                 … 全面を透明にする
;   alphawin_show x, y             … 描いた内容を画面へ出す（位置もここで決める）
;   a = alphawin_alpha(x, y)       … その画素の不透明度 0～255（当たり判定に使う）
;   h = alphawin_hwnd()            … ウィンドウハンドル
;============================================================
#ifndef __MOD_ALPHAWIN__
#define __MOD_ALPHAWIN__

#module alphawin

#uselib "user32.dll"
#cfunc aw_GetWindowLong "GetWindowLongW" int, int
#func aw_SetWindowLong "SetWindowLongW" int, int, int
#func aw_ShowWindow "ShowWindow" int, int
#func aw_SetWindowPos "SetWindowPos" int, int, int, int, int, int, int
#func aw_UpdateLayeredWindow "UpdateLayeredWindow" int, int, var, var, int, var, int, var, int
#uselib "gdi32.dll"
#cfunc aw_CreateCompatibleDC "CreateCompatibleDC" int
#cfunc aw_CreateDIBSection "CreateDIBSection" int, var, int, var, int, int
#func aw_SelectObject "SelectObject" int, int
#uselib "gdiplus.dll"
#func aw_GdiplusStartup "GdiplusStartup" var, var, int
#func aw_GdipCreateBitmapFromScan0 "GdipCreateBitmapFromScan0" int, int, int, int, int, var
#func aw_GdipGetImageGraphicsContext "GdipGetImageGraphicsContext" int, var
#func aw_GdipSetSmoothingMode "GdipSetSmoothingMode" int, int
#func aw_GdipGraphicsClear "GdipGraphicsClear" int, int


#deffunc alphawin_init int p_id, int p_w, int p_h, int p_x, int p_y
	; 初期状態で隠した枠なしウィンドウを、半透明・タスクバーに出さない・フォーカスを取らない設定にする
	bgscr p_id, p_w, p_h, 2, p_x, p_y
	hw = hwnd
	exs = aw_GetWindowLong(hw, -20)
	exs = exs | 0x80000 | 0x80 | 0x08000000
	aw_SetWindowLong hw, -20, exs
	aw_ShowWindow hw, 4
	aw_SetWindowPos hw, -1, 0, 0, 0, 0, 0x13
	; 描画先：32bit DIB を作り、同じメモリを GDI+ のビットマップ（PARGB）としても使う
	dim si, 4 : si(0) = 1
	aw_GdiplusStartup tok, si, 0
	dim bmi, 10
	bmi(0) = 40 : bmi(1) = p_w : bmi(2) = -p_h : bmi(3) = 1 | (32 << 16)
	ppv = 0
	hbmp = aw_CreateDIBSection(0, bmi, 0, ppv, 0, 0)
	mdc = aw_CreateCompatibleDC(0)
	aw_SelectObject mdc, hbmp
	dupptr bits, ppv, p_w * p_h * 4, 2
	aw_GdipCreateBitmapFromScan0 p_w, p_h, p_w * 4, 0xE200B, ppv, gb
	aw_GdipGetImageGraphicsContext gb, g
	aw_GdipSetSmoothingMode g, 4
	ww = p_w : hh = p_h
	dim psz, 2 : psz(0) = ww : psz(1) = hh
	dim pts, 2 : dim ptd, 2
	blend = 0x01FF0000
	return

#defcfunc alphawin_graphics
	return g

#defcfunc alphawin_hwnd
	return hw

#deffunc alphawin_clear
	aw_GdipGraphicsClear g, 0
	return

#deffunc alphawin_show int p_x, int p_y
	ptd(0) = p_x : ptd(1) = p_y
	aw_UpdateLayeredWindow hw, 0, ptd, psz, mdc, pts, 0, blend, 2
	return

#defcfunc alphawin_alpha int p_x, int p_y
	if (p_x < 0) | (p_y < 0) | (p_x >= ww) | (p_y >= hh) : return 0
	return (lpeek(bits, (p_y * ww + p_x) * 4) >> 24) & 255

#global
#endif
