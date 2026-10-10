"""ui 包：PyQt6 界面层。

本包依赖 ``weather_data``（纯数据层），但数据层绝不反向依赖本包，
以此保证数据层可以在无 GUI 环境下被测试。

模块：
    * :mod:`ui.worker`      —— 后台线程，避免网络请求阻塞 UI。
    * :mod:`ui.main_window` —— 主窗口。
    * :mod:`ui.theme`       —— 浅色主题（QPalette）。
"""

from __future__ import annotations

__all__ = ["main_window", "worker", "theme"]