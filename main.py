"""
Nexa - Hybrid AI Desktop Assistant
Main Entry Point

Created by: Ali Adil Waseem
"""
import sys
import os
import logging
from pathlib import Path

# Set up project root before other imports
# Handle both development and frozen (PyInstaller) environments
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    # APP_ROOT = where exe lives (for user data)
    # BUNDLE_ROOT = where bundled data lives (_internal folder)
    APP_ROOT = Path(sys.executable).parent
    BUNDLE_ROOT = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else APP_ROOT
else:
    # Running as script - both point to same location
    APP_ROOT = Path(__file__).parent
    BUNDLE_ROOT = APP_ROOT

# PROJECT_ROOT kept for backward compatibility
PROJECT_ROOT = APP_ROOT

# Add project root to Python path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import core modules
from config.settings import Config
from core.brain import NexaBrain
from capabilities.llm.gpu_monitor import GPUMonitor
from core.kernel import NexaKernel
from utils.logging_formatter import setup_logging, log_section
from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity

# Import UI components
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, Signal, QObject, QTimer
from ui.nexa_modern_window import NexaModernWindow
from capabilities.web.auth_manager import AuthManager
from ui.login_dialog import LoginDialog
from ui.widgets.loading_dialog import LoadingDialog

# Global references
hud_window = None
brain_instance = None
config_instance = None
gpu_monitor = None  # GPU monitor instance
kernel_instance = None  # Core AI Kernel instance


class InitWorker(QThread):
    """
    Background thread for heavy initialization (model loading).
    Emits signals so the main thread event loop stays free and the
    loading spinner keeps spinning smoothly.
    """
    status_update = Signal(str, str)      # (status_text, detail_text)
    finished_ok = Signal(object, object)  # (config, brain)
    finished_fail = Signal()

    def run(self):
        """Run initialization in background thread."""
        logger = logging.getLogger(__name__)
        log_section(logger, "NEXA AI ASSISTANT - INITIALIZATION", logging.INFO)

        def update_status(status, detail=""):
            self.status_update.emit(status, detail)

        try:
            # Load configuration
            update_status("Loading configuration...", "Reading settings and environment")
            logger.info("📋 Loading configuration...")
            config = Config()
            logger.info("✅ Configuration loaded successfully")

            # Verify critical paths
            update_status("Verifying system...", "Checking models and paths")
            logger.info("🔍 Verifying system requirements...")
            if not config.verify_setup():
                logger.error("❌ System verification failed. Check your .env and model paths.")
                self.finished_fail.emit()
                return

            logger.info("✅ System verification passed")

            # Initialize Nexa Brain (heavy — loads LLM, STT, TTS models)
            update_status("Initializing AI Brain...", "Loading LLM, STT, and TTS models")
            logger.info("🧠 Initializing Nexa Brain...")
            brain = NexaBrain(config)
            logger.info("✅ Nexa Brain initialized successfully")

            # Verify LLM model is ready
            if brain.llm_manager.ollama_prewarmed:
                update_status("AI model ready!", "Pre-warmed for instant responses")
                logger.info("🚀 AI model pre-warmed and ready!")
            else:
                logger.warning("⚠️ AI model not pre-warmed")

            # Initialize GPU Monitor
            update_status("Starting GPU Monitor...", "Tracking model memory usage")
            logger.info("📊 Initializing GPU Monitor...")
            global gpu_monitor
            gpu_reports_dir = config.logs_dir / "gpu_reports"
            gpu_reports_dir.mkdir(parents=True, exist_ok=True)
            gpu_monitor = GPUMonitor(gpu_reports_dir)
            gpu_monitor.start_monitoring()

            gpu_monitor.register_model_load("Faster-Whisper (large-v3)")
            gpu_monitor.register_model_load("Llama 3.1 8B")
            gpu_monitor.register_model_load("SpeechBrain ECAPA-TDNN")
            logger.info("✅ GPU Monitor started successfully")

            # Initialize Core AI Kernel
            update_status("Starting Core Kernel...", "Task governance and priority scheduling")
            logger.info("🔷 Initializing Core AI Kernel...")
            global kernel_instance
            kernel_instance = NexaKernel(gpu_monitor=gpu_monitor)
            logger.info("✅ Core AI Kernel initialized")

            self.finished_ok.emit(config, brain)

        except Exception as e:
            user_msg, recovered = handle_error(
                error=e,
                context="initialize_application",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.CRITICAL,
                user_message="Failed to start Nexa. Please check configuration.",
                recovery_suggestion="Verify .env file and system requirements"
            )
            logger.critical(f"CRITICAL: {user_msg}")
            self.finished_fail.emit()


