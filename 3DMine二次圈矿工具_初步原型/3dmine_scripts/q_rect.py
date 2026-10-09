import ctypes
u = ctypes.windll.user32
class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
h = ctypes.c_void_p(0x530274)
r = RECT()
ok = u.GetWindowRect(h, ctypes.byref(r))
out = 'GetWindowRect ok=%s rect=(%d,%d)-(%d,%d) w=%d h=%d' % (ok, r.left, r.top, r.right, r.bottom, r.right - r.left, r.bottom - r.top)
out += '\nminimized=%s visible=%s fg=%s' % (bool(u.IsIconic(h)), bool(u.IsWindowVisible(h)), hex(u.GetForegroundWindow()))
import sys
sys.stdout.write(out + '\n')
sys.stdout.flush()
