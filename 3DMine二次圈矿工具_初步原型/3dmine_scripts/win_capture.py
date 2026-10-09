import ctypes, ctypes.wintypes as wt, struct
u = ctypes.windll.user32
g = ctypes.windll.gdi32

hwnd = 0x81762
r = wt.RECT()
u.GetWindowRect(hwnd, ctypes.byref(r))
w = r.right - r.left
h = r.bottom - r.top
print('win', w, h, flush=True)

hdc_win = u.GetWindowDC(hwnd)
hdc_mem = g.CreateCompatibleDC(hdc_win)
bmp = g.CreateCompatibleBitmap(hdc_win, w, h)
g.SelectObject(hdc_mem, bmp)
# PW_RENDERFULLCONTENT = 2
res = u.PrintWindow(hwnd, hdc_mem, 2)
print('PrintWindow', res, flush=True)

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

# write BMP manually (BITMAPFILEHEADER + DIB)
bf_off = ctypes.sizeof(ctypes.c_ushort) * 2 + ctypes.sizeof(ctypes.c_uint) + ctypes.sizeof(ctypes.c_ushort) * 2 + ctypes.sizeof(ctypes.c_uint)
file_size = bf_off + len(buf)
bmp_header = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, bf_off)
dib = ctypes.string_at(ctypes.byref(bi), ctypes.sizeof(BITMAPINFOHEADER))
data = bmp_header + dib + buf.raw
out = r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\win_capture.bmp'
open(out, 'wb').write(data)
print('saved', out, len(data), flush=True)
g.DeleteObject(bmp)
g.DeleteDC(hdc_mem)
u.ReleaseDC(hwnd, hdc_win)
