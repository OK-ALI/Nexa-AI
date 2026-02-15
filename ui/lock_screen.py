"""
Lock Screen Overlay for Nexa AI
Full-window overlay that blocks all interaction until unlocked.
Matches the NEXA futuristic dark theme aesthetic.
Features frosted-glass blur behind the lock dialog.

Author: Ali Adil Waseem
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QImage,
    QPixmap, QPainterPath
)

logger = logging.getLogger(__name__)


class LockScreen(QWidget):
    """
    Full-window overlay lock screen.
    Blocks all interaction and shows password prompt to unlock.
    """

    unlocked = Signal()  # Emitted when user successfully unlocks

    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager

        # Cover entire parent
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Blur background
        self._blur_pixmap = None  # Frozen blurred snapshot of parent
        self._overlay_opacity = 1.0  # For unlock fade-out

        self._setup_ui()

        # Start hidden
        self.hide()

    def _setup_ui(self):
        """Build lock screen UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Center container
        center = QWidget()
        center.setFixedWidth(380)
        center.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(30, 40, 30, 40)
        center_layout.setSpacing(12)

        # Lock icon
        lock_icon = QLabel("🔒")
        lock_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_icon.setFont(QFont("Segoe UI Emoji", 40))
        lock_icon.setStyleSheet("background: transparent;")
        center_layout.addWidget(lock_icon)

        center_layout.addSpacing(5)

        # Title
        self.lock_title = QLabel("NEXA LOCKED")
        self.lock_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.lock_title.setStyleSheet("color: #00D4FF; letter-spacing: 4px; background: transparent;")

        # Static glow effect on title
        title_glow = QGraphicsDropShadowEffect(self.lock_title)
        title_glow.setOffset(0, 0)
        title_glow.setBlurRadius(25)
        title_glow.setColor(QColor(0, 212, 255, 160))
        self.lock_title.setGraphicsEffect(title_glow)
        center_layout.addWidget(self.lock_title)

        # User label
        self.user_label = QLabel("")
        self.user_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user_label.setFont(QFont("Segoe UI", 11))
        self.user_label.setStyleSheet("color: #0088CC; background: transparent;")
        center_layout.addWidget(self.user_label)

        center_layout.addSpacing(15)

        # Password input with show/hide toggle
        pw_container = QWidget()
        pw_container.setStyleSheet("background: transparent;")
        pw_layout = QHBoxLayout(pw_container)
        pw_layout.setContentsMargins(0, 0, 0, 0)
        pw_layout.setSpacing(6)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password to unlock")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.setStyleSheet("""
            QLineEdit {
                background: rgba(50, 70, 100, 120);
                color: #FFFFFF;
                border: 1px solid rgba(0, 212, 255, 80);
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                font-family: 'Segoe UI';
                selection-background-color: rgba(0, 212, 255, 100);
            }
            QLineEdit:focus {
                border: 1px solid #00D4FF;
                background: rgba(50, 70, 100, 180);
            }
        """)
        self.password_input.returnPressed.connect(self._do_unlock)
        pw_layout.addWidget(self.password_input)

        self._show_pw_btn = QPushButton("👁")
        self._show_pw_btn.setFixedSize(44, 44)
        self._show_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._show_pw_btn.setToolTip("Show password")
        self._show_pw_btn.setStyleSheet("""
            QPushButton {
                background: rgba(50, 70, 100, 120);
                color: #8899AA;
                border: 1px solid rgba(0, 212, 255, 80);
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(50, 70, 100, 180);
                color: #00D4FF;
            }
        """)
        self._show_pw_btn.clicked.connect(self._toggle_password_visibility)
        pw_layout.addWidget(self._show_pw_btn)

        center_layout.addWidget(pw_container)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("color: #FF4757; font-size: 12px; background: transparent;")
        center_layout.addWidget(self.error_label)

        center_layout.addSpacing(5)

        # Unlock button
        unlock_btn = QPushButton("UNLOCK")
        unlock_btn.setMinimumHeight(44)
        unlock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        unlock_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 212, 255, 50);
                color: #FFFFFF;
                border: 1px solid #00D4FF;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                letter-spacing: 2px;
            }
            QPushButton:hover {
                background: rgba(0, 212, 255, 100);
            }
            QPushButton:pressed {
                background: rgba(0, 212, 255, 140);
            }
        """)
        unlock_btn.clicked.connect(self._do_unlock)
        center_layout.addWidget(unlock_btn)

        main_layout.addWidget(center)

    def paintEvent(self, event):
        """Draw frosted-glass blur background with dark overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw blurred snapshot if available
        if self._blur_pixmap:
            painter.drawPixmap(0, 0, self._blur_pixmap.scaled(
                self.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        # Dark tinted overlay on top of blur
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(10, 15, 25, 190))
        gradient.setColorAt(1.0, QColor(5, 10, 18, 210))
        painter.fillRect(self.rect(), gradient)
        painter.end()

    def activate(self):
        """Show the lock screen with frosted-glass blur and lock the session."""
        self.auth_manager.lock()
        self.user_label.setText(f"User: {self.auth_manager.current_user or 'Unknown'}")
        self.password_input.clear()
        self.error_label.setText("")

        # Capture blurred snapshot of parent before overlaying
        self._capture_blur_background()

        # Resize to cover parent
        if self.parent():
            self.setGeometry(self.parent().rect())

        # Reset opacity for fade-in
        self._overlay_opacity = 1.0
        self.setWindowOpacity(1.0)

        self.show()
        self.raise_()
        self.password_input.setFocus()
        logger.info("Lock screen activated with blur background")

    def _do_unlock(self):
        """Attempt to unlock with smooth blur-clear transition."""
        password = self.password_input.text()
        if not password:
            self.error_label.setText("Please enter your password")
            return

        success, msg = self.auth_manager.unlock(password)
        if success:
            # Smooth fade-out transition
            self._fade_out_and_dismiss()
            logger.info("Lock screen unlocking with fade transition")
        else:
            self.error_label.setText(msg)
            self.password_input.clear()
            self.password_input.setFocus()

    def _fade_out_and_dismiss(self):
        """Smoothly fade out the lock screen overlay then dismiss."""
        # Use QGraphicsOpacityEffect for smooth fade
        opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(1.0)

        self._fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
        self._fade_anim.setDuration(400)  # 400ms fade
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_complete)
        self._fade_anim.start()

    def _on_fade_complete(self):
        """Called when fade-out animation finishes."""
        self.hide()
        self.setGraphicsEffect(None)  # Remove opacity effect for next show
        self._blur_pixmap = None  # Free memory
        self.unlocked.emit()
        logger.info("Lock screen dismissed - session unlocked")

    def _capture_blur_background(self):
        """Capture and blur the parent window content as background."""
        try:
            parent = self.parent()
            if not parent:
                self._blur_pixmap = None
                return

            # Grab the parent widget content as a pixmap
            pixmap = parent.grab()

            # Convert to QImage for blur processing
            img = pixmap.toImage()

            # Apply box blur (fast approximation of Gaussian blur)
            img = self._apply_blur(img, radius=20)

            self._blur_pixmap = QPixmap.fromImage(img)
            logger.debug("Captured and blurred parent background")

        except Exception as e:
            logger.warning(f"Failed to capture blur background: {e}")
            self._blur_pixmap = None

    @staticmethod
    def _apply_blur(image: QImage, radius: int = 20) -> QImage:
        """
        Apply a fast box blur to a QImage.
        Uses a two-pass horizontal+vertical box blur for performance.
        Multiple passes approximate a Gaussian blur.
        """
        from PySide6.QtCore import QRect

        # Scale down → blur → scale up for efficient, strong blur
        w, h = image.width(), image.height()
        scale_factor = 0.15  # Scale to 15% — large blur effect

        small = image.scaled(
            max(1, int(w * scale_factor)),
            max(1, int(h * scale_factor)),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Scale back up (the bilinear interpolation creates the blur)
        blurred = small.scaled(
            w, h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        return blurred

    def _toggle_password_visibility(self):
        """Toggle between showing and hiding the password."""
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_pw_btn.setText("🔒")
            self._show_pw_btn.setToolTip("Hide password")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_pw_btn.setText("👁")
            self._show_pw_btn.setToolTip("Show password")

    def resizeEvent(self, event):
        """Keep overlay covering the parent."""
        super().resizeEvent(event)

    # Block all mouse events to prevent interaction behind lock screen
    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseMoveEvent(self, event):
        event.accept()

    def keyPressEvent(self, event):
        """Only allow typing in password field, block everything else."""
        if self.password_input.hasFocus():
            super().keyPressEvent(event)
        else:
            self.password_input.setFocus()
            super().keyPressEvent(event)
        event.accept()
