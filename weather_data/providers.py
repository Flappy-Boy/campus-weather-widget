"""天气数据 Provider：可切换的数据来源实现。

设计要点：
    1. 数据层与 UI 层严格分离：本模块**不 import 任何 PyQt 模块**，
       可以在 headless 环境下被 pytest 直接导入。
    2. ``requests`` 采用**惰性导入**：只有在真正发起 HTTP 请求时才导入，
       这样即使环境里没有安装 requests，纯数据层仍可被导入与测试。
    3. 提供两种实现：

       * :class:`OpenMeteoProvider`：真实 HTTP 调用 Open-Meteo 三个接口。
       * :class:`OfflineProvider`：确定性假数据，相同输入永远返回相同输出，
         供测试与离线演示使用。

    4. 通过 :func:`create_provider` / :func:`get_default_provider` 选择实现，
       支持环境变量 ``WEATHER_PROVIDER=offline|openmeteo``（默认 openmeteo）。

    Open-Meteo 说明：
        * Geocoding: https://geocoding-api.open-meteo.com/v1/search
        * Forecast : https://api.open-meteo.com/v1/forecast
        * Archive  : https://archive-api.open-meteo.com/v1/archive

        注意 daily 变量中**不存在** ``relative_humidity_2m_mean``，
        因此湿度改为用 ``hourly=relative_humidity_2m`` 再按天求均值。
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Optional, Sequence

from .date_router import DateRange, classify_date
from .models import DailyWeather, Location
from .weather_codes import describe_weather_code

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DEFAULT_TIMEOUT = 10  # 秒

# daily 变量（注意：daily 不提供湿度，湿度单独用 hourly 处理）
DAILY_VARIABLES = (
    "weather_code,"
    "temperature_2m_max,"
    "temperature_2m_min,"
    "precipitation_sum,"
    "wind_speed_10m_max"
)
HOURLY_VARIABLES = "relative_humidity_2m"


class WeatherError(Exception):
    """数据层统一异常，携带面向用户的中文提示信息。"""


# --------------------------------------------------------------------------- #
# 解析辅助函数（纯函数，便于测试）
# --------------------------------------------------------------------------- #


def _as_float(value: Any) -> Optional[float]:
    """安全转换为 float，失败或 None 返回 None。"""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    """安全转换为 int，失败或 None 返回 None。"""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first(sequence: Any) -> Any:
    """取序列首元素；对 None / 空序列 / 非序列返回 None。"""
    if isinstance(sequence, (list, tuple)) and sequence:
        return sequence[0]
    return None


def _mean_humidity(hourly: dict) -> Optional[float]:
    """把 hourly.relative_humidity_2m 聚合为按天均值。

    过滤掉 None 与非数值项，全部无效时返回 None。
    """
    values = hourly.get("relative_humidity_2m")
    if not isinstance(values, (list, tuple)):
        return None
    numbers = [v for v in (_as_float(x) for x in values) if v is not None]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 1)


def parse_daily_weather(
    payload: dict, target_date: date, source: str
) -> DailyWeather:
    """把 Open-Meteo 返回的 JSON 解析为 :class:`DailyWeather`。

    解析缺失字段时优雅降级（返回 None），不抛异常。
    """
    payload = payload or {}
    daily = payload.get("daily") or {}
    hourly = payload.get("hourly") or {}

    code = _as_int(_first(daily.get("weather_code")))

    return DailyWeather(
        date=target_date,
        temp_max=_as_float(_first(daily.get("temperature_2m_max"))),
        temp_min=_as_float(_first(daily.get("temperature_2m_min"))),
        humidity=_mean_humidity(hourly),
        wind_speed=_as_float(_first(daily.get("wind_speed_10m_max"))),
        precipitation=_as_float(_first(daily.get("precipitation_sum"))),
        weather_code=code,
        weather_desc=describe_weather_code(code),
        source=source,
    )


# --------------------------------------------------------------------------- #
# 抽象基类
# --------------------------------------------------------------------------- #


class WeatherProvider(ABC):
    """天气数据源抽象接口。

    所有实现必须提供 :meth:`search_city` 与 :meth:`get_weather` 两个方法，
    且均不得依赖任何 GUI 组件。
    """

    @abstractmethod
    def search_city(self, name: str) -> list[Location]:
        """根据城市名称检索候选地点。

        Args:
            name: 用户输入的城市名，可为中文或英文。

        Returns:
            候选 :class:`Location` 列表，按相关度排序；无结果时返回空列表。
        """
        raise NotImplementedError

    @abstractmethod
    def get_weather(self, location: Location, target_date: date) -> DailyWeather:
        """获取指定地点、指定日期的天气。

        Args:
            location: 目标地点。
            target_date: 目标日期。

        Returns:
            :class:`DailyWeather` 实例。

        Raises:
            WeatherError: 网络异常、数据范围超限等可预期错误。
        """
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Open-Meteo 真实实现
# --------------------------------------------------------------------------- #


class OpenMeteoProvider(WeatherProvider):
    """基于 Open-Meteo 免费接口的真实数据源（无需 API Key）。"""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout

    # -- 内部工具 ---------------------------------------------------------- #

    @staticmethod
    def _requests_module():
        """惰性导入 requests，缺依赖时抛出友好的 WeatherError。"""
        try:
            import requests  # 局部导入，保证数据层在无 requests 时仍可导入
        except ImportError as exc:  # pragma: no cover - 取决于运行环境
            raise WeatherError(
                "缺少依赖 requests，请先执行：pip install requests"
            ) from exc
        return requests

    def _get_json(self, url: str, params: dict) -> dict:
        """发起 GET 请求并返回 JSON；统一处理网络异常。"""
        requests = self._requests_module()
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as exc:
            raise WeatherError(
                f"请求超时（超过 {self.timeout} 秒），请检查网络后重试。"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise WeatherError("网络连接失败，请检查网络连接后重试。") from exc
        except requests.exceptions.HTTPError as exc:
            status = getattr(exc.response, "status_code", "未知")
            raise WeatherError(f"服务端返回错误（HTTP {status}），请稍后重试。") from exc
        except requests.exceptions.RequestException as exc:
            raise WeatherError(f"请求发生异常：{exc}") from exc
        except ValueError as exc:
            raise WeatherError("服务端返回的数据格式无法解析。") from exc

    # -- 接口实现 ---------------------------------------------------------- #

    def search_city(self, name: str) -> list[Location]:
        """调用 Geocoding 接口检索城市。"""
        name = (name or "").strip()
        if not name:
            return []

        params = {
            "name": name,
            "count": 5,
            "language": "zh",
            "format": "json",
        }
        data = self._get_json(GEOCODING_URL, params)
        results = data.get("results") or []

        locations: list[Location] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            latitude = _as_float(item.get("latitude"))
            longitude = _as_float(item.get("longitude"))
            if latitude is None or longitude is None:
                continue
            locations.append(
                Location(
                    name=str(item.get("name") or name),
                    latitude=latitude,
                    longitude=longitude,
                    country=item.get("country"),
                    admin1=item.get("admin1"),
                    timezone=item.get("timezone"),
                )
            )
        return locations

    def get_weather(self, location: Location, target_date: date) -> DailyWeather:
        """按日期自动路由到 Forecast 或 Archive 接口。"""
        routing = classify_date(target_date)
        if routing is DateRange.OUT_OF_RANGE:
            raise WeatherError(
                "所选日期超出 Open-Meteo 可查询范围"
                "（1940 年至今，未来约 16 天）。"
            )

        url = FORECAST_URL if routing is DateRange.FORECAST else ARCHIVE_URL
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "daily": DAILY_VARIABLES,
            "hourly": HOURLY_VARIABLES,
            "timezone": "auto",
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        }

        payload = self._get_json(url, params)
        weather = parse_daily_weather(payload, target_date, source=routing.value)
        return weather


# --------------------------------------------------------------------------- #
# 离线 / 测试实现
# --------------------------------------------------------------------------- #


class OfflineProvider(WeatherProvider):
    """离线确定性数据源。

    * 相同输入（城市名 + 日期）永远返回相同的输出，便于断言。
    * 完全不访问网络，也不依赖 requests，可在无 GUI、无网络的 CI 中运行。
    * 对常见城市返回近似真实的经纬度，其余城市由名称哈希推导出稳定坐标。
    """

    # 内置城市：显示名 -> (纬度, 经度, 国家, 行政区, 时区)
    _KNOWN_CITIES: dict[str, tuple[float, float, str, str, str]] = {
        "北京": (39.9042, 116.4074, "中国", "北京市", "Asia/Shanghai"),
        "上海": (31.2304, 121.4737, "中国", "上海市", "Asia/Shanghai"),
        "广州": (23.1291, 113.2644, "中国", "广东省", "Asia/Shanghai"),
        "深圳": (22.5431, 114.0579, "中国", "广东省", "Asia/Shanghai"),
        "成都": (30.5728, 104.0668, "中国", "四川省", "Asia/Shanghai"),
        "杭州": (30.2741, 120.1551, "中国", "浙江省", "Asia/Shanghai"),
        "伦敦": (51.5074, -0.1278, "英国", "英格兰", "Europe/London"),
        "东京": (35.6762, 139.6503, "日本", "东京都", "Asia/Tokyo"),
        "纽约": (40.7128, -74.0060, "美国", "纽约州", "America/New_York"),
        "巴黎": (48.8566, 2.3522, "法国", "法兰西岛", "Europe/Paris"),
    }

    # 确定性假数据用到的天气代码池
    _CODE_POOL = (0, 1, 2, 3, 45, 51, 61, 63, 65, 71, 73, 75, 80, 95)

    @staticmethod
    def _seed(*parts: str) -> int:
        """把若干字符串稳定地映射为一个非负整数（与 PYTHONHASHSEED 无关）。"""
        raw = "|".join(parts).encode("utf-8")
        digest = hashlib.md5(raw).hexdigest()
        return int(digest[:8], 16)

    def search_city(self, name: str) -> list[Location]:
        """返回确定性的候选地点。"""
        name = (name or "").strip()
        if not name:
            return []

        # 1) 命中内置城市（支持包含匹配，例如"北京市"）
        for city, (lat, lon, country, admin1, tz) in self._KNOWN_CITIES.items():
            if name in city or city in name:
                return [
                    Location(
                        name=city,
                        latitude=lat,
                        longitude=lon,
                        country=country,
                        admin1=admin1,
                        timezone=tz,
                    )
                ]

        # 2) 未命中：由名称哈希推导稳定坐标（纬度 -60~60，经度 -180~180）
        seed = self._seed(name)
        latitude = round((seed % 12000) / 100.0 - 60.0, 4)
        longitude = round(((seed // 12000) % 36000) / 100.0 - 180.0, 4)
        return [
            Location(
                name=name,
                latitude=latitude,
                longitude=longitude,
                country="测试国",
                admin1="测试省",
                timezone="UTC",
            )
        ]

    def get_weather(self, location: Location, target_date: date) -> DailyWeather:
        """返回确定性的天气假数据。"""
        seed = self._seed(location.name, target_date.isoformat())

        temp_min = round(-10 + (seed % 2000) / 100.0, 1)          # -10 ~ 10
        temp_max = round(temp_min + 5 + ((seed // 7) % 1500) / 100.0, 1)
        humidity = round(30 + ((seed // 13) % 6000) / 100.0, 1)    # 30 ~ 90
        wind_speed = round(((seed // 17) % 6000) / 100.0, 1)       # 0 ~ 60
        precipitation = round(((seed // 23) % 3000) / 100.0, 1)    # 0 ~ 30
        weather_code = self._CODE_POOL[seed % len(self._CODE_POOL)]

        return DailyWeather(
            date=target_date,
            temp_max=temp_max,
            temp_min=temp_min,
            humidity=humidity,
            wind_speed=wind_speed,
            precipitation=precipitation,
            weather_code=weather_code,
            weather_desc=describe_weather_code(weather_code),
            # 离线数据来源固定标记为 "offline"，与 UI 中"离线模拟数据"文案对应
            source="offline",
        )


# 语义别名：测试中常写作 MockProvider
MockProvider = OfflineProvider


# --------------------------------------------------------------------------- #
# Provider 工厂
# --------------------------------------------------------------------------- #

_PROVIDER_ALIASES = {
    "openmeteo": "openmeteo",
    "open-meteo": "openmeteo",
    "online": "openmeteo",
    "offline": "offline",
    "mock": "offline",
    "fake": "offline",
}


def create_provider(name: str | None = None) -> WeatherProvider:
    """根据名称创建 Provider（构造函数注入方式）。

    Args:
        name: "openmeteo" 或 "offline"（大小写不敏感，含常见别名）；
              为 None 时读取环境变量 ``WEATHER_PROVIDER``，默认 openmeteo。
    """
    if name is None:
        name = os.environ.get("WEATHER_PROVIDER", "openmeteo")
    key = _PROVIDER_ALIASES.get(str(name).strip().lower())
    if key == "offline":
        return OfflineProvider()
    if key == "openmeteo":
        return OpenMeteoProvider()
    raise WeatherError(
        f"未知的 Provider 名称：{name!r}，可选值为 openmeteo / offline。"
    )


def get_default_provider() -> WeatherProvider:
    """按环境变量 ``WEATHER_PROVIDER`` 返回默认 Provider（默认 openmeteo）。"""
    return create_provider(None)


__all__ = [
    "WeatherError",
    "WeatherProvider",
    "OpenMeteoProvider",
    "OfflineProvider",
    "MockProvider",
    "create_provider",
    "get_default_provider",
    "parse_daily_weather",
    "GEOCODING_URL",
    "FORECAST_URL",
    "ARCHIVE_URL",
]