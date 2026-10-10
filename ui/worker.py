"""后台线程：把耗时的网络请求移出 UI 线程。

线程边界说明：
    * 每个 Worker 都是 :class:`PyQt6.QtCore.QThread` 的子类。
    * 请求在 ``run()`` 中执行（后台线程），结果通过信号回传到 UI 线程。
    * 信号携带的是纯 Python 对象（list / DailyWeather），跨线程传递是安全的。
    * UI 层必须持有 Worker 的引用（存到 self._xxx_worker）直到线程结束，
      否则对象会被垃圾回收导致崩溃。
"""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QThread, pyqtSignal

from weather_data import DailyWeather, Location, WeatherProvider


class SearchCityWorker(QThread):
    """在后台线程中检索城市。"""

    # 成功：携带 list[Location]
    succeeded = pyqtSignal(list)
    # 失败：携带面向用户的中文错误信息
    failed = pyqtSignal(str)

    def __init__(self, provider: WeatherProvider, name: str, parent=None) -> None:
        super().__init__(parent)
        self._provider = provider
        self._name = name

    def run(self) -> None:  # noqa: D401 - Qt 约定方法
        try:
            locations = self._provider.search_city(self._name)
            self.succeeded.emit(list(locations))
        except Exception as exc:  # 捕获所有异常，避免线程内崩溃
            self.failed.emit(str(exc) or "查询城市时发生未知错误。")


class FetchWeatherWorker(QThread):
    """在后台线程中获取指定城市、指定日期的天气。"""

    # 成功：携带 DailyWeather
    succeeded = pyqtSignal(object)
    # 失败：携带面向用户的中文错误信息
    failed = pyqtSignal(str)

    def __init__(
        self,
        provider: WeatherProvider,
        location: Location,
        target_date: date,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._provider = provider
        self._location = location
        self._target_date = target_date

    def run(self) -> None:  # noqa: D401 - Qt 约定方法
        try:
            weather: DailyWeather = self._provider.get_weather(
                self._location, self._target_date
            )
            self.succeeded.emit(weather)
        except Exception as exc:
            self.failed.emit(str(exc) or "获取天气时发生未知错误。")