import ctypes, ctypes.wintypes as wt, struct, time

u = ctypes.windll.user32
g = ctypes.windll.gdi32
HWND = 0x81762
out = r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\diag.bmp'
lines = []
def log(s):
    lines.append(str(s))

r = wt.RECT()
okr = u.GetWindowRect(HWND, ctypes.byref(r))
log('GetWindowRect=%s rect=%d,%d,%d,%d' % (okr, r.left, r.top, r.right, r.bottom))
log('IsWindow=%s IsWindowVisible=%s' % (bool(u.IsWindow(HWND)), bool(u.IsWindowVisible(HWND))))
w = r.right - r.left
h = r.bottom - r.top
hdc_win = u.GetWindowDC(HWND)
log('hdc_win=%d' % bool(hdc_win))
hdc_mem = g.CreateCompatibleDC(hdc_win)
bmp = g.CreateCompatibleBitmap(hdc_win, w, h)
log('bmp=%d' % bool(bmp))
g.SelectObject(hdc_mem, bmp)
res = u.PrintWindow(HWND, hdc_mem, 2)
log('PrintWindow=%d' % res)

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
                ('biPlanes', wt.WORD), ('biBitCount', wt.WORD), ('biCompression', wt.DWORD),
                ('biSizeImage', wt.DWORD), ('biXPelsPerMeter', wt.LONG), ('biYPelsPerMeter', wt.LONG),
                ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]
bi = BITMAPINFOHEADER()
bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bi.biWidth = w
bi.biHeight = -h
bi.biPlanes = 1
bi.biBitCount = 32
bi.biCompression = 0
buf = ctypes.create_string_buffer(w * h * 4)
gd = g.GetDIBits(hdc_mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
log('GetDIBits=%d' % gd)
try:
    data = buf.raw
    bf_off = 54
    hdr = struct.pack('<2sIHHI', b'BM', bf_off + len(data), 0, 0, bf_off)
    open(out, 'wb').write(hdr + ctypes.string_at(ctypes.byref(bi), 40) + data)
    log('saved bytes=%d' % (bf_off + len(data)))
except Exception as e:
    log('save error: %r' % e)
g.DeleteObject(bmp)
g.DeleteDC(hdc_mem)
u.ReleaseDC(HWND, hdc_win)
open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\diag_log.txt', 'w', encoding='utf-8').write('\n'.join(lines))
