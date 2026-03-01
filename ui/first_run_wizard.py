import sys
import os
import shutil
import subprocess
import json
import logging
from pathlib import Path
from PySide6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QLabel, 
                               QProgressBar, QMessageBox, QApplication, 
                               QPushButton, QHBoxLayout, QLineEdit)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon

logger = logging.getLogger(__name__)

def get_user_data_dir() -> Path:
    """Get the user-writable data directory for .env, config, etc.
    Uses %LOCALAPPDATA%\\Nexa AI when running as exe (works in Program Files).
    Uses project root when running from source."""
    if getattr(sys, 'frozen', False):
        appdata_dir = Path(os.environ.get('LOCALAPPDATA', Path(sys.executable).parent)) / 'Nexa AI'
        appdata_dir.mkdir(parents=True, exist_ok=True)
        return appdata_dir
    else:
        return Path(__file__).parent.parent

def get_app_root() -> Path:
    """Get the application root directory (where exe lives).
    DEPRECATED: Use get_user_data_dir() for user-writable data."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent

def get_bundle_root() -> Path:
    """Get the bundled data root directory (for assets, config templates, etc.)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent

class WorkerThread(QThread):
    progress = Signal(str)
    finished = Signal(bool)

    def __init__(self, command):
        super().__init__()
        self.command = command

    def run(self):
        try:
            process = subprocess.Popen(
                self.command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.progress.emit(output.strip())
            
            rc = process.poll()
            self.finished.emit(rc == 0)
        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")
            self.finished.emit(False)

class IntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to Nexa Beta")
        self.setSubTitle("Let's get everything set up for you.")
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Logo section
        logo_layout = QHBoxLayout()
        logo_layout.addStretch()
        
        logo_label = QLabel()
        # Try to load the icon (bundled asset)
        icon_path = get_bundle_root() / 'assets' / 'icon.ico'
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                # Scale to reasonable size
                scaled_pixmap = pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
        
        logo_layout.addWidget(logo_label)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)
        
        # Welcome text
        welcome_label = QLabel("✨ Welcome to Nexa AI Assistant! ✨")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2196F3;")
        layout.addWidget(welcome_label)
        
        # Description
        desc_label = QLabel(
            "This wizard will help you set up Nexa:\n\n"
            "  1️⃣  Check for Ollama (AI Engine)\n"
            "  2️⃣  Download the Llama 3.1 8B Model\n"
            "  3️⃣  Set up your name for personalization\n"
            "  4️⃣  Configure optional features (weather, etc.)\n\n"
            "Click Next to continue."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 13px; padding: 10px;")
        layout.addWidget(desc_label)
        
        layout.addStretch()
        self.setLayout(layout)

class DependencyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Checking Dependencies")
        self.setSubTitle("Verifying AI Engine and Model...")
        
        self.layout = QVBoxLayout()
        
        self.status_label = QLabel("Status: Waiting to start...")
        self.layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.progress_bar.hide()
        self.layout.addWidget(self.progress_bar)
        
        self.setLayout(self.layout)
        self.is_complete = False

    def initializePage(self):
        self.check_dependencies()

    def check_dependencies(self):
        # 1. Check Ollama
        if not shutil.which("ollama"):
            QMessageBox.critical(self, "Ollama Missing", 
                                 "Ollama is not installed.\nPlease install it from ollama.com and restart this installer.")
            QApplication.quit()
            return

        self.status_label.setText("Ollama found. Checking for Llama 3.1 8b model...")
        
        # 2. Check Model
        self.check_model()

    def check_model(self):
        try:
            result = subprocess.run("ollama list", shell=True, capture_output=True, text=True)
            if "llama3.1:8b" in result.stdout:
                self.status_label.setText("✅ Model 'llama3.1:8b' is already installed!")
                self.is_complete = True
                self.completeChanged.emit()
            else:
                self.status_label.setText("Model not found. Downloading Llama 3.1 8b (approx 4.7GB)... This may take a while.")
                self.download_model()
        except Exception as e:
            self.status_label.setText(f"Error checking model: {e}")

    def download_model(self):
        self.progress_bar.show()
        self.worker = WorkerThread("ollama pull llama3.1:8b")
        self.worker.progress.connect(self.update_status)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.start()

    def update_status(self, text):
        # Update label with last line of output (progress)
        if "%" in text or "pulling" in text:
            self.status_label.setText(f"Downloading: {text}")

    def on_download_finished(self, success):
        self.progress_bar.hide()
        if success:
            self.status_label.setText("✅ Model downloaded successfully!")
            self.is_complete = True
            self.completeChanged.emit()
        else:
            self.status_label.setText("❌ Download failed. Please try running 'ollama pull llama3.1:8b' manually.")

    def isComplete(self):
        return self.is_complete


class VoiceNamePage(QWizardPage):
    """
    Voice-based name capture page for the First Run Wizard.
    User speaks their name and Nexa captures it via voice.
    """
    
    def __init__(self, config=None):
        super().__init__()
        self.setTitle("Let's Get Acquainted")
        self.setSubTitle("Tell me your name so I can personalize your experience.")
        
        self.config = config
        self.user_name = None
        self.listener = None
        self.is_listening = False
        self.is_complete = False
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Instructions
        instructions = QLabel(
            "🎤 When you click 'Start Listening', say your name clearly.\n\n"
            "For example: \"My name is Alex\" or just \"Alex\"\n\n"
            "I'll repeat it back to confirm."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(instructions)
        
        # Status display
        self.status_label = QLabel("Click 'Start Listening' when you're ready.")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            font-size: 16px; 
            padding: 20px; 
            background-color: rgba(100, 100, 100, 0.2);
            border-radius: 10px;
        """)
        layout.addWidget(self.status_label)
        
        # Captured name display
        self.name_display = QLabel("")
        self.name_display.setAlignment(Qt.AlignCenter)
        self.name_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50; padding: 10px;")
        layout.addWidget(self.name_display)
        
        # Buttons layout
        btn_layout = QHBoxLayout()
        
        # Start Listening button
        self.listen_btn = QPushButton("🎤 Start Listening")
        self.listen_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #888;
            }
        """)
        self.listen_btn.clicked.connect(self._start_listening)
        btn_layout.addWidget(self.listen_btn)
        
        # Confirm button (hidden initially)
        self.confirm_btn = QPushButton("✓ That's Correct")
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        self.confirm_btn.clicked.connect(self._confirm_name)
        self.confirm_btn.hide()
        btn_layout.addWidget(self.confirm_btn)
        
        # Retry button (hidden initially)
        self.retry_btn = QPushButton("Try Again")
        self.retry_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.retry_btn.clicked.connect(self._retry_listening)
        self.retry_btn.hide()
        btn_layout.addWidget(self.retry_btn)
        
        layout.addLayout(btn_layout)
        
        # Manual entry fallback
        layout.addSpacing(20)
        fallback_label = QLabel("Or type your name manually:")
        fallback_label.setStyleSheet("font-size: 12px; color: #888;")
        layout.addWidget(fallback_label)
        
        manual_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your name here...")
        self.name_input.setStyleSheet("font-size: 14px; padding: 8px; border-radius: 5px;")
        self.name_input.textChanged.connect(self._on_manual_input)
        manual_layout.addWidget(self.name_input)
        
        self.manual_confirm_btn = QPushButton("Use This Name")
        self.manual_confirm_btn.setEnabled(False)
        self.manual_confirm_btn.clicked.connect(self._confirm_manual_name)
        manual_layout.addWidget(self.manual_confirm_btn)
        
        layout.addLayout(manual_layout)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def _start_listening(self):
        """Start voice listening for name capture."""
        self.listen_btn.setEnabled(False)
        self.listen_btn.setText("🎧 Listening...")
        self.status_label.setText("Listening... Say your name now!")
        self.status_label.setStyleSheet("""
            font-size: 16px; 
            padding: 20px; 
            background-color: rgba(33, 150, 243, 0.3);
            border-radius: 10px;
            border: 2px solid #2196F3;
        """)
        
        # Use a timer to simulate listening (actual implementation would use listener)
        QTimer.singleShot(100, self._do_voice_capture)
    
    def _do_voice_capture(self):
        """Perform actual voice capture."""
        try:
            # Try to import and use the listener
            from core.interface.voice_listener import Listener
            
            # Create a temporary listener for name capture
            temp_listener = Listener()
            
            # Listen for a single utterance
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self.status_label.setText("🎤 Speak now...")
                
                try:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    text = recognizer.recognize_google(audio)
                    
                    # Extract name from text
                    name = self._extract_name(text)
                    if name:
                        self.user_name = name
                        self._show_captured_name(name)
                    else:
                        self._show_error("Couldn't understand. Please try again.")
                        
                except sr.WaitTimeoutError:
                    self._show_error("Didn't hear anything. Please try again.")
                except sr.UnknownValueError:
                    self._show_error("Couldn't understand. Please speak more clearly.")
                except sr.RequestError:
                    self._show_error("Speech recognition unavailable. Please type your name.")
                    
        except ImportError as e:
            logger.warning(f"Could not import listener: {e}")
            self._show_error("Voice recognition not available. Please type your name.")
        except Exception as e:
            logger.error(f"Voice capture error: {e}")
            self._show_error("Voice capture failed. Please type your name.")
    
    def _extract_name(self, text: str) -> str:
        """Extract name from spoken text."""
        text = text.strip()
        
        # Common patterns: "My name is X", "I'm X", "It's X", "Call me X", or just "X"
        patterns = [
            "my name is ", "i'm ", "im ", "i am ", "it's ", "its ",
            "call me ", "they call me ", "you can call me "
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            if pattern in text_lower:
                idx = text_lower.find(pattern)
                name = text[idx + len(pattern):].strip()
                # Capitalize first letter
                return name.title().split()[0] if name else None
        
        # If no pattern matched, assume the whole text is the name
        # Take only the first word
        words = text.split()
        if words:
            return words[0].title()
        
        return None
    
    def _show_captured_name(self, name: str):
        """Show the captured name for confirmation."""
        self.name_display.setText(f"Hello, {name}!")
        self.status_label.setText(f"Did I hear that correctly? Your name is \"{name}\"?")
        self.status_label.setStyleSheet("""
            font-size: 16px; 
            padding: 20px; 
            background-color: rgba(76, 175, 80, 0.2);
            border-radius: 10px;
            border: 2px solid #4CAF50;
        """)
        
        self.listen_btn.hide()
        self.confirm_btn.show()
        self.retry_btn.show()
    
    def _show_error(self, message: str):
        """Show error message."""
        self.status_label.setText(f"❌ {message}")
        self.status_label.setStyleSheet("""
            font-size: 16px; 
            padding: 20px; 
            background-color: rgba(244, 67, 54, 0.2);
            border-radius: 10px;
        """)
        self.listen_btn.setEnabled(True)
        self.listen_btn.setText("🎤 Start Listening")
    
    def _retry_listening(self):
        """Retry voice capture."""
        self.user_name = None
        self.name_display.setText("")
        self.confirm_btn.hide()
        self.retry_btn.hide()
        self.listen_btn.show()
        self.listen_btn.setEnabled(True)
        self.listen_btn.setText("🎤 Start Listening")
        self.status_label.setText("Click 'Start Listening' when you're ready.")
        self.status_label.setStyleSheet("""
            font-size: 16px; 
            padding: 20px; 
            background-color: rgba(100, 100, 100, 0.2);
            border-radius: 10px;
        """)
    
    def _confirm_name(self):
        """Confirm the captured name and save it."""
        if self.user_name:
            self._save_name(self.user_name)
            self.is_complete = True
            self.status_label.setText(f"✅ Great! Nice to meet you, {self.user_name}!")
            self.status_label.setStyleSheet("""
                font-size: 16px; 
                padding: 20px; 
                background-color: rgba(76, 175, 80, 0.3);
                border-radius: 10px;
            """)
            self.confirm_btn.hide()
            self.retry_btn.hide()
            self.completeChanged.emit()
    
    def _on_manual_input(self, text: str):
        """Handle manual name input."""
        self.manual_confirm_btn.setEnabled(len(text.strip()) >= 2)
    
    def _confirm_manual_name(self):
        """Confirm manually entered name."""
        name = self.name_input.text().strip().title()
        if name:
            self.user_name = name
            self._save_name(name)
            self.is_complete = True
            self.name_display.setText(f"Hello, {name}!")
            self.status_label.setText(f"✅ Great! Nice to meet you, {name}!")
            self.status_label.setStyleSheet("""
                font-size: 16px; 
                padding: 20px; 
                background-color: rgba(76, 175, 80, 0.3);
                border-radius: 10px;
            """)
            self.name_input.setEnabled(False)
            self.manual_confirm_btn.setEnabled(False)
            self.listen_btn.hide()
            self.confirm_btn.hide()
            self.retry_btn.hide()
            self.completeChanged.emit()
    
    def _save_name(self, name: str):
        """Save the user's name to user_prefs.json."""
        try:
            # Determine data directory
            prefs_path = get_app_root() / 'data' / 'user_prefs.json'
            
            # Load existing prefs or create new
            prefs = {}
            if prefs_path.exists():
                with open(prefs_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
                    prefs = json.load(f)
            
            # Update user name
            prefs['user_name'] = name
            
            # Save back
            prefs_path.parent.mkdir(parents=True, exist_ok=True)
            with open(prefs_path, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2)
            
            logger.info(f"✅ Saved user name: {name}")
            
            # Also update config if available
            if self.config:
                self.config.user_name = name
                
        except Exception as e:
            logger.error(f"Failed to save user name: {e}")
    
    def isComplete(self):
        return self.is_complete


class APIKeysPage(QWizardPage):
    """
    Optional API keys setup page.
    Users can add their own API keys for optional features like weather.
    """
    
    def __init__(self, config=None):
        super().__init__()
        self.setTitle("Optional Features Setup")
        self.setSubTitle("Add API keys for extra features (you can skip this)")
        
        self.config = config
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Info label
        info = QLabel(
            "🌤️ <b>Weather Features</b><br><br>"
            "To enable weather commands like 'What's the weather?' you need a free API key.<br><br>"
            "📌 Get your free key from: <a href='https://openweathermap.org/api'>openweathermap.org/api</a><br>"
            "📌 Free tier: 1,000 calls/day (more than enough!)<br><br>"
            "This step is <b>optional</b> - Nexa works great without it!"
        )
        info.setWordWrap(True)
        info.setOpenExternalLinks(True)
        info.setStyleSheet("font-size: 13px; padding: 10px; background-color: rgba(100, 100, 100, 0.1); border-radius: 8px;")
        layout.addWidget(info)
        
        # Weather API Key input
        weather_layout = QHBoxLayout()
        weather_label = QLabel("OpenWeatherMap API Key:")
        weather_label.setStyleSheet("font-weight: bold;")
        weather_layout.addWidget(weather_label)
        
        self.weather_key_input = QLineEdit()
        self.weather_key_input.setPlaceholderText("Paste your API key here (optional)")
        self.weather_key_input.setEchoMode(QLineEdit.EchoMode.Password)  # Hide key
        self.weather_key_input.setStyleSheet("padding: 8px; border-radius: 5px; font-size: 13px;")
        weather_layout.addWidget(self.weather_key_input)
        
        # Show/Hide button
        self.show_key_btn = QPushButton("👁")
        self.show_key_btn.setFixedWidth(40)
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.clicked.connect(self._toggle_key_visibility)
        weather_layout.addWidget(self.show_key_btn)
        
        layout.addLayout(weather_layout)
        
        # Test button
        test_layout = QHBoxLayout()
        test_layout.addStretch()
        
        self.test_btn = QPushButton("🔍 Test API Key")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.test_btn.clicked.connect(self._test_api_key)
        test_layout.addWidget(self.test_btn)
        
        layout.addLayout(test_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Skip note
        skip_note = QLabel(
            "💡 <i>You can always add API keys later by editing the .env file in Nexa's folder.</i>"
        )
        skip_note.setWordWrap(True)
        skip_note.setStyleSheet("color: #888; font-size: 11px; padding-top: 20px;")
        layout.addWidget(skip_note)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _toggle_key_visibility(self):
        """Toggle API key visibility."""
        if self.show_key_btn.isChecked():
            self.weather_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("🔒")
        else:
            self.weather_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("👁")
    
    def _test_api_key(self):
        """Test the weather API key."""
        api_key = self.weather_key_input.text().strip()
        
        if not api_key:
            self.status_label.setText("⚠️ Please enter an API key first")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 13px;")
            return
        
        self.status_label.setText("🔄 Testing API key...")
        self.status_label.setStyleSheet("color: #2196F3; font-size: 13px;")
        self.test_btn.setEnabled(False)
        
        # Test in background
        QTimer.singleShot(100, lambda: self._do_test(api_key))
    
    def _do_test(self, api_key: str):
        """Perform actual API test."""
        try:
            import requests
            
            # Test with a simple weather request
            url = f"https://api.openweathermap.org/data/2.5/weather?q=London&appid={api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                self.status_label.setText("✅ API key is valid! Weather features will be enabled.")
                self.status_label.setStyleSheet("color: #4CAF50; font-size: 13px; font-weight: bold;")
            elif response.status_code == 401:
                self.status_label.setText("❌ Invalid API key. Please check and try again.")
                self.status_label.setStyleSheet("color: #F44336; font-size: 13px;")
            else:
                self.status_label.setText(f"⚠️ Unexpected response: {response.status_code}")
                self.status_label.setStyleSheet("color: #FF9800; font-size: 13px;")
                
        except requests.exceptions.Timeout:
            self.status_label.setText("⚠️ Connection timed out. Check your internet connection.")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 13px;")
        except Exception as e:
            self.status_label.setText(f"❌ Test failed: {str(e)}")
            self.status_label.setStyleSheet("color: #F44336; font-size: 13px;")
        
        self.test_btn.setEnabled(True)
    
    def validatePage(self):
        """Save API key when moving to next page."""
        api_key = self.weather_key_input.text().strip()
        
        if api_key:
            self._save_api_key(api_key)
        
        return True  # Always allow proceeding (API key is optional)
    
    def _save_api_key(self, api_key: str):
        """Save API key to .env file in user data directory."""
        try:
            # Use user data directory (works even in Program Files)
            user_data = get_user_data_dir()
            env_path = user_data / '.env'
            
            # Get .env.example from bundle (if exists) for template
            env_example_path = get_bundle_root() / '.env.example'
            
            # If .env doesn't exist, copy from .env.example or create new
            if not env_path.exists():
                if env_example_path.exists():
                    shutil.copy(env_example_path, env_path)
                else:
                    # Create minimal .env
                    env_path.write_text("# Nexa Configuration\n\n", encoding='utf-8')
            
            # Read existing .env
            env_content = ""
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_content = f.read()
            
            # Update or add OPENWEATHERMAP_API_KEY
            if 'OPENWEATHERMAP_API_KEY=' in env_content:
                # Replace existing key
                lines = env_content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('OPENWEATHERMAP_API_KEY='):
                        lines[i] = f'OPENWEATHERMAP_API_KEY={api_key}'
                        break
                env_content = '\n'.join(lines)
            else:
                # Add new key
                env_content += f'\nOPENWEATHERMAP_API_KEY={api_key}\n'
            
            # Save
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            logger.info(f"✅ Weather API key saved to {env_path}")
            
            # Update config if available
            if self.config:
                self.config.weather_api_key = api_key
                
        except Exception as e:
            logger.error(f"Failed to save API key: {e}")


class FirstRunWizard(QWizard):
    def __init__(self, config=None):
        super().__init__()
        self.setWindowTitle("Nexa Setup Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(600, 500)
        self.config = config
        
        # Set window icon (bundled asset)
        icon_path = get_bundle_root() / 'assets' / 'icon.ico'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Wizard pages in order:
        # 1. Welcome/Intro
        # 2. Check Ollama & download model
        # 3. Voice name capture
        # 4. Optional API keys (weather, etc.)
        self.addPage(IntroPage())
        self.addPage(DependencyPage())
        self.addPage(VoiceNamePage(config))
        self.addPage(APIKeysPage(config))  # Optional API keys setup
        
        self.setOption(QWizard.NoCancelButton, False)
        
    def accept(self):
        # Create a flag file to indicate setup is done
        super().accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = FirstRunWizard()
    wizard.show()
    sys.exit(app.exec())
