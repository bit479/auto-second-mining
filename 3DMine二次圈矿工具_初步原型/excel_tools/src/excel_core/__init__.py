"""Excel 数据处理核心层。

提供与业务无关的基础能力：
* :mod:`model`     —— 统一数据表模型与值清洗
* :mod:`reader`    —— 多格式读取、表头自动定位
* :mod:`transform` —— 拼接、对齐、去重、分组聚合
* :mod:`writer`    —— 样式化写出
"""

__version__ = "1.0.0"
