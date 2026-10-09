import ctypes, ctypes.wintypes as wt, struct

u = ctypes.windll.user32
g = ctypes.windll.gdi32

w, h = 1536, 864
hdc_screen = u.GetDC(None)
hdc_mem = g.CreateCompatibleDC(hdc_screen)
bmp = g.CreateCompatibleBitmap(hdc_screen, w, h)
g.SelectObject(hdc_mem, bmp)
ok = g.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)  # SRCCOPY

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
g.GetDIBits(hdc_mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
bf_off = 54
hdr = struct.pack('<2sIHHI', b'BM', bf_off + len(buf), 0, 0, bf_off)
out = r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\screen.bmp'
open(out, 'wb').write(hdr + ctypes.string_at(ctypes.byref(bi), 40) + buf.raw)
g.DeleteObject(bmp)
g.DeleteDC(hdc_mem)
u.ReleaseDC(None, hdc_screen)
open(r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\screen_log.txt', 'w', encoding='utf-8').write('bitblt ok=%s bytes=%d' % (ok, bf_off + len(buf)))
