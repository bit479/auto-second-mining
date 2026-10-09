import ctypes, ctypes.wintypes as wt, time

u = ctypes.windll.user32
lines = []

def enum_proc(hwnd, lparam):
    cls = ctypes.create_unicode_buffer(256)
    txt = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(hwnd, cls, 256)
    u.GetWindowTextW(hwnd, txt, 256)
    r = wt.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    vis = u.IsWindowVisible(hwnd)
    if vis and cls.value in ('#32770', 'AfxWnd140u', 'Afx:400000:8:00010003:0000000000000003:0000000032C51973'):
        lines.append('dlg=0x%X class=[%s] title=[%s] rect=(%d,%d)-(%d,%d)' % (hwnd, cls.value, txt.value, r.left, r.top, r.right, r.bottom))
    return True

CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
u.EnumWindows(CB(enum_proc), 0)
# Also capture the small child dialog windows of 3DMine
for h in [0x81762]:
    u.EnumChildWindows(h, CB(enum_proc), 0)

open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\dlgs.txt', 'w', encoding='utf-8').write('\n'.join(lines) if lines else 'no dialogs')
