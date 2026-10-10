"""date_router 测试：三态边界、类型校验、常量与描述文案。"""

from __future__ import annotations

from datetime import date

import pytest

from weather_data import (
    ARCHIVE_DELAY_DAYS,
    ARCHIVE_START_DATE,
    FORECAST_DAYS,
    DateRange,
    archive_end_date,
    classify_date,
    describe_date_range,
    forecast_end_date,
)

TODAY = date(2024, 6, 15)


def test_constants() -> None:
    assert ARCHIVE_START_DATE == date(1940, 1, 1)
    assert ARCHIVE_DELAY_DAYS == 5
    assert FORECAST_DAYS == 16


def test_end_dates() -> None:
    assert forecast_end_date(TODAY) == date(2024, 6, 30)  # today + 15
    assert archive_end_date(TODAY) == date(2024, 6, 10)   # today - 5


@pytest.mark.parametrize(
    "target,expected",
    [
        (date(1939, 12, 31), DateRange.OUT_OF_RANGE),  # 早于归档起点
        (date(1940, 1, 1), DateRange.ARCHIVE),          # 恰为归档起点
        (date(2024, 6, 9), DateRange.ARCHIVE),          # today-6
        (date(2024, 6, 10), DateRange.ARCHIVE),         # today-5（边界，含）
        (date(2024, 6, 11), DateRange.FORECAST),        # today-4
        (date(2024, 6, 15), DateRange.FORECAST),        # today
        (date(2024, 6, 30), DateRange.FORECAST),        # today+15（边界，含）
        (date(2024, 7, 1), DateRange.OUT_OF_RANGE),     # today+16
    ],
)
def test_classify_date_boundaries(target: date, expected: DateRange) -> None:
    assert classify_date(target, TODAY) is expected


@pytest.mark.parametrize("bad", ["2024-06-15", 20240615, None, 3.14, [], object()])
def test_classify_date_type_error(bad: object) -> None:
    with pytest.raises(TypeError):
        classify_date(bad, TODAY)  # type: ignore[arg-type]


def test_classify_date_default_today() -> None:
    assert classify_date(date.today()) is DateRange.FORECAST


def test_describe_date_range() -> None:
    assert describe_date_range(TODAY, TODAY) == "预报数据"
    assert describe_date_range(date(2024, 6, 10), TODAY) == "历史归档数据"
    assert describe_date_range(date(1939, 1, 1), TODAY) == "超出可查询范围"


def test_enum_values() -> None:
    assert DateRange.FORECAST.value == "forecast"
    assert DateRange.ARCHIVE.value == "archive"
    assert DateRange.OUT_OF_RANGE.value == "out_of_range"