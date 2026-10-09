# 炮孔数据报告汇总工具

把若干份 3DMine 导出的**炮孔数据库报告**（`工作簿1.xlsx`、`工作簿2.xlsx`……）
汇总成一份**炮孔数据报告**（如 `3940平台 1008炮孔数据报告.xlsx`）。

已用北部山头 3940 平台 1008 真实数据验证：输出结果与人工成果**逐行、逐值一致**。

---

## 一、快速开始

### 1. 图形界面（推荐）

双击 **`启动汇总工具.bat`**，或：

```bash
python main.py --gui
```

添加文件（或整个目录）→ 选择输出路径 → 点"开始汇总"。

### 2. 命令行

```bash
# 按目录批量收集
python main.py -d "D:\WK\N CRT\handle" -p "工作簿*.xlsx" ^
               -o "D:\WK\N CRT\handle\3940平台 1008炮孔数据报告.xlsx"

# 或逐个指定文件
python main.py -i "D:\WK\N CRT\handle\工作簿1.xlsx" "D:\WK\N CRT\handle\工作簿2.xlsx" ^
               -o "D:\WK\N CRT\handle\3940平台 1008炮孔数据报告.xlsx"
```

参数说明：

| 参数 | 作用 |
|---|---|
| `-i / --inputs` | 输入文件，支持通配符（`工作簿*.xlsx`），也可直接给目录 |
| `-d / --dir` | 批量收集输入文件的目录 |
| `-p / --pattern` | 目录匹配模式，默认 `*.xls*` |
| `-o / --output` | 输出 xlsx 路径 |
| `-t / --title` | 报告大标题，默认取输出文件名 |
| `--no-appendix` | 不在下方追加各源文件原始报告 |
| `--values` | 小计/合计写死数值（默认写 Excel 公式） |
| `--gap N` | 汇总区与附录区之间的空行数，默认 8 |
| `--gui` | 启动图形界面 |

### 3. 依赖

```bash
pip install -r requirements.txt   # openpyxl（必需）、xlrd（读 .xls 时用）
```

双击 `启动汇总工具.bat` 时会自动检查并安装，无需手动操作。

> **注意**：`.bat` 文件内容保持纯 ASCII（英文），中文提示由 Python 输出。
> cmd.exe 按 GBK 解析 `.bat`，一旦文件里写中文 UTF-8，就会被拆成乱码指令，
> 报"'xxx' 不是内部或外部命令"。修改启动脚本时请留意这一点。

---

## 二、汇总规则（与人工成果一致）

1. **按品位档归组**，档位由高到低：`≥3.000` → `1.500-3.000` → `1.000-1.500` → `0.500-1.000`；
   同档内保留源文件的出现顺序，体号原样保留。
2. 每个档位先列全部**明细行**，随后一行**小计**。
3. 末尾一行**合计**，等于各小计之和。
4. 体积、重量、金属量**直接求和**。
5. **平均品位 = 金属量 × 100 ÷ 重量**（不是简单算术平均）。
6. 小计/合计默认写成 Excel **公式**（可审计、可追溯）；`--values` 改写成数值。
7. 可选在下方（`--no-appendix` 关闭）追加每个源文件的原始报告，版式与人工粘贴一致。

输出版式：标题合并居中加粗、表头 6 列、汇总区全表细边框、品位列 `0.00` 数字格式。

---

## 三、目录结构

程序分两层：**通用 Excel 处理能力层**（与业务无关）+ **炮孔报告业务层**。

```
Excel处理工具/
├── main.py                 命令行入口
├── gui.py                  图形界面（tkinter）
├── bootstrap.py            启动前自检（Python 版本 + 依赖自动安装）
├── 启动汇总工具.bat         一键启动（内容为纯 ASCII，避免 cmd 编码问题）
├── requirements.txt
├── src/
│   ├── excel_core/         ← 基础能力层（可复用于任何 Excel 处理）
│   │   ├── model.py        统一数据表模型 DataTable；值清洗 to_number/to_text
│   │   ├── reader.py       多格式读取 xlsx/xls/csv；表头自动定位；批量收集
│   │   ├── transform.py    纵向拼接、列对齐、去重、分组聚合、加权平均
│   │   └── writer.py       样式化写出：合并标题、边框、列宽、数字格式
│   └── blast_report/       ← 炮孔报告业务层
│       ├── schema.py       字段定义、列名同义词、品位档解析与排序
│       ├── parser.py       解析 3DMine 报告（自动跳过标题行、小计行）
│       └── builder.py      归组汇总 + 生成成果表
└── tests/test_merge.py     自检：与人工成果逐项比对
```

### 基础能力层可以直接复用

```python
from src.excel_core.reader import read_table, find_input_files
from src.excel_core.transform import concat, dedupe
from src.excel_core.writer import SheetPlan, StyleSpec, write_workbook

# 读：自动探测表头、自动剔除"小计/合计"行、数值自动转 float
tables = read_table(r"D:\data\某表.xlsx")

# 拼：列不齐也能拼，缺列补 None
merged = concat(tables)

# 写：标题合并 + 表头 + 边框 + 列宽
write_workbook("结果.xlsx", [SheetPlan(
    name="汇总", title="汇总表",
    columns=["类型", "体号", "体积"],
    rows=[["1.500-3.000", 1, 515.29]],
)])
```

---

## 四、自检

```bash
python tests/test_merge.py
```

会用 `handle` 目录下 3 个工作簿跑一遍，把体积/重量/品位/金属量与人工成果逐行比对：

```
类型             体号              体积           重量         品位        金属量   比对
1.500-3.000    1           515.29     1391.282       2.16     30.052   OK
小计                         515.29     1391.282 2.160022195356513     30.052   OK
...
合计                       2903.655     7839.867 1.046229483229754     82.023   OK

结论： 全部一致 ✓
```
