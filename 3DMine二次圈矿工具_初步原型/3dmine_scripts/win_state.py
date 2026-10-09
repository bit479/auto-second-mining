import ctypes, ctypes.wintypes as wt
u = ctypes.windll.user32
lines = []
for h in [0x81762, 0xA0E8A]:
    if u.IsWindow(h):
        txt = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(h, txt, 256)
        cls = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(h, cls, 256)
        r = wt.RECT()
        u.GetWindowRect(h, ctypes.byref(r))
        lines.append('0x%X title=[%s] class=[%s] rect=(%d,%d)-(%d,%d) visible=%s iconic=%s' % (h, txt.value, cls.value, r.left, r.top, r.right, r.bottom, bool(u.IsWindowVisible(h)), bool(u.IsIconic(h))))
    else:
        lines.append('0x%X NOT a window' % h)
lines.append('fg=0x%X' % u.GetForegroundWindow())
open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\win_state.txt', 'w', encoding='utf-8').write('\n'.join(lines))
