import sys
import time
from datetime import datetime

from PySide6.QtCore import (
    Qt, QTimer, QPoint, QEasingCurve, QPropertyAnimation,
    Property, QRect, QSettings
)
from PySide6.QtGui import QColor, QPainter, QFont, QAction
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QMenu, QDialog, QFormLayout, QSpinBox,
    QDialogButtonBox
)


APP_NAME = "FlipFocus"
ORG_NAME = "OrcaApps"


class FlipCard(QWidget):
    """Minimal split-flap-like card. Only animates when value changes."""
    def __init__(self, value="00", parent=None):
        super().__init__(parent)
        self._value = value
        self._old_value = value
        self._progress = 1.0
        self.setMinimumSize(92, 116)

        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.setDuration(340)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def get_progress(self):
        return self._progress

    def set_progress(self, p):
        self._progress = float(p)
        self.update()

    progress = Property(float, get_progress, set_progress)

    def set_value(self, value, animate=True):
        value = str(value).zfill(2)
        if value == self._value:
            return
        self._old_value = self._value
        self._value = value
        if animate:
            self._anim.stop()
            self._progress = 0.0
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        else:
            self._progress = 1.0
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        r = self.rect().adjusted(2, 2, -2, -2)
        radius = 12

        p.setBrush(QColor(25, 25, 27, 245))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, radius, radius)

        y = r.center().y()
        p.setPen(QColor(255, 255, 255, 15))
        p.drawLine(r.left() + 7, y, r.right() - 7, y)

        font = QFont("Segoe UI Variable Display", 42, QFont.DemiBold)
        p.setFont(font)
        p.setPen(QColor(245, 245, 247))

        if self._progress >= 0.999:
            p.drawText(r, Qt.AlignCenter, self._value)
            return

        t = self._progress
        old_h = max(1, int(r.height() * 0.5 * (1.0 - t)))
        new_h = max(1, int(r.height() * 0.5 * t))

        bottom = QRect(r.left(), y, r.width(), r.height() // 2)

        p.save()
        p.setClipRect(bottom)
        p.drawText(r, Qt.AlignCenter, self._value)
        p.restore()

        if old_h > 1:
            old_rect = QRect(r.left(), y - old_h, r.width(), old_h)
            p.save()
            p.setClipRect(old_rect)
            p.translate(0, -(r.height()//2 - old_h) * 0.25)
            p.drawText(r, Qt.AlignCenter, self._old_value)
            p.restore()

        if new_h > 1:
            new_rect = QRect(r.left(), y - new_h, r.width(), new_h)
            p.save()
            p.setClipRect(new_rect)
            p.translate(0, (r.height()//2 - new_h) * 0.18)
            p.drawText(r, Qt.AlignCenter, self._value)
            p.restore()


class StaticCard(QWidget):
    """For seconds: same aesthetic, no flip animation."""
    def __init__(self, value="00", parent=None):
        super().__init__(parent)
        self.value = value
        self.setMinimumSize(92, 116)

    def set_value(self, value):
        value = str(value).zfill(2)
        if value != self.value:
            self.value = value
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -2)

        p.setBrush(QColor(25, 25, 27, 245))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 12, 12)

        p.setPen(QColor(255, 255, 255, 15))
        p.drawLine(r.left()+7, r.center().y(), r.right()-7, r.center().y())

        p.setFont(QFont("Segoe UI Variable Display", 42, QFont.DemiBold))
        p.setPen(QColor(245, 245, 247))
        p.drawText(r, Qt.AlignCenter, self.value)


class SettingsDialog(QDialog):
    def __init__(self, parent, focus_minutes, short_break_minutes):
        super().__init__(parent)
        self.setWindowTitle("Pomodoro Settings")
        self.setModal(True)

        layout = QFormLayout(self)

        self.focus = QSpinBox()
        self.focus.setRange(1, 180)
        self.focus.setValue(focus_minutes)

        self.short_break = QSpinBox()
        self.short_break.setRange(1, 60)
        self.short_break.setValue(short_break_minutes)

        layout.addRow("Focus (min)", self.focus)
        layout.addRow("Break (min)", self.short_break)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class FlipFocus(QWidget):
    def __init__(self):
        super().__init__()

        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.mode = self.settings.value("mode", "clock")
        self.always_on_top = self.settings.value("always_on_top", True, type=bool)
        self.window_opacity = float(self.settings.value("opacity", 0.94))
        self.focus_minutes = int(self.settings.value("focus_minutes", 25))
        self.short_break_minutes = int(self.settings.value("short_break_minutes", 5))

        self.drag_position = QPoint()
        self.stopwatch_running = False
        self.stopwatch_elapsed = 0.0
        self.stopwatch_started_at = None

        self.pomodoro_running = False
        self.pomodoro_is_break = False
        self.pomodoro_remaining = self.focus_minutes * 60
        self.pomodoro_last_tick = None

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool |
            (Qt.WindowStaysOnTopHint if self.always_on_top else Qt.Widget)
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(self.window_opacity)

        self.build_ui()

        size = self.settings.value("size")
        pos = self.settings.value("pos")
        if size:
            self.resize(size)
        else:
            self.resize(420, 190)
        if pos:
            self.move(pos)

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

        self.tick()

    def build_ui(self):
        self.setStyleSheet("""
            QWidget {
                color: #f5f5f7;
                font-family: "Segoe UI Variable", "Segoe UI";
            }
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(245,245,247,0.62);
                padding: 7px 10px;
                border-radius: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.07);
                color: rgba(255,255,255,0.95);
            }
            QPushButton[active="true"] {
                background: rgba(255,255,255,0.10);
                color: white;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(3)

        self.btn_clock = QPushButton("Clock")
        self.btn_stopwatch = QPushButton("Stopwatch")
        self.btn_pomodoro = QPushButton("Pomodoro")

        self.btn_clock.clicked.connect(lambda: self.set_mode("clock"))
        self.btn_stopwatch.clicked.connect(lambda: self.set_mode("stopwatch"))
        self.btn_pomodoro.clicked.connect(lambda: self.set_mode("pomodoro"))

        mode_row.addWidget(self.btn_clock)
        mode_row.addWidget(self.btn_stopwatch)
        mode_row.addWidget(self.btn_pomodoro)
        mode_row.addStretch(1)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedWidth(32)
        self.close_btn.clicked.connect(self.close)
        mode_row.addWidget(self.close_btn)

        root.addLayout(mode_row)

        cards = QHBoxLayout()
        cards.setSpacing(8)
        cards.setContentsMargins(0, 0, 0, 0)

        self.hour_card = FlipCard("00")
        self.minute_card = FlipCard("00")
        self.second_card = StaticCard("00")

        cards.addWidget(self.hour_card, 1)
        cards.addWidget(self.minute_card, 1)
        cards.addWidget(self.second_card, 1)

        root.addLayout(cards)

        bottom = QHBoxLayout()
        self.status = QLabel("")
        self.status.setStyleSheet("color: rgba(245,245,247,0.48); font-size: 11px; padding-left: 4px;")

        self.start_pause_btn = QPushButton("Start")
        self.reset_btn = QPushButton("Reset")
        self.start_pause_btn.clicked.connect(self.start_pause)
        self.reset_btn.clicked.connect(self.reset_current)

        bottom.addWidget(self.status)
        bottom.addStretch(1)
        bottom.addWidget(self.start_pause_btn)
        bottom.addWidget(self.reset_btn)

        root.addLayout(bottom)
        self.update_mode_ui()

    def set_mode(self, mode):
        self.mode = mode
        self.settings.setValue("mode", mode)
        self.update_mode_ui()
        self.tick()

    def update_mode_ui(self):
        for btn, name in [
            (self.btn_clock, "clock"),
            (self.btn_stopwatch, "stopwatch"),
            (self.btn_pomodoro, "pomodoro")
        ]:
            btn.setProperty("active", self.mode == name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        interactive = self.mode != "clock"
        self.start_pause_btn.setVisible(interactive)
        self.reset_btn.setVisible(interactive)

        if self.mode == "clock":
            self.status.setText("local time")
        elif self.mode == "stopwatch":
            self.status.setText("space · start/pause   r · reset")
            self.start_pause_btn.setText("Pause" if self.stopwatch_running else "Start")
        else:
            label = "break" if self.pomodoro_is_break else "focus"
            self.status.setText(
                f"{label} · {self.short_break_minutes if self.pomodoro_is_break else self.focus_minutes} min"
            )
            self.start_pause_btn.setText("Pause" if self.pomodoro_running else "Start")

    def tick(self):
        if self.mode == "clock":
            now = datetime.now()
            self.hour_card.set_value(now.strftime("%H"), animate=True)
            self.minute_card.set_value(now.strftime("%M"), animate=True)
            self.second_card.set_value(now.strftime("%S"))
            return

        if self.mode == "stopwatch":
            elapsed = self.stopwatch_elapsed
            if self.stopwatch_running and self.stopwatch_started_at is not None:
                elapsed += time.perf_counter() - self.stopwatch_started_at

            total = int(elapsed)
            h = total // 3600
            m = (total % 3600) // 60
            s = total % 60
            self.hour_card.set_value(h, animate=True)
            self.minute_card.set_value(m, animate=True)
            self.second_card.set_value(s)
            return

        if self.mode == "pomodoro":
            if self.pomodoro_running and self.pomodoro_last_tick is not None:
                now = time.perf_counter()
                delta = now - self.pomodoro_last_tick
                if delta >= 1.0:
                    dec = int(delta)
                    self.pomodoro_remaining = max(0, self.pomodoro_remaining - dec)
                    self.pomodoro_last_tick += dec

                    if self.pomodoro_remaining <= 0:
                        QApplication.beep()
                        self.pomodoro_running = False
                        self.pomodoro_is_break = not self.pomodoro_is_break
                        self.pomodoro_remaining = (
                            self.short_break_minutes * 60
                            if self.pomodoro_is_break
                            else self.focus_minutes * 60
                        )
                        self.update_mode_ui()

            total = int(self.pomodoro_remaining)
            h = total // 3600
            m = (total % 3600) // 60
            s = total % 60
            self.hour_card.set_value(h, animate=True)
            self.minute_card.set_value(m, animate=True)
            self.second_card.set_value(s)

    def start_pause(self):
        if self.mode == "stopwatch":
            if not self.stopwatch_running:
                self.stopwatch_running = True
                self.stopwatch_started_at = time.perf_counter()
            else:
                self.stopwatch_elapsed += time.perf_counter() - self.stopwatch_started_at
                self.stopwatch_running = False
                self.stopwatch_started_at = None

        elif self.mode == "pomodoro":
            self.pomodoro_running = not self.pomodoro_running
            self.pomodoro_last_tick = time.perf_counter() if self.pomodoro_running else None

        self.update_mode_ui()

    def reset_current(self):
        if self.mode == "stopwatch":
            self.stopwatch_running = False
            self.stopwatch_elapsed = 0.0
            self.stopwatch_started_at = None

        elif self.mode == "pomodoro":
            self.pomodoro_running = False
            self.pomodoro_is_break = False
            self.pomodoro_remaining = self.focus_minutes * 60
            self.pomodoro_last_tick = None

        self.update_mode_ui()
        self.tick()

    def toggle_top(self, checked):
        self.always_on_top = bool(checked)
        self.settings.setValue("always_on_top", self.always_on_top)
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def set_opacity_percent(self, value):
        self.window_opacity = max(0.35, min(1.0, value / 100.0))
        self.setWindowOpacity(self.window_opacity)
        self.settings.setValue("opacity", self.window_opacity)

    def open_pomodoro_settings(self):
        dlg = SettingsDialog(self, self.focus_minutes, self.short_break_minutes)
        if dlg.exec():
            self.focus_minutes = dlg.focus.value()
            self.short_break_minutes = dlg.short_break.value()
            self.settings.setValue("focus_minutes", self.focus_minutes)
            self.settings.setValue("short_break_minutes", self.short_break_minutes)

            if self.mode == "pomodoro" and not self.pomodoro_running:
                self.pomodoro_is_break = False
                self.pomodoro_remaining = self.focus_minutes * 60
            self.update_mode_ui()
            self.tick()

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        top_action = QAction("Always on top", self, checkable=True)
        top_action.setChecked(self.always_on_top)
        top_action.toggled.connect(self.toggle_top)
        menu.addAction(top_action)

        opacity_menu = menu.addMenu("Opacity")
        for pct in (100, 90, 80, 70, 60, 50):
            action = QAction(f"{pct}%", self)
            action.triggered.connect(lambda _, v=pct: self.set_opacity_percent(v))
            opacity_menu.addAction(action)

        menu.addSeparator()

        pomo_settings = QAction("Pomodoro settings…", self)
        pomo_settings.triggered.connect(self.open_pomodoro_settings)
        menu.addAction(pomo_settings)

        menu.addSeparator()

        reset_size = QAction("Reset size", self)
        reset_size.triggered.connect(lambda: self.resize(420, 190))
        menu.addAction(reset_size)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and self.mode != "clock":
            self.start_pause()
            event.accept()
            return
        if event.key() == Qt.Key_R and self.mode != "clock":
            self.reset_current()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("size", self.size())
        self.settings.sync()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)

    window = FlipFocus()
    window.show()
    sys.exit(app.exec())
