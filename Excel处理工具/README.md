# 炮孔数据工具

两组能力，共用一个界面：

| 功能 | 干什么 | 入口 |
|---|---|---|
| **炮孔数据报告汇总** | 把若干份 3DMine 导出的炮孔数据库报告（`工作簿1.xlsx`…）汇总成一份炮孔数据报告 | 标签页① / CLI 默认模式 |
| **单日数据并入总表** | 把某一天的 `xls / mdb / 报告` 三份文件并入 2026 年三份总表 | 标签页② / CLI `--daily` |

两组功能都已用北部山头 3940 平台 1008 真实数据验证：输出与人工成果**逐行、逐值一致**。

---

## 一、快速开始

### 1. 图形界面（推荐）

双击 **`启动汇总工具.bat`**（打开"报告汇总"页）或 **`启动单日并入.bat`**（打开"单日并入"页），或：

```bash
python main.py --gui              # 报告汇总页
python main.py --gui --tab daily  # 单日并入页
```

### 2. 报告汇总（命令行）

```bash
# 按目录批量收集
python main.py -d "D:\WK\N CRT\handle" -p "工作簿*.xlsx" ^
               -o "D:\WK\N CRT\handle\3940平台 1008炮孔数据报告.xlsx"

# 或逐个指定文件
python main.py -i "D:\WK\N CRT\handle\工作簿1.xlsx" "D:\WK\N CRT\handle\工作簿2.xlsx" ^
               -o "D:\WK\N CRT\handle\3940平台 1008炮孔数据报告.xlsx"
```

### 3. 单日数据并入总表（命令行）

```bash
# 只给一个单日目录，六个文件全自动识别
python main.py --daily --day-dir "D:\WK\N CRT\北部山头3940平台2026\7、单日数据\北部山头3940平台-1008"

# 先预演，不写盘
python main.py --daily --day-dir "…\北部山头3940平台-1008" --dry-run

# 一并支持 3960 平台，同一套命令
python main.py --daily --day-dir "D:\WK\N CRT\北部山头3960平台2026\7、单日数据\北部山头3960平台-1008"

# 回滚：从 *_并入<日>.bak 还原三份总表
python main.py --daily --restore --master-dir "D:\WK\N CRT\北部山头3940平台2026" --day 1008
```

### 4. 依赖

```bash
pip install -r requirements.txt
# openpyxl（必需）；xlrd / xlwt / xlutils / pyodbc（单日并入需要）
```

双击 `.bat` 时会自动检查并安装，无需手动操作。

> **注意**：`.bat` 文件内容保持纯 ASCII（英文），中文提示由 Python 输出。
> cmd.exe 按 GBK 解析 `.bat`，一旦文件里写中文 UTF-8，就会被拆成乱码指令。
>
> **`pyodbc` 需要**本机已装 `Microsoft Access Driver (*.mdb, *.accdb)`（Windows 自带，随 Office / Access Database Engine 提供）。

---

## 二、单日数据并入总表 —— 怎么并

一次调用处理三对文件（自动探测或显式指定）：

| 单日文件 | 总表 | 做法 |
|---|---|---|
| `1、…炮孔数据库1008.xls` | `1、北部山头…炮孔数据库-2026.xls` | `定位表 / 测斜表 / pit_blast` 三张表逐行追加 |
| `2、…炮孔数据库1008.mdb` | `2、北部山头…炮孔数据库-2026.mdb` | 同上，Access SQL 插入；3DMine 元数据表不碰 |
| `3940平台 1008炮孔数据报告.xlsx` | `3、北部山头…炮孔数据报告-2026综合.xlsx` | 整体粘贴"标题→合计"汇总块 |

### 探测规则

单日目录按前缀找：`1、*.xls` / `2、*.mdb` / `*炮孔数据报告*.xlsx`；
总表目录按前缀找：`1、*.xls` / `2、*.mdb` / `3、*.xlsx`。
总表目录不给就**从单日目录向上回溯**自动定位；日期代号（`1008`）从目录名或工程号推断。

### 并入细则

* **判重**：按工程号判重（`pit_blast` 按 `(工程号, 从)`，因为 Access 上有唯一索引），
  总表已有的孔直接跳过，所以**反复运行是安全的**。
* **xls 保真**：先把总表原始 BIFF 结构整体复制成可写簿，字体、数字格式、列宽、
  其余工作表全部原样保留；新增行沿用"该列最后一个数据单元格"的样式。
* **报告公式平移**：块内公式按行偏移整体平移（`=C3+C4` → `=C25+C26`），
  字体、边框、对齐、数字格式、合并单元格一并带走。只搬**汇总块**，
  单日报告下方的"3DMine 炮孔数据库报告"附录不进总表（与历史成果一致）。
* **自动备份**：确有改动才写盘，写前把总表备份成 `<原名>_并入<日>.bak`（不覆盖旧备份）。
* **合计自检**：用文件里缓存的计算值复核"合计 = 各明细行之和"；
  发现源报告公式漏项时**明确告警但原样并入**，绝不擅自改数。

### 命令参数

| 参数 | 作用 |
|---|---|
| `--day-dir` | 单日数据目录（必填，除非用 `--src-*`） |
| `--master-dir` | 总表目录，留空自动定位 |
| `--day` | 日期代号，留空自动识别 |
| `--src-xls / --src-mdb / --src-report` | 逐个指定单日文件（覆盖自动探测） |
| `--dst-xls / --dst-mdb / --dst-report` | 逐个指定总表文件 |
| `--allow-duplicates` | 不判重，工程号已存在也照插 |
| `--with-appendix` | 报告并入时连同附录一起搬 |
| `--no-backup` | 写入前不备份 |
| `--dry-run` | 只计算不写盘 |
| `--restore` | 从 `*_并入<日>.bak` 还原总表 |

