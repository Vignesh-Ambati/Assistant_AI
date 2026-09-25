"""
chat_window.py — Dark-mode AI chat panel with streaming, model picker,
thinking animation, and true maximize / restore.
"""
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QScrollArea, QFrame,
    QSizePolicy, QComboBox, QApplication, QSpacerItem
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QPoint, QSize,
    QEasingCurve, QTimer, QRectF, pyqtProperty
)
from PyQt6.QtGui import (
    QColor, QFont, QKeyEvent, QPainter, QPen, QBrush,
    QLinearGradient, QPainterPath, QFontMetrics
)

from ai_backend import StreamWorker

# ── Colour palette ────────────────────────────────────────────────────
BG_DARK      = "#0d0d14"
BG_PANEL     = "#12121f"
BG_HEADER    = "#0f0f1b"
BG_INPUT     = "#16162a"
BG_BUBBLE_AI = "#1a1a2e"
BG_BUBBLE_U  = "#4f46e5"
BORDER       = "#1f1f38"
BORDER_LT    = "#2a2a44"
TEXT_PRI     = "#e4e4ef"
TEXT_SEC     = "#8888a8"
TEXT_DIM     = "#55557a"
ACCENT       = "#6366f1"
ACCENT_LT    = "#818cf8"
DANGER       = "#ef4444"


# ═════════════════════════════════════════════════════════════════════
#  Thinking Dots
# ═════════════════════════════════════════════════════════════════════
class ThinkingDots(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 32)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._phase = 0
        self._timer.start()
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._phase = (self._phase + 1) % 15
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() / 2
        cy = self.height() / 2
        for i in range(3):
            phase = (self._phase - i * 3) % 15
            dy = -4.0 * max(0, 1 - abs(phase - 3) / 3) if phase < 7 else 0
            alpha = 240 if phase < 7 else 100
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(ACCENT_LT) if phase < 7 else QColor(TEXT_DIM))
            p.drawEllipse(QRectF(cx - 20 + i * 16 - 3.5, cy + dy - 3.5, 7, 7))


# ═════════════════════════════════════════════════════════════════════
#  Message Row  — avatar + bubble, cleanly aligned
# ═════════════════════════════════════════════════════════════════════
def _make_avatar(letter, bg_color, size=28):
    """Tiny circular avatar label."""
    lbl = QLabel(letter)
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"""
        QLabel {{
            background-color: {bg_color};
            color: #fff;
            border-radius: {size // 2}px;
            font-size: 12px;
            font-weight: 700;
        }}
    """)
    return lbl


