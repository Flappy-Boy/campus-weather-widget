"""pytest 全局配置：保证可导入 weather_data / ui，并提供无头 QApplication。

注意：
    * 数据层（weather_data）不依赖 PyQt，因此本文件在**顶层**不导入 PyQt6，
      以免在未安装 PyQt6 的环境中导致整个测试收集失败。
    * UI 测试通过 ``pytest.importorskip("PyQt6")`` 自行跳过。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 把项目根目录（包含 weather_data/ 与 ui/ 的目录）加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 无头运行 Qt：必须在创建 QApplication 之前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """整个测试会话共享一个 QApplication（offscreen 平台）。"""
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app