import sys
import time
import os
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QPoint, QEasingCurve, QPropertyAnimation, Property, QRect, QSettings
from PySide6.QtGui import QColor, QPainter, QFont, QAction, QIcon, QPixmap, QLinearGradient
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QMenu,
    QDialog, QFormLayout, QSpinBox, QDialogButtonBox, QSystemTrayIcon
)

APP_NAME = "FlipFocus"
ORG_NAME = "OrcaApps"


def make_tray_icon():
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(24, 24, 27))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(6, 6, 52, 52, 13, 13)
    p.setPen(QColor(245, 245, 247))
    p.setFont(QFont("Segoe UI Variable Display", 25, QFont.Bold))
    p.drawText(pix.rect(), Qt.AlignCenter, "F")
    p.end()
    return QIcon(pix)


class FlipCard(QWidget):
    """Split-flap inspired card with a soft physical flip illusion."""
    def __init__(self, value="00", parent=None):
        super().__init__(parent)
        self._value = value
        self._old_value = value
        self._progress = 1.0
        self.setMinimumSize(84, 108)

        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.setDuration(420)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_progress(self):
        return self._progress

    def set_progress(self, value):
        self._progress = float(value)
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

    def _draw_text(self, painter, rect, value, clip=None, opacity=1.0):
        painter.save()
        if clip is not None:
            painter.setClipRect(clip)
        painter.setOpacity(opacity)
        painter.setPen(QColor(247, 247, 249))
        painter.setFont(QFont("Segoe UI Variable Display", 42, QFont.DemiBold))
        painter.drawText(rect, Qt.AlignCenter, value)
        painter.restore()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        r = self.rect().adjusted(2, 2, -2, -2)
        center_y = r.center().y()
        top = QRect(r.left(), r.top(), r.width(), r.height() // 2)
        bottom = QRect(r.left(), center_y, r.width(), r.height() // 2)

        bg = QLinearGradient(r.topLeft(), r.bottomLeft())
        bg.setColorAt(0.0, QColor(35, 35, 38, 250))
        bg.setColorAt(1.0, QColor(20, 20, 22, 250))
        p.setBrush(bg)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 12, 12)

        p.setPen(QColor(255, 255, 255, 16))
        p.drawLine(r.left() + 7, center_y, r.right() - 7, center_y)

        if self._progress >= 0.999:
            self._draw_text(p, r, self._value)
            return

        t = self._progress

        # Lower half already shows incoming value.
        self._draw_text(p, r, self._value, bottom)

        # Old top half folds toward the hinge.
        old_scale = max(0.02, 1.0 - t)
        old_h = max(1, int(top.height() * old_scale))
        old_clip = QRect(top.left(), center_y - old_h, top.width(), old_h)
        self._draw_text(p, r, self._old_value, old_clip, 1.0 - 0.25 * t)

        # Moving flap shadow makes the hinge feel more physical.
        shadow_alpha = int(105 * (1.0 - abs(0.5 - t) * 2.0))
        if shadow_alpha > 0:
            p.fillRect(QRect(r.left() + 4, center_y - 5, r.width() - 8, 10), QColor(0, 0, 0, shadow_alpha))

        # Incoming top half opens after halfway.
        reveal = max(0.0, (t - 0.45) / 0.55)
        if reveal > 0:
            new_h = max(1, int(top.height() * reveal))
            new_clip = QRect(top.left(), center_y - new_h, top.width(), new_h)
            self._draw_text(p, r, self._value, new_clip, 0.72 + 0.28 * reveal)


class StaticCard(QWidget):
    def __init__(self, value="00", parent=None):
        super().__init__(parent)
        self.value = value
        self.setMinimumSize(84, 108)

    def set_value(self, value):
        value = str(value).zfill(2)
        if value != self.value:
            self.value = value
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -2)

        bg = QLinearGradient(r.topLeft(), r.bottomLeft())
        bg.setColorAt(0.0, QColor(35, 35, 38, 250))
        bg.setColorAt(1.0, QColor(20, 20, 22, 250))
        p.setBrush(bg)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 12, 12)

        p.setPen(QColor(255, 255, 255, 16))
        p.drawLine(r.left() + 7, r.center().y(), r.right() - 7, r.center().y())

        p.setFont(QFont("Segoe UI Variable Display", 42, QFont.DemiBold))
        p.setPen(QColor(247, 247, 249))
        p.drawText(r, Qt.AlignCenter, self.value)


