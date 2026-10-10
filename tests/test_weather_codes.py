"""weather_codes 纯函数测试：精确映射、兜底、绝不抛异常。"""

from __future__ import annotations

import pytest

from weather_data import (
    UNKNOWN_DESCRIPTION,
    WEATHER_CODE_MAP,
    describe_weather_code,
)


@pytest.mark.parametrize(
    "code,expected",
    [
        (0, "晴"),
        (2, "多云"),
        (3, "阴"),
        (45, "雾"),
        (61, "小雨"),
        (63, "中雨"),
        (65, "大雨"),
        (71, "小雪"),
        (80, "小阵雨"),
        (95, "雷阵雨"),
    ],
)
def test_exact_mapping(code: int, expected: str) -> None:
    assert describe_weather_code(code) == expected


def test_none_returns_unknown() -> None:
    assert describe_weather_code(None) == UNKNOWN_DESCRIPTION


@pytest.mark.parametrize("bad", ["abc", "", "1.5", object(), [1, 2], {"a": 1}])
def test_illegal_values_return_unknown_without_raising(bad: object) -> None:
    assert describe_weather_code(bad) == UNKNOWN_DESCRIPTION  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "code,expected",
    [
        (47, "雾"),        # 45<=x<=48 区间兜底
        (52, "毛毛雨"),     # 51<=x<=57
        (62, "雨"),        # 61<=x<=67
        (72, "雪"),        # 71<=x<=77
        (97, "雷暴"),       # 95<=x<=99
    ],
)
def test_range_fallback(code: int, expected: str) -> None:
    assert code not in WEATHER_CODE_MAP  # 前提：确属"未收录"
    assert describe_weather_code(code) == expected


@pytest.mark.parametrize("code", [-100, -1, 100, 1000, 4, 50, 60, 84, 90, 94])
def test_out_of_range_falls_back_to_unknown(code: int) -> None:
    assert describe_weather_code(code) == UNKNOWN_DESCRIPTION


def test_never_raises_for_wide_input_space() -> None:
    for value in range(-50, 250):
        assert isinstance(describe_weather_code(value), str)
    for weird in [None, "x", 3.9, True, [], ()]:
        assert isinstance(describe_weather_code(weird), str)  # type: ignore[arg-type]


def test_module_constants() -> None:
    assert UNKNOWN_DESCRIPTION == "未知天气"
    assert isinstance(WEATHER_CODE_MAP, dict)
    assert WEATHER_CODE_MAP[0] == "晴"