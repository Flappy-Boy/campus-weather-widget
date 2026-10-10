# 天气查询桌面应用（PyQt6 + Open-Meteo）

一个根据"城市 + 日期"展示当天天气的桌面应用。数据来自免费的
[Open-Meteo](https://open-meteo.com/) 接口，无需 API Key。

## 功能

- 输入城市名（中文/英文）搜索候选地点并选择
- 使用日期选择器（日历弹出）选择日期，默认今天
- 展示：天气状况、最高/最低气温、平均湿度、最大风速、降水量
- 自动路由：所选日期自动决定走"未来预报"还是"历史归档"接口
- 网络请求在后台线程执行，界面不会卡死；失败时有友好提示

## 环境要求

- Python 3.10+（开发环境为 Python 3.13）
- 依赖：`PyQt6`、`requests`、`pytest`

## 安装

```powershell
pip install -r requirements.txt
```

## 运行

```powershell
python main.py
```

切换为离线模式（不联网，使用确定性假数据，适合演示）：

```powershell
$env:WEATHER_PROVIDER="offline"; python main.py
```

## 目录结构

```
weather/
├── main.py                     # 应用入口（强制浅色 Fusion 主题）
├── requirements.txt
├── README.md
├── weather_data/               # 纯数据层（不依赖 PyQt，可 headless 测试）
│   ├── __init__.py             # 统一对外导出
│   ├── models.py               # Location / DailyWeather 数据模型
│   ├── weather_codes.py        # WMO 天气代码 -> 中文描述（纯函数）
│   ├── date_router.py          # 日期路由（预报 / 归档 / 超范围）
│   └── providers.py            # WeatherProvider / OpenMeteo / Offline
└── ui/                         # PyQt6 界面层
    ├── __init__.py
    ├── theme.py                # 浅色主题（QPalette）
    ├── worker.py               # QThread 后台请求
    └── main_window.py          # 主窗口
```

## 架构说明

- **数据层与 UI 层严格分离**：`weather_data` 不 import 任何 PyQt 模块，
  可在无图形环境中被 pytest 直接导入。
- **Provider 机制**：
  - `OpenMeteoProvider`：真实 HTTP 调用（惰性导入 `requests`，超时 10 秒）。
  - `OfflineProvider` / `MockProvider`：确定性假数据，相同输入必然相同输出。
  - 通过环境变量 `WEATHER_PROVIDER=openmeteo|offline` 或构造函数注入选择。
- **日期路由规则**：
  - 早于 1940-01-01 或晚于今天 + 15 天 → 超出可查询范围。
  - 距今 5 天及以上 → 历史归档接口（`/v1/archive`）。
  - 其余（最近 5 天 + 今天 + 未来约 16 天）→ 未来预报接口（`/v1/forecast`）。
- **湿度处理**：Open-Meteo 的 `daily` 变量不提供湿度均值，改用
  `hourly=relative_humidity_2m` 再按天聚合求均值；字段缺失时优雅降级为 `None`。

## 常见问题

- 若界面在 Windows 深色模式下显示异常，请确认通过 `main.py` 启动，
  它会强制应用 Fusion 浅色调色板（见 `ui/theme.py`）。
- 历史归档数据有约 5 天延迟，最近几天的日期请使用预报接口。