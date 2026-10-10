"""数据模型测试：Location / DailyWeather 的语义与默认值。"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from weather_data import DailyWeather, Location


def test_location_display_name_full() -> None:
    loc = Location("北京", 39.9042, 116.4074, "中国", "北京市", "Asia/Shanghai")
    assert loc.display_name() == "北京 · 北京市 · 中国"


def test_location_display_name_admin_equals_name() -> None:
    loc = Location("北京", 39.9, 116.4, "中国", "北京")
    assert loc.display_name() == "北京 · 中国"


def test_location_display_name_minimal() -> None:
    loc = Location("某地", 0.0, 0.0)
    assert loc.display_name() == "某地"


def test_location_is_frozen() -> None:
    loc = Location("北京", 39.9, 116.4)
    with pytest.raises(FrozenInstanceError):
        loc.name = "上海"  # type: ignore[misc]


def test_daily_weather_defaults() -> None:
    w = DailyWeather(date=date(2024, 6, 15))
    assert w.temp_max is None
    assert w.weather_code is None
    assert w.weather_desc == "未知"
    assert w.source == ""


def test_daily_weather_extra_is_isolated_per_instance() -> None:
    a = DailyWeather(date=date(2024, 6, 15))
    b = DailyWeather(date=date(2024, 6, 15))
    a.extra["k"] = 1
    assert b.extra == {}


def test_daily_weather_equality() -> None:
    a = DailyWeather(date=date(2024, 6, 15), temp_max=25.0, source="offline")
    b = DailyWeather(date=date(2024, 6, 15), temp_max=25.0, source="offline")
    assert a == b