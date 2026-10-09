# -*- coding: utf-8 -*-
"""VBA 模块流提取：搜索压缩源码头 0x01 0x00 0x00 后解压。"""
import olefile


def vba_decompress(data):
    pos = 0
    out = bytearray()
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
    return bytes(out)


def find_header(data):
    """返回第一个 0x01 0x00 0x00 出现位置（在该位置前可能有模块名等元数据）。"""
    for i in range(len(data) - 2):
        if data[i] == 1 and data[i + 1] == 0 and data[i + 2] == 0:
            return i
    return -1


def extract_vbm(path):
    res = []
    if not olefile.isOleFile(path):
        return res
    ole = olefile.OleFileIO(path)
    try:
        for entry in ole.listdir():
            j = "/".join(entry)
            if "/VBA/" not in j:
                continue
            if entry[-1] in ("dir", "_VBA_PROJECT", "PROJECT", "PROJECTwm", "__SRP_0", "__SRP_1", "__SRP_2", "__SRP_3"):
                continue
            data = ole.openstream(entry).read()
            hdr = find_header(data)
            if hdr >= 0:
                dec = vba_decompress(data[hdr:])
                res.append((j, dec))
    finally:
        ole.close()
    return res


if __name__ == "__main__":
    import os, sys
    d = r"E:\gzRJ\3Dmine\2022\demo\专题示例\10_二次开发\VBA示例"
    names = sys.argv[1:] if len(sys.argv) > 1 else ["创建点.vbm", "创建面.vbm", "创建多段线.vbm", "创建单行文字.vbm", "创建多行文字.vbm", "数据库测试_遍历所有孔_打印孔号.vbm", "填充.vbm", "图层操作.vbm"]
    out = []
    for f in names:
        p = os.path.join(d, f)
        out.append("########## %s ##########" % f)
        got = extract_vbm(p)
        if not got:
            out.append("(no module source found)")
        for stream, code in got:
            out.append("--- stream %s (%d bytes) ---" % (stream, len(code)))
            try:
                txt = code.decode("utf-8")
            except Exception:
                try:
                    txt = code.decode("gbk")
                except Exception:
                    txt = repr(code)
            out.append(txt[:8000])
        out.append("")
    open(r"D:\WK\N CRT\3DMine二次圈矿工具_初步原型\output\1004_macro\vba_source.txt", "w", encoding="utf-8").write("\n".join(out))
    print("ok")
