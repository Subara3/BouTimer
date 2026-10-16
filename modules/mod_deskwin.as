;============================================================
; mod_deskwin.as
; デスクトップに開いているウィンドウを「足場」として列挙する（HSP3.7）
;
; ・位置は DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS) で取るので、
;   Windows 10/11 の見えない影の分のずれがありません
; ・最小化・最大化・透過（クリック素通し）・裏に隠れた UWP（cloaked）は除きます
; ・手前の別のウィンドウに隠れている辺かどうかを判定できます
;
;   deskwin_scan selfhwnd          … 手前から順に集める（自分のウィンドウは除く）
;   n = deskwin_count()
;   v = deskwin_get(i, k)          … k: 0=hwnd 1=左 2=上 3=右 4=下
;   ok = deskwin_visible(i, x, y)  … 点(x,y)で一番手前にあるのが i 番のウィンドウか
;   deskwin_rect hwnd, 配列        … 指定ウィンドウの実寸（配列(0..3)=左,上,右,下）。失敗で stat=0
;============================================================
#ifndef __MOD_DESKWIN__
#define __MOD_DESKWIN__

#module deskwin

#uselib "user32.dll"
#cfunc dw_GetTopWindow "GetTopWindow" int
#cfunc dw_GetWindow "GetWindow" int, int
#cfunc dw_IsWindowVisible "IsWindowVisible" int
#cfunc dw_IsIconic "IsIconic" int
#cfunc dw_IsZoomed "IsZoomed" int
#cfunc dw_GetWindowLong "GetWindowLongW" int, int
#cfunc dw_WindowFromPoint "WindowFromPoint" int, int
#cfunc dw_GetAncestor "GetAncestor" int, int
#func dw_GetWindowRect "GetWindowRect" int, var
#uselib "dwmapi.dll"
#func dw_DwmGetWindowAttribute "DwmGetWindowAttribute" int, int, var, int


#deffunc deskwin_rect int p_h, array p_rc
	if dw_IsWindowVisible(p_h) = 0 : return 0
	dim rr, 4
	dw_DwmGetWindowAttribute p_h, 9, rr, 16
	if stat != 0 : dw_GetWindowRect p_h, rr
	p_rc(0) = rr(0) : p_rc(1) = rr(1) : p_rc(2) = rr(2) : p_rc(3) = rr(3)
	return 1

#deffunc deskwin_scan int p_self
	if inited = 0 : dim wl, 5, 512 : inited = 1
	n = 0
	dim rr, 4
	h = dw_GetTopWindow(0)
	repeat
		if (h = 0) | (n >= 512) : break
		ok = (h != p_self) & dw_IsWindowVisible(h)
		if ok : ok = (dw_IsIconic(h) = 0) & (dw_IsZoomed(h) = 0) & ((dw_GetWindowLong(h, -20) & 0x20) = 0)
		if ok {
			cloak = 0
			dw_DwmGetWindowAttribute h, 14, cloak, 4
			if cloak = 0 {
				dw_DwmGetWindowAttribute h, 9, rr, 16
				if stat != 0 : dw_GetWindowRect h, rr
				if (rr(2) - rr(0) >= 60) & (rr(3) - rr(1) >= 20) {
					wl(0, n) = h : wl(1, n) = rr(0) : wl(2, n) = rr(1) : wl(3, n) = rr(2) : wl(4, n) = rr(3)
					n++
				}
			}
		}
		h = dw_GetWindow(h, 2)
	loop
	return n

#defcfunc deskwin_count
	return n

#defcfunc deskwin_get int p_i, int p_k
	return wl(p_k, p_i)

#defcfunc deskwin_visible int p_i, int p_x, int p_y
	return dw_GetAncestor(dw_WindowFromPoint(p_x, p_y), 2) = wl(0, p_i)

#global
#endif
