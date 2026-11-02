# 新版界面 · 功能接入清单（逐按钮）

> 用途：证明新界面里**没有"看起来能点、点了没反应"的假按钮**，并说明每个操作最终落到哪段原有代码。
> 结论先行：所有业务动作都走原有脚本/函数，命令行参数与原工具一致；算法与 Excel 口径零改动。

约定：
* `run_strip` = `core/run_strip.py`；`excel` = `excel_tools/main.py`；参数与路径见 `client/ui_v2/services/`。
* "后台"= 起独立进程（QProcess），界面不卡；"进程内"= 纯读函数，毫秒级。

## 1. 工作台（dashboard）

| 控件 | 动作 | 落到哪 |
|---|---|---|
| 6 个快捷操作卡片 | 跳到对应页面 | `MainWindow.navigate()` |
| 最近任务表（双击） | 打开该任务的成果目录 | `paths.open_path()` |
| 最近成果表（双击） | 打开文件 | `paths.open_path()` |
| 项目目录 / 参数文件 / 验收报告 | 打开文件或目录 | `paths.*`；报告不存在时跳到验收页 |
| 品位分级图例 | 只读展示 | `core/grades.py`（读 `grade_profiles.json`） |

## 2. 单炮区二次圈矿（single_mining）

| 控件 | 动作 | 落到哪 |
|---|---|---|
| 数据库「浏览」/ 拖入 | 选文件 + 自动识别 | `files.parse_platform_date()`、`files.find_composite()`、自动取用同目录 `.3ds` |
| 综合图「浏览」/ 拖入 | 选综合图 | 同上（必填校验） |
| 平台 / 日期输入 | 手动改，联动参数层 | `config.params_for(platform, date)` |
| 矿段下拉 | 自动 / 金斗山 / 中心矿段 | 自动 = `grades.use_for()` 同规则；显式 = 传 `--grades <key>` |
| 输出目录 | 选择/拖入文件夹 | 默认 `<数据库目录>\二次圈矿成果_<平台>_<日期>` |
| 模式卡片 ①②③ | 切换模式 + 显示/隐藏 `.3ds` 行 | ①无参数；②`--manual-blocks`；③`--outline` |
| 轮廓「添加 .3ds」 | 多选文件，分号拼接 | 同上 |
| 刷新 | 重读三层参数 + 来源标注 | `core/params.py: for_blast/for_platform/load` |
| 存为平台默认 / 存为当前炮区 | 写 `圈矿参数.json` | `core/params.py: save`（只 update 对应层） |
| 转 DWG 2010（勾选） | 第 2 步 | 后台 `core/dxf2dwg.py <dxf> --start` |
| 并入综合图副本（勾选） | 第 3 步 | 后台 `core/merge_to_composite.py <dwg> <3ds> --start` |
| **一键出三件套** | 串行跑 1→2→3 步 | 后台 `core/run_strip.py <xls> <平台> <日期> <输出> <综合图> [--grades] [--manual-blocks/--outline]` |
| 取消 | 终止当前子进程 | `QProcess.kill()` |
| 成果文件行的小箭头 | 打开文件 | `paths.open_path()` |
| 另存日志 | 存 `圈矿日志.txt` | 本地文件写入 |

## 3. 批量处理（batch_mining）

| 控件 | 动作 | 落到哪 |
|---|---|---|
| 父目录 / 综合图 | 选择 | `files.scan_day_folders()` 用 |
| 扫描炮区 | 列出子目录里的 `1、*.xls`，识别平台/日期 | `files.scan_day_folders()` |
| 全选 / 行勾选 | 队列选择 | 表内状态 |
| **开始批量圈矿** | 逐条执行，实时状态 | 后台队列 `core/run_strip.py`（每行一个进程） |
| 跑原批量流程（含汇总表） | 原样调用 | 后台 `core/run_batch.py <父目录> <综合图> <输出> [--grades]` |
| 中止队列 | 清空队列 + 终止当前 | `QProcess.kill()` |
| 重试失败项 | 失败行重新入队 | 队列 |
| 点某行 | 看该行日志 | 日志按 tid 过滤 |
| 打开父目录 | 资源管理器 | `paths.open_path()` |

## 4. 人工圈矿与参数标定（manual_calibration）

| 控件 | 动作 | 落到哪 |
|---|---|---|
| 读取人工图块 | 只读扫描块数/面积 | 线程内 `core/composite.load_composite_blocks()` |
| 跑一次自动圈矿 | 生成用于对比的成果 | 后台 `core/run_strip.py`，随后读报告 xlsx 汇总 |
| 自动标定（演练） | 只打印推荐值 | 后台 `core/calibrate.py <日期> <人工图> --platform <平台>` |
| 自动标定并写入参数 | 二次确认后写参数 | 同上 + `--write` |
| 对比表 | 人工/自动/差异 | 人工来自扫描，自动来自报告 |

