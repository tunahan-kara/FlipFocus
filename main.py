import os
import sys
import time
from datetime import datetime

from PySide6.QtCore import (
    Qt, QTimer, QPoint, QEasingCurve, QPropertyAnimation,
    Property, QRect, QSettings, QSize
)
from PySide6.QtGui import (
    QAction, QColor, QFont, QIcon, QLinearGradient,
    QPainter, QPen, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QMenu, QPushButton, QSpinBox,
    QSystemTrayIcon, QVBoxLayout, QWidget
)

APP_NAME = "FlipFocus"
APP_VERSION = "1.0.0"
ORG_NAME = "OrcaApps"

TR = {
    "clock": "Saat",
    "stopwatch": "Kronometre",
    "pomodoro": "Pomodoro",
    "local_time": "yerel saat",
    "start": "Başlat",
    "pause": "Duraklat",
    "reset": "Sıfırla",
    "focus": "odak",
    "break": "mola",
    "long_break": "uzun mola",
    "always_on_top": "Her zaman üstte",
    "lock_position": "Konumu kilitle",
    "compact_mode": "Kompakt mod",
    "show_seconds": "Saniyeyi göster",
    "clock_24h": "24 saat biçimi",
    "start_windows": "Windows ile başlat",
    "opacity": "Saydamlık",
    "pomodoro_settings": "Pomodoro ayarları…",
    "reset_size": "Boyutu sıfırla",
    "quit": "Çıkış",
    "show": "FlipFocus'u göster",
    "language": "Dil",
    "english": "English",
    "turkish": "Türkçe",
    "hide_to_tray": "Sistem tepsisine gizle",
    "close_to_tray": "Çarpıya basınca arka planda çalıştır",
    "pomodoro_done": "Odak süresi tamamlandı",
    "break_done": "Mola tamamlandı",
    "focus_min": "Odak (dk)",
    "short_break_min": "Kısa mola (dk)",
    "long_break_min": "Uzun mola (dk)",
    "long_break_after": "Uzun mola turu",
    "space_hint": "boşluk · başlat/duraklat   r · sıfırla",
}

EN = {
    "clock": "Clock",
    "stopwatch": "Stopwatch",
    "pomodoro": "Pomodoro",
    "local_time": "local time",
    "start": "Start",
    "pause": "Pause",
    "reset": "Reset",
    "focus": "focus",
    "break": "break",
    "long_break": "long break",
    "always_on_top": "Always on top",
    "lock_position": "Lock position",
    "compact_mode": "Compact mode",
    "show_seconds": "Show seconds",
    "clock_24h": "24-hour clock",
    "start_windows": "Start with Windows",
    "opacity": "Opacity",
    "pomodoro_settings": "Pomodoro settings…",
    "reset_size": "Reset size",
    "quit": "Quit",
    "show": "Show FlipFocus",
    "language": "Language",
    "english": "English",
    "turkish": "Türkçe",
    "hide_to_tray": "Hide to tray",
    "close_to_tray": "Keep running in tray when closed",
    "pomodoro_done": "Focus session complete",
    "break_done": "Break complete",
    "focus_min": "Focus (min)",
    "short_break_min": "Short break (min)",
    "long_break_min": "Long break (min)",
    "long_break_after": "Long break after",
    "space_hint": "space · start/pause   r · reset",
}


def app_icon() -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    bg = QLinearGradient(8, 8, 56, 56)
    bg.setColorAt(0.0, QColor(46, 46, 51))
    bg.setColorAt(1.0, QColor(18, 18, 21))
    p.setBrush(bg)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(6, 6, 52, 52, 14, 14)

    p.setPen(QColor(248, 248, 250))
    p.setFont(QFont("Segoe UI Variable Display", 25, QFont.Bold))
    p.drawText(pix.rect(), Qt.AlignCenter, "F")
    p.end()
    return QIcon(pix)



