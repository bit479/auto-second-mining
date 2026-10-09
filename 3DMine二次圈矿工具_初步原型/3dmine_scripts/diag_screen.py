import ctypes, ctypes.wintypes as wt, time, traceback
try:
    u = ctypes.windll.user32
    lines = []
    lines.append('primary screen: %dx%d' % (u.GetSystemMetrics(0), u.GetSystemMetrics(1)))
    lines.append('virtual screen: x=%d y=%d w=%d h=%d' % (u.GetSystemMetrics(76), u.GetSystemMetrics(77), u.GetSystemMetrics(78), u.GetSystemMetrics(79)))
    ok = u.SetCursorPos(1230, 25)
    lines.append('SetCursorPos ok=%d' % ok)
    time.sleep(0.3)
    pt = wt.POINT()
    u.GetCursorPos(ctypes.byref(pt))
    lines.append('cursor now at (%d,%d)' % (pt.x, pt.y))
    open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\diag_screen.txt', 'w', encoding='utf-8').write('\n'.join(lines))
except Exception:
    open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\diag_screen.txt', 'w', encoding='utf-8').write(traceback.format_exc())
