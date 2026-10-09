import ctypes, ctypes.wintypes as wt, time, sys

u = ctypes.windll.user32
HWND = 0x81762

def activate_strong():
    # attach input threads to bypass foreground lock
    fg = u.GetForegroundWindow()
    fg_tid = u.GetWindowThreadProcessId(fg, None)
    my_tid = u.GetWindowThreadProcessId(HWND, None)
    u.AttachThreadInput(my_tid, fg_tid, True)
    u.BringWindowToTop(HWND)
    u.SetForegroundWindow(HWND)
    u.AttachThreadInput(my_tid, fg_tid, False)
    time.sleep(0.5)
    return u.GetForegroundWindow()

def click(x, y):
    # absolute pixel coords on 1536x864
    sx = int(x * 65535 / 1536)
    sy = int(y * 65535 / 864)
    u.mouse_event(0x8001, sx, sy, 0, 0)
    time.sleep(0.3)
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.1)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.6)

mode = sys.argv[1]
out = []
out.append('fg_before=0x%X' % u.GetForegroundWindow())
fg = activate_strong()
out.append('fg_after_activate=0x%X' % fg)
if mode == 'click':
    x = int(sys.argv[2]); y = int(sys.argv[3])
    click(x, y)
    out.append('clicked (%d,%d) fg_now=0x%X' % (x, y, u.GetForegroundWindow()))
elif mode == 'key':
    # alt + letter
    u.keybd_event(0x12, 0, 0, 0)
    time.sleep(0.15)
    u.keybd_event(ord(sys.argv[2]), 0, 0, 0)
    time.sleep(0.1)
    u.keybd_event(ord(sys.argv[2]), 0, 2, 0)
    time.sleep(0.1)
    u.keybd_event(0x12, 0, 2, 0)
    time.sleep(0.8)
    out.append('sent alt+%s fg_now=0x%X' % (sys.argv[2], u.GetForegroundWindow()))
elif mode == 'enter':
    u.keybd_event(0x0D, 0, 0, 0)
    time.sleep(0.1)
    u.keybd_event(0x0D, 0, 2, 0)
    time.sleep(0.6)
    out.append('enter sent')
open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\drive_log.txt', 'w', encoding='utf-8').write('\n'.join(out))
