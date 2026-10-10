"""日期路由：判断某个日期应当走"未来预报"还是"历史归档"接口。

    Open-Meteo 有两条数据通路：

    * Forecast（``/v1/forecast``）：提供从今天起约 16 天的预报，
      也支持查询最近几天的实况（含今天）。
    * Archive（``/v1/archive``）：提供 1940 年至今的历史再分析数据，
      但有约 5 天的延迟（最近 5 天内可能没有数据）。

    因此给定一个日期，需要路由到合适的接口。本模块只包含纯函数与常量，
    不依赖任何第三方库，方便单元测试。
"""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum

# 历史归档数据的最早可用日期（Open-Meteo 官方为 1940-01-01）
ARCHIVE_START_DATE: date = date(1940, 1, 1)

# 归档数据的延迟天数：距今 5 天以内的数据可能尚未归档
ARCHIVE_DELAY_DAYS: int = 5

# 预报接口可覆盖的总天数（含今天），Open-Meteo 约为 16 天
FORECAST_DAYS: int = 16


class DateRange(Enum):
    """日期所属的数据范围。

    * ``FORECAST``: 走预报接口（覆盖过去几天实况 + 未来约 16 天）。
    * ``ARCHIVE``: 走历史归档接口（1940 年至约 5 天前）。
    * ``OUT_OF_RANGE``: 超出可查询范围。
    """

    FORECAST = "forecast"
    ARCHIVE = "archive"
    OUT_OF_RANGE = "out_of_range"


def forecast_end_date(today: date | None = None) -> date:
    """返回预报接口能够覆盖的最后一天（含）。"""
    if today is None:
        today = date.today()
    return today + timedelta(days=FORECAST_DAYS - 1)


def archive_end_date(today: date | None = None) -> date:
    """返回历史归档接口可靠覆盖的最后一天（含）。"""
    if today is None:
        today = date.today()
    return today - timedelta(days=ARCHIVE_DELAY_DAYS)


def classify_date(target: date, today: date | None = None) -> DateRange:
    """判断 ``target`` 日期应走哪个数据接口。

    Args:
        target: 待查询的日期。
        today: 用于计算边界的"今天"，默认取系统当天；显式传入便于测试。

    Returns:
        :class:`DateRange` 枚举值。

    Raises:
        TypeError: 当 ``target`` 不是 :class:`datetime.date` 时。
    """
    # 注意：datetime.datetime 是 date 的子类，这里统一按日期处理
    if not isinstance(target, date):
        raise TypeError(f"target 必须是 datetime.date，实际为 {type(target)!r}")

    if today is None:
        today = date.today()

    # 早于归档起点：完全查不到
    if target < ARCHIVE_START_DATE:
        return DateRange.OUT_OF_RANGE

    # 晚于预报末日：超出范围
    if target > forecast_end_date(today):
        return DateRange.OUT_OF_RANGE

    # 距今 5 天及以上：走历史归档（更可靠）
    if target <= archive_end_date(today):
        return DateRange.ARCHIVE

    # 其余（最近 5 天内 + 今天 + 未来约 16 天）：走预报接口
    return DateRange.FORECAST


def describe_date_range(target: date, today: date | None = None) -> str:
    """返回给用户看的中文范围说明，便于界面提示。"""
    routing = classify_date(target, today)
    if routing is DateRange.FORECAST:
        return "预报数据"
    if routing is DateRange.ARCHIVE:
        return "历史归档数据"
    return "超出可查询范围"