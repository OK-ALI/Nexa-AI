"""
Login Dialog for Nexa AI
Styled dark-theme login/registration dialog.
Matches the NEXA futuristic aesthetic.

Author: Ali Adil Waseem
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)

# Shared dark theme stylesheet
DIALOG_STYLE = """
    QDialog {
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #0A0F19,
            stop:1 #050A12
        );
    }
    QLabel {
        color: #FFFFFF;
        background: transparent;
    }
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
    QLineEdit::placeholder {
        color: rgba(255, 255, 255, 80);
    }
    QPushButton {
        background: rgba(0, 212, 255, 40);
        color: #00D4FF;
        border: 1px solid rgba(0, 212, 255, 80);
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: bold;
        font-family: 'Segoe UI';
    }
    QPushButton:hover {
        background: rgba(0, 212, 255, 80);
        color: #FFFFFF;
    }
    QPushButton:pressed {
        background: rgba(0, 212, 255, 120);
    }
"""


class LoginDialog(QDialog):
    """
    Login/Registration dialog for Nexa AI.
    Shows login form if users exist, registration form if first time.
    """

    login_successful = Signal(str)  # Emits username on success

    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self._authenticated = False
        self._username = ""

        self.setWindowTitle("NEXA - Login")
        self.setFixedSize(420, 520)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(DIALOG_STYLE)

        self._drag_position = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the dialog UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(0)

        # --- Close button (top right) ---
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200, 50, 50, 80);
                color: #FF6B6B;
                border: none;
                border-radius: 16px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(220, 70, 70, 150);
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.reject)
        close_row.addWidget(close_btn)
        main_layout.addLayout(close_row)

        # --- Title ---
        title = QLabel("NEXA")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        title.setStyleSheet("color: #00D4FF; letter-spacing: 6px; background: transparent;")
        main_layout.addWidget(title)

        subtitle = QLabel("AI ASSISTANT")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #0088CC; letter-spacing: 3px; background: transparent;")
        main_layout.addWidget(subtitle)

        main_layout.addSpacing(30)

        # --- Stacked widget: Login / Register ---
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        # Login page
        self.login_page = self._build_login_page()
        self.stack.addWidget(self.login_page)

        # Register page
        self.register_page = self._build_register_page()
        self.stack.addWidget(self.register_page)

        main_layout.addWidget(self.stack)
        main_layout.addStretch()

        # --- Error label ---
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("color: #FF4757; font-size: 12px; background: transparent;")
        self.error_label.setWordWrap(True)
        main_layout.addWidget(self.error_label)

        main_layout.addSpacing(10)

        # Show login if users exist, else registration
        if self.auth_manager.has_users():
            self.stack.setCurrentIndex(0)
        else:
            self.stack.setCurrentIndex(1)

    def _build_login_page(self) -> QWidget:
        """Build the login form."""
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QLabel("Welcome Back")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        header.setStyleSheet("color: #FFFFFF; background: transparent;")
        layout.addWidget(header)

        layout.addSpacing(8)

        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Username")
        self.login_username.setMinimumHeight(44)
        layout.addWidget(self.login_username)

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setMinimumHeight(44)
        self.login_password.returnPressed.connect(self._do_login)

        login_pw_row = QHBoxLayout()
        login_pw_row.setContentsMargins(0, 0, 0, 0)
        login_pw_row.setSpacing(6)
        login_pw_row.addWidget(self.login_password)
        self._login_show_btn = self._create_eye_button(self.login_password)
        login_pw_row.addWidget(self._login_show_btn)
        layout.addLayout(login_pw_row)

        layout.addSpacing(8)

        login_btn = QPushButton("LOGIN")
        login_btn.setMinimumHeight(44)
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 212, 255, 60);
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
        """)
        login_btn.clicked.connect(self._do_login)
        layout.addWidget(login_btn)

        layout.addSpacing(6)

        # Switch to register
        switch_btn = QPushButton("Create new account")
        switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        switch_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #0088CC;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #00D4FF;
            }
        """)
        switch_btn.clicked.connect(lambda: self._switch_page(1))
        layout.addWidget(switch_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    def _build_register_page(self) -> QWidget:
        """Build the registration form."""
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QLabel("Create Account")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        header.setStyleSheet("color: #FFFFFF; background: transparent;")
        layout.addWidget(header)

        layout.addSpacing(8)

        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Choose a username")
        self.reg_username.setMinimumHeight(44)
        layout.addWidget(self.reg_username)

        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Choose a password")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_password.setMinimumHeight(44)

        reg_pw_row = QHBoxLayout()
        reg_pw_row.setContentsMargins(0, 0, 0, 0)
        reg_pw_row.setSpacing(6)
        reg_pw_row.addWidget(self.reg_password)
        self._reg_show_btn = self._create_eye_button(self.reg_password)
        reg_pw_row.addWidget(self._reg_show_btn)
        layout.addLayout(reg_pw_row)

        self.reg_confirm = QLineEdit()
        self.reg_confirm.setPlaceholderText("Confirm password")
        self.reg_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_confirm.setMinimumHeight(44)
        self.reg_confirm.returnPressed.connect(self._do_register)

        reg_confirm_row = QHBoxLayout()
        reg_confirm_row.setContentsMargins(0, 0, 0, 0)
        reg_confirm_row.setSpacing(6)
        reg_confirm_row.addWidget(self.reg_confirm)
        self._reg_confirm_show_btn = self._create_eye_button(self.reg_confirm)
        reg_confirm_row.addWidget(self._reg_confirm_show_btn)
        layout.addLayout(reg_confirm_row)

        layout.addSpacing(8)

        reg_btn = QPushButton("REGISTER")
        reg_btn.setMinimumHeight(44)
        reg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reg_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 255, 150, 40);
                color: #00FF96;
                border: 1px solid rgba(0, 255, 150, 80);
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                letter-spacing: 2px;
            }
            QPushButton:hover {
                background: rgba(0, 255, 150, 80);
                color: #FFFFFF;
            }
        """)
        reg_btn.clicked.connect(self._do_register)
        layout.addWidget(reg_btn)

        layout.addSpacing(6)

        # Switch to login (only if users exist)
        if self.auth_manager.has_users():
            switch_btn = QPushButton("Already have an account? Login")
            switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            switch_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #0088CC;
                    border: none;
                    font-size: 12px;
                }
                QPushButton:hover {
                    color: #00D4FF;
                }
            """)
            switch_btn.clicked.connect(lambda: self._switch_page(0))
            layout.addWidget(switch_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    def _switch_page(self, index: int):
        """Switch between login and register pages."""
        self.error_label.setText("")
        self.stack.setCurrentIndex(index)

    def _do_login(self):
        """Attempt login."""
        username = self.login_username.text().strip()
        password = self.login_password.text()

        if not username or not password:
            self.error_label.setText("Please enter both username and password")
            return

        success, msg = self.auth_manager.login(username, password)
        if success:
            self._authenticated = True
            self._username = username
            self.login_successful.emit(username)
            self.accept()
        else:
            self.error_label.setText(msg)
            self.login_password.clear()
            self.login_password.setFocus()

    def _do_register(self):
        """Attempt registration."""
        username = self.reg_username.text().strip()
        password = self.reg_password.text()
        confirm = self.reg_confirm.text()

        if not username or not password:
            self.error_label.setText("Please fill in all fields")
            return

        if password != confirm:
            self.error_label.setText("Passwords do not match")
            self.reg_confirm.clear()
            self.reg_confirm.setFocus()
            return

        success, msg = self.auth_manager.register(username, password)
        if success:
            # Auto-login after registration
            self.auth_manager.login(username, password)
            self._authenticated = True
            self._username = username
            self.login_successful.emit(username)
            self.accept()
        else:
            self.error_label.setText(msg)

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    @property
    def username(self) -> str:
        return self._username

    def _create_eye_button(self, password_field: QLineEdit) -> QPushButton:
        """Create a show/hide password toggle button linked to a password field."""
        btn = QPushButton("👁")
        btn.setFixedSize(44, 44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip("Show password")
        btn.setStyleSheet("""
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
        btn.clicked.connect(lambda: self._toggle_pw_visibility(password_field, btn))
        return btn

    @staticmethod
    def _toggle_pw_visibility(field: QLineEdit, btn: QPushButton):
        """Toggle password field echo mode and update button icon."""
        if field.echoMode() == QLineEdit.EchoMode.Password:
            field.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("🔒")
            btn.setToolTip("Hide password")
        else:
            field.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("👁")
            btn.setToolTip("Show password")

    # --- Dragging support for frameless window ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_position and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_position = None