## 5. 综合图管理（composite_manager）

| 控件 | 动作 | 落到哪 |
|---|---|---|
| 只读扫描历史矿块 | 块数/面积 | 线程内 `core/composite.load_composite_blocks()` |
| 打开预览图 | 看 `_预览.png` | `paths.open_path()` |
| 生成合并副本 | 只出副本 + 预览 | 后台 `core/merge_to_composite.py <综合图> <3ds> --start` |
| 确认替换综合图原件 | 二次确认 → 备份原件 → 覆盖 | 后台 `core/apply_merge.py <副本dwg>` |
| 另存日志 | 写 `综合图操作日志.txt` | 本地文件 |

## 6. Excel 数据工具（excel_tools）

| 控件 | 动作 | 落到哪 |
|---|---|---|
| 添加文件 / 添加目录 / 移除 / 上移 / 下移 | 列表维护（顺序影响同档体号） | 界面状态 |
| 汇总方式 | total / detail | `--mode` |
| 品位分级 | auto / 金斗山 / 中心矿段 | `--grades` |
| 输出 xlsx / 报告标题 | 路径与标题 | `-o` / `-t` |
| 追加原始报告 / 写公式 勾选 | 附录与公式 | `--no-appendix` / `--values` |
| **开始汇总** | 后台汇总 | `excel_tools/main.py -i <files…> …` |
| 单日：预演（不写盘） | 计划核对 | `--daily --day-dir … --dry-run` |
| 单日：正式并入 | 二次确认后写入 | `--daily --day-dir … [--master-dir] [--allow-duplicates|--no-backup|--no-map]` |
| 单日：还原备份 | 二次确认后还原 | `--daily --restore --master-dir …` |

## 7. 炮孔数据库生成（database_builder）

| 控件 | 动作 | 落到哪 |
|---|---|---|
| 坐标 TXT | 选择 + 自动识别平台/日期 | `core/make_database.parse_tag_from_txt()` |
| 品位表粘贴框 | 多格式粘贴 | `parse_grades()`（预览时调用） |
| 解析预览 | 表格 + 缺/多/冲突提示 | 进程内 `parse_txt/parse_grades`（纯函数） |
| 生成 .xls / .mdb | 后台生成（已存在则先备份） | `core/make_database.py <txt> --grades-file … --platform … --date … [--force]` |

## 8. 参数管理（parameter_manager）

| 控件 | 动作 | 落到哪 |
|---|---|---|
| 参数层级树 | 点一层看原始 JSON | `core/params.py: load()` |
| 覆盖关系表 | 全局/平台/炮区/生效值/来源 | `config.param_sources()`（读同一份 JSON 判断） |
| 刷新 / 打开 JSON | 重读 / 打开文件 | `paths.params_json()` |
| 参数台账 | 后台输出台账 | `_probe/params_report.py` |

## 9. 验收与诊断（diagnostics）

| 控件 | 动作 | 落到哪 |
|---|---|---|
| 一键全量验收 / 快速验收 | 后台跑验收，逐项解析状态 | `_probe/accept_all.py [--quick] --no-open` |
| 打开验收报告 | 打开 `验收报告.md` | `paths.open_path()` |
| 打开 _probe 目录 | 资源管理器 | `paths.open_path()` |
| 另存日志 | 写 `验收日志.txt` | 本地文件 |

## 10. 系统设置（settings）

| 控件 | 动作 | 落到哪 |
|---|---|---|
| 打开旧版界面 | 起旧 Tkinter 界面 | `client/gui.py`（子进程） |
| 打开数据目录 / 配置文件 | 资源管理器 / 默认程序 | `paths.*` |
| 重建默认配置（先备份） | 用包内默认覆盖 `圈矿参数.json` | 先写 `圈矿参数.bak.json` 再覆盖 |
| 清空最近记录 | 清 `.ui_state.json` 的 tasks/outputs | 不动任何成果文件 |

---

## 与原有逻辑的一致性

| 关注点 | 是否改动 |
|---|---|
| 圈矿算法（Voronoi/矿界/分块/算量） | **未改动**（`core/*.py` 仅新增 `SM_HOME` 路径支持） |
| Excel 报告口径（total/detail、公式写法） | **未改动** |
| 单日并入判重/备份/矿块图同步 | **未改动** |
| 成果文件命名与格式（xlsx/xls/png/dxf/dwg/3ds） | **未改动** |
| 参数三层优先级 | **未改动**（界面只做读取与按层保存） |
| 品位分级来源 | 仍唯一来自 `excel_tools/config/grade_profiles.json` |
| 综合图安全 | 只读扫描、只出副本、替换前备份 + 二次确认 |
