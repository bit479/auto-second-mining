# -*- coding: utf-8 -*-
"""二次圈矿智能工作台 · 新版桌面 UI（PySide6）。

模块结构::

    ui_v2/
    ├── app.py            入口（GUI / 单文件 exe 的 --run-script 派发）
    ├── main_window.py    主窗口：侧栏导航 + 顶栏 + QStackedWidget
    ├── theme.py          配色与 QSS
    ├── icons.py          内联 SVG 线性图标
    ├── components/       卡片、徽章、日志台、参数格、表格等公共组件
    ├── services/         路径、后台任务、配置/参数、文件识别（UI 与业务的唯一桥梁）
    └── pages/            十个业务页面
"""

from .services.paths import APP_NAME, APP_NAME_EN, APP_VERSION

__all__ = ["APP_NAME", "APP_NAME_EN", "APP_VERSION"]
