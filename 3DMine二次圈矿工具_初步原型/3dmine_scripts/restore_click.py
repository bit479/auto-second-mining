import ctypes, ctypes.wintypes as wt, time, sys

u = ctypes.windll.user32
HWND = 0x81762

def restore_and_activate():
    u.ShowWindow(HWND, 9)  # SW_RESTORE
    time.sleep(0.5)
    u.SetForegroundWindow(HWND)
    time.sleep(0.5)
    r = wt.RECT()
    u.GetWindowRect(HWND, ctypes.byref(r))
    return 'rect=(%d,%d)-(%d,%d) iconic=%s' % (r.left, r.top, r.right, r.bottom, bool(u.IsIconic(HWND)))

def click(x, y):
    sx = int(x * 65535 / 1536)
    sy = int(y * 65535 / 864)
    u.mouse_event(0x8001, sx, sy, 0, 0)
    time.sleep(0.3)
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.1)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.7)

out = [restore_and_activate()]
mode = sys.argv[1]
if mode == 'click':
    click(int(sys.argv[2]), int(sys.argv[3]))
    out.append('clicked (%s,%s)' % (sys.argv[2], sys.argv[3]))
open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\restore_log.txt', 'w', encoding='utf-8').write('\n'.join(out))
