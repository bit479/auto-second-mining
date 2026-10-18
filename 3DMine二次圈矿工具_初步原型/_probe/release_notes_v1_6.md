## 二次圈矿工具 v1.6（提速）

### DXF → DWG 2010：不再只走 AutoCAD COM，自动挑最快的

| 顺序 | 转换器 | 用时（实测同一张 1008 图） | 要不要 AutoCAD |
|---|---|---|---|
| ① | **ODA File Converter**（装了才用） | ~1 秒 | **不要** |
| ② | **accoreconsole**（AutoCAD 自带的无界面内核） | **约 2 秒** | 要，但不开界面、不走 COM、独立进程 |
| ③ | AutoCAD COM（旧路径） | 6~7 秒；AutoCAD 没开还要多等 30~60 秒启动 | 要 |

程序按 ①→②→③ 自动试，日志里写明**用的哪条、用时多少**。

> **想彻底不用 AutoCAD**：装 [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter)
> （Open Design Alliance 的免费工具），装好后程序自动发现；装在别处就设环境变量
> `ODA_FILE_CONVERTER=<ODAFileConverter.exe 的完整路径>`。

顺带修了一个坑：accoreconsole 那条原来因为**中文路径**在脚本里变成问号而静默失败、退回了慢的 COM；
现在输入/输出都先落到临时目录的 ASCII 文件名再搬回来，中文路径也稳。

### 综合图扫描也提速

COM 失败/没缓存时，改用 **accoreconsole 把 DWG 转 DXF（约 3 秒）+ ezdxf 读**，并写回缓存。
另外加了面积上限 20000 m²：综合图里有一条 **50 万 m² 的图框**，以前会在某些扫法下被当成"历史矿块"。

### 每一步都显示耗时

GUI 日志现在这样：

```
[完成] 第 1 步 圈矿算量 + 出报告/图/.3ds（用时 5.8 秒）
OK  DWG 版本头 AC1024，50.7 KB（accoreconsole 无界面内核，用时 1.8 秒）
[完成] 第 2 步 DXF → DWG 2010（AutoCAD）（用时 2.0 秒）
```

### 同时包含 v1.5 的内容

人工画的 .3ds **没闭合**也能出图（闭合线=矿界、开口线=分块切线）；
交付里多 `.xls` 报告与 `炮孔数据报告分表/`；人工圈矿/精确/自动三种模式；
程序自己在炮区文件夹里找 .3ds；成品图严格照你画的线、不画综合图灰线；报告无底纹；
拖拽；Excel 工具（报告汇总 / 单日并入总表）已整合；窗口标题带版本号（本版 **v1.6**）。
