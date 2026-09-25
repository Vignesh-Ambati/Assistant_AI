import sys
import math
from PyQt6.QtWidgets import (
    QWidget, QMenu, QApplication, QSystemTrayIcon
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QPoint, QPointF, QTimer,
    QEasingCurve, QRectF
)
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient,
    QBrush, QPen, QAction, QIcon, QPixmap, QFont,
    QPainterPath, QPolygonF
)


class FloatingButton(QWidget):
    """
    Sleek rounded-square floating button inspired by the ScreenXpert reference.
    Dark background with a silver/white AI-sparkle icon.
    Fades to 30% opacity after 5s of no hover; fully opaque on hover.
    """

    def __init__(self, chat_window, parent=None):
        super().__init__(parent)
        self.chat_window = chat_window
        self._target_opacity = 1.0
        self.is_hovered = False
        self.drag_position = None
        self._was_dragged = False
        self.init_ui()

    # ── UI Setup ──────────────────────────────────────────────────────
    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(60, 60)

        # Position bottom-right
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - 100, screen.height() - 100)

        # Fade-out timer: starts 5s after mouse leaves
        self.fade_timer = QTimer(self)
        self.fade_timer.setSingleShot(True)
        self.fade_timer.setInterval(5000)
        self.fade_timer.timeout.connect(self._fade_out)

        # Opacity animation
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(600)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.setWindowOpacity(1.0)
        self.fade_timer.start()  # start idle countdown immediately

        self.setup_tray_icon()

    # ── Tray Icon ─────────────────────────────────────────────────────
    def setup_tray_icon(self):
        pixmap = self._render_icon(32)
        self.tray_icon = QSystemTrayIcon(QIcon(pixmap), self)
        self.tray_icon.setToolTip("AI Assistant")

        menu = QMenu()
        show_action = menu.addAction("Show / Hide")
        show_action.triggered.connect(self.toggle_chat)
        menu.addSeparator()
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(QApplication.quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_chat()

    # ── Icon Rendering ────────────────────────────────────────────────
    @staticmethod
    def _render_icon(size):
        """Render a dark rounded-square with a silver AI-sparkle, matching the reference."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dark rounded-square background
        r = QRectF(0, 0, size, size)
        radius = size * 0.22
        bg = QLinearGradient(0, 0, size, size)
        bg.setColorAt(0, QColor(40, 40, 48))
        bg.setColorAt(1, QColor(24, 24, 30))
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, radius, radius)

        # Subtle border
        p.setPen(QPen(QColor(80, 80, 100, 60), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

        # AI sparkle/neural icon — two overlapping angular strokes
        cx, cy = size / 2, size / 2
        s = size * 0.28  # stroke half-length

        grad = QLinearGradient(cx - s, cy - s, cx + s, cy + s)
        grad.setColorAt(0, QColor(220, 220, 230))
        grad.setColorAt(0.5, QColor(255, 255, 255))
        grad.setColorAt(1, QColor(180, 180, 200))

        pen = QPen(QBrush(grad), size * 0.09, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)

        # Two angular strokes forming an AI-like mark
        path = QPainterPath()
        # Upper-left to center stroke
        path.moveTo(cx - s * 0.8, cy - s * 0.5)
        path.lineTo(cx - s * 0.1, cy + s * 0.6)
        # Center to upper-right stroke
        path.moveTo(cx + s * 0.1, cy - s * 0.6)
        path.lineTo(cx + s * 0.8, cy + s * 0.5)
        p.drawPath(path)

        # Small dot at top-right (like a neural node / sparkle)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 220))
        dot_r = size * 0.055
        p.drawEllipse(QPointF(cx + s * 0.55, cy - s * 0.75), dot_r, dot_r)

        p.end()
        return pixmap

    # ── Paint ─────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(self.width(), self.height())
        margin = 2 if self.is_hovered else 4
        r = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
        radius = size * 0.22

        # Glow shadow on hover
        if self.is_hovered:
            glow = QRadialGradient(r.center(), size * 0.6)
            glow.setColorAt(0, QColor(100, 120, 255, 40))
            glow.setColorAt(1, QColor(100, 120, 255, 0))
            p.setBrush(QBrush(glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(r.adjusted(-6, -6, 6, 6))

        # Background
        bg = QLinearGradient(r.topLeft(), r.bottomRight())
        if self.is_hovered:
            bg.setColorAt(0, QColor(50, 50, 60))
            bg.setColorAt(1, QColor(32, 32, 40))
        else:
            bg.setColorAt(0, QColor(38, 38, 46))
            bg.setColorAt(1, QColor(22, 22, 28))
        p.setBrush(QBrush(bg))
        p.setPen(QPen(QColor(90, 90, 110, 80), 1))
        p.drawRoundedRect(r, radius, radius)

        # Draw icon inside
        icon_size = int(size * 0.55)
        icon_pix = self._render_icon(icon_size)
        ix = (size - icon_size) / 2
        iy = (size - icon_size) / 2
        p.drawPixmap(int(ix), int(iy), icon_pix)

    # ── Hover / Fade Logic ────────────────────────────────────────────
    def enterEvent(self, event):
        self.is_hovered = True
        self.fade_timer.stop()
        self._animate_opacity(1.0)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.fade_timer.start()  # restart 5s countdown
        self.update()
        super().leaveEvent(event)

    def _fade_out(self):
        if not self.is_hovered:
            self._animate_opacity(0.30)

    def _animate_opacity(self, target):
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.windowOpacity())
        self.opacity_anim.setEndValue(target)
        self.opacity_anim.start()

    # ── Mouse Events (drag + click) ───────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._was_dragged = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            if not self._was_dragged:
                diff = new_pos - self.pos()
                if abs(diff.x()) + abs(diff.y()) > 4:
                    self._was_dragged = True
            if self._was_dragged:
                self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._was_dragged:
                self.toggle_chat()
            self.drag_position = None
            event.accept()

    # ── Toggle Chat ───────────────────────────────────────────────────
    def toggle_chat(self):
        if self.chat_window.isVisible():
            self.chat_window.hide_window()
        else:
            self.chat_window.show_window(self.pos())

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item { padding: 6px 24px; border-radius: 4px; }
            QMenu::item:selected { background-color: #45475a; }
        """)
        menu.addAction("Show / Hide Chat").triggered.connect(self.toggle_chat)
        menu.addSeparator()
        menu.addAction("Exit").triggered.connect(QApplication.quit)
        menu.exec(pos)