class MessageBubble(QLabel):
    """Single chat bubble with proper styling."""
    def __init__(self, text="", is_user=True, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        bg = BG_BUBBLE_U if is_user else BG_BUBBLE_AI
        border = "none" if is_user else f"1px solid {BORDER}"
        text_c = "#ffffff" if is_user else TEXT_PRI
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {text_c};
                border-radius: 12px;
                border: {border};
                padding: 10px 14px;
                font-size: 13px;
                line-height: 1.45;
            }}
        """)


def build_message_row(text, is_user, max_bubble_width=340):
    """Return (QHBoxLayout, MessageBubble)."""
    bubble = MessageBubble(text, is_user)
    bubble.setMaximumWidth(max_bubble_width)
    row = QHBoxLayout()
    row.setContentsMargins(4, 2, 4, 2)
    row.setSpacing(8)
    if is_user:
        row.addStretch()
        row.addWidget(bubble)
        row.addWidget(_make_avatar("U", "#4f46e5"))
    else:
        row.addWidget(_make_avatar("AI", "#1e1b4b"))
        row.addWidget(bubble)
        row.addStretch()
    return row, bubble


# ═════════════════════════════════════════════════════════════════════
#  Chat Window
# ═════════════════════════════════════════════════════════════════════
class ChatWindow(QWidget):
    DEFAULT_SIZE = QSize(440, 620)

    def __init__(self, ai_backend, parent=None):
        super().__init__(parent)
        self.ai_backend = ai_backend
        self.worker = None
        self._current_ai_bubble = None
        self._is_maximized = False
        self._restore_geo = None        # (pos, size) before maximize
        self._stream_buf = ""
        self._thinking_row = None
        self._init_ui()

    # ── fixedSize property (for animation) ────────────────────────────
    @pyqtProperty(QSize)
    def fixedSize(self):
        return self.size()

    @fixedSize.setter
    def fixedSize(self, s):
        self.setFixedSize(s)

    # ── Build ─────────────────────────────────────────────────────────
    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setFixedSize(self.DEFAULT_SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Container
        self.container = QFrame()
        self.container.setObjectName("ctr")
        self._apply_container_style(16)
        cl = QVBoxLayout(self.container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # ── Header ─────────────────────────────────────────────
        hdr = QFrame()
        hdr.setFixedHeight(44)
        hdr.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_HEADER};
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}
        """)
        self._header = hdr
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 0, 8, 0)
        hl.setSpacing(6)

        dot = QLabel("●")
        dot.setStyleSheet(f"color:{ACCENT}; font-size:10px;")
        title = QLabel(" AI Assistant")
        title.setStyleSheet(f"color:{TEXT_PRI}; font-weight:600; font-size:14px;")

        self._min_btn = self._hbtn("─", tooltip="Minimize (restore default size)")
        self._max_btn = self._hbtn("□", tooltip="Maximize (full screen)")
        self._close_btn = self._hbtn("✕", tooltip="Close", hover_bg=DANGER)

        self._min_btn.clicked.connect(self._do_minimize)
        self._max_btn.clicked.connect(self._do_maximize_toggle)
        self._close_btn.clicked.connect(self.hide_window)

        hl.addWidget(dot)
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(self._min_btn)
        hl.addWidget(self._max_btn)
        hl.addWidget(self._close_btn)

        # ── Model bar ─────────────────────────────────────────
        mbar = QFrame()
        mbar.setFixedHeight(36)
        mbar.setStyleSheet(f"background:{BG_PANEL}; border:none;")
        self._model_bar = mbar
        ml = QHBoxLayout(mbar)
        ml.setContentsMargins(16, 2, 16, 2)
        ml.setSpacing(8)

        ml.addWidget(self._small_label("Model"))

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(160)
        self.model_combo.setStyleSheet(f"""
            QComboBox {{
                background:{BG_INPUT}; color:{TEXT_PRI};
                border:1px solid {BORDER}; border-radius:6px;
                padding:2px 8px; font-size:12px;
            }}
            QComboBox::drop-down {{ border:none; width:18px; }}
            QComboBox::down-arrow {{ image:none; }}
            QComboBox QAbstractItemView {{
                background:{BG_INPUT}; color:{TEXT_PRI};
                selection-background-color:{BORDER_LT};
                border:1px solid {BORDER}; outline:none;
            }}
        """)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)

        ref = QPushButton("⟳")
        ref.setFixedSize(24, 24)
        ref.setToolTip("Refresh")
        ref.setStyleSheet(f"""
            QPushButton {{background:transparent; color:{TEXT_SEC};
                          border:none; font-size:15px;}}
            QPushButton:hover {{color:{TEXT_PRI};}}
        """)
        ref.clicked.connect(self._refresh_models)

        self.auto_btn = QPushButton("Auto")
        self.auto_btn.setCheckable(True)
        self.auto_btn.setFixedHeight(24)
        self.auto_btn.setToolTip("Auto-select smaller model for simple questions")
        self.auto_btn.setStyleSheet(f"""
            QPushButton {{
                background:{BG_INPUT}; color:{TEXT_SEC};
                border:1px solid {BORDER}; border-radius:6px;
                padding:1px 10px; font-size:11px;
            }}
            QPushButton:checked {{
                background:{ACCENT}; color:#fff; border:1px solid {ACCENT_LT};
            }}
        """)

        ml.addWidget(self.model_combo, 1)
        ml.addWidget(ref)
        ml.addWidget(self.auto_btn)

        # ── Chat scroll ───────────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none; background: {BG_DARK};
            }}
            QScrollBar:vertical {{
                width:5px; background:transparent; margin:2px;
            }}
            QScrollBar::handle:vertical {{
                background:{BORDER_LT}; border-radius:2px; min-height:30px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background:none; }}
        """)

        self.chat_w = QWidget()
        self.chat_w.setStyleSheet(f"background:{BG_DARK};")
        self.chat_lay = QVBoxLayout(self.chat_w)
        self.chat_lay.setContentsMargins(8, 12, 8, 12)
        self.chat_lay.setSpacing(4)
        self.chat_lay.addStretch()
        self.scroll.setWidget(self.chat_w)

        # Welcome message
        welcome = QLabel("Ask me anything — I'm running locally on your machine.")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setStyleSheet(f"color:{TEXT_DIM}; font-size:12px; padding:30px;")
        welcome.setWordWrap(True)
        self.chat_lay.insertWidget(0, welcome)
        self._welcome = welcome

        # Thinking indicator
        self.thinking = ThinkingDots(self)
        self.thinking.hide()

        # ── Input ─────────────────────────────────────────────
        inp = QFrame()
        inp.setStyleSheet(f"""
            QFrame {{
                background:{BG_PANEL};
                border-top:1px solid {BORDER};
                border-bottom-left-radius:16px;
                border-bottom-right-radius:16px;
            }}
        """)
        self._input_frame = inp
        il = QHBoxLayout(inp)
        il.setContentsMargins(12, 8, 12, 10)
        il.setSpacing(8)

        self.text_input = QTextEdit()
        self.text_input.setFixedHeight(46)
        self.text_input.setPlaceholderText("Message…")
        self.text_input.setStyleSheet(f"""
            QTextEdit {{
                background:{BG_INPUT}; color:{TEXT_PRI};
                border:1px solid {BORDER}; border-radius:12px;
                padding:8px 14px; font-size:13px;
                selection-background-color:{ACCENT};
            }}
            QTextEdit:focus {{
                border:1px solid {ACCENT};
            }}
        """)
        self.text_input.installEventFilter(self)

        self.send_btn = QPushButton("↑")
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background:{ACCENT}; color:#fff; border:none;
                border-radius:10px; font-size:18px; font-weight:bold;
            }}
            QPushButton:hover {{ background:{ACCENT_LT}; }}
            QPushButton:disabled {{ background:{BORDER}; color:{TEXT_DIM}; }}
        """)
        self.send_btn.clicked.connect(self.send_message)

        il.addWidget(self.text_input, 1)
        il.addWidget(self.send_btn, 0, Qt.AlignmentFlag.AlignBottom)

        # ── Status ────────────────────────────────────────────
        self.status = QLabel("Ready")
        self.status.setFixedHeight(18)
        self.status.setStyleSheet(
            f"color:{TEXT_DIM}; font-size:10px; padding:0 16px;"
        )

        # ── Assemble ──────────────────────────────────────────
        cl.addWidget(hdr)
        cl.addWidget(mbar)
        cl.addWidget(self.scroll, 1)
        cl.addWidget(inp)
        cl.addWidget(self.status)
        root.addWidget(self.container)

        # Slide-in animation
        self._slide = QPropertyAnimation(self, b"pos")
        self._slide.setDuration(200)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)

        QTimer.singleShot(300, self._refresh_models)

    # ── Helpers ───────────────────────────────────────────────────────
    def _apply_container_style(self, radius):
        self.container.setStyleSheet(f"""
            QFrame#ctr {{
                background:{BG_DARK};
                border-radius:{radius}px;
                border:1px solid {BORDER};
            }}
        """)

    @staticmethod
    def _small_label(text):
        l = QLabel(text)
        l.setStyleSheet(f"color:{TEXT_SEC}; font-size:11px;")
        return l

    @staticmethod
    def _hbtn(text, tooltip="", hover_bg=BORDER_LT):
        b = QPushButton(text)
        b.setFixedSize(26, 26)
        b.setToolTip(tooltip)
        b.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{TEXT_SEC};
                border:none; border-radius:7px;
                font-size:12px; font-weight:600;
            }}
            QPushButton:hover {{
                background:{hover_bg}; color:{TEXT_PRI};
            }}
        """)
        return b

    # ── Minimize (restore to default size) ────────────────────────────
    def _do_minimize(self):
        if self._is_maximized:
            self._do_maximize_toggle()   # restore first
        # Already at default size — just a no-op or could hide
        # But per user's spec, minimize = default size
        self.setFixedSize(self.DEFAULT_SIZE)
        self._apply_container_style(16)
        self._update_header_radius(16)

    # ── Maximize (fill screen minus taskbar) / restore ────────────────
    def _do_maximize_toggle(self):
        if self._is_maximized:
            # Restore
            if self._restore_geo:
                pos, size = self._restore_geo
                self.setFixedSize(size)
                self.move(pos)
            else:
                self.setFixedSize(self.DEFAULT_SIZE)
            self._is_maximized = False
            self._max_btn.setText("□")
            self._max_btn.setToolTip("Maximize")
            self._apply_container_style(16)
            self._update_header_radius(16)
        else:
            # Save current geometry
            self._restore_geo = (self.pos(), self.size())
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(screen.topLeft())
            self.setFixedSize(screen.size())
            self._is_maximized = True
            self._max_btn.setText("❐")
            self._max_btn.setToolTip("Restore")
            self._apply_container_style(0)
            self._update_header_radius(0)

    def _update_header_radius(self, r):
        self._header.setStyleSheet(f"""
            QFrame {{
                background-color:{BG_HEADER};
                border-top-left-radius:{r}px;
                border-top-right-radius:{r}px;
            }}
        """)
        self._input_frame.setStyleSheet(f"""
            QFrame {{
                background:{BG_PANEL};
                border-top:1px solid {BORDER};
                border-bottom-left-radius:{r}px;
                border-bottom-right-radius:{r}px;
            }}
        """)

    # ── Model management ──────────────────────────────────────────────
    def _refresh_models(self):
        models = self.ai_backend.get_available_models()
        self.model_combo.blockSignals(True)
        cur = self.model_combo.currentText()
        self.model_combo.clear()
        if models:
            self.model_combo.addItems(models)
            if cur in models:
                self.model_combo.setCurrentText(cur)
            else:
                for m in models:
                    if self.ai_backend.model_name in m:
                        self.model_combo.setCurrentText(m)
                        break
        else:
            self.model_combo.addItem("(no models)")
        self.model_combo.blockSignals(False)

    def _on_model_changed(self, name):
        if name and not name.startswith("("):
            self.ai_backend.set_model(name)
            self.status.setText(f"Model → {name}")

    def _auto_pick(self, msg):
        if not self.auto_btn.isChecked():
            return
        models = self.ai_backend.get_available_models()
        if len(models) <= 1:
            return
        small = sorted(m for m in models if any(
            t in m for t in ('0.5b','1b','1.5b','2b','3b','tiny','mini','small')
        ))
        rest = [m for m in models if m not in small]
        if len(msg.strip()) < 80 and small:
            pick = small[0]
        elif rest:
            pick = rest[0]
        else:
            return
        self.ai_backend.set_model(pick)
        self.model_combo.blockSignals(True)
        self.model_combo.setCurrentText(pick)
        self.model_combo.blockSignals(False)
        self.status.setText(f"Auto → {pick}")

    # ── Key filter ────────────────────────────────────────────────────
    def eventFilter(self, obj, event):
        if obj is self.text_input and event.type() == QKeyEvent.Type.KeyPress:
            if (event.key() == Qt.Key.Key_Return
                    and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    # ── Message helpers ───────────────────────────────────────────────
    def _add_bubble(self, text, is_user):
        if hasattr(self, '_welcome') and self._welcome.isVisible():
            self._welcome.hide()
        max_w = min(int(self.width() * 0.7), 500)
        row, bubble = build_message_row(text, is_user, max_w)
        n = self.chat_lay.count()
        self.chat_lay.insertLayout(n - 1, row)
        QTimer.singleShot(20, self._scroll_btm)
        return bubble

    def _scroll_btm(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── Send + stream ─────────────────────────────────────────────────
    def send_message(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            return
        self.text_input.clear()
        self._add_bubble(text, True)
        self._auto_pick(text)
        self._show_thinking()
        self.send_btn.setEnabled(False)
        self._stream_buf = ""

        self.worker = StreamWorker(self.ai_backend, text)
        self.worker.token_received.connect(self._on_token)
        self.worker.stream_finished.connect(self._on_done)
        self.worker.error_occurred.connect(self._on_err)
        self.worker.start()

    def _show_thinking(self):
        row = QHBoxLayout()
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(8)
        row.addWidget(_make_avatar("AI", "#1e1b4b"))
        row.addWidget(self.thinking)
        row.addStretch()
        n = self.chat_lay.count()
        self.chat_lay.insertLayout(n - 1, row)
        self._thinking_row = row
        self.thinking.start()
        self.status.setText("Thinking…")
        QTimer.singleShot(20, self._scroll_btm)

    def _hide_thinking(self):
        self.thinking.stop()
        self.thinking.setParent(self)
        self.thinking.hide()

    def _on_token(self, tok):
        if self._current_ai_bubble is None:
            self._hide_thinking()
            self.status.setText("Generating…")
            self._current_ai_bubble = self._add_bubble("", False)
        self._stream_buf += tok
        self._current_ai_bubble.setText(self._stream_buf)
        self._current_ai_bubble.adjustSize()
        QTimer.singleShot(5, self._scroll_btm)

    def _on_done(self):
        self._current_ai_bubble = None
        self._stream_buf = ""
        self.send_btn.setEnabled(True)
        self.status.setText("Ready")

    def _on_err(self, msg):
        self._hide_thinking()
        if self._current_ai_bubble is None:
            self._add_bubble(f"⚠ {msg}", False)
        self._current_ai_bubble = None
        self._stream_buf = ""
        self.send_btn.setEnabled(True)
        self.status.setText("Error")

    # ── Position / show / hide ────────────────────────────────────────
    def set_position(self, btn_pos):
        scr = QApplication.primaryScreen().availableGeometry()
        tx = btn_pos.x() - self.width() - 14
        ty = btn_pos.y() - self.height() + 56
        tx = max(scr.x() + 4, min(tx, scr.right() - self.width() - 4))
        ty = max(scr.y() + 4, min(ty, scr.bottom() - self.height() - 4))
        return QPoint(tx, ty)

    def show_window(self, btn_pos):
        if self._is_maximized:
            self._do_maximize_toggle()
        target = self.set_position(btn_pos)
        start = QPoint(target.x() + 30, target.y())
        self.move(start)
        self.show()
        self.raise_()
        self._slide.setStartValue(start)
        self._slide.setEndValue(target)
        self._slide.start()

    def hide_window(self):
        self.hide()
