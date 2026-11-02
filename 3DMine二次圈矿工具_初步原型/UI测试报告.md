# 新版界面（v1.15 · PySide6）测试报告

- 测试时间：2026-11-02
- 被测对象：`client/ui_v2/`（新界面）+ `dist/二次圈矿智能工作台.exe`（单文件）
- 环境：Windows 11 / Python 3.13.13 / PySide6 6.10.x / 显卡 DPI 100%
- 结论：**全部通过**。核心圈矿链路（单炮区、批量）用真实生产数据跑通，
  原生验收脚本 `_probe/accept_all.py` 全量通过（算法零改动）。

---

## 1. 新界面自检 `_probe/test_ui_v2.py --with-batch`

```
共 23 项检查，23 项通过     结论：全部通过 ✓
```

| 组 | 检查项 | 结果 |
|---|---|---|
| 页面 | 10 个页面全部能建、能切（dashboard / single / batch / manual / composite / excel / database / params / diagnostics / settings） | 10/10 |
| 单炮区 | 任务在后台 QProcess 启动（不阻塞 UI） | ✓ |
| 单炮区 | 真实数据 3940-1008 跑完 → 报告 xlsx / 矿块边界线 .3ds / 成果图 DXF 三件套齐全 | 3/3 |
| 单炮区 | 日志有输出（507 字符）；报告档位列正常（`1.000-1.500` / `0.500-1.000`） | 2/2 |
| 批量 | 临时父目录扫描到 1 个炮区，平台/日期识别 3940 / 1008 | 2/2 |
| 批量 | 队列启动 → 状态「完成」→ 成果目录里有报告 xlsx 与 .3ds，单任务日志 1134 字符 | 4/4 |

跑法：

```bat
set QT_QPA_PLATFORM=offscreen
python _probe\test_ui_v2.py --with-batch
```

> 单炮区与批量都真实调用 `core/run_strip.py`，输出到临时目录，**不写生产数据目录**。

## 2. 原生验收（算法未被 UI 影响）

`python _probe/accept_all.py --no-open`，2026-11-02 18:11:32：

| 项 | 结果 |
|---|---|
| ① 圈矿验收闸门（selftest.py，常规档 + 严格档） | 通过 |
| ② 报告口径回归（report_check_all.py） | 通过 |
| ③ 成果图实体自检（3940 五个炮区 + 3960 十二个炮区，共 17 个） | 通过 |
| ④ 精确模式自检 | 通过 |
| ⑤ Excel 工具自检（6 项） | 通过 |
| ⑥ 数据库生成（TXT + 品位表） | 通过 |
| ⑦ 自动矿块形状（连通 / 抽稀） | 通过 |
| ⑧ 综合图参考（直接相接） | 通过 |
| ⑨ 品位分级按矿段 | 通过 |

结论行：`结论：**全部通过 ✓**`

## 3. Excel 工具（新界面「Excel 数据工具」页背后的同一套业务函数）

| 自检 | 结果 |
|---|---|
| `tests/test_by_total.py`（total 口径对齐 1011 人工成果） | 14 / 14 |
| `tests/test_grade_profiles.py`（金斗山 / 中心矿段分级） | 48 / 48 |
| `tests/test_formats.py`（xls / xlsx 自适应） | 25 / 25 |
| `tests/test_locks.py`（文件占用检测） | 13 / 13 |
| `tests/test_merge.py`（detail 口径，需本机 `D:\WK\N CRT\handle`） | 跳过（本机无该批历史数据） |
| `tests/test_daily_merge.py`（单日并入，需本机生产总表） | 跳过（同上） |

命令行实测（中心矿段 3570-1023 报告）：

```
[标题] 中心矿段3570平台1023炮孔数据报告
[分级] 中心矿段（3550~3640 平台） —— 0.500-0.800 / 0.800-1.000 / 1.000-999.000（按路径识别）
[汇总] 矿块 1 个，品位档 0.800-1.000
[合计] 体积 3816.566 m³ | 重量 10304.728 t | 平均品位 0.8177 g/t | 金属量 84.257 百克
```

## 4. 炮孔数据库生成

```
core/make_database.py 坐标.txt --grades-file 品位.txt --out-dir 输出目录
完成：2 孔
  XLS: 1、3570平台 炮孔数据库0101.xls
  MDB: 2、3570平台炮孔数据库0101.mdb
  台阶高度 10.00 m；品位保留 2 位小数
```

字段、模板、取整口径与原工具一致（走的是同一个 `core/make_database.py`）。

## 5. 界面与交互

| 项 | 结果 |
|---|---|
| 1440×900 默认尺寸 / 1280×720 最小尺寸 | 通过（1280 下无控件被裁切，页面可滚动） |
| 高 DPI（125% / 150%） | 由 Qt 缩放策略 + 内联 SVG 图标保证，未出现模糊位图；截图按系统缩放抓取核对 |
| 文件拖拽（炮孔数据库 / 综合图 / 坐标 TXT） | 通过（`TkinterDnD` 不再需要；Qt 原生 drop） |
| 平台 / 日期自动识别 | 通过（`3570取样1023.txt` → 平台 3570、日期 1023，读第一条工程号） |
| 参数读取优先级（全局默认 → 平台 → 炮区） | 通过，界面按层显示；保存走原 `core/params.py` |
| 三种圈矿模式（自动 / 人工 / 精确） | 通过，按钮参数与原 GUI 完全一致 |
| DWG 2010 转换 / 并入综合图副本 | 通过（勾选项 → 原 `dxf2dwg` / `merge_to_composite` 子命令） |
| 后台任务（不卡界面、日志实时、防重复启动、关闭时提示） | 通过 |
| 单文件 exe 启动 | 通过（首次启动在 exe 旁建 `data\`，配置与成果都落在这里） |

## 6. 已知限制 / 未覆盖

1. `client/prep_generic.py`、`make_dwg_generic.py` 与根目录旧 `main.py`（旧 PoC）**不在新界面链路上**，
   新界面只走 `core/` 下现行脚本。
2. 「人工圈矿与参数标定」的左右图形对比目前调用已有 DXF/PNG 预览，**没有做交互式缩放漫游**；
   统计对比表已接入真实数据。
3. `test_merge.py` / `test_daily_merge.py` 需要本机生产数据（`D:\WK\N CRT\...`），
   在没有该目录的机器上自动跳过并返回 0，不算失败。
4. 单文件 exe 约 111 MB（PySide6 + scipy + matplotlib），首次启动解包约 3~5 秒；
   要更快可用 `打包exe.bat --onedir` 出目录版（启动约 1 秒）。

---

## 附：复现命令

```bat
rem 新界面自检（无窗口）
set QT_QPA_PLATFORM=offscreen
python _probe\test_ui_v2.py --with-batch

rem 原生全量验收
python _probe\accept_all.py --no-open

rem Excel 工具六套自检
cd excel_tools
python tests\test_by_total.py
python tests\test_grade_profiles.py
python tests\test_formats.py
python tests\test_locks.py
```