class ResizeHandle(QWidget):
    """Visible bottom-right resize grip with its own mouse handling."""

    def __init__(self, parent):
        super().__init__(parent)
        self.host = parent
        self.dragging = False
        self.start_global = QPoint()
        self.start_size = QSize()
        self.setFixedSize(28, 28)
        self.setCursor(Qt.SizeFDiagCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.hide()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(247, 247, 249, 170), 1.8))
        p.drawLine(7, 21, 21, 7)
        p.drawLine(12, 21, 21, 12)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.host.lock_position:
            self.dragging = True
            self.start_global = event.globalPosition().toPoint()
            self.start_size = self.host.size()
            self.grabMouse()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.dragging:
            return
        delta = event.globalPosition().toPoint() - self.start_global
        new_w = max(
            self.host.MIN_SIZE.width(),
            min(self.host.MAX_SIZE.width(), self.start_size.width() + delta.x()),
        )
        new_h = max(
            self.host.MIN_SIZE.height(),
            min(self.host.MAX_SIZE.height(), self.start_size.height() + delta.y()),
        )
        self.host.resize(new_w, new_h)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self.dragging and event.button() == Qt.LeftButton:
            self.dragging = False
            self.releaseMouse()
            self.host.settings.setValue("window_size", self.host.size())
            self.host.hide_timer.start()
            event.accept()

class DigitCard(QWidget):
    """Split-flap digit with a downward calendar-style page drop."""

    def __init__(self, value="0", parent=None):
        super().__init__(parent)
        self._value = str(value)[-1:]
        self._old_value = self._value
        self._progress = 1.0

        self.setMinimumSize(58, 88)
        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.setDuration(460)
        self._anim.setEasingCurve(QEasingCurve.Linear)

    def sizeHint(self):
        return QSize(78, 122)

    def get_progress(self):
        return self._progress

    def set_progress(self, value):
        self._progress = float(value)
        self.update()

    progress = Property(float, get_progress, set_progress)

    def set_value(self, value, animate=True):
        value = str(value)[-1:]
        if value == self._value:
            return

        self._old_value = self._value
        self._value = value
        self._anim.stop()

        if animate:
            self._progress = 0.0
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        else:
            self._progress = 1.0
            self.update()

    @staticmethod
    def _ease_in_cubic(t):
        return t * t * t

    @staticmethod
    def _ease_out_cubic(t):
        return 1 - (1 - t) ** 3

    @staticmethod
    def _draw_digit(painter, rect, digit, clip=None, opacity=1.0, y_offset=0):
        painter.save()
        painter.setOpacity(opacity)
        if clip is not None:
            painter.setClipRect(clip)
        painter.translate(0, y_offset)

        painter.setPen(QColor(247, 247, 249))
        font = QFont(
            "Segoe UI Variable Display",
            max(26, int(rect.height() * 0.47)),
            QFont.DemiBold,
        )
        font.setLetterSpacing(QFont.AbsoluteSpacing, -1.0)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, digit)
        painter.restore()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        r = self.rect().adjusted(2, 2, -2, -2)
        mid = r.center().y()
        top = QRect(r.left(), r.top(), r.width(), mid - r.top())
        bottom = QRect(r.left(), mid, r.width(), r.bottom() - mid + 1)

        body = QLinearGradient(r.topLeft(), r.bottomLeft())
        body.setColorAt(0.0, QColor(43, 43, 47, 252))
        body.setColorAt(0.48, QColor(30, 30, 33, 252))
        body.setColorAt(1.0, QColor(19, 19, 22, 252))
        p.setBrush(body)
        p.setPen(QPen(QColor(255, 255, 255, 12), 1))
        p.drawRoundedRect(r, 12, 12)

        p.setPen(QPen(QColor(255, 255, 255, 9), 1))
        p.drawRoundedRect(r.adjusted(2, 2, -2, -2), 10, 10)

        if self._progress >= 0.999:
            self._draw_digit(p, r, self._value)
        else:
            t = self._progress

            # Real flip-clock logic:
            # new top waits behind, old bottom remains visible,
            # old top falls to hinge, then new bottom page drops down.
            self._draw_digit(p, r, self._value, top)
            self._draw_digit(p, r, self._old_value, bottom)

            if t < 0.48:
                phase = self._ease_in_cubic(t / 0.48)
                h = max(1, int(top.height() * (1.0 - phase)))
                moving = QRect(top.left(), mid - h, top.width(), h)

                self._draw_digit(
                    p, r, self._old_value, moving,
                    opacity=1.0 - 0.15 * phase,
                    y_offset=int(phase * 3),
                )

                shade = int(135 * phase)
                if shade:
                    p.fillRect(moving, QColor(0, 0, 0, shade))

                # Cast shadow under the falling page.
                shadow_h = max(2, int(8 + 12 * phase))
                p.fillRect(
                    QRect(r.left() + 5, mid, r.width() - 10, shadow_h),
                    QColor(0, 0, 0, int(70 + 85 * phase)),
                )

            else:
                phase = self._ease_out_cubic((t - 0.48) / 0.52)
                h = max(1, int(bottom.height() * phase))
                moving = QRect(bottom.left(), mid, bottom.width(), h)

                # New page physically unfolds DOWN from the hinge.
                self._draw_digit(
                    p, r, self._value, moving,
                    opacity=0.72 + 0.28 * phase,
                    y_offset=int((1.0 - phase) * -3),
                )

                shade = int(135 * (1.0 - phase))
                if shade:
                    p.fillRect(moving, QColor(0, 0, 0, shade))

                shadow_h = max(2, int(18 * (1.0 - phase)))
                if shadow_h > 2:
                    p.fillRect(
                        QRect(r.left() + 5, mid + h - shadow_h, r.width() - 10, shadow_h),
                        QColor(0, 0, 0, int(105 * (1.0 - phase))),
                    )

        p.setPen(QPen(QColor(5, 5, 6, 185), 2))
        p.drawLine(r.left() + 5, mid, r.right() - 5, mid)
        p.setPen(QPen(QColor(255, 255, 255, 14), 1))
        p.drawLine(r.left() + 7, mid + 1, r.right() - 7, mid + 1)

        p.setBrush(QColor(8, 8, 10, 210))
        p.setPen(Qt.NoPen)
        p.drawEllipse(r.left() + 5, mid - 2, 4, 4)
        p.drawEllipse(r.right() - 9, mid - 2, 4, 4)


class TimeDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = [DigitCard("0", self) for _ in range(4)]

        self.seconds = QLabel("00", self)
        self.seconds.setAlignment(Qt.AlignCenter)
        self.seconds.setFixedSize(46, 32)
        self.seconds.setStyleSheet(
            """
            QLabel {
                color: rgba(247,247,249,0.72);
                background: rgba(255,255,255,0.055);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
                font-family: "Segoe UI Variable";
                font-size: 14px;
                font-weight: 600;
            }
            """
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(self.cards[0], 1)
        row.addWidget(self.cards[1], 1)
        row.addSpacing(5)
        row.addWidget(self.cards[2], 1)
        row.addWidget(self.cards[3], 1)
        row.addSpacing(2)
        row.addWidget(self.seconds, 0, Qt.AlignVCenter)

    def set_time(self, hour, minute, second, animate=True):
        value = str(hour).zfill(2)[-2:] + str(minute).zfill(2)[-2:]
        for index, digit in enumerate(value):
            self.cards[index].set_value(digit, animate=animate)
        self.seconds.setText(str(second).zfill(2)[-2:])

    def set_seconds_visible(self, visible):
        self.seconds.setVisible(visible)


class SettingsDialog(QDialog):
    def __init__(self, parent, focus, short_break, long_break, rounds, lang):
        super().__init__(parent)
        self.lang = lang
        self.texts = TR if lang == "tr" else EN
        self.setWindowTitle(self.texts["pomodoro_settings"].replace("…", ""))
        self.setModal(True)
        self.setMinimumWidth(310)

        self.setStyleSheet(
            """
            QDialog { background: #171719; color: #f5f5f7; }
            QLabel { color: rgba(245,245,247,0.78); }
            QSpinBox {
                min-height: 28px;
                background: #222225;
                color: #f5f5f7;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 7px;
                padding: 2px 7px;
            }
            QPushButton { min-height: 28px; padding: 0 12px; }
            """
        )

        form = QFormLayout(self)
        form.setSpacing(10)

        self.focus = QSpinBox()
        self.focus.setRange(1, 180)
        self.focus.setValue(focus)

        self.short_break = QSpinBox()
        self.short_break.setRange(1, 60)
        self.short_break.setValue(short_break)

        self.long_break = QSpinBox()
        self.long_break.setRange(1, 90)
        self.long_break.setValue(long_break)

        self.rounds = QSpinBox()
        self.rounds.setRange(2, 12)
        self.rounds.setValue(rounds)

        form.addRow(self.texts["focus_min"], self.focus)
        form.addRow(self.texts["short_break_min"], self.short_break)
        form.addRow(self.texts["long_break_min"], self.long_break)
        form.addRow(self.texts["long_break_after"], self.rounds)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class FlipFocus(QWidget):
    NORMAL_SIZE = QSize(432, 212)
    CLEAN_SIZE = QSize(432, 148)
    COMPACT_SIZE = QSize(326, 136)
    MIN_SIZE = QSize(280, 124)
    MAX_SIZE = QSize(760, 360)
    RESIZE_MARGIN = 20

    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG_NAME, APP_NAME)

        self.language = self.settings.value("language", "tr")
        self.mode = self.settings.value("mode", "clock")
        self.always_on_top = self.settings.value("always_on_top", True, type=bool)
        self.window_opacity = float(self.settings.value("opacity", 0.96))
        self.compact_mode = self.settings.value("compact_mode", False, type=bool)
        self.show_seconds = self.settings.value("show_seconds", True, type=bool)
        self.use_24h = self.settings.value("use_24h", True, type=bool)
        self.lock_position = self.settings.value("lock_position", False, type=bool)
        self.close_to_tray = self.settings.value("close_to_tray", False, type=bool)

        self.focus_minutes = int(self.settings.value("focus_minutes", 25))
        self.short_break_minutes = int(self.settings.value("short_break_minutes", 5))
        self.long_break_minutes = int(self.settings.value("long_break_minutes", 15))
        self.rounds_before_long_break = int(self.settings.value("rounds_before_long_break", 4))

        self.drag_position = QPoint()
        self.controls_visible = True
        self.force_quit = False

        self.resize_hot = False
        self.resizing = False
        self.resize_start_global = QPoint()
        self.resize_start_size = QSize()
        saved_normal_size = self.settings.value("normal_window_size")
        self.normal_window_size = saved_normal_size if saved_normal_size else self.NORMAL_SIZE

        self.stopwatch_running = False
        self.stopwatch_elapsed = 0.0
        self.stopwatch_started_at = None

        self.pomodoro_running = False
        self.pomodoro_is_break = False
        self.pomodoro_long_break = False
        self.pomodoro_remaining = self.focus_minutes * 60
        self.pomodoro_last_tick = None
        self.completed_focus_sessions = 0

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(app_icon())
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(self.window_opacity)
        self.setMouseTracking(True)
        self.setMinimumSize(self.MIN_SIZE)
        self.setMaximumSize(self.MAX_SIZE)
        self._apply_window_flags()

        self._build_ui()

        self.resize_handle = ResizeHandle(self)
        self._position_resize_handle()

        self._setup_tray()

        pos = self.settings.value("pos")
        saved_size = self.settings.value("window_size")
        if saved_size and not self.compact_mode:
            self.normal_window_size = saved_size
            self.resize(saved_size)
        if pos:
            self.move(pos)

        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(250)
        self.tick_timer.timeout.connect(self.tick)
        self.tick_timer.start()

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(1400)
        self.hide_timer.timeout.connect(self.hide_controls)

        self._apply_compact_mode(initial=True)
        self.apply_language()
        self.tick(first=True)
        self.hide_timer.start()

    @property
    def t(self):
        return TR if self.language == "tr" else EN

    def _apply_window_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _build_ui(self):
        self.setStyleSheet(
            """
            QWidget {
                color: #f5f5f7;
                font-family: "Segoe UI Variable", "Segoe UI";
            }
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(245,245,247,0.58);
                padding: 6px 10px;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.075);
                color: rgba(255,255,255,0.96);
            }
            QPushButton[active="true"] {
                background: rgba(255,255,255,0.105);
                color: white;
            }
            """
        )

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(12, 10, 12, 10)
        self.root.setSpacing(8)

        self.top_bar = QWidget(self)
        top = QHBoxLayout(self.top_bar)
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(2)

        self.btn_clock = QPushButton()
        self.btn_stopwatch = QPushButton()
        self.btn_pomodoro = QPushButton()

        self.btn_clock.clicked.connect(lambda: self.set_mode("clock"))
        self.btn_stopwatch.clicked.connect(lambda: self.set_mode("stopwatch"))
        self.btn_pomodoro.clicked.connect(lambda: self.set_mode("pomodoro"))

        top.addWidget(self.btn_clock)
        top.addWidget(self.btn_stopwatch)
        top.addWidget(self.btn_pomodoro)
        top.addStretch(1)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(30, 28)
        self.close_btn.clicked.connect(self.handle_close_button)
        top.addWidget(self.close_btn)
        self.root.addWidget(self.top_bar)

        self.display = TimeDisplay(self)
        self.root.addWidget(self.display, 1)

        self.bottom_bar = QWidget(self)
        bottom = QHBoxLayout(self.bottom_bar)
        bottom.setContentsMargins(2, 0, 2, 0)
        bottom.setSpacing(3)

        self.status = QLabel("")
        self.status.setStyleSheet(
            "color: rgba(245,245,247,0.42); font-size: 11px; padding-left: 2px;"
        )
        self.start_pause_btn = QPushButton()
        self.reset_btn = QPushButton()
        self.start_pause_btn.clicked.connect(self.start_pause)
        self.reset_btn.clicked.connect(self.reset_current)

        bottom.addWidget(self.status)
        bottom.addStretch(1)
        bottom.addWidget(self.start_pause_btn)
        bottom.addWidget(self.reset_btn)
        self.root.addWidget(self.bottom_bar)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return

        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(f"{APP_NAME} {APP_VERSION}")
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()
        self.rebuild_tray_menu()

    def rebuild_tray_menu(self):
        if not self.tray:
            return

        menu = QMenu()
        show_action = QAction(self.t["show"], self)
        show_action.triggered.connect(self.show_normal)
        menu.addAction(show_action)
        menu.addSeparator()

        quit_action = QAction(self.t["quit"], self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)

    def apply_language(self):
        self.btn_clock.setText(self.t["clock"])
        self.btn_stopwatch.setText(self.t["stopwatch"])
        self.btn_pomodoro.setText(self.t["pomodoro"])
        self.close_btn.setToolTip(
            self.t["hide_to_tray"] if self.close_to_tray else self.t["quit"]
        )
        self.reset_btn.setText(self.t["reset"])
        self.rebuild_tray_menu()
        self.update_mode_ui()

    def set_language(self, lang):
        if lang not in ("tr", "en"):
            return
        self.language = lang
        self.settings.setValue("language", lang)
        self.apply_language()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_normal()

    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.show_controls()

    def handle_close_button(self):
        if self.close_to_tray and self.tray is not None:
            self.hide()
        else:
            self.quit_app()

    def quit_app(self):
        self.force_quit = True
        self._save_window_state()
        if self.tray:
            self.tray.hide()
        QApplication.quit()

    def toggle_close_to_tray(self):
        self.close_to_tray = not self.close_to_tray
        self.settings.setValue("close_to_tray", self.close_to_tray)
        self.close_btn.setToolTip(
            self.t["hide_to_tray"] if self.close_to_tray else self.t["quit"]
        )

    def enterEvent(self, event):
        self.show_controls()
        self._show_resize_handle()
        self.hide_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.resizing and not self.resize_handle.dragging:
            self.resize_hot = False
            self.setCursor(Qt.ArrowCursor)
            self.resize_handle.hide()
            self.update()
            self.hide_timer.start()
        super().leaveEvent(event)

    def _position_resize_handle(self):
        if hasattr(self, "resize_handle"):
            self.resize_handle.move(
                self.width() - self.resize_handle.width() - 3,
                self.height() - self.resize_handle.height() - 3,
            )
            self.resize_handle.raise_()

    def _show_resize_handle(self):
        if not hasattr(self, "resize_handle"):
            return
        self._position_resize_handle()
        if not self.lock_position:
            self.resize_handle.show()
            self.resize_handle.raise_()

    def resizeEvent(self, event):
        self._position_resize_handle()
        super().resizeEvent(event)

    def show_controls(self):
        if self.compact_mode:
            self._show_resize_handle()
            return
        if not self.controls_visible:
            self.controls_visible = True
            self.top_bar.show()
            self.bottom_bar.show()

    def hide_controls(self):
        if self.compact_mode or self.resizing:
            return
        self.controls_visible = False
        self.top_bar.hide()
        self.bottom_bar.hide()
        self.update()

    def toggle_compact(self):
        if not self.compact_mode:
            self.normal_window_size = self.size()
            self.settings.setValue("normal_window_size", self.normal_window_size)
        self.compact_mode = not self.compact_mode
        self.settings.setValue("compact_mode", self.compact_mode)
        self._apply_compact_mode()

    def _apply_compact_mode(self, initial=False):
        if self.compact_mode:
            self.controls_visible = False
            self.top_bar.hide()
            self.bottom_bar.hide()
            self.display.set_seconds_visible(False)
            self.root.setContentsMargins(8, 8, 8, 8)
            self.resize(self.COMPACT_SIZE)
        else:
            self.controls_visible = True
            self.top_bar.show()
            self.bottom_bar.show()
            self.display.set_seconds_visible(self.show_seconds)
            self.root.setContentsMargins(12, 10, 12, 10)
            if initial:
                saved_size = self.settings.value("normal_window_size")
                self.normal_window_size = saved_size if saved_size else self.normal_window_size
                self.resize(self.normal_window_size)
            else:
                self.resize(self.normal_window_size)
            self.hide_timer.start()

    def set_mode(self, mode):
        self.mode = mode
        self.settings.setValue("mode", mode)
        self.update_mode_ui()
        self.tick(first=True)
        self.hide_timer.start()

    def update_mode_ui(self):
        for button, name in (
            (self.btn_clock, "clock"),
            (self.btn_stopwatch, "stopwatch"),
            (self.btn_pomodoro, "pomodoro"),
        ):
            button.setProperty("active", self.mode == name)
            button.style().unpolish(button)
            button.style().polish(button)

        interactive = self.mode != "clock"
        self.start_pause_btn.setVisible(interactive)
        self.reset_btn.setVisible(interactive)

        if self.mode == "clock":
            self.status.setText(self.t["local_time"])
        elif self.mode == "stopwatch":
            self.status.setText(self.t["space_hint"])
            self.start_pause_btn.setText(
                self.t["pause"] if self.stopwatch_running else self.t["start"]
            )
        else:
            if self.pomodoro_long_break:
                phase = self.t["long_break"]
            elif self.pomodoro_is_break:
                phase = self.t["break"]
            else:
                phase = self.t["focus"]

            completed = self.completed_focus_sessions % self.rounds_before_long_break
            self.status.setText(f"{phase} · {completed}/{self.rounds_before_long_break}")
            self.start_pause_btn.setText(
                self.t["pause"] if self.pomodoro_running else self.t["start"]
            )

    def tick(self, first=False):
        if self.mode == "clock":
            now = datetime.now()
            hour = now.strftime("%H" if self.use_24h else "%I")
            self.display.set_time(
                hour, now.strftime("%M"), now.strftime("%S"), animate=not first
            )
            return

        if self.mode == "stopwatch":
            elapsed = self.stopwatch_elapsed
            if self.stopwatch_running and self.stopwatch_started_at is not None:
                elapsed += time.perf_counter() - self.stopwatch_started_at

            total = int(elapsed)
            self.display.set_time(
                total // 3600,
                (total % 3600) // 60,
                total % 60,
                animate=not first,
            )
            return

        if self.pomodoro_running and self.pomodoro_last_tick is not None:
            now = time.perf_counter()
            delta = now - self.pomodoro_last_tick
            if delta >= 1.0:
                decrement = int(delta)
                self.pomodoro_remaining = max(0, self.pomodoro_remaining - decrement)
                self.pomodoro_last_tick += decrement

                if self.pomodoro_remaining <= 0:
                    QApplication.beep()
                    completed_was_break = self.pomodoro_is_break
                    self.pomodoro_running = False
                    self._advance_pomodoro_phase()
                    if self.tray is not None:
                        title = APP_NAME
                        message = (
                            self.t["break_done"]
                            if completed_was_break
                            else self.t["pomodoro_done"]
                        )
                        self.tray.showMessage(title, message, app_icon(), 3500)
                    self.update_mode_ui()

        total = int(self.pomodoro_remaining)
        self.display.set_time(
            total // 3600,
            (total % 3600) // 60,
            total % 60,
            animate=not first,
        )

    def _advance_pomodoro_phase(self):
        if not self.pomodoro_is_break:
            self.completed_focus_sessions += 1
            self.pomodoro_is_break = True
            self.pomodoro_long_break = (
                self.completed_focus_sessions % self.rounds_before_long_break == 0
            )
            duration = (
                self.long_break_minutes
                if self.pomodoro_long_break
                else self.short_break_minutes
            )
            self.pomodoro_remaining = duration * 60
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
                self.stopwatch_started_at = None
                self.stopwatch_running = False

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
        self.tick(first=True)

    def toggle_top(self, checked):
        self.always_on_top = bool(checked)
        self.settings.setValue("always_on_top", self.always_on_top)
        pos = self.pos()
        self._apply_window_flags()
        self.show()
        self.move(pos)

    def set_opacity_percent(self, value):
        self.window_opacity = max(0.45, min(1.0, value / 100.0))
        self.settings.setValue("opacity", self.window_opacity)
        self.setWindowOpacity(self.window_opacity)

    def toggle_seconds(self):
        self.show_seconds = not self.show_seconds
        self.settings.setValue("show_seconds", self.show_seconds)
        if not self.compact_mode:
            self.display.set_seconds_visible(self.show_seconds)

    def toggle_time_format(self):
        self.use_24h = not self.use_24h
        self.settings.setValue("use_24h", self.use_24h)
        self.tick(first=True)

    def toggle_lock_position(self):
        self.lock_position = not self.lock_position
        self.settings.setValue("lock_position", self.lock_position)
        if self.lock_position:
            self.resize_handle.hide()
        else:
            self._show_resize_handle()

    def startup_enabled(self):
        if sys.platform != "win32":
            return False
        try:
            import winreg
            path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except Exception:
            return False

    def toggle_startup(self):
        if sys.platform != "win32":
            return
        try:
            import winreg
            path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
                if self.startup_enabled():
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
                else:
                    executable = os.path.abspath(sys.executable)
                    if getattr(sys, "frozen", False):
                        command = f'"{executable}"'
                    else:
                        script = os.path.abspath(sys.argv[0])
                        command = f'"{executable}" "{script}"'
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        except Exception:
            QApplication.beep()

    def open_pomodoro_settings(self):
        dialog = SettingsDialog(
            self,
            self.focus_minutes,
            self.short_break_minutes,
            self.long_break_minutes,
            self.rounds_before_long_break,
            self.language,
        )

        if dialog.exec():
            self.focus_minutes = dialog.focus.value()
            self.short_break_minutes = dialog.short_break.value()
            self.long_break_minutes = dialog.long_break.value()
            self.rounds_before_long_break = dialog.rounds.value()

            self.settings.setValue("focus_minutes", self.focus_minutes)
            self.settings.setValue("short_break_minutes", self.short_break_minutes)
            self.settings.setValue("long_break_minutes", self.long_break_minutes)
            self.settings.setValue("rounds_before_long_break", self.rounds_before_long_break)

            if self.mode == "pomodoro" and not self.pomodoro_running:
                self.pomodoro_is_break = False
                self.pomodoro_long_break = False
                self.pomodoro_remaining = self.focus_minutes * 60
                self.completed_focus_sessions = 0

            self.update_mode_ui()
            self.tick(first=True)

    def contextMenuEvent(self, event):
        self.show_controls()
        menu = QMenu(self)

        top_action = QAction(self.t["always_on_top"], self, checkable=True)
        top_action.setChecked(self.always_on_top)
        top_action.toggled.connect(self.toggle_top)
        menu.addAction(top_action)

        lock_action = QAction(self.t["lock_position"], self, checkable=True)
        lock_action.setChecked(self.lock_position)
        lock_action.triggered.connect(self.toggle_lock_position)
        menu.addAction(lock_action)

        compact_action = QAction(self.t["compact_mode"], self, checkable=True)
        compact_action.setChecked(self.compact_mode)
        compact_action.triggered.connect(self.toggle_compact)
        menu.addAction(compact_action)

        seconds_action = QAction(self.t["show_seconds"], self, checkable=True)
        seconds_action.setChecked(self.show_seconds)
        seconds_action.setEnabled(not self.compact_mode)
        seconds_action.triggered.connect(self.toggle_seconds)
        menu.addAction(seconds_action)

        format_action = QAction(self.t["clock_24h"], self, checkable=True)
        format_action.setChecked(self.use_24h)
        format_action.triggered.connect(self.toggle_time_format)
        menu.addAction(format_action)

        close_action = QAction(self.t["close_to_tray"], self, checkable=True)
        close_action.setChecked(self.close_to_tray)
        close_action.triggered.connect(self.toggle_close_to_tray)
        menu.addAction(close_action)

        if sys.platform == "win32":
            startup_action = QAction(self.t["start_windows"], self, checkable=True)
            startup_action.setChecked(self.startup_enabled())
            startup_action.triggered.connect(self.toggle_startup)
            menu.addAction(startup_action)

        opacity = menu.addMenu(self.t["opacity"])
        for percent in (100, 95, 90, 80, 70, 60, 50):
            action = QAction(f"{percent}%", self)
            action.setCheckable(True)
            action.setChecked(abs(self.window_opacity * 100 - percent) < 1)
            action.triggered.connect(
                lambda _checked=False, value=percent: self.set_opacity_percent(value)
            )
            opacity.addAction(action)

        language_menu = menu.addMenu(self.t["language"])
        tr_action = QAction(self.t["turkish"], self, checkable=True)
        tr_action.setChecked(self.language == "tr")
        tr_action.triggered.connect(lambda: self.set_language("tr"))
        language_menu.addAction(tr_action)

        en_action = QAction(self.t["english"], self, checkable=True)
        en_action.setChecked(self.language == "en")
        en_action.triggered.connect(lambda: self.set_language("en"))
        language_menu.addAction(en_action)

        menu.addSeparator()

        pomodoro_settings = QAction(self.t["pomodoro_settings"], self)
        pomodoro_settings.triggered.connect(self.open_pomodoro_settings)
        menu.addAction(pomodoro_settings)

        menu.addSeparator()

        reset_size = QAction(self.t["reset_size"], self)
        reset_size.triggered.connect(
            lambda: self.resize(self.COMPACT_SIZE if self.compact_mode else self.NORMAL_SIZE)
        )
        menu.addAction(reset_size)

        quit_action = QAction(self.t["quit"], self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())
        self.hide_timer.start()

    def _in_resize_corner(self, pos):
        return (
            pos.x() >= self.width() - self.RESIZE_MARGIN
            and pos.y() >= self.height() - self.RESIZE_MARGIN
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.resize_hot or self.lock_position:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(245, 245, 247, 135), 1.6))
        x = self.width() - 8
        y = self.height() - 8
        p.drawLine(x - 10, y, x, y - 10)
        p.drawLine(x - 5, y, x, y - 5)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and not self.resizing:
            self.toggle_compact()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        self.show_controls()
        self.hide_timer.start()

        pos = event.position().toPoint()
        if (
            event.button() == Qt.LeftButton
            and not self.lock_position
            and self._in_resize_corner(pos)
        ):
            self.resizing = True
            self.resize_start_global = event.globalPosition().toPoint()
            self.resize_start_size = self.size()
            self.setCursor(Qt.SizeFDiagCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton and not self.lock_position:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        self._show_resize_handle()
        pos = event.position().toPoint()

        if self.resizing:
            delta = event.globalPosition().toPoint() - self.resize_start_global
            new_w = max(
                self.MIN_SIZE.width(),
                min(self.MAX_SIZE.width(), self.resize_start_size.width() + delta.x()),
            )
            new_h = max(
                self.MIN_SIZE.height(),
                min(self.MAX_SIZE.height(), self.resize_start_size.height() + delta.y()),
            )
            self.resize(new_w, new_h)
            event.accept()
            return

        hot = self._in_resize_corner(pos) and not self.lock_position
        if hot != self.resize_hot:
            self.resize_hot = hot
            self.update()

        self.setCursor(Qt.SizeFDiagCursor if hot else Qt.ArrowCursor)
        self.show_controls()
        self.hide_timer.start()

        if event.buttons() & Qt.LeftButton and not self.lock_position and not hot:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.resizing and event.button() == Qt.LeftButton:
            self.resizing = False
            self.host.settings.setValue("window_size", self.host.size())
            if not self.host.compact_mode:
                self.host.normal_window_size = self.host.size()
                self.host.settings.setValue("normal_window_size", self.host.normal_window_size)
            self.host.hide_timer.start()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def showEvent(self, event):
        if hasattr(self, "tick_timer"):
            self.tick_timer.setInterval(250)
            if not self.tick_timer.isActive():
                self.tick_timer.start()
            self.tick(first=True)
        super().showEvent(event)

    def hideEvent(self, event):
        if hasattr(self, "tick_timer"):
            if self.pomodoro_running:
                self.tick_timer.setInterval(1000)
            else:
                self.tick_timer.stop()
        super().hideEvent(event)

    def _save_window_state(self):
        self.settings.setValue("pos", self.pos())
        if not self.compact_mode:
            self.normal_window_size = self.size()
            self.settings.setValue("window_size", self.size())
            self.settings.setValue("normal_window_size", self.normal_window_size)
        self.settings.sync()

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
        if event.key() == Qt.Key_Escape:
            if self.tray is not None:
                self.hide()
            else:
                self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._save_window_state()

        if self.force_quit:
            event.accept()
            return

        if self.close_to_tray and self.tray is not None and self.tray.isVisible():
            self.hide()
            event.ignore()
            return

        if self.tray:
            self.tray.hide()
        event.accept()
        QTimer.singleShot(0, QApplication.quit)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORG_NAME)
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(True)

    window = FlipFocus()
    window.show()
    sys.exit(app.exec())
