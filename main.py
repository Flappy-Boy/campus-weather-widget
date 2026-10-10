"""天气查询应用入口。

用法::

    python main.py

可选环境变量：
    WEATHER_PROVIDER=openmeteo   # 默认，真实调用 Open-Meteo
    WEATHER_PROVIDER=offline     # 使用离线确定性假数据（无需联网）

说明：
    本机 Windows 处于深色模式时，Qt 控件会被绘制成深色导致看不清，
    因此这里强制使用 Fusion 风格 + 浅色调色板（见 ui.theme）。
"""

from __future__ import annotations

import os
import sys

# 保证从任意工作目录启动时都能找到本项目的包
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui.main_window import MainWindow  # noqa: E402
from ui.theme import apply_light_theme  # noqa: E402
from weather_data import WeatherError, get_default_provider  # noqa: E402


def main() -> int:
    """应用主函数，返回进程退出码。"""
    app = QApplication(sys.argv)
    app.setApplicationName("天气查询")

    # 强制浅色主题，避免深色模式下文字不可读
    apply_light_theme(app)

    # Provider 选择：环境变量 WEATHER_PROVIDER=offline|openmeteo（默认 openmeteo）
    try:
        provider = get_default_provider()
    except WeatherError:
        # 配置错误时降级到离线 Provider，保证应用仍可启动
        from weather_data import OfflineProvider

        provider = OfflineProvider()

    window = MainWindow(provider=provider)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())