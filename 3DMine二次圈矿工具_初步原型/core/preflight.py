# -*- coding: utf-8 -*-
"""首次运行/换机器时的环境自检（双击 首次运行检查.bat 等价）。

检查：Python 版本 → 依赖包 → 数据目录 → 参数文件 → 输出目录可写 → AutoCAD（可选）→ 综合图。
退出码 0 = 可以直接开始出图；1 = 有必须解决的项（逐条给出怎么修）。
"""
from __future__ import annotations
import importlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAY = ROOT.parent

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ok_list, bad_list, warn_list = [], [], []


def ok(msg):
    ok_list.append(msg)
    print("  [OK]   %s" % msg)


def bad(msg, fix):
    bad_list.append((msg, fix))
    print("  [FAIL] %s\n          → %s" % (msg, fix))


def warn(msg, hint=""):
    warn_list.append(msg)
    print("  [警告] %s%s" % (msg, ("\n          → " + hint) if hint else ""))


print("=" * 74)
print("二次圈矿工具 · 环境自检")
print("=" * 74)

# 1) Python
v = sys.version_info
print("\n1) Python")
if v >= (3, 10):
    ok("Python %d.%d.%d（%s）" % (v.major, v.minor, v.micro, sys.executable))
else:
    bad("Python %d.%d（低于 3.10）" % (v.major, v.minor), "装 Python 3.10+，或用程序自带的启动脚本")

# 2) 依赖
print("\n2) 依赖包")
need = [("numpy", 1), ("scipy", 1), ("shapely", 1), ("matplotlib", 1),
        ("ezdxf", 1), ("openpyxl", 1), ("xlrd", 1)]
opt = [("win32com.client", "AutoCAD 只读扫描 / DXF→DWG2010（没有也能出 DXF）"),
       ("pyodbc", "直读 .mdb 数据库（正常流程用导出的 Excel，不需要）")]
for name, must in need:
    try:
        importlib.import_module(name)
        ok("import %s" % name)
    except Exception as exc:
        bad("缺少 %s（%s）" % (name, exc), "pip install %s" % name)
for name, why in opt:
    try:
        importlib.import_module(name)
        ok("import %s（可选，%s）" % (name, why))
    except Exception:
        warn("缺少可选包 %s —— %s" % (name, why))

# 3) 数据目录
print("\n3) 数据目录（%s）" % DAY)
for plat in ("3940", "3960"):
    d = DAY / ("北部山头%s平台2026" % plat)
    if (d / "7、单日数据").exists():
        days = [x for x in (d / "7、单日数据").iterdir() if x.is_dir()]
        comp = sorted(d.glob("*综合*.dwg"))
        ok("%s：单日数据 %d 个目录，综合图 %s" %
           (d.name, len(days), comp[0].name if comp else "**没找到**"))
        if not comp:
            warn("%s 下没找到综合图 DWG" % d.name,
                 "自动圈矿照样能跑；只是「贴历史块」那步会跳过")
    else:
        warn("%s 不存在（不影响别的平台）" % d.name)

# 4) 参数文件
print("\n4) 参数文件")
pf = ROOT / "圈矿参数.json"
if pf.exists():
    try:
        cfg = json.loads(pf.read_text(encoding="utf-8"))
        ok("圈矿参数.json 可读（平台 %d 个、炮区覆盖 %d 个）" %
           (len(cfg.get("platforms", {})), len(cfg.get("blasts", {}))))
    except Exception as exc:
        bad("圈矿参数.json 读不动：%s" % exc, "用 git 恢复一份：git checkout -- 圈矿参数.json")
else:
    bad("找不到 圈矿参数.json", "它应该在：%s" % pf)

# 5) 输出目录可写
print("\n5) 输出目录")
out = ROOT / "sample_data" / "output"
try:
    out.mkdir(parents=True, exist_ok=True)
    t = out / "_自检写测试.tmp"
    t.write_text("ok", encoding="utf-8")
    t.unlink()
    ok("可写：%s" % out)
except Exception as exc:
    bad("输出目录不可写（%s）" % exc, "换一个可写的位置，或给该目录权限")

# 6) AutoCAD（可选，但影响两件事）
print("\n6) AutoCAD（可选）")
running = False
try:
    import subprocess
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acad.exe"], capture_output=True, text=True)
    running = "acad.exe" in (r.stdout or "").lower()
except Exception:
    pass
if running:
    ok("AutoCAD 正在运行（只读扫描综合图 / 转 DWG2010 都能用）")
else:
    warn("AutoCAD 没在运行",
         "不影响出 DXF 与报告；只是：① 综合图历史块读不到（跳过贴块）② 不能自动转 DWG2010。"
         "要用这两项就先打开 AutoCAD 并让它空闲着")

print("\n" + "=" * 74)
if bad_list:
    print("结论：有 %d 项必须解决（见上面 FAIL 的 →）：" % len(bad_list))
    for msg, fix in bad_list:
        print("  · %s → %s" % (msg, fix))
    print("=" * 74)
    sys.exit(1)
print("结论：可以直接用 ✓" +
      ("（有 %d 条提示，见上面「警告」）" % len(warn_list) if warn_list else ""))
print("下一步：双击 启动二次圈矿工具.bat 出图；双击 跑验收.bat 自查。")
print("=" * 74)
sys.exit(0)
