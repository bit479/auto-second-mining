# -*- coding: utf-8 -*-
import olefile

p = r"E:\gzRJ\3Dmine\2022\demo\专题示例\10_二次开发\VBA示例\创建点.vbm"
ole = olefile.OleFileIO(p)


def vba_decompress(data, verbose=False):
    pos = 0
    out = bytearray()
    steps = 0
    while pos < len(data):
        flag = data[pos]
        pos += 1
        for bit in range(8):
            if pos >= len(data):
                return bytes(out)
            if (flag >> bit) & 1 == 0:
                out.append(data[pos])
                pos += 1
            else:
                b1 = data[pos]
                if (b1 & 0x10) == 0:
                    if pos + 1 >= len(data):
                        return bytes(out)
                    length = b1 & 0x0F
                    offset = data[pos + 1]
                    pos += 2
                else:
                    if pos + 2 >= len(data):
                        return bytes(out)
                    length = ((b1 & 0x0F) << 4) + (data[pos + 1] >> 4) + 0x10
                    offset = ((data[pos + 1] & 0x0F) << 8) + data[pos + 2]
                    pos += 3
                if offset == 0 or length == 0:
                    return bytes(out)
                start = len(out) - offset
                if start < 0:
                    return bytes(out)
                for _ in range(length):
                    out.append(out[start])
                    start += 1
            steps += 1
            if steps > 100000:
                return bytes(out)
    return bytes(out)


streams = {
    "ThisDrawing": "apc/The VBA Project/_VBA_Project/VBA/ThisDrawing",
    "SRP_0": "apc/The VBA Project/_VBA_Project/VBA/__SRP_0",
    "SRP_1": "apc/The VBA Project/_VBA_Project/VBA/__SRP_1",
    "SRP_2": "apc/The VBA Project/_VBA_Project/VBA/__SRP_2",
    "SRP_3": "apc/The VBA Project/_VBA_Project/VBA/__SRP_3",
}
out = []
for name, path in streams.items():
    data = ole.openstream(path).read()
    out.append("=== %s size=%d head=%s" % (name, len(data), data[:12].hex(" ")))
    for off in [0, 3, 6]:
        if data[off:off+3] == b"\x01\x00\x00":
            dec = vba_decompress(data[off:])
            txt = dec.decode("latin-1", "replace")
            out.append("  off=%d -> %d bytes" % (off, len(dec)))
            out.append("  " + txt[:200].replace("\r", "\\r").replace("\n", "\\n"))
ole.close()
open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\vba_debug2.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
