# client/ui_v2 —— 二次圈矿智能工作台（PySide6 新版界面）

旧界面（`client/gui.py`，Tkinter）**原样保留**，随时可回退；本目录是独立的新界面，
只调用原有脚本与业务函数，**不复制、不修改**圈矿算法与 Excel 口径。

## 目录结构

```
ui_v2/
├── app.py               入口：开界面；单文件 exe 里还负责 --run-script 派发
├── main_window.py       主窗口：无边框沉浸式外壳 + 侧栏导航(10 页) + QStackedWidget
│                        Win32 原生 hit-test（拖动/双击最大化/Win11 贴靠/边缘缩放/工作区最大化）
├── theme.py             设计令牌 + 全局 QSS（深蓝外框 + 浅色工作面；品位颜色不在这里定义）
├── icons.py             内联 SVG 线性图标（24×24 / 1.75 描边 / 多档 DPR 位图，无外部资源）
├── components/
│   ├── shell.py         标题栏 TitleBar / 窗口按钮 WindowButton / 导航 NavItem / 侧栏 Sidebar
│   ├── drop_overlay.py  全局拖放提示层（拖入态 / 解析中 / 结果小卡片）
│   └── widgets.py       卡片 Card / 表格卡 TableCard / 快捷卡 QuickCard / 空状态 EmptyState /
│                        统计块 StatTile / 徽章 Badge / 自绘 Combo 与 CheckRow /
│                        日志台 LogView / 文件行 FileRow / 参数格 ParamGrid / 提示条 Banner
├── services/
│   ├── paths.py         路径与运行环境（源码 / 单文件 exe 双模式；SM_HOME 可写根）
│   ├── runner.py        后台任务（QProcess）：实时日志、状态、取消、防重复
│   ├── config.py        品位分级(profiles)/圈矿参数(三层+来源)/最近记录(StateStore)
│   ├── files.py         平台日期识别、综合图匹配、.3ds 行数、批量目录扫描
│   ├── txt_import.py    坐标 TXT 解析引擎（编码/分隔符/表头/元数据/异常统计/规范化副本）
│   ├── drop_manager.py  全局 TXT 拖放（应用级事件过滤 + 后台线程解析 + 去重排队 + 取消）
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

## 全局 TXT 拖放导入（v1.17）

* 坐标 TXT 拖到**任意页面**即可：主窗口 `acceptDrops` 注册 OLE 放置目标，
  `GlobalFileDropManager` 作为 `QApplication` 事件过滤器接住 `DragEnter/Drop`；
* 只拦截单个 `.txt/.dat`，其它类型放行给页面原有的 `FileRow`；
* 解析在 `QThreadPool` 里跑，`Esc` 可取消；解析成功写入 `AppContext.txt_import` 并跳到
  「炮孔数据库生成」页自动填参数、列炮孔、给出门禁；
* 解析规则：编码 UTF-8(BOM)/GBK，分隔符 制表符/逗号/分号/空格，带表头或不带表头，
  元数据优先级「文件内标注/炮孔编号 → 文件名 → 保留页面值」，绝不从 Z 推断平台、绝不填当天日期；
* 核心脚本只认「UTF-8 + 逗号 + 5 列」，不兼容的文件会生成规范化副本到 `%TEMP%\sm_txt_import`，
  原文件不动。详见 `docs/功能说明_TXT拖放导入_v1.17.md`。

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

## 视觉规范（v1.16）

完整规范见 `docs/UI设计规范_v1.16.md`，令牌全部在 `theme.py`。

| 项 | 取值 |
|---|---|
| 外框（标题栏/侧栏） | `#0E1B2A`（hover `#16283C`，选中 `#1B3350`，分隔线 `#1E3349`） |
| 工作面 / 卡片 | `#F1F4F8` / `#FFFFFF`（边框 `#E3E9F0`） |
| 主按钮 / 强调 | `#2A6F97` / `#B0774A`（铜褐仅用于品位类强调） |
| 正文 / 次级 / 说明 | `#1B2735` / `#455667` / `#6F7F90` |
| 成功 / 警告 / 错误 | `#1F8A5F` / `#C08319` / `#C0453C` |
| 尺寸 | 标题栏 56px、侧栏 236px、导航项 38px、控件 34px、表格行 34px、间距 14px |
| 圆角 | 卡片 10px、控件 6px、胶囊 999px；只用 1px 边框，不用阴影 |
| 字号 | 数值 24、页标题 18、区块 15、卡片标题 14、正文 13、说明 12、徽章 11 |
| 图标 | 24×24 viewBox 线性 SVG，1.75 描边；导航 20px、按钮 16px、功能卡 22px |
| 品位颜色 | 取自 `grade_profiles.json` 经 `core/grades.py` 给的色号，与成果图一致 |

### 图标渲染的历史坑（v1.16 已修）

旧 `icons._render()` 先 `setDevicePixelRatio(dpr)` 再按 `size*dpr` 绘制，等于把图放大 `dpr` 倍后
塞进同一张画布，只画进左上角 1/dpr² 区域 —— 表现就是「图标只剩左上角一小段」。现在改为
**先按设备像素铺满绘制，再设 DPR**，并为 1/1.25/1.5/1.75/2/2.5/3 六档各缓存一张位图供 QIcon 精确匹配。
