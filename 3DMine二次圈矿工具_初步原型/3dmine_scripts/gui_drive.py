import ctypes, ctypes.wintypes as wt, struct, time, sys

u = ctypes.windll.user32
g = ctypes.windll.gdi32

HWND = 0x81762

def fg():
    u.SetForegroundWindow(HWND)
    time.sleep(0.4)

def key(vk, down=True):
    u.keybd_event(vk, 0, 2 if down else 0, 0)
    time.sleep(0.05)

def alt_key(vk):
    key(0x12)          # ALT down
    time.sleep(0.1)
    key(vk)            # letter down
    time.sleep(0.05)
    key(vk, False)     # letter up
    time.sleep(0.05)
    key(0x12, False)   # ALT up
    time.sleep(0.5)

def capture(out):
    r = wt.RECT()
    u.GetWindowRect(HWND, ctypes.byref(r))
    w = r.right - r.left
    h = r.bottom - r.top
    hdc_win = u.GetWindowDC(HWND)
    hdc_mem = g.CreateCompatibleDC(hdc_win)
    bmp = g.CreateCompatibleBitmap(hdc_win, w, h)
    g.SelectObject(hdc_mem, bmp)
    res = u.PrintWindow(HWND, hdc_mem, 2)

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
    bf_off = 14 + 40
    file_size = bf_off + len(buf)
    hdr = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, bf_off)
    open(out, 'wb').write(hdr + ctypes.string_at(ctypes.byref(bi), 40) + buf.raw)
    g.DeleteObject(bmp)
    g.DeleteDC(hdc_mem)
    u.ReleaseDC(HWND, hdc_win)
    return res

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'shot'
    out = sys.argv[2] if len(sys.argv) > 2 else r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\shot.bmp'
    fg()
    if action == 'alt_o':
        alt_key(ord('O'))
    elif action == 'alt_d':
        alt_key(ord('D'))
    elif action == 'alt_m':
        alt_key(ord('M'))
    elif action == 'alt_f':
        alt_key(ord('F'))
    elif action == 'alt_v':
        alt_key(ord('V'))
    elif action == 'esc':
        key(0x1B)
        time.sleep(0.4)
    elif action == 'enter':
        key(0x0D)
        time.sleep(0.4)
    elif action == 'down':
        key(0x28)
        time.sleep(0.3)
    elif action == 'click':
        x = int(sys.argv[2]); y = int(sys.argv[3])
        out = sys.argv[4] if len(sys.argv) > 4 else r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\shot_click.bmp'
        sx = int(x * 65535 / 1536)
        sy = int(y * 65535 / 864)
        u.mouse_event(0x8001, sx, sy, 0, 0)  # ABSOLUTE | MOVE
        time.sleep(0.3)
        u.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.08)
        u.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(0.5)
    elif action == 'rclick':
        x = int(sys.argv[2]); y = int(sys.argv[3])
        out = sys.argv[4] if len(sys.argv) > 4 else r'D:\WK\N CRT\3DMine二次圈矿工具_初步原型\3dmine_scripts\shot_rclick.bmp'
        sx = int(x * 65535 / 1536)
        sy = int(y * 65535 / 864)
        u.mouse_event(0x8001, sx, sy, 0, 0)
        time.sleep(0.3)
        u.mouse_event(0x0008, 0, 0, 0, 0)
        time.sleep(0.08)
        u.mouse_event(0x0010, 0, 0, 0, 0)
        time.sleep(0.5)
    capture(out)
    print('ok', action, out)
