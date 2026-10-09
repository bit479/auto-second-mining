import ctypes
u = ctypes.windll.user32
hwnd = 0xD205C
r1 = u.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
ctypes.windll.kernel32.Sleep(800)
r2 = u.IsWindow(hwnd)
open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\close_dlg_log.txt', 'w', encoding='utf-8').write('post close=%d still_window=%d' % (r1, r2))
