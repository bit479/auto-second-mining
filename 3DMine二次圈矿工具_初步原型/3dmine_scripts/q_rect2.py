import ctypes
u = ctypes.windll.user32
class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
h = ctypes.c_void_p(0x81762)
r = RECT()
ok = u.GetWindowRect(h, ctypes.byref(r))
out = 'hwnd=0x81762 GetWindowRect ok=%s rect=(%d,%d)-(%d,%d) w=%d h=%d' % (ok, r.left, r.top, r.right, r.bottom, r.right - r.left, r.bottom - r.top)
out += '\nminimized=%s visible=%s fg=%s' % (bool(u.IsIconic(h)), bool(u.IsWindowVisible(h)), hex(u.GetForegroundWindow()))
# enumerate top-level windows of the 3dmine process to find all its windows
import subprocess
proc = subprocess.run(['powershell','-NoProfile','-Command','(Get-Process VisualMine).Id'], capture_output=True, text=True)
out += '\nVisualMine pids: ' + proc.stdout.strip()
# find windows owned by that pid
def enum(hwnd, lparam):
    pid = ctypes.c_ulong()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == 41560:
        sb = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(hwnd, sb, 256)
        rr = RECT()
        u.GetWindowRect(hwnd, ctypes.byref(rr))
        out_lines.append('  hwnd=0x%X title=[%s] rect=(%d,%d)-(%d,%d) visible=%s' % (hwnd, sb.value, rr.left, rr.top, rr.right, rr.bottom, bool(u.IsWindowVisible(hwnd))))
    return True
out_lines = []
u.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum), 0)
out += '\nWindows of pid 41560:\n' + '\n'.join(out_lines)
open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\q_rect2_out.txt', 'w', encoding='utf-8').write(out)