class SettingsDialog(QDialog):
    def __init__(self, parent, focus_minutes, short_break_minutes, long_break_minutes):
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

        self.long_break = QSpinBox()
        self.long_break.setRange(1, 90)
        self.long_break.setValue(long_break_minutes)

        layout.addRow("Focus (min)", self.focus)
        layout.addRow("Short break (min)", self.short_break)
        layout.addRow("Long break (min)", self.long_break)

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
        self.compact_mode = self.settings.value("compact_mode", False, type=bool)
        self.show_seconds = self.settings.value("show_seconds", True, type=bool)
        self.use_24h = self.settings.value("use_24h", True, type=bool)
        self.lock_position = self.settings.value("lock_position", False, type=bool)
        self.focus_minutes = int(self.settings.value("focus_minutes", 25))
        self.short_break_minutes = int(self.settings.value("short_break_minutes", 5))
        self.long_break_minutes = int(self.settings.value("long_break_minutes", 15))

        self.drag_position = QPoint()
        self.stopwatch_running = False
        self.stopwatch_elapsed = 0.0
        self.stopwatch_started_at = None

        self.pomodoro_running = False
        self.pomodoro_is_break = False
        self.pomodoro_long_break = False
        self.pomodoro_remaining = self.focus_minutes * 60
        self.pomodoro_last_tick = None
        self.completed_focus_sessions = 0

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(make_tray_icon())
        self._apply_window_flags()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(self.window_opacity)
        self.setMouseTracking(True)

        self.build_ui()
        self.setup_tray()

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

        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(1200)
        self.hover_timer.timeout.connect(self.hide_controls)

        self.apply_compact_mode()
        self.tick()

    def _apply_window_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def build_ui(self):
        self.setStyleSheet("""
            QWidget {
                color: #f5f5f7;
                font-family: "Segoe UI Variable", "Segoe UI";
            }
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(245,245,247,0.58);
                padding: 6px 9px;
                border-radius: 9px;
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

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(14, 12, 14, 12)
        self.root.setSpacing(8)

        self.top_bar = QWidget(self)
        mode_row = QHBoxLayout(self.top_bar)
        mode_row.setContentsMargins(0, 0, 0, 0)
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
        self.close_btn.clicked.connect(self.hide)
        mode_row.addWidget(self.close_btn)

        self.root.addWidget(self.top_bar)

        cards = QHBoxLayout()
        cards.setSpacing(8)
        cards.setContentsMargins(0, 0, 0, 0)

        self.hour_card = FlipCard("00")
        self.minute_card = FlipCard("00")
        self.second_card = StaticCard("00")

        cards.addWidget(self.hour_card, 1)
        cards.addWidget(self.minute_card, 1)
        cards.addWidget(self.second_card, 1)
        self.root.addLayout(cards)

        self.bottom_bar = QWidget(self)
        bottom = QHBoxLayout(self.bottom_bar)
        bottom.setContentsMargins(0, 0, 0, 0)

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

        self.root.addWidget(self.bottom_bar)
        self.update_mode_ui()

    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return

        self.tray = QSystemTrayIcon(make_tray_icon(), self)
        tray_menu = QMenu()

        show_action = QAction("Show FlipFocus", self)
        show_action.triggered.connect(self.show_normal)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)

        self.tray.setContextMenu(tray_menu)
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_normal()

    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def enterEvent(self, event):
        self.show_controls()
        self.hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_timer.start()
        super().leaveEvent(event)

    def show_controls(self):
        if not self.compact_mode:
            self.top_bar.show()
            self.bottom_bar.show()

    def hide_controls(self):
        if not self.compact_mode:
            self.top_bar.hide()
            self.bottom_bar.hide()

    def toggle_compact(self):
        self.compact_mode = not self.compact_mode
        self.settings.setValue("compact_mode", self.compact_mode)
        self.apply_compact_mode()

    def apply_compact_mode(self):
        self.second_card.setVisible((not self.compact_mode) and self.show_seconds)
        self.top_bar.setVisible(not self.compact_mode)
        self.bottom_bar.setVisible(not self.compact_mode)
        self.root.setContentsMargins(8 if self.compact_mode else 14, 8 if self.compact_mode else 12,
                                     8 if self.compact_mode else 14, 8 if self.compact_mode else 12)
        if self.compact_mode:
            self.resize(max(220, self.width() - 110), 126)
        else:
            self.resize(max(380, self.width()), max(180, self.height()))

    def set_mode(self, mode):
        self.mode = mode
        self.settings.setValue("mode", mode)
        self.update_mode_ui()
        self.tick()

    def update_mode_ui(self):
        for btn, name in [
            (self.btn_clock, "clock"),
            (self.btn_stopwatch, "stopwatch"),
            (self.btn_pomodoro, "pomodoro"),
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
            phase = "long break" if self.pomodoro_long_break else ("break" if self.pomodoro_is_break else "focus")
            self.status.setText(f"{phase} · sessions {self.completed_focus_sessions}/4")
            self.start_pause_btn.setText("Pause" if self.pomodoro_running else "Start")

    def tick(self):
        if self.mode == "clock":
            now = datetime.now()
            hour_fmt = "%H" if self.use_24h else "%I"
            self.hour_card.set_value(now.strftime(hour_fmt), animate=True)
            self.minute_card.set_value(now.strftime("%M"), animate=True)
            self.second_card.set_value(now.strftime("%S"))
            return

        if self.mode == "stopwatch":
            elapsed = self.stopwatch_elapsed
            if self.stopwatch_running and self.stopwatch_started_at is not None:
                elapsed += time.perf_counter() - self.stopwatch_started_at

            total = int(elapsed)
            self.hour_card.set_value(total // 3600, animate=True)
            self.minute_card.set_value((total % 3600) // 60, animate=True)
            self.second_card.set_value(total % 60)
            return

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
                    self._advance_pomodoro_phase()
                    self.update_mode_ui()

        total = int(self.pomodoro_remaining)
        self.hour_card.set_value(total // 3600, animate=True)
        self.minute_card.set_value((total % 3600) // 60, animate=True)
        self.second_card.set_value(total % 60)

    def _advance_pomodoro_phase(self):
        if not self.pomodoro_is_break:
            self.completed_focus_sessions += 1
            self.pomodoro_is_break = True
            self.pomodoro_long_break = self.completed_focus_sessions % 4 == 0
            minutes = self.long_break_minutes if self.pomodoro_long_break else self.short_break_minutes
            self.pomodoro_remaining = minutes * 60
        else:
            self.pomodoro_is_break = False
            self.pomodoro_long_break = False
            self.pomodoro_remaining = self.focus_minutes * 60

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
            self.pomodoro_long_break = False
            self.pomodoro_remaining = self.focus_minutes * 60
            self.pomodoro_last_tick = None
            self.completed_focus_sessions = 0

        self.update_mode_ui()
        self.tick()

    def toggle_top(self, checked):
        self.always_on_top = bool(checked)
        self.settings.setValue("always_on_top", self.always_on_top)
        self._apply_window_flags()
        self.show()

    def set_opacity_percent(self, value):
        self.window_opacity = max(0.35, min(1.0, value / 100.0))
        self.setWindowOpacity(self.window_opacity)
        self.settings.setValue("opacity", self.window_opacity)

    def open_pomodoro_settings(self):
        dlg = SettingsDialog(self, self.focus_minutes, self.short_break_minutes, self.long_break_minutes)
        if dlg.exec():
            self.focus_minutes = dlg.focus.value()
            self.short_break_minutes = dlg.short_break.value()
            self.long_break_minutes = dlg.long_break.value()

            self.settings.setValue("focus_minutes", self.focus_minutes)
            self.settings.setValue("short_break_minutes", self.short_break_minutes)
            self.settings.setValue("long_break_minutes", self.long_break_minutes)

            if self.mode == "pomodoro" and not self.pomodoro_running:
                self.pomodoro_is_break = False
                self.pomodoro_long_break = False
                self.pomodoro_remaining = self.focus_minutes * 60

            self.update_mode_ui()
            self.tick()

    def toggle_seconds(self):
        self.show_seconds = not self.show_seconds
        self.settings.setValue("show_seconds", self.show_seconds)
        self.second_card.setVisible((not self.compact_mode) and self.show_seconds)

    def toggle_time_format(self):
        self.use_24h = not self.use_24h
        self.settings.setValue("use_24h", self.use_24h)
        self.tick()

    def toggle_lock_position(self):
        self.lock_position = not self.lock_position
        self.settings.setValue("lock_position", self.lock_position)

    def startup_enabled(self):
        if sys.platform != "win32":
            return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except Exception:
            return False

    def toggle_startup(self):
        if sys.platform != "win32":
            return
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if self.startup_enabled():
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
                else:
                    exe = os.path.abspath(sys.executable)
                    if getattr(sys, "frozen", False):
                        command = f'"{exe}"'
                    else:
                        script = os.path.abspath(sys.argv[0])
                        command = f'"{exe}" "{script}"'
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        except Exception:
            pass

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        top_action = QAction("Always on top", self, checkable=True)
        top_action.setChecked(self.always_on_top)
        top_action.toggled.connect(self.toggle_top)
        menu.addAction(top_action)

        compact_action = QAction("Compact mode", self, checkable=True)
        compact_action.setChecked(self.compact_mode)
        compact_action.triggered.connect(self.toggle_compact)
        menu.addAction(compact_action)

        seconds_action = QAction("Show seconds", self, checkable=True)
        seconds_action.setChecked(self.show_seconds)
        seconds_action.triggered.connect(self.toggle_seconds)
        menu.addAction(seconds_action)

        format_action = QAction("24-hour clock", self, checkable=True)
        format_action.setChecked(self.use_24h)
        format_action.triggered.connect(self.toggle_time_format)
        menu.addAction(format_action)

        lock_action = QAction("Lock position", self, checkable=True)
        lock_action.setChecked(self.lock_position)
        lock_action.triggered.connect(self.toggle_lock_position)
        menu.addAction(lock_action)

        if sys.platform == "win32":
            startup_action = QAction("Start with Windows", self, checkable=True)
            startup_action.setChecked(self.startup_enabled())
            startup_action.triggered.connect(self.toggle_startup)
            menu.addAction(startup_action)

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
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_compact()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        self.show_controls()
        self.hover_timer.start()
        if event.button() == Qt.LeftButton and not self.lock_position:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        self.show_controls()
        self.hover_timer.start()
        if event.buttons() & Qt.LeftButton and not self.lock_position:
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
        if event.key() == Qt.Key_C:
            self.toggle_compact()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("size", self.size())
        self.settings.sync()

        if self.tray is not None and self.tray.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setQuitOnLastWindowClosed(False)

    window = FlipFocus()
    window.show()
    sys.exit(app.exec())
