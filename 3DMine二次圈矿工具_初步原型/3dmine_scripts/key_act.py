import ctypes, ctypes.wintypes as wt, time, sys

u = ctypes.windll.user32
HWND = 0x81762

def activate():
    u.ShowWindow(HWND, 9)
    time.sleep(0.4)
    fg = u.GetForegroundWindow()
    # if not our window, force
    if fg != HWND:
        my_tid = u.GetWindowThreadProcessId(HWND, None)
        fg_tid = u.GetWindowThreadProcessId(fg, None)
        u.AttachThreadInput(my_tid, fg_tid, True)
        u.BringWindowToTop(HWND)
        u.SetForegroundWindow(HWND)
        u.AttachThreadInput(my_tid, fg_tid, False)
    time.sleep(0.4)
    return u.GetForegroundWindow()

def key(vk, up=False):
    u.keybd_event(vk, 0, 2 if up else 0, 0)
    time.sleep(0.06)

def tap(vk):
    key(vk); time.sleep(0.05); key(vk, True); time.sleep(0.4)

lines = ['fg_before=0x%X' % u.GetForegroundWindow()]
fg = activate()
lines.append('fg_after=0x%X hwnd=0x%X' % (fg, HWND))
mode = sys.argv[1]
if mode == 'f10':
    tap(0x77)
    lines.append('sent F10')
elif mode == 'alt':
    key(0x12); time.sleep(0.2); key(0x12, True); time.sleep(0.4)
    lines.append('sent Alt')
elif mode.startswith('alt_'):
    letter = mode.split('_')[1].upper()
    key(0x12); time.sleep(0.15)
    key(ord(letter)); time.sleep(0.08)
    key(ord(letter), True); time.sleep(0.08)
    key(0x12, True); time.sleep(0.7)
    lines.append('sent Alt+%s' % letter)
elif mode == 'right':
    tap(0x27)
    lines.append('right')
elif mode == 'down':
    tap(0x28)
    lines.append('down')
elif mode == 'enter':
    tap(0x0D)
    lines.append('enter')
elif mode == 'esc':
    tap(0x1B)
    lines.append('esc')
open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\key_log.txt', 'w', encoding='utf-8').write('\n'.join(lines))
