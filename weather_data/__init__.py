"""weather_data 包：纯数据层（不依赖任何 GUI 库）。

对外统一导出数据模型、Provider、天气代码映射与日期路由工具。

用法示例::

    from weather_data import OfflineProvider
    provider = OfflineProvider()
    cities = provider.search_city("北京")
    weather = provider.get_weather(cities[0], date.today())
"""

from __future__ import annotations

from .date_router import (
    ARCHIVE_DELAY_DAYS,
    ARCHIVE_START_DATE,
    FORECAST_DAYS,
    DateRange,
    archive_end_date,
    classify_date,
    describe_date_range,
    forecast_end_date,
)
from .models import DailyWeather, Location
from .providers import (
    ARCHIVE_URL,
    FORECAST_URL,
    GEOCODING_URL,
    MockProvider,
    OfflineProvider,
    OpenMeteoProvider,
    WeatherError,
    WeatherProvider,
    create_provider,
    get_default_provider,
    parse_daily_weather,
)
from .weather_codes import (
    UNKNOWN_DESCRIPTION,
    WEATHER_CODE_MAP,
    describe_weather_code,
)

__version__ = "1.0.0"

__all__ = [
    # 数据模型
    "Location",
    "DailyWeather",
    # Provider
    "WeatherProvider",
    "OpenMeteoProvider",
    "OfflineProvider",
    "MockProvider",
    "WeatherError",
    "create_provider",
    "get_default_provider",
    "parse_daily_weather",
    # 天气代码
    "describe_weather_code",
    "WEATHER_CODE_MAP",
    "UNKNOWN_DESCRIPTION",
    # 日期路由
    "DateRange",
    "classify_date",
    "describe_date_range",
    "forecast_end_date",
    "archive_end_date",
    "ARCHIVE_START_DATE",
    "ARCHIVE_DELAY_DAYS",
    "FORECAST_DAYS",
    # 接口地址常量
    "GEOCODING_URL",
    "FORECAST_URL",
    "ARCHIVE_URL",
    # 版本
    "__version__",
]