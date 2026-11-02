# client/ui_v2 —— 二次圈矿智能工作台（PySide6 新版界面）

旧界面（`client/gui.py`，Tkinter）**原样保留**，随时可回退；本目录是独立的新界面，
只调用原有脚本与业务函数，**不复制、不修改**圈矿算法与 Excel 口径。

## 目录结构

```
ui_v2/
├── app.py               入口：开界面；单文件 exe 里还负责 --run-script 派发
├── main_window.py       主窗口：侧栏导航(10 页) + 顶栏状态 + QStackedWidget
├── theme.py             配色与 QSS（浅色 + 深色侧栏；品位颜色不在这里定义）
├── icons.py             内联 SVG 线性图标（QSvgRenderer 渲染，无外部图片依赖）
├── components/widgets.py  卡片 Card / 状态徽章 Badge / 日志台 LogView / 文件行 FileRow /
│                          统计块 StatTile / 参数格 ParamGrid / 提示条 Banner / 表格工厂
├── services/
│   ├── paths.py         路径与运行环境（源码 / 单文件 exe 双模式；SM_HOME 可写根）
│   ├── runner.py        后台任务（QProcess）：实时日志、状态、取消、防重复
│   ├── config.py        品位分级(profiles)/圈矿参数(三层+来源)/最近记录(StateStore)
│   ├── files.py         平台日期识别、综合图匹配、.3ds 行数、批量目录扫描
│   └── context.py       跨页面上下文（当前数据库/平台/日期/矿段/模式）
└── pages/               10 个业务页面（见下）
```

## 页面与功能接入

| 页面 | 文件 | 调用的原有实现 |
|---|---|---|
| 工作台 | `pages/dashboard.py` | `StateStore`（最近任务/成果）、`grade_profiles.json`（图例）、快捷入口 |
| 单炮区二次圈矿 | `pages/single_mining.py` | `core/run_strip.py` → `core/dxf2dwg.py` → `core/merge_to_composite.py`；参数走 `core/params.py` |
| 批量处理 | `pages/batch_mining.py` | 队列逐条 `core/run_strip.py`；原批量 `core/run_batch.py` |
| 人工圈矿与参数标定 | `pages/manual_calibration.py` | `core/composite.load_composite_blocks`（只读）、`core/run_strip.py`、`core/calibrate.py` |
| 综合图管理 | `pages/composite_manager.py` | `core/composite.py`、`core/merge_to_composite.py`、`core/apply_merge.py` |
| Excel 数据工具 | `pages/excel_tools.py` | `excel_tools/main.py`（报告汇总 / `--daily` 并入 / `--restore`） |
| 炮孔数据库生成 | `pages/database_builder.py` | `core/make_database.parse_txt/parse_grades`（预览）、`core/make_database.py`（生成） |
| 参数管理 | `pages/parameter_manager.py` | `core/params.py`（三层解析）、`_probe/params_report.py`（台账） |
| 验收与诊断 | `pages/diagnostics.py` | `_probe/accept_all.py`（全量 / `--quick`） |
| 系统设置 | `pages/settings.py` | 环境查询、`client/gui.py`（回退入口）、配置重建 |

**没有假按钮**：每个按钮要么改界面状态（模式、勾选、选择文件），要么起一个真实子进程/线程；
逐条对应关系见项目根的 `UI功能接入清单.md`。

## 后台任务与日志

* 所有长任务（圈矿、DWG 转换、批量、标定、验收、数据库生成）都通过 `services/runner.py`
  的 `QProcess` 执行，界面线程只处理信号；
* 日志按行实时回传（保留半行，避免 QProcess 分片把一行切断），并着色（失败红/警告橙/成功绿）；
* 同一个 `key`（如 `run_strip`）在执行期间不会被重复启动；
* 关窗口时若仍有任务，会列出任务名并二次确认后才终止；
* 子进程命令行与原命令行**完全一致**，只把 "python 脚本" 换成 "exe 自派发"（见下）。

## 源码运行 vs 单文件 exe

| | 源码运行 | 单文件 exe |
|---|---|---|
| 解释器 | 系统 Python（需 PySide6） | exe 自带 |
| 子进程 | `python -X utf8 core/xxx.py …` | `exe --run-script core/xxx.py …` |
| 代码/资源 | 项目目录 | `sys._MEIPASS`（只读） |
| 可写配置 | 项目根 | **exe 同目录 `data\`**（首次运行自动铺开） |

`services/paths.py` 用 `SM_HOME` 环境变量把"可写根目录"传给子进程；
`core/params.py`、`core/grades.py`、`core/make_database.py`、
`excel_tools/src/blast_report/profiles.py` 都已支持 `SM_HOME`（未设置时行为与以前完全一致）。

## 构建

```bat
打包exe.bat                :: 单文件（默认）
打包exe.bat --onedir       :: 目录版（启动快，便于排错）
```

底层是 `_probe/build_exe.py`：先做一份干净的数据树（排除 `__pycache__`/`_out`/`归档`/`bak`），
再用 PyInstaller 收集 `core/`、`excel_tools/`、`_probe/`、`sample_data/`、`assets/`、`圈矿参数.json`。

## 视觉规范对照

| 项 | 取值 |
|---|---|
| 主背景 / 卡片 | `#F4F6F8` / `#FFFFFF` |
| 侧栏 | `#14263D`（选中 `#25456A` + 左侧 3px `#2878A5`） |
| 主按钮 / 强调 | `#2878A5` / `#B87945` |
| 正文 / 辅助 | `#263445` / `#7B8794` |
| 成功 / 警告 / 错误 | `#26966D` / `#D69A35` / `#D65353` |
| 圆角 | 卡片 10px、控件 6~8px；边框 1px `#E3E8EE`，不用阴影堆叠 |
| 字号 | 正文 13px，页标题 16px，卡片标题 14px，辅助 11~12px |
| 图标 | 24×24 viewBox 线性 SVG，1.6 描边，按主题色渲染 |
| 品位颜色 | 取自 `grade_profiles.json` 经 `core/grades.py` 给的色号（青/蓝/红/黄），与成果图一致 |
