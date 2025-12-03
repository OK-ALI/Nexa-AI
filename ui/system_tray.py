"""
System Tray Integration - Quick access and notifications for Nexa
"""

import logging
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QSystemTrayIcon, QMenu
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtCore import Qt, QSize

from core.brain import NexaState

logger = logging.getLogger(__name__)


class NexaSystemTray(QSystemTrayIcon):
    """
    System tray icon for Nexa with quick actions and notifications.
    """
    
    def __init__(self, parent=None):
        """Initialize system tray icon."""
        # Create initial icon
        icon = self._create_icon(NexaState.IDLE)
        super().__init__(icon, parent)
        
        self.parent_window = parent
        self.current_state = NexaState.IDLE
        
        # Create context menu
        self._create_context_menu()
        
        # Connect signals
        self.activated.connect(self._on_tray_activated)
        
        # Set initial tooltip
        self.setToolTip("Nexa AI Assistant - Idle")
        
        logger.info("System tray icon initialized")
    
    def _create_icon(self, state: NexaState, size: int = 64) -> QIcon:
        """
        Create colored icon for system tray based on state.
        
        Args:
            state: Current Nexa state
            size: Icon size in pixels
            
        Returns:
            QIcon with state-appropriate color
        """
        # State colors
        state_colors = {
            NexaState.IDLE: QColor(100, 100, 100),
            NexaState.LISTENING: QColor(0, 217, 255),
            NexaState.THINKING: QColor(157, 0, 255),
            NexaState.SPEAKING: QColor(0, 255, 136),
            NexaState.EXECUTING: QColor(157, 0, 255),
            NexaState.CONTENT_MODE: QColor(147, 51, 234),  # Deep purple for content work
            NexaState.ERROR: QColor(255, 50, 50)
        }
        
        color = state_colors.get(state, state_colors[NexaState.IDLE])
        
        # Create pixmap
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        # Draw circle
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw filled circle
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, size - 4, size - 4)
        
        # Draw inner highlight
        highlight = QColor(255, 255, 255, 100)
        painter.setBrush(highlight)
        painter.drawEllipse(int(size * 0.2), int(size * 0.2), 
                          int(size * 0.3), int(size * 0.3))
        
        painter.end()
        
        return QIcon(pixmap)
    
    def _create_context_menu(self):
        """Create context menu with quick actions."""
        menu = QMenu()
        
        # Show/Hide window
        self.show_action = QAction("Show Nexa", self)
        self.show_action.triggered.connect(self._toggle_window)
        menu.addAction(self.show_action)
        
        menu.addSeparator()
        
        # Pause/Resume listening
        self.pause_action = QAction("⏸️ Pause Listening", self)
        self.pause_action.triggered.connect(self._toggle_listening)
        menu.addAction(self.pause_action)
        
        # Online/Offline toggle
        self.mode_action = QAction("🌐 Switch to Offline", self)
        self.mode_action.triggered.connect(self._toggle_mode)
        menu.addAction(self.mode_action)
        
        menu.addSeparator()
        
        # Clear history
        clear_action = QAction("🧹 Clear History", self)
        clear_action.triggered.connect(self._clear_history)
        menu.addAction(clear_action)
        
        menu.addSeparator()
        
        # Exit
        exit_action = QAction("❌ Exit Nexa", self)
        exit_action.triggered.connect(self._exit_application)
        menu.addAction(exit_action)
        
        self.setContextMenu(menu)
        
        logger.debug("System tray context menu created")
    
    def _on_tray_activated(self, reason):
        """
        Handle tray icon activation.
        
        Args:
            reason: Activation reason (click, double-click, etc.)
        """
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_window()
        elif reason == QSystemTrayIcon.Trigger:
            # Single click on Windows shows context menu
            pass
    
    def _toggle_window(self):
        """Show or hide main window."""
        if self.parent_window:
            if self.parent_window.isVisible():
                self.parent_window.hide()
                self.show_action.setText("Show Nexa")
                self.showMessage(
                    "Nexa Minimized",
                    "Nexa is running in the background. Click the tray icon to restore.",
                    QSystemTrayIcon.Information,
                    2000
                )
            else:
                self.parent_window.show()
                self.parent_window.activateWindow()
                self.show_action.setText("Hide Nexa")
    
    def _toggle_listening(self):
        """Toggle listening state."""
        if self.parent_window and hasattr(self.parent_window, 'brain'):
            brain = self.parent_window.brain
            
            if hasattr(brain, 'listener') and brain.listener:
                if brain.listener.is_listening:
                    brain.listener.stop_listening()
                    self.pause_action.setText("▶️ Resume Listening")
                    self.showMessage(
                        "Listening Paused",
                        "Nexa will not respond to voice commands.",
                        QSystemTrayIcon.Information,
                        2000
                    )
                else:
                    brain.listener.start_listening()
                    self.pause_action.setText("⏸️ Pause Listening")
                    self.showMessage(
                        "Listening Resumed",
                        "Nexa is now listening for commands.",
                        QSystemTrayIcon.Information,
                        2000
                    )
    
    def _toggle_mode(self):
        """Toggle between online and offline mode."""
        if self.parent_window and hasattr(self.parent_window, 'brain'):
            brain = self.parent_window.brain
            
            if hasattr(brain, 'llm_manager'):
                current_mode = brain.llm_manager.current_mode
                
                if current_mode == "online":
                    brain.llm_manager.switch_to_offline()
                    self.mode_action.setText("🌐 Switch to Online")
                    self.showMessage(
                        "Offline Mode",
                        "Using local Llama3 model.",
                        QSystemTrayIcon.Information,
                        2000
                    )
                else:
                    brain.llm_manager.switch_to_online()
                    self.mode_action.setText("💻 Switch to Offline")
                    self.showMessage(
                        "Online Mode",
                        "Using Llama 3.1 AI.",
                        QSystemTrayIcon.Information,
                        2000
                    )
    
    def _clear_history(self):
        """Clear conversation history."""
        if self.parent_window and hasattr(self.parent_window, 'chat_display'):
            self.parent_window.chat_display.clear_history()
            if hasattr(self.parent_window, 'brain'):
                self.parent_window.brain.context_manager.clear_history()
            
            self.showMessage(
                "History Cleared",
                "Conversation history has been cleared.",
                QSystemTrayIcon.Information,
                2000
            )
    
    def _exit_application(self):
        """Exit the application."""
        if self.parent_window:
            # Actually quit, not just close
            if hasattr(self.parent_window, 'quit_application'):
                self.parent_window.quit_application()
            else:
                self.parent_window.close()
    
    def update_state(self, state: NexaState):
        """
        Update tray icon to reflect current state.
        
        Args:
            state: New Nexa state
        """
        self.current_state = state
        
        # Update icon
        icon = self._create_icon(state)
        self.setIcon(icon)
        
        # Update tooltip
        state_text = {
            NexaState.IDLE: "Idle",
            NexaState.LISTENING: "Listening...",
            NexaState.THINKING: "Thinking...",
            NexaState.SPEAKING: "Speaking...",
            NexaState.EXECUTING: "Executing...",
            NexaState.CONTENT_MODE: "Content Mode",
            NexaState.ERROR: "Error"
        }
        
        tooltip = f"Nexa AI Assistant - {state_text.get(state, 'Active')}"
        self.setToolTip(tooltip)
        
        logger.debug(f"System tray updated: {state.value}")
    
    def show_notification(self, title: str, message: str, duration: int = 3000):
        """
        Show system notification.
        
        Args:
            title: Notification title
            message: Notification message
            duration: Duration in milliseconds
        """
        self.showMessage(title, message, QSystemTrayIcon.Information, duration)
