"""
Loading Dialog for Nexa AI
Shows an initializing spinner after login while core components load.

Author: Ali Adil Waseem
"""

import logging
import math
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication
from PySide6.QtCore import Qt, QTimer, QRectF, Property
from PySide6.QtGui import QFont, QPainter, QColor, QConicalGradient, QPen

logger = logging.getLogger(__name__)


class SpinnerWidget(QLabel):
    """Animated circular spinner with Nexa cyan/purple gradient."""

    def __init__(self, parent=None, size=80):
        super().__init__(parent)
        self._angle = 0
        self._size = size
        self.setFixedSize(size, size)

        # Animation timer - 60fps smooth rotation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(16)  # ~60fps

    def _rotate(self):
        self._angle = (self._angle + 4) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Center and size
        s = self._size
        margin = 8
        rect = QRectF(margin, margin, s - 2 * margin, s - 2 * margin)

        # Draw background ring (faint)
        bg_pen = QPen(QColor(50, 70, 100, 60), 4)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Draw spinning gradient arc
        gradient = QConicalGradient(s / 2, s / 2, -self._angle)
        gradient.setColorAt(0.0, QColor(0, 212, 255, 255))    # Cyan
        gradient.setColorAt(0.4, QColor(147, 51, 234, 200))   # Purple
        gradient.setColorAt(0.7, QColor(0, 212, 255, 80))     # Faded cyan
        gradient.setColorAt(1.0, QColor(0, 212, 255, 0))      # Transparent

        arc_pen = QPen(gradient, 4)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)

        # Draw 270-degree arc (leaves a gap for the "tail" effect)
        start_angle = int(self._angle * 16)
        span_angle = 270 * 16
        painter.drawArc(rect, start_angle, span_angle)

        # Draw leading dot
        angle_rad = math.radians(self._angle)
        cx = s / 2 + (s / 2 - margin - 2) * math.cos(angle_rad)
        cy = s / 2 - (s / 2 - margin - 2) * math.sin(angle_rad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 212, 255, 255))
        painter.drawEllipse(QRectF(cx - 3, cy - 3, 6, 6))

        painter.end()

    def stop(self):
        """Stop the spinner animation."""
        self._timer.stop()


class LoadingDialog(QDialog):
    """
    Loading/Initializing dialog shown after login.
    Displays a circular spinner with status text.
    Matches the Login dialog size and Nexa dark theme.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NEXA - Initializing")
        self.setFixedSize(420, 520)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._setup_ui()
        logger.info("⏳ Loading dialog created")

    def _setup_ui(self):
        """Build the loading dialog UI."""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0A0F19,
                    stop:1 #050A12
                );
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 60, 40, 40)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # NEXA Logo/Title
        title = QLabel("NEXA")
        title.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color: #00D4FF;
            background: transparent;
            letter-spacing: 8px;
        """)
        layout.addWidget(title)
        layout.addSpacing(8)

        # Subtitle
        subtitle = QLabel("AI Desktop Assistant")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: rgba(255,255,255,0.5); background: transparent;")
        layout.addWidget(subtitle)

        layout.addSpacing(60)

        # Spinner
        self.spinner = SpinnerWidget(self, size=80)
        spinner_layout = QVBoxLayout()
        spinner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinner_layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(spinner_layout)

        layout.addSpacing(30)

        # Status text
        self.status_label = QLabel("Initializing...")
        self.status_label.setFont(QFont("Segoe UI", 13))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.8);
            background: transparent;
        """)
        layout.addWidget(self.status_label)

        layout.addSpacing(10)

        # Detail text (smaller, for specific component being loaded)
        self.detail_label = QLabel("Loading configuration...")
        self.detail_label.setFont(QFont("Segoe UI", 10))
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_label.setStyleSheet("""
            color: rgba(0, 212, 255, 0.5);
            background: transparent;
        """)
        layout.addWidget(self.detail_label)

        layout.addStretch()

        # Version/footer
        footer = QLabel("Please wait while components are loading")
        footer.setFont(QFont("Segoe UI", 9))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: rgba(255,255,255,0.25); background: transparent;")
        layout.addWidget(footer)

    def set_status(self, text: str, detail: str = ""):
        """Update the status and detail text (thread-safe via signal connection)."""
        self.status_label.setText(text)
        if detail:
            self.detail_label.setText(detail)

    def close_dialog(self):
        """Stop spinner and close."""
        self.spinner.stop()
        self.close()
        logger.info("✅ Loading dialog closed")