def main():
    """
    Main application entry point.
    Initializes Qt application, Nexa components, and starts the event loop.
    """
    global hud_window, brain_instance, config_instance
    
    # Setup enhanced logging FIRST
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Use %LOCALAPPDATA%\Nexa AI for logs when frozen (UAC-safe location)
    if getattr(sys, 'frozen', False):
        user_data_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'Nexa AI'
    else:
        user_data_dir = PROJECT_ROOT
    
    log_file = user_data_dir / "data" / "logs" / f"nexa_{log_level_str.lower()}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    setup_logging(
        level=log_level,
        log_file=str(log_file),
        use_colors=True,
        show_module=True
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create Qt Application
        logger.info("🖥️  Creating Qt Application...")
        app = QApplication(sys.argv)
        app.setApplicationName("Nexa AI Assistant")
        app.setOrganizationName("Ali Adil Waseem")
        logger.info("✅ Qt Application created")
        
        # First Run Wizard Check - BEFORE initializing components
        # This ensures API keys entered in wizard are available when config loads
        # Use %LOCALAPPDATA%\Nexa AI for user data (works even in Program Files)
        if getattr(sys, 'frozen', False):
            user_data_dir = Path(os.environ.get('LOCALAPPDATA', APP_ROOT)) / 'Nexa AI'
        else:
            user_data_dir = APP_ROOT
        user_config_dir = user_data_dir / "config"
        user_config_dir.mkdir(parents=True, exist_ok=True)
        setup_marker = user_config_dir / "setup_complete.marker"
        
        if not setup_marker.exists():
            logger.info("🆕 First run detected. Launching Setup Wizard...")
            from ui.first_run_wizard import FirstRunWizard
            
            wizard = FirstRunWizard()
            if wizard.exec():
                logger.info("✅ Setup completed successfully")
                setup_marker.touch()
            else:
                logger.warning("⚠️ Setup cancelled by user. Exiting.")
                sys.exit(0)
        
        # --- Authentication ---
        auth_data_dir = user_data_dir / "data"
        auth_data_dir.mkdir(parents=True, exist_ok=True)
        auth_manager = AuthManager(auth_data_dir)
        
        login_dialog = LoginDialog(auth_manager)
        if login_dialog.exec() != LoginDialog.DialogCode.Accepted:
            logger.warning("⚠️ Login cancelled by user. Exiting.")
            sys.exit(0)
        
        logger.info(f"🔐 Authenticated as: {auth_manager.current_user}")
        
        # Show loading dialog while initializing
        loading_dialog = LoadingDialog()
        loading_dialog.show()
        QApplication.processEvents()
        
        # ── Run initialization in background thread so spinner keeps spinning ──
        from PySide6.QtCore import QEventLoop
        
        init_worker = InitWorker()
        init_result = {}  # Mutable container for thread result
        init_loop = QEventLoop()  # Local event loop — keeps UI responsive
        
        def _on_status(text, detail):
            loading_dialog.set_status(text, detail)
        
        def _on_init_ok(config_obj, brain_obj):
            init_result['config'] = config_obj
            init_result['brain'] = brain_obj
            init_result['success'] = True
            init_loop.quit()
        
        def _on_init_fail():
            init_result['success'] = False
            init_loop.quit()
        
        init_worker.status_update.connect(_on_status)
        init_worker.finished_ok.connect(_on_init_ok)
        init_worker.finished_fail.connect(_on_init_fail)
        
        init_worker.start()
        init_loop.exec()  # Spins event loop — spinner keeps animating
        init_worker.wait()  # Ensure thread fully finished
        
        # Retrieve results
        success = init_result.get('success', False)
        config_instance = init_result.get('config')
        brain_instance = init_result.get('brain')
        
        if not success:
            loading_dialog.close_dialog()
            logger.critical("Failed to initialize Nexa. Exiting.")
            sys.exit(1)
        
        # Update loading status before creating UI
        loading_dialog.set_status("Launching interface...", "Creating main window")
        
        # Create Modern window (new clean design matching reference image)
        log_section(logger, "LAUNCHING NEXA UI", logging.INFO)
        hud_window = NexaModernWindow(brain_instance, config_instance)
        
        # Attach lock screen to window
        hud_window.setup_lock_screen(auth_manager)
        
        # Close loading dialog before showing main window
        loading_dialog.close_dialog()
        
        hud_window.show()
        logger.info("✅ Modern UI launched")
        
        # Connect window to brain for UI control (e.g., theme switching)
        brain_instance.set_window(hud_window)
        
        # Connect GPU monitor to brain for usage queries
        if gpu_monitor is not None:
            brain_instance.set_gpu_monitor(gpu_monitor)
        
        # Connect Core AI Kernel to brain and window
        if kernel_instance is not None:
            brain_instance.set_kernel(kernel_instance)
            hud_window.set_kernel(kernel_instance)
        
        # Start the brain (listening, processing, etc.)
        logger.info("🧠 Starting Nexa Brain...")
        brain_instance.start()
        logger.info("✅ Nexa Brain started and listening")
        
        log_section(logger, "NEXA IS READY! 🚀", logging.INFO)
        logger.info("🎤 Say 'Hey Nexa' or just speak your command")
        logger.info("⏸️  Press Ctrl+C or click X to exit")
        
        # Start Qt event loop
        exit_code = app.exec()
        
        # Cleanup
        log_section(logger, "SHUTTING DOWN", logging.INFO)
        logger.info("🛑 Stopping Nexa Brain...")
        brain_instance.shutdown()
        logger.info("✅ Nexa Brain stopped")
        
        # Shutdown Core AI Kernel
        if kernel_instance is not None:
            logger.info("🔷 Shutting down Core AI Kernel...")
            kernel_instance.shutdown()
            logger.info("✅ Core AI Kernel stopped")
        
        # Stop GPU monitoring and generate report
        if gpu_monitor is not None:
            logger.info("📊 Stopping GPU Monitor and generating report...")
            gpu_monitor.stop_monitoring()
            logger.info("✅ GPU Monitor stopped - report saved")
        
        logger.info("👋 Goodbye!")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("\n⏸️  Keyboard interrupt received")
        logger.info("🛑 Shutting down gracefully...")
        sys.exit(0)
        
    except Exception as e:
        user_msg, recovered = handle_error(
            error=e,
            context="main",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            user_message="Nexa encountered a critical error",
            recovery_suggestion="Check logs and restart Nexa"
        )
        logger.critical(f"💥 CRITICAL ERROR: {user_msg}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Emergency crash handler - write to user data dir for UAC compatibility
        import traceback
        if getattr(sys, 'frozen', False):
            crash_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'Nexa AI'
            crash_dir.mkdir(parents=True, exist_ok=True)
            crash_file = crash_dir / "crash.txt"
        else:
            crash_file = Path("crash.txt")
        
        with open(crash_file, "w", encoding="utf-8") as f:
            f.write(f"CRITICAL CRASH:\n{str(e)}\n\nTRACEBACK:\n{traceback.format_exc()}")
        print(f"CRITICAL CRASH: {e}")
        print(f"Crash log saved to: {crash_file}")
        input("Press Enter to exit...")
