import ctypes, ctypes.wintypes as wt

u = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

hwnd = 0x81762
lines = []

def enum_proc(child, lparam):
    cls = ctypes.create_unicode_buffer(256)
    txt = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(child, cls, 256)
    u.GetWindowTextW(child, txt, 256)
    r = RECT()
    u.GetWindowRect(child, ctypes.byref(r))
    vis = u.IsWindowVisible(child)
    if vis and r.right > r.left:
        lines.append('child=0x%X class=[%s] title=[%s] rect=(%d,%d)-(%d,%d)' % (child, cls.value, txt.value, r.left, r.top, r.right, r.bottom))
    return True

CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
u.EnumChildWindows(hwnd, CB(enum_proc), 0)
open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\children.txt', 'w', encoding='utf-8').write('\n'.join(lines) if lines else 'no children')
