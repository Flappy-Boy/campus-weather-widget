"""providers 测试：解析函数、离线源、工厂、OpenMeteo（打桩，不联网）。"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from weather_data import (
    ARCHIVE_URL,
    FORECAST_URL,
    MockProvider,
    OfflineProvider,
    OpenMeteoProvider,
    WeatherError,
    WeatherProvider,
    create_provider,
    describe_weather_code,
    parse_daily_weather,
)
from weather_data import Location

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SAMPLE_PAYLOAD = {
    "daily": {
        "weather_code": [2],
        "temperature_2m_max": [25.5],
        "temperature_2m_min": [15.2],
        "precipitation_sum": [0.0],
        "wind_speed_10m_max": [12.3],
    },
    "hourly": {"relative_humidity_2m": [50, 60, 70]},
}


# --------------------------------------------------------------------------- #
# parse_daily_weather
# --------------------------------------------------------------------------- #
def test_parse_daily_weather_typical() -> None:
    target = date(2024, 6, 15)
    w = parse_daily_weather(SAMPLE_PAYLOAD, target, "forecast")
    assert w.date == target
    assert w.temp_max == 25.5
    assert w.temp_min == 15.2
    assert w.wind_speed == 12.3
    assert w.precipitation == 0.0
    assert w.weather_code == 2
    assert w.weather_desc == "多云"
    assert w.humidity == 60.0  # mean(50,60,70)
    assert w.source == "forecast"


def test_parse_daily_weather_humidity_rounding() -> None:
    payload = {"hourly": {"relative_humidity_2m": [10, 20, 25]}}
    w = parse_daily_weather(payload, date(2024, 6, 15), "archive")
    assert w.humidity == 18.3  # 55/3=18.333... -> 18.3


def test_parse_daily_weather_humidity_filters_invalid() -> None:
    payload = {"hourly": {"relative_humidity_2m": [None, "x", 40, 60]}}
    w = parse_daily_weather(payload, date(2024, 6, 15), "forecast")
    assert w.humidity == 50.0


@pytest.mark.parametrize(
    "hourly",
    [
        {"relative_humidity_2m": []},
        {"relative_humidity_2m": [None, None]},
        {"relative_humidity_2m": "not-a-list"},
        {},
    ],
)
def test_parse_daily_weather_humidity_degrade(hourly: dict) -> None:
    w = parse_daily_weather({"hourly": hourly}, date(2024, 6, 15), "forecast")
    assert w.humidity is None


def test_parse_daily_weather_takes_first_element() -> None:
    payload = {"daily": {"weather_code": [3, 95], "temperature_2m_max": [10, 99]}}
    w = parse_daily_weather(payload, date(2024, 6, 15), "forecast")
    assert w.weather_code == 3
    assert w.temp_max == 10.0


@pytest.mark.parametrize("payload", [{}, {"daily": None, "hourly": None}, {"daily": {}}])
def test_parse_daily_weather_missing_fields_degrade(payload: dict) -> None:
    w = parse_daily_weather(payload, date(2024, 6, 15), "forecast")
    assert w.temp_max is None
    assert w.weather_code is None
    assert w.weather_desc == "未知天气"
    assert w.source == "forecast"


def test_parse_daily_weather_never_raises_on_garbage() -> None:
    w = parse_daily_weather({"daily": {"weather_code": "abc"}}, date(2024, 6, 15), "x")
    assert w.weather_code is None


# --------------------------------------------------------------------------- #
# OfflineProvider
# --------------------------------------------------------------------------- #
def test_offline_search_empty() -> None:
    assert OfflineProvider().search_city("") == []
    assert OfflineProvider().search_city("   ") == []


@pytest.mark.parametrize(
    "name,lat,lon",
    [
        ("北京", 39.9042, 116.4074),
        ("上海", 31.2304, 121.4737),
        ("广州", 23.1291, 113.2644),
        ("深圳", 22.5431, 114.0579),
        ("成都", 30.5728, 104.0668),
        ("杭州", 30.2741, 120.1551),
        ("伦敦", 51.5074, -0.1278),
        ("东京", 35.6762, 139.6503),
        ("纽约", 40.7128, -74.0060),
        ("巴黎", 48.8566, 2.3522),
    ],
)
def test_offline_known_cities(name: str, lat: float, lon: float) -> None:
    results = OfflineProvider().search_city(name)
    assert len(results) == 1
    assert results[0].latitude == pytest.approx(lat)
    assert results[0].longitude == pytest.approx(lon)


def test_offline_search_is_deterministic_for_unknown_city() -> None:
    p = OfflineProvider()
    a = p.search_city("不存在的城市XYZ")
    b = p.search_city("不存在的城市XYZ")
    assert a == b
    assert len(a) == 1
    assert -90 <= a[0].latitude <= 90
    assert -180 <= a[0].longitude <= 180


def test_offline_get_weather_deterministic_and_source() -> None:
    p = OfflineProvider()
    loc = p.search_city("北京")[0]
    w1 = p.get_weather(loc, date(2024, 6, 15))
    w2 = p.get_weather(loc, date(2024, 6, 15))
    assert w1 == w2
    assert w1.source == "offline"
    assert w1.weather_desc == describe_weather_code(w1.weather_code)
    assert w1.temp_max is not None and w1.temp_min is not None
    assert w1.temp_max >= w1.temp_min


def test_mock_provider_alias() -> None:
    assert MockProvider is OfflineProvider


# --------------------------------------------------------------------------- #
# create_provider / get_default_provider
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["offline", "OFFLINE", "mock", "fake", " Mock "])
def test_create_provider_offline_aliases(name: str) -> None:
    assert isinstance(create_provider(name), OfflineProvider)


@pytest.mark.parametrize("name", ["openmeteo", "open-meteo", "online", "OpenMeteo"])
def test_create_provider_openmeteo_aliases(name: str) -> None:
    assert isinstance(create_provider(name), OpenMeteoProvider)


def test_create_provider_unknown_raises() -> None:
    with pytest.raises(WeatherError):
        create_provider("nope")


def test_create_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEATHER_PROVIDER", "offline")
    assert isinstance(create_provider(None), OfflineProvider)
    monkeypatch.setenv("WEATHER_PROVIDER", "openmeteo")
    assert isinstance(create_provider(None), OpenMeteoProvider)


def test_create_provider_default_is_openmeteo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEATHER_PROVIDER", raising=False)
    assert isinstance(create_provider(None), OpenMeteoProvider)


# --------------------------------------------------------------------------- #
# OpenMeteoProvider（全部打桩，不联网）
# --------------------------------------------------------------------------- #
def test_openmeteo_forecast_uses_forecast_url(monkeypatch: pytest.MonkeyPatch) -> None:
    p = OpenMeteoProvider()
    captured: dict = {}

    def fake_get_json(url: str, params: dict) -> dict:
        captured["url"] = url
        return SAMPLE_PAYLOAD

    monkeypatch.setattr(p, "_get_json", fake_get_json)
    loc = Location("北京", 39.9, 116.4)
    w = p.get_weather(loc, date.today())
    assert captured["url"] == FORECAST_URL
    assert w.source == "forecast"
    assert w.weather_code == 2


def test_openmeteo_archive_uses_archive_url(monkeypatch: pytest.MonkeyPatch) -> None:
    p = OpenMeteoProvider()
    captured: dict = {}

    def fake_get_json(url: str, params: dict) -> dict:
        captured["url"] = url
        return SAMPLE_PAYLOAD

    monkeypatch.setattr(p, "_get_json", fake_get_json)
    loc = Location("北京", 39.9, 116.4)
    w = p.get_weather(loc, date(2020, 1, 1))
    assert captured["url"] == ARCHIVE_URL
    assert w.source == "archive"


def test_openmeteo_out_of_range_raises_without_http(monkeypatch: pytest.MonkeyPatch) -> None:
    p = OpenMeteoProvider()

    def boom(url: str, params: dict) -> dict:
        raise AssertionError("超出范围时不应发起网络请求")

    monkeypatch.setattr(p, "_get_json", boom)
    with pytest.raises(WeatherError):
        p.get_weather(Location("北京", 39.9, 116.4), date(1900, 1, 1))


def test_openmeteo_search_city_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    p = OpenMeteoProvider()
    payload = {
        "results": [
            {"name": "北京", "latitude": 39.9, "longitude": 116.4,
             "country": "中国", "admin1": "北京市", "timezone": "Asia/Shanghai"},
            {"name": "坏数据", "latitude": None, "longitude": None},
        ]
    }
    monkeypatch.setattr(p, "_get_json", lambda url, params: payload)
    results = p.search_city("北京")
    assert len(results) == 1
    assert results[0].name == "北京"
    assert results[0].latitude == 39.9


def test_openmeteo_search_empty_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    p = OpenMeteoProvider()

    def boom(url: str, params: dict) -> dict:
        raise AssertionError("空查询不应发起网络请求")

    monkeypatch.setattr(p, "_get_json", boom)
    assert p.search_city("") == []


def test_weather_provider_is_abstract() -> None:
    with pytest.raises(TypeError):
        WeatherProvider()  # type: ignore[abstract]


# --------------------------------------------------------------------------- #
# 数据层无 GUI 依赖（子进程隔离验证）
# --------------------------------------------------------------------------- #
def test_data_layer_does_not_import_pyqt() -> None:
    code = (
        "import weather_data, sys;"
        "assert 'PyQt6' not in sys.modules, "
        "sorted(k for k in sys.modules if k.startswith('PyQt6'));"
        "print('DATA_LAYER_CLEAN')"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "DATA_LAYER_CLEAN" in proc.stdout