---

## 三、报告汇总 —— 汇总规则（与人工成果一致）

1. **按品位档归组**，档位由高到低：`≥3.000` → `1.500-3.000` → `1.000-1.500` → `0.500-1.000`；
   同档内保留源文件的出现顺序，体号原样保留。
2. 每个档位先列全部**明细行**，随后一行**小计**。
3. 末尾一行**合计**，等于各小计之和。
4. 体积、重量、金属量**直接求和**。
5. **平均品位 = 金属量 × 100 ÷ 重量**（不是简单算术平均）。
6. 小计/合计默认写成 Excel **公式**（可审计、可追溯）；`--values` 改写成数值。
7. 可选在下方追加每个源文件的原始报告（`--no-appendix` 关闭）。

| 报告汇总参数 | 作用 |
|---|---|
| `-i / --inputs` | 输入文件，支持通配符，也可直接给目录 |
| `-d / --dir` | 批量收集输入文件的目录 |
| `-p / --pattern` | 目录匹配模式，默认 `*.xls*` |
| `-o / --output` | 输出 xlsx 路径 |
| `-t / --title` | 报告大标题，默认取输出文件名 |
| `--no-appendix` | 不追加各源文件原始报告 |
| `--values` | 小计/合计写死数值 |
| `--gap N` | 汇总区与附录区之间的空行数，默认 8 |

---

## 四、目录结构

程序分三层：**通用 Excel 处理能力层** → **业务层**（两组功能各一层）。

```
Excel处理工具/
├── main.py                     命令行入口（报告汇总 / --daily 单日并入）
├── gui.py                      图形界面（ttk.Notebook 两个标签页）
├── bootstrap.py                启动前自检（Python 版本 + 依赖自动安装）
├── 启动汇总工具.bat              一键启动（默认"报告汇总"页）
├── 启动单日并入.bat              一键启动（默认"单日并入"页）
├── requirements.txt
├── src/
│   ├── excel_core/             ← 基础能力层（可复用于任何 Excel 处理）
│   │   ├── model.py            统一数据表模型 DataTable；值清洗 to_number/to_text
│   │   ├── reader.py           多格式读取 xlsx/xls/csv；表头自动定位；批量收集
│   │   ├── transform.py        纵向拼接、列对齐、去重、分组聚合、加权平均
│   │   └── writer.py           样式化写出：合并标题、边框、列宽、数字格式
│   ├── blast_report/           ← 业务层①：报告汇总
│   │   ├── schema.py           字段定义、列名同义词、品位档解析与排序
│   │   ├── parser.py           解析 3DMine 报告（自动跳过标题行、小计行）
│   │   └── builder.py          归组汇总 + 生成成果表
│   └── daily_merge/            ← 业务层②：单日数据并入总表
│       ├── schema.py           表结构、判重键、文件名探测模式
│       ├── discover.py         自动探测六个文件 / 回溯总表目录 / 生成计划
│       ├── db_xls.py           炮孔数据库 .xls 追加（xlutils 保结构）
│       ├── db_mdb.py           炮孔数据库 .mdb 追加（pyodbc）
│       ├── report_xlsx.py      报告汇总块粘贴 + 公式平移 + 合计自检
│       └── pipeline.py         编排：预演 → 备份 → 三对并入 → 复核 → 还原
└── tests/
    ├── test_merge.py           自检①：与人工成果逐项比对
    └── test_daily_merge.py     自检②：单日并入（30 项检查）
```

### 基础能力层可以直接复用

```python
from src.excel_core.reader import read_table, find_input_files
from src.excel_core.transform import concat, dedupe
from src.excel_core.writer import SheetPlan, StyleSpec, write_workbook

tables = read_table(r"D:\data\某表.xlsx")     # 读：自动探测表头、剔除"小计/合计"行
merged = concat(tables)                        # 拼：列不齐也能拼，缺列补 None
write_workbook("结果.xlsx", [SheetPlan(        # 写：标题合并 + 表头 + 边框 + 列宽
    name="汇总", title="汇总表",
    columns=["类型", "体号", "体积"],
    rows=[["1.500-3.000", 1, 515.29]],
)])
```

---

## 五、自检

```bash
python tests/test_merge.py         # 报告汇总：与人工成果逐行比对
python tests/test_daily_merge.py   # 单日并入：30 项检查
```

`test_daily_merge.py` 全程在 `_out/daily_test` 的副本里操作，**不会碰真实数据**，
覆盖：自动识别 3 对文件 → 首次并入（行数、逐值比对）→ 重复执行判重 →
备份还原，共 30 项断言。

```
共 30 项检查，30 项通过
结论：全部一致 ✓
```

---

## 六、已知限制

* **`.xls` 写入有 65536 行 / 256 列上限**（BIFF8 固有），炮孔数据远未触及。
* **`.mdb` 写入需要 Access ODBC 驱动**；若 3DMine 正打开着该库，先关掉再并入。
* **`.xlsx` 报告写回由 openpyxl 重写整份文件**，图表、图片、枢轴表等复杂对象不保证保留
  （总表是纯数据表，不受影响）。并入前请确保文件没在 Excel / WPS 里打开。
* **`.xls` 与 `.mdb` 是两套独立数据**：`.mdb` 里 `最大孔深` 等字段的精度与 `.xls` 不同
  （3DMine 导出时的差异），工具按各自来源原样追加，不做交叉修正。
