# -*- coding: utf-8 -*-
"""清除 00_标准界面 menu_default.xml 开头的残缺 <menu_group 残留标签。"""
import re

p = r"E:\gzRJ\3Dmine\2023\3DMine V202310\3DMine V202310\common\cui\3dmine_profile_chinese\00_标准界面\menu_default.xml"
s = open(p, encoding="utf-8", errors="replace").read()

# 清理 <3dmine_menu> 后、第一个正常组前的残缺内容
head = s[:500]
print("BEFORE:")
print(repr(head[:300]))

# 删除残缺标签行 + 多余空行：模式 = 3dmine_menu> 之后任意 残缺 <menu_group name="xxx（无闭合）... 直到 <menu_group name="文件
s2 = re.sub(
    r'(<3dmine_menu>\s*)(?:<menu_group[^>]*"?\s*)+(?=<menu_group name="文件)',
    r'\1',
    s,
    flags=re.S,
)
if s2 == s:
    # 兜底：直接删掉"<menu_group name=\"  " 残缺片段及其后多余空行
    s2 = re.sub(r'<menu_group name="\s+</?3dmine_menu>', "</3dmine_menu>", s)
    s2 = re.sub(r'(<3dmine_menu>)\s*<menu_group name="\s*(\n\s*)*', r'\1\n', s2, flags=re.S)

open(p, "w", encoding="utf-8").write(s2)
head2 = s2[:300]
print("\nAFTER:")
print(repr(head2[:300]))
# 检查平衡
import re as _re
sc = _re.sub(r"<!--.*?-->", "", s2, flags=_re.S)
print("groups: %d/%d" % (sc.count("<menu_group"), sc.count("</menu_group>")))
print("items: %d/%d" % (sc.count("<menu_item"), sc.count("</menu_item>")))
print("PyMacro:", "PyMacro" in s2)
