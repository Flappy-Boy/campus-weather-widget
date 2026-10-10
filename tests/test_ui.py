"""UI 层少量测试：纯函数 + offscreen 下 MainWindow 构造与渲染。

未安装 PyQt6 时整体跳过，不影响数据层测试。
"""

from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("PyQt6")

from weather_data import DailyWeather, OfflineProvider  # noqa: E402

from ui.main_window import PLACEHOLDER, MainWindow, _fmt, weather_emoji  # noqa: E402


@pytest.mark.parametrize(
    "code,expected",
    [
        (None, "❔"),
        (0, "☀️"),
        (1, "🌤️"),
        (2, "⛅"),
        (3, "☁️"),
        (45, "🌫️"),
        (61, "🌧️"),
        (71, "🌨️"),
        (80, "🌦️"),
        (95, "⛈️"),
        (100, "❔"),
        ("abc", "❔"),
    ],
)
def test_weather_emoji(code: object, expected: str) -> None:
    assert weather_emoji(code) == expected  # type: ignore[arg-type]


def test_fmt() -> None:
    assert _fmt(None, "°C") == PLACEHOLDER
    assert _fmt(25.0, "°C") == "25.0 °C"
    assert _fmt(25.0, "°C", 0) == "25 °C"
    assert _fmt(60.0, "%") == "60.0 %"


def test_main_window_constructs_offscreen(qapp) -> None:
    window = MainWindow(provider=OfflineProvider())
    assert window.windowTitle() == "天气查询 · Open-Meteo"
    assert window._selected_date() == date.today()
    window.close()


def test_main_window_render_weather_offline_source(qapp) -> None:
    window = MainWindow(provider=OfflineProvider())
    w = DailyWeather(
        date=date(2024, 6, 15),
        temp_max=25.5,
        temp_min=15.2,
        humidity=60.0,
        wind_speed=12.3,
        precipitation=0.0,
        weather_code=2,
        weather_desc="多云",
        source="offline",
    )
    window._render_weather(w)
    assert window.icon_label.text() == weather_emoji(2)
    assert window._fields["weather_desc"].text() == "多云"
    assert window._fields["temp_max"].text() == "25.5 °C"
    assert window._fields["humidity"].text() == "60.0 %"
    assert window._fields["source"].text() == "离线模拟数据"
    window.close()