"""WMO 天气代码（weather code）到中文描述的映射。

    Open-Meteo 的 ``weather_code`` 字段采用 WMO 4677 天气代码标准。
    本模块只提供**纯函数**，不依赖任何外部库，方便单元测试。

    对于未知代码，提供按数值区间的兜底文案，绝不抛异常。
"""

from __future__ import annotations

from typing import Optional

# WMO 天气代码 -> 中文描述（精确匹配表）
WEATHER_CODE_MAP: dict[int, str] = {
    0: "晴",
    1: "基本晴朗",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇（沉积雾）",
    51: "小毛毛雨",
    53: "中等毛毛雨",
    55: "浓密毛毛雨",
    56: "轻度冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "轻度冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷阵雨",
    96: "雷阵雨伴小冰雹",
    99: "雷阵雨伴大冰雹",
}

# 未知代码的兜底文案
UNKNOWN_DESCRIPTION = "未知天气"


def describe_weather_code(code: Optional[int]) -> str:
    """把 WMO 天气代码转换为中文描述。

    Args:
        code: WMO 天气代码，允许 None 或任意可转换为 int 的值。

    Returns:
        中文描述字符串；对 None / 非法值 / 未收录代码返回兜底文案，
        **绝不抛出异常**。
    """
    if code is None:
        return UNKNOWN_DESCRIPTION

    try:
        value = int(code)
    except (TypeError, ValueError):
        return UNKNOWN_DESCRIPTION

    if value in WEATHER_CODE_MAP:
        return WEATHER_CODE_MAP[value]

    # 区间兜底：即使服务端将来新增代码，也能给出合理描述
    if 0 <= value <= 3:
        return "晴间多云"
    if 45 <= value <= 48:
        return "雾"
    if 51 <= value <= 57:
        return "毛毛雨"
    if 61 <= value <= 67:
        return "雨"
    if 71 <= value <= 77:
        return "雪"
    if 80 <= value <= 82:
        return "阵雨"
    if 85 <= value <= 86:
        return "阵雪"
    if 95 <= value <= 99:
        return "雷暴"
    return UNKNOWN_DESCRIPTION