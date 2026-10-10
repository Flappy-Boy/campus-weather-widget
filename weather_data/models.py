"""数据模型定义。

说明：
    本模块属于**纯数据层**，严禁 import 任何 PyQt / GUI 相关模块，
    以保证可以在无图形环境（headless）下被 pytest 直接导入与测试。

    所有数值字段均允许为 ``None``，用于表达"数据缺失"的情况，
    避免上游解析失败时抛出异常导致界面崩溃。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Location:
    """一个地理位置（城市）。

    Attributes:
        name: 城市名称，例如 "北京"。
        latitude: 纬度（-90 ~ 90）。
        longitude: 经度（-180 ~ 180）。
        country: 国家 / 地区名称，可为 None。
        admin1: 一级行政区（省 / 州），可为 None。
        timezone: IANA 时区名，例如 "Asia/Shanghai"，可为 None。
    """

    name: str
    latitude: float
    longitude: float
    country: Optional[str] = None
    admin1: Optional[str] = None
    timezone: Optional[str] = None

    def display_name(self) -> str:
        """返回用于界面展示的完整地名，例如 "北京 · 北京市 · 中国"。"""
        parts = [self.name]
        if self.admin1 and self.admin1 != self.name:
            parts.append(self.admin1)
        if self.country:
            parts.append(self.country)
        return " · ".join(parts)


@dataclass
class DailyWeather:
    """某一天的天气数据。

    Attributes:
        date: 该天气数据对应的日期。
        temp_max: 当日最高气温（摄氏度），缺失为 None。
        temp_min: 当日最低气温（摄氏度），缺失为 None。
        humidity: 当日平均相对湿度（百分比），缺失为 None。
        wind_speed: 当日最大风速（km/h），缺失为 None。
        precipitation: 当日累计降水量（mm），缺失为 None。
        weather_code: WMO 天气代码，缺失为 None。
        weather_desc: 天气代码对应的中文描述，缺失时为兜底文案。
        source: 数据来源标识，取值 "forecast" / "archive" / "offline" 等。
    """

    date: date
    temp_max: Optional[float] = None
    temp_min: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    precipitation: Optional[float] = None
    weather_code: Optional[int] = None
    weather_desc: str = "未知"
    source: str = ""
    extra: dict = field(default_factory=dict)