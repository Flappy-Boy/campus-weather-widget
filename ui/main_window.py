"""主窗口：城市检索、日期选择与天气展示。

线程边界：
    网络请求全部通过 :mod:`ui.worker` 中的 QThread 子类在后台执行，
    主线程只负责更新界面。所有后台线程实例都保存在 ``self._workers``
    列表中，直到线程 ``finished`` 才移除，避免被垃圾回收。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PyQt6.QtCore import QDate, QThread, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from weather_data import (
    DailyWeather,
    DateRange,
    Location,
    WeatherProvider,
    classify_date,
    get_default_provider,
)

from .worker import FetchWeatherWorker, SearchCityWorker

# 展示占位符
PLACEHOLDER = "—"


def weather_emoji(code: Optional[int]) -> str:
    """把 WMO 天气代码映射为一个 emoji 图标（仅用于界面展示）。"""
    if code is None:
        return "❔"
    try:
        value = int(code)
    except (TypeError, ValueError):
        return "❔"

    if value == 0:
        return "☀️"
    if value == 1:
        return "🌤️"
    if value == 2:
        return "⛅"
    if value == 3:
        return "☁️"
    if value in (45, 48):
        return "🌫️"
    if 51 <= value <= 57:
        return "🌦️"
    if 61 <= value <= 67:
        return "🌧️"
    if 71 <= value <= 77:
        return "🌨️"
    if 80 <= value <= 82:
        return "🌦️"
    if 85 <= value <= 86:
        return "🌨️"
    if 95 <= value <= 99:
        return "⛈️"
    return "❔"


def _fmt(value: Optional[float], unit: str, digits: int = 1) -> str:
    """把可选数值格式化为带单位的字符串。"""
    if value is None:
        return PLACEHOLDER
    return f"{value:.{digits}f} {unit}"


class MainWindow(QMainWindow):
    """天气查询主窗口。"""

    def __init__(self, provider: Optional[WeatherProvider] = None) -> None:
        super().__init__()
        # Provider 可注入，便于测试与离线演示
        self._provider: WeatherProvider = provider or get_default_provider()
        self._workers: list[QThread] = []  # 持有后台线程引用，防止被 GC

        self.setWindowTitle("天气查询 · Open-Meteo")
        self.resize(560, 520)

        self._build_ui()
        self._update_range_hint()
        self._show_placeholder()

    # ------------------------------------------------------------------ #
    # 界面构建
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # --- 查询条件区 ---
        query_box = QGroupBox("查询条件")
        form = QFormLayout(query_box)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # 城市输入 + 搜索按钮
        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("请输入城市名，例如：北京 / 上海 / 东京")
        self.city_input.returnPressed.connect(self._on_search_city)

        self.search_button = QPushButton("搜索城市")
        self.search_button.clicked.connect(self._on_search_city)

        city_row = QHBoxLayout()
        city_row.addWidget(self.city_input, 1)
        city_row.addWidget(self.search_button)
        city_widget = QWidget()
        city_widget.setLayout(city_row)
        form.addRow("城市：", city_widget)

        # 候选城市下拉框
        self.city_combo = QComboBox()
        self.city_combo.setPlaceholderText("搜索结果将显示在此处")
        self.city_combo.setMinimumWidth(260)
        form.addRow("选择城市：", self.city_combo)

        # 日期选择器
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMinimumDate(QDate(1940, 1, 1))
        self.date_edit.setMaximumDate(QDate.currentDate().addDays(15))
        self.date_edit.dateChanged.connect(self._update_range_hint)
        form.addRow("日期：", self.date_edit)

        # 查询按钮
        self.query_button = QPushButton("查询天气")
        self.query_button.clicked.connect(self._on_query_weather)
        form.addRow("", self.query_button)

        root.addWidget(query_box)

        # --- 结果展示区（卡片） ---
        self.card = QFrame()
        self.card.setObjectName("WeatherCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        header = QHBoxLayout()
        self.icon_label = QLabel("❔")
        self.icon_label.setObjectName("CardIcon")
        header.addWidget(self.icon_label)

        self.title_label = QLabel("暂无数据")
        self.title_label.setObjectName("CardTitle")
        header.addWidget(self.title_label, 1)
        card_layout.addLayout(header)

        self.subtitle_label = QLabel("")
        self.subtitle_label.setWordWrap(True)
        card_layout.addWidget(self.subtitle_label)

        # 字段网格
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(8)
        self._fields: dict[str, QLabel] = {}
        field_defs = [
            ("weather_desc", "天气状况"),
            ("temp_max", "最高气温"),
            ("temp_min", "最低气温"),
            ("humidity", "平均湿度"),
            ("wind_speed", "最大风速"),
            ("precipitation", "降水量"),
            ("source", "数据来源"),
        ]
        for index, (key, label_text) in enumerate(field_defs):
            row, col = divmod(index, 2)
            key_label = QLabel(f"{label_text}：")
            key_label.setObjectName("FieldKey")
            value_label = QLabel(PLACEHOLDER)
            value_label.setObjectName("FieldValue")
            grid.addWidget(key_label, row, col * 2)
            grid.addWidget(value_label, row, col * 2 + 1)
            self._fields[key] = value_label
        card_layout.addLayout(grid)

        root.addWidget(self.card)
        root.addStretch(1)

        # 状态栏
        self.statusBar().showMessage("就绪")

    # ------------------------------------------------------------------ #
    # 辅助方法
    # ------------------------------------------------------------------ #

    def _show_placeholder(self) -> None:
        """恢复为初始占位状态。"""
        self.icon_label.setText("❔")
        self.title_label.setText("暂无数据")
        self.subtitle_label.setText("请先搜索并选择城市，再选择日期后点击“查询天气”。")
        for label in self._fields.values():
            label.setText(PLACEHOLDER)

    def _selected_location(self) -> Optional[Location]:
        """取出下拉框中选中的地点。"""
        data = self.city_combo.currentData()
        if isinstance(data, Location):
            return data
        return None

    def _selected_date(self) -> date:
        """取出日期选择器中的日期（转换为 datetime.date）。"""
        return self.date_edit.date().toPyDate()

    def _update_range_hint(self) -> None:
        """根据当前日期更新范围提示与查询按钮可用性。"""
        target = self._selected_date()
        routing = classify_date(target)
        if routing is DateRange.OUT_OF_RANGE:
            self.statusBar().showMessage("提示：所选日期超出可查询范围。")
        else:
            self.statusBar().showMessage(
                f"当前日期将使用：{'未来预报接口' if routing is DateRange.FORECAST else '历史归档接口'}"
            )

    def _track_worker(self, worker) -> None:
        """登记后台线程，线程结束后自动移除引用。"""
        self._workers.append(worker)

        def _cleanup(w=worker) -> None:
            if w in self._workers:
                self._workers.remove(w)
            w.deleteLater()

        worker.finished.connect(_cleanup)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        """切换忙碌状态（禁用按钮 + 状态栏提示）。"""
        self.search_button.setEnabled(not busy)
        self.query_button.setEnabled(not busy)
        self.city_input.setEnabled(not busy)
        self.city_combo.setEnabled(not busy)
        self.date_edit.setEnabled(not busy)
        if message:
            self.statusBar().showMessage(message)

    # ------------------------------------------------------------------ #
    # 槽函数
    # ------------------------------------------------------------------ #

    def _on_search_city(self) -> None:
        """点击"搜索城市"：后台检索候选地点。"""
        name = self.city_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入要搜索的城市名称。")
            return

        self.city_combo.clear()
        self._set_busy(True, f"正在搜索城市：{name} …")

        worker = SearchCityWorker(self._provider, name, self)
        worker.succeeded.connect(self._on_search_succeeded)
        worker.failed.connect(self._on_search_failed)
        self._track_worker(worker)
        worker.start()

    def _on_search_succeeded(self, locations: list) -> None:
        self._set_busy(False, "搜索完成")
        if not locations:
            QMessageBox.information(
                self, "未找到", "未找到匹配的城市，请尝试更换关键词。"
            )
            return
        for location in locations:
            self.city_combo.addItem(location.display_name(), location)
        self.city_combo.setCurrentIndex(0)
        self.statusBar().showMessage(f"找到 {len(locations)} 个候选城市，请选择后查询。")

    def _on_search_failed(self, message: str) -> None:
        self._set_busy(False, "搜索失败")
        QMessageBox.critical(self, "搜索失败", message)

    def _on_query_weather(self) -> None:
        """点击"查询天气"：后台获取天气数据。"""
        location = self._selected_location()
        if location is None:
            QMessageBox.warning(
                self, "提示", "请先搜索并选择一个城市，再点击“查询天气”。"
            )
            return

        target = self._selected_date()
        if classify_date(target) is DateRange.OUT_OF_RANGE:
            QMessageBox.warning(
                self,
                "日期超出范围",
                "所选日期超出可查询范围（1940 年至今，未来约 16 天）。",
            )
            return

        self._set_busy(True, "正在获取天气数据 …")
        self.title_label.setText("加载中…")
        self.icon_label.setText("⏳")

        worker = FetchWeatherWorker(self._provider, location, target, self)
        worker.succeeded.connect(self._on_weather_succeeded)
        worker.failed.connect(self._on_weather_failed)
        self._track_worker(worker)
        worker.start()

    def _on_weather_succeeded(self, weather: DailyWeather) -> None:
        self._set_busy(False, "查询完成")
        self._render_weather(weather)

    def _on_weather_failed(self, message: str) -> None:
        self._set_busy(False, "查询失败")
        self._show_placeholder()
        QMessageBox.critical(self, "查询失败", message)

    def _render_weather(self, weather: DailyWeather) -> None:
        """把 DailyWeather 渲染到卡片上。"""
        self.icon_label.setText(weather_emoji(weather.weather_code))
        self.title_label.setText(
            f"{weather.date.isoformat()}　{weather.weather_desc}"
        )

        if weather.temp_max is not None and weather.temp_min is not None:
            self.subtitle_label.setText(
                f"气温区间 {weather.temp_min:.1f} ~ {weather.temp_max:.1f} °C"
            )
        else:
            self.subtitle_label.setText("部分数据缺失，已做降级展示。")

        source_text = {
            "forecast": "未来预报接口",
            "archive": "历史归档接口",
            "offline": "离线模拟数据",
        }.get(weather.source, weather.source or PLACEHOLDER)

        self._fields["weather_desc"].setText(weather.weather_desc)
        self._fields["temp_max"].setText(_fmt(weather.temp_max, "°C"))
        self._fields["temp_min"].setText(_fmt(weather.temp_min, "°C"))
        self._fields["humidity"].setText(_fmt(weather.humidity, "%"))
        self._fields["wind_speed"].setText(_fmt(weather.wind_speed, "km/h"))
        self._fields["precipitation"].setText(_fmt(weather.precipitation, "mm"))
        self._fields["source"].setText(source_text)

    # ------------------------------------------------------------------ #
    # 关闭处理
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt 约定方法名
        """关闭窗口时等待后台线程结束，避免残留线程导致崩溃。

        注意：Worker 重写了 ``run()`` 且不运行事件循环，``quit()`` 对其是空操作；
        ``wait(1500)`` 在网络请求（超时 10 秒）未返回时会超时失败，随后
        MainWindow 被销毁而 QThread 仍在运行，Qt 会抛出
        "QThread: Destroyed while thread is still running" 并 abort。
        因此这里改用无参 ``wait()`` 阻塞至请求真正返回。
        """
        for worker in list(self._workers):
            if worker.isRunning():
                worker.wait()  # 阻塞至请求返回（最长约 timeout 秒），避免对象被销毁
        super().closeEvent(event)