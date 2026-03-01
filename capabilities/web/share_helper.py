"""
Custom Share Dialog for Windows
Shows a modern dialog with sharing options when native Windows Share UI is unavailable
"""
import subprocess
import sys
import os
import shutil
import winreg
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QListWidget, QListWidgetItem, 
                             QMessageBox, QFrame, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QLinearGradient, QPainter

class ShareDialog(QDialog):
    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path
        self.result = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Share")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setMinimumHeight(550)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Main container with rounded corners
        main_container = QFrame(self)
        main_container.setObjectName("mainContainer")
        main_container.setStyleSheet("""
            QFrame#mainContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f5f7fa);
                border-radius: 16px;
                border: 1px solid rgba(0, 0, 0, 0.08);
            }
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 40))
        main_container.setGraphicsEffect(shadow)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_container)
        
        # Content layout inside container
        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #6b7280;
                font-size: 28px;
                font-weight: bold;
                border-radius: 16px;
            }
            QPushButton:hover {
                background: #f3f4f6;
                color: #111827;
            }
        """)
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)
        
        # Header section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel("Share File")
        title.setStyleSheet("""
            QLabel {
                color: #111827;
                font-size: 26px;
                font-weight: 700;
                letter-spacing: -0.5px;
            }
        """)
        header_layout.addWidget(title)
        
        # File info card
        file_card = QFrame()
        file_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(16, 16, 16, 16)
        
        filename = QLabel(self.file_path.name)
        filename.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 15px;
                font-weight: 600;
            }
        """)
        filename.setWordWrap(True)
        file_layout.addWidget(filename)
        
        file_size = self.file_path.stat().st_size / 1024
        if file_size > 1024:
            size_text = f"{file_size / 1024:.1f} MB"
        else:
            size_text = f"{file_size:.1f} KB"
            
        file_info = QLabel(f"📄 {size_text}")
        file_info.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
            }
        """)
        file_layout.addWidget(file_info)
        
        header_layout.addWidget(file_card)
        layout.addLayout(header_layout)
        
        # Share options label
        options_label = QLabel("Choose sharing method")
        options_label.setStyleSheet("""
            QLabel {
                color: #6b7280;
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
        """)
        layout.addWidget(options_label)
        
        # Share options list
        self.options_list = QListWidget()
        self.options_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 8px;
                outline: none;
            }
            QListWidget::item {
                background: transparent;
                color: #111827;
                font-size: 14px;
                padding: 14px 16px;
                border-radius: 8px;
                margin: 2px 0px;
            }
            QListWidget::item:hover {
                background: #f3f4f6;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                color: white;
                font-weight: 600;
            }
        """)
        self.options_list.setIconSize(QSize(24, 24))
        self.options_list.setSpacing(2)
        
        # Detect available sharing methods
        self.share_methods = self.detect_share_methods()
        
        for method in self.share_methods:
            item_text = f"{method['icon']}  {method['name']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, method)
            self.options_list.addItem(item)
        
        self.options_list.itemDoubleClicked.connect(self.on_share_clicked)
        layout.addWidget(self.options_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(44)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #f3f4f6;
                color: #374151;
                border: none;
                border-radius: 10px;
                padding: 0px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #e5e7eb;
            }
            QPushButton:pressed {
                background: #d1d5db;
            }
        """)
        
        share_btn = QPushButton("Share")
        share_btn.setFixedHeight(44)
        share_btn.clicked.connect(self.on_share_clicked)
        share_btn.setDefault(True)
        share_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0px 32px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #7c3aed);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1d4ed8, stop:1 #6d28d9);
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(share_btn)
        
        layout.addLayout(button_layout)
        
    def detect_share_methods(self):
        """Detect available sharing applications and methods"""
        methods = []
        
        # 1. Copy File to Clipboard (Universal - RECOMMENDED)
        methods.append({
            'name': 'Copy File (Recommended) ⭐',
            'icon': '📎',
            'action': 'clipboard_file',
            'description': 'Paste anywhere: WhatsApp, Telegram, Email'
        })
        
        # 2. Google Drive Upload
        methods.append({
            'name': 'Google Drive',
            'icon': '☁️',
            'action': 'google_drive',
            'description': 'Upload to cloud storage'
        })
        
        # 3. Open File Location
        methods.append({
            'name': 'Open File Location',
            'icon': '📁',
            'action': 'open_location',
            'description': 'View in Explorer'
        })
        
        # 4. Copy File Path
        methods.append({
            'name': 'Copy File Path',
            'icon': '📋',
            'action': 'clipboard_path',
            'description': 'Copy path as text'
        })
        
        return methods
    
    def check_protocol_handler(self, protocol):
        """Check if a protocol handler is registered"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, protocol)
            winreg.CloseKey(key)
            return True
        except:
            return False
    
    def on_share_clicked(self):
        """Handle share button click"""
        current_item = self.options_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a sharing method")
            return
        
        method = current_item.data(Qt.UserRole)
        self.result = method
        
        try:
            if method['action'] == 'google_drive':
                self.share_google_drive()
            elif method['action'] == 'clipboard_path':
                self.copy_to_clipboard()
            elif method['action'] == 'clipboard_file':
                self.copy_file_to_clipboard()
            elif method['action'] == 'open_location':
                self.open_file_location()
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to share: {str(e)}")
    
    def share_google_drive(self):
        """Upload file to Google Drive"""
        try:
            # Import the sharing service to use its Google Drive upload method
            import sys
            from pathlib import Path
            
            # Add parent directory to path to import sharing_service
            sys.path.insert(0, str(Path(__file__).parent))
            from sharing_service import SharingService
            
            sharing = SharingService()
            
            # Show progress message
            progress_msg = QMessageBox(self)
            progress_msg.setWindowTitle("Google Drive")
            progress_msg.setText("⏳ Uploading to Google Drive...\n\nPlease wait...")
            progress_msg.setStandardButtons(QMessageBox.NoButton)
            progress_msg.show()
            QApplication.processEvents()
            
            # Upload file
            result = sharing.copy_to_google_drive(str(self.file_path))
            
            progress_msg.close()
            
            if result.get('success'):
                QMessageBox.information(self, "Google Drive", 
                                       f"✅ File uploaded successfully!\n\n"
                                       f"📁 Location: {result.get('location', 'Google Drive')}\n"
                                       f"📎 File: {result.get('file_name', self.file_path.name)}")
            else:
                QMessageBox.warning(self, "Google Drive", 
                                   f"⚠️ Upload failed\n\n{result.get('message', 'Unknown error')}")
                
        except Exception as e:
            QMessageBox.critical(self, "Google Drive Error", 
                               f"Failed to upload to Google Drive:\n{str(e)}")
    
    def copy_to_clipboard(self):
        """Copy file path to clipboard"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(str(self.file_path))
        QMessageBox.information(self, "Copied", "File path copied to clipboard")
    
    def copy_file_to_clipboard(self):
        """Copy actual file to clipboard"""
        # Use Windows.Forms to copy file to clipboard (works with Ctrl+V in chat apps)
        ps_cmd = f'''
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.Clipboard]::Clear()
        $files = New-Object System.Collections.Specialized.StringCollection
        $files.Add("{self.file_path}")
        [System.Windows.Forms.Clipboard]::SetFileDropList($files)
        '''
        subprocess.run(['powershell', '-Command', ps_cmd], check=True, 
                      capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        QMessageBox.information(self, "✅ Ready to Share!", 
                               f"📎 File copied to clipboard!\n\n"
                               f"📄 {self.file_path.name}\n\n"
                               f"🚀 How to share:\n\n"
                               f"📱 To Phone:\n"
                               f"  • Open WhatsApp/Telegram on phone\n"
                               f"  • Open any chat → Press Ctrl+V\n"
                               f"  • File attaches automatically!\n\n"
                               f"💻 On PC:\n"
                               f"  • Any chat app → Ctrl+V\n"
                               f"  • Email → Ctrl+V to attach\n"
                               f"  • Explorer → Ctrl+V to paste\n\n"
                               f"✨ Works everywhere!")
    
    def open_file_location(self):
        """Open file location in Explorer"""
        subprocess.Popen(f'explorer.exe /select,"{self.file_path}"')
        QMessageBox.information(self, "File Location", 
                               f"📁 File location opened\n\n"
                               f"{self.file_path.name}\n\n"
                               f"You can:\n"
                               f"• Drag file to any app\n"
                               f"• Right-click for more options\n"
                               f"• Copy and move as needed")

def open_share_dialog_with_file(file_path: str):
    """
    Opens custom share dialog with various sharing options
    Returns True if user selected a sharing method
    """
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return False
    
    app = QApplication(sys.argv)
    dialog = ShareDialog(file_path)
    result = dialog.exec_()
    
    return result == QDialog.Accepted

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: share_helper.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    success = open_share_dialog_with_file(file_path)
    sys.exit(0 if success else 1)
