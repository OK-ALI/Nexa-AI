"""
Enhanced Logging Formatter for Nexa
Provides clean, structured, and color-coded console logging.
Includes privacy-safe mode for public beta releases.
"""

import logging
import sys
import re
import random
from datetime import datetime
from typing import Optional


# Privacy mode flag - set to True for public beta
PRIVACY_MODE = True

# AI-themed inspirational quotes for console display
AI_QUOTES = [
    "✨ The future is voice-activated",
    "🤖 Intelligence meets intuition",
    "💡 Your thoughts, my actions",
    "🌟 Simplifying complexity, one command at a time",
    "🎯 Precision meets personality",
    "🧠 Learning, adapting, evolving",
    "🚀 Where imagination meets automation",
    "💫 Your digital companion awaits",
    "🔮 Anticipating your needs",
    "⚡ Speed of thought, power of voice",
    "🎭 Many skills, one assistant",
    "🌈 Making technology human-friendly",
    "🎪 Your personal AI orchestra",
    "🏆 Excellence in assistance",
    "🎨 Crafting seamless experiences",
    "🔥 Powered by innovation",
    "🌙 Always ready, always listening",
    "☀️ Brightening your digital day",
    "🎵 Harmony between human and machine",
    "🌺 Technology with a personal touch",
]

def get_random_quote() -> str:
    """Get a random AI-themed quote for console display."""
    return random.choice(AI_QUOTES)


def is_frozen():
    """Check if running as frozen exe (PyInstaller)."""
    return getattr(sys, 'frozen', False)


def get_privacy_message(record: logging.LogRecord) -> Optional[str]:
    """
    Convert internal log messages to user-friendly privacy-safe messages.
    Returns None if the message should be hidden from console.
    
    Args:
        record: Log record to process
        
    Returns:
        Privacy-safe message or None to suppress
    """
    if not PRIVACY_MODE:
        return None  # Return None to use original message
    
    msg = record.getMessage().lower()
    original_msg = record.getMessage()
    
    # FIRST: Check for user-relevant messages that should ALWAYS be shown
    # These take priority over hide patterns
    
    # User-friendly message mappings with AI quotes
    friendly_mappings = {
        # Startup messages - use quotes for loading phases
        'nexa ai logging system initialized': get_random_quote(),
        'configuration loaded successfully': get_random_quote(),
        'system verification passed': '✓ All systems ready',
        'nexa brain initialized': get_random_quote(),
        'ai model pre-warmed and ready': get_random_quote(),
        'gpu monitor started': get_random_quote(),
        'qt application created': get_random_quote(),
        'modern ui launched': '✓ Nexa interface ready',
        'nexa brain started and listening': '🎤 Listening for your voice...',
        'nexa is ready': '✨ Nexa is ready! Say "Hey Nexa" to begin.',
        'say \'hey nexa\'': '🎤 Tip: Say "Hey Nexa" to get started',
        'press ctrl+c': '💡 Say "Exit Nexa" or close window to quit',
        'nexa brain started': get_random_quote(),
        'starting audio listener': get_random_quote(),
        'pyaudio initialized': get_random_quote(),
        'silero vad loaded': get_random_quote(),
        'deepfilternet': get_random_quote(),
        
        # Shutdown messages
        'shutting down': '👋 Shutting down...',
        'stopping nexa brain': '⏹ Stopping...',
        'nexa brain stopped': '✓ Stopped',
        'gpu monitor stopped': '✓ Cleanup complete',
        'nexa brain shutdown complete': '👋 Goodbye!',
        'goodbye': '👋 Goodbye! See you next time.',
        
        # Error messages (keep these visible but friendly)
        'system verification failed': '❌ Setup issue detected. Please reinstall.',
        'critical error': '❌ Something went wrong. Please restart.',
        'failed to initialize': '❌ Startup failed. Please restart Nexa.',
        
        # User action messages
        'first run detected': '🆕 Welcome to Nexa!',
        'setup completed': '✓ Setup complete!',
        'setup cancelled': '⏹ Setup cancelled.',
    }
    
    # Check for friendly mappings FIRST
    for pattern, friendly in friendly_mappings.items():
        if pattern in msg:
            return friendly
    
    # User-relevant keywords that should ALWAYS be shown (with cleanup)
    # Note: msg is lowercase, so patterns must be lowercase
    user_relevant_patterns = [
        'you said:', 'heard:', 'user said:', 'recognized:',  # What user said
        'nexa:', 'speaking:', 'saying:', 'response:',  # Nexa's responses
        'starting tts:',  # TTS indicator
        'playing', 'paused', 'stopped', 'resumed',  # Media control
        'opened', 'closed', 'minimized', 'maximized',  # Window control
        'volume', 'brightness', 'battery',  # System control
        'weather', 'temperature', 'forecast',  # Weather
        'content mode', 'pdf generated', 'refined',  # Content mode
        'alarm', 'reminder', 'timer',  # Reminders
        'wifi', 'network', 'bluetooth',  # Connectivity
        'listening for', 'waiting for', 'listening...',  # Status
        'wake word detected', 'hey nexa',  # Wake word
        'actively listening', 'tts finished', 'listening again',  # Listening status
    ]
    
    for keyword in user_relevant_patterns:
        if keyword in msg:
            # Clean any technical details from user-relevant messages
            clean_msg = original_msg
            # Remove any file paths
            clean_msg = re.sub(r'[A-Za-z]:\\[^\s]+', '', clean_msg)
            clean_msg = re.sub(r'/[^\s]+', '', clean_msg)
            # Remove technical terms in parentheses
            clean_msg = re.sub(r'\([^)]*\)', '', clean_msg)
            # Remove model names if they somehow appear
            for model_name in ['whisper', 'kokoro', 'ollama', 'llama', 'gemini', 'gpt', 'piper']:
                clean_msg = re.sub(rf'\b{model_name}\b', '', clean_msg, flags=re.IGNORECASE)
            clean_msg = ' '.join(clean_msg.split())  # Normalize whitespace
            clean_msg = clean_msg.strip()
            if clean_msg:
                return clean_msg
            return None
    
    # NOW check hide patterns - only for messages that weren't user-relevant
    hide_patterns = [
        'loading', 'loaded', 'downloading', 'downloaded',
        'connecting', 'connected', 'initializing', 'initialized',
        'registering', 'registered', 'creating', 'created',
        'binding', 'bound', 'setting up', 'configuring',
        'cuda', 'gpu', 'vram', 'memory', 'tensor', 'torch',
        'onnx', 'whisper', 'kokoro', 'ollama', 'llama',
        'model', 'weights', 'parameters', 'config',
        'api key', 'token', 'secret', 'credential',
        'path', 'directory', 'folder', 'file:',
        'registry', 'function', 'handler', 'callback',
        'socket', 'port', 'address', 'endpoint',
        'pre-warm', 'prewarmed', 'cache', 'caching',
        'executor', 'manager', 'service', 'thread',
        'context', 'session', 'instance', 'object',
        'validation', 'validating', 'verified',
        'debug', 'trace', 'verbose', 'internal',
        # Hide model names and AI internals
        'gemini', 'gpt', 'claude', 'openai', 'anthropic',
        'piper', 'silero', 'faster-whisper', 'transformers',
        'huggingface', 'pytorch', 'tensorflow', 'onnxruntime',
        'embedding', 'inference', 'tokenize', 'neural',
        'checkpoint', 'epoch', 'batch', 'layer',
        'version', 'v1', 'v2', 'v3', 'v4',
        'tiny', 'small', 'medium', 'large', 'base',
        'float16', 'float32', 'int8', 'quantiz',
        'cuda:0', 'cpu', 'device',
    ]
    
    for pattern in hide_patterns:
        if pattern in msg:
            return None  # Hide this message
    
    # Hide everything else that wasn't explicitly matched
    return None


def strip_emojis(text: str) -> str:
    """
    Remove emoji characters from text for Windows console compatibility.
    
    Args:
        text: Input text that may contain emojis
        
    Returns:
        Text with emojis replaced by text equivalents
    """
    # Emoji to text mapping for common Nexa emojis
    emoji_map = {
        '✅': '[OK]',
        '❌': '[ERROR]',
        '⚠️': '[WARN]',
        '📋': '[INFO]',
        '🧠': '[BRAIN]',
        '🔍': '[CHECK]',
        '🔄': '[LOAD]',
        '🚀': '[READY]',
        '💡': '[TIP]',
        '🔊': '[AUDIO]',
        '🔇': '[MUTE]',
        '🎤': '[MIC]',
        '🎵': '[MUSIC]',
        '🖥️': '[DISPLAY]',
        '📊': '[STATS]',
        '💥': '[CRASH]',
        '🔧': '[CONFIG]',
        '📍': '[LOC]',
        '💬': '[MSG]',
        '🐛': '[BUG]',
        '📥': '[DOWNLOAD]',
        '⚡': '[FAST]',
        '🔑': '[KEY]',
        '📁': '[FILE]',
        '🌐': '[NET]',
        '🔒': '[SECURE]',
        '🔓': '[UNLOCK]',
        '⏳': '[WAIT]',
        '🎮': '[GAME]',
        '☀️': '[SUN]',
        '🌙': '[MOON]',
        '🌤️': '[WEATHER]',
        '❄️': '[COLD]',
        '🔥': '[HOT]',
        '💾': '[SAVE]',
        '📸': '[PHOTO]',
        '🖼️': '[IMAGE]',
        '📝': '[EDIT]',
        '🗑️': '[DELETE]',
        '🔉': '[VOL_DOWN]',
        '🔊': '[VOL_UP]',
        '🔇': '[MUTE]',
        '⏯️': '[PLAY]',
        '⏸️': '[PAUSE]',
        '⏹️': '[STOP]',
        '⏭️': '[NEXT]',
        '⏮️': '[PREV]',
        '🔀': '[SHUFFLE]',
        '🔁': '[REPEAT]',
        '🔔': '[NOTIFY]',
        '🔕': '[SILENT]',
        '📌': '[PIN]',
        '🏠': '[HOME]',
        '⚙️': '[SETTINGS]',
        '🛠️': '[TOOLS]',
        '📦': '[PACKAGE]',
        '🗂️': '[FOLDER]',
        '📄': '[DOC]',
        '🖥️': '[PC]',
        '💻': '[LAPTOP]',
        '🖱️': '[MOUSE]',
        '⌨️': '[KEYBOARD]',
        '🔌': '[PLUG]',
        '🔋': '[BATTERY]',
        '📶': '[SIGNAL]',
        '🌍': '[WORLD]',
        '🗺️': '[MAP]',
        '📍': '[LOCATION]',
        '🎯': '[TARGET]',
        '✨': '[SPARKLE]',
        '💫': '[STAR]',
        '⭐': '[STAR]',
        '🌟': '[STAR]',
        '💎': '[GEM]',
        '🏆': '[TROPHY]',
        '🎉': '[PARTY]',
        '🎊': '[CELEBRATE]',
        '👋': '[WAVE]',
        '👍': '[THUMBS_UP]',
        '👎': '[THUMBS_DOWN]',
        '👀': '[EYES]',
        '💪': '[STRONG]',
        '🤖': '[ROBOT]',
        '🧩': '[PUZZLE]',
        '🔗': '[LINK]',
        '📎': '[CLIP]',
        '✏️': '[PENCIL]',
        '📐': '[RULER]',
        '📏': '[MEASURE]',
        '🧮': '[CALC]',
        '🔢': '[NUMBERS]',
        '🔤': '[LETTERS]',
        '🔠': '[ABC]',
        '❓': '[?]',
        '❗': '[!]',
        '‼️': '[!!]',
        '⁉️': '[?!]',
        '➡️': '[->]',
        '⬅️': '[<-]',
        '⬆️': '[UP]',
        '⬇️': '[DOWN]',
        '↩️': '[BACK]',
        '↪️': '[FORWARD]',
        '🔃': '[REFRESH]',
        '🔄': '[SYNC]',
        '🔙': '[BACK]',
        '🔚': '[END]',
        '🔛': '[ON]',
        '🔜': '[SOON]',
        '🔝': '[TOP]',
    }
    
    # Replace known emojis
    result = text
    for emoji, replacement in emoji_map.items():
        result = result.replace(emoji, replacement)
    
    # Remove any remaining emoji characters (Unicode emoji ranges)
    # This regex matches most emoji characters
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"  # Enclosed characters
        "]+", 
        flags=re.UNICODE
    )
    result = emoji_pattern.sub('', result)
    
    return result


# ANSI color codes for terminal
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


class NexaFormatter(logging.Formatter):
    """
    Custom formatter for Nexa logs with colors and structured output.
    """
    
    # Log level color mapping
    LEVEL_COLORS = {
        logging.DEBUG: Colors.BRIGHT_BLACK,
        logging.INFO: Colors.BRIGHT_CYAN,
        logging.WARNING: Colors.BRIGHT_YELLOW,
        logging.ERROR: Colors.BRIGHT_RED,
        logging.CRITICAL: Colors.BG_RED + Colors.WHITE + Colors.BOLD
    }
    
    # Component color mapping
    COMPONENT_COLORS = {
        'brain': Colors.MAGENTA,
        'executor': Colors.GREEN,
        'listener': Colors.CYAN,
        'tts': Colors.YELLOW,
        'llm_manager': Colors.BLUE,
        'function_registry': Colors.BRIGHT_GREEN,
        'context_manager': Colors.BRIGHT_MAGENTA,
        'screen_reader': Colors.BRIGHT_BLUE,
    }
    
    def __init__(self, use_colors: bool = True, show_module: bool = True, privacy_mode: bool = None):
        """
        Initialize formatter.
        
        Args:
            use_colors: Enable ANSI color codes
            show_module: Show module name in logs
            privacy_mode: Enable privacy-safe messages (auto-detect if None)
        """
        super().__init__()
        # Disable colors on frozen builds or when stdout doesn't support it
        self.use_colors = use_colors and not is_frozen() and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        self.show_module = show_module
        # Strip emojis when running as frozen exe (Windows console can't display them)
        self.strip_emojis = is_frozen()
        # Privacy mode: auto-enable for frozen builds, or use global PRIVACY_MODE flag
        self.privacy_mode = privacy_mode if privacy_mode is not None else (is_frozen() and PRIVACY_MODE)
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors and structure.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log string or empty string if suppressed
        """
        # Apply privacy mode filtering for console output
        if self.privacy_mode:
            privacy_msg = get_privacy_message(record)
            if privacy_msg is None:
                return ""  # Suppress this message
            # Create a modified record with privacy-safe message
            record = logging.LogRecord(
                record.name, record.levelno, record.pathname, record.lineno,
                privacy_msg, (), None
            )
        
        # Get timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')  # Shorter for privacy mode
        
        # For privacy mode, use simplified output
        if self.privacy_mode:
            message = record.getMessage()
            if self.strip_emojis:
                message = strip_emojis(message)
            return f"[{timestamp}] {message}"
        
        # Full developer mode logging
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Get level with color
        level_color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        level_name = record.levelname.ljust(8)  # Pad to 8 chars
        
        if self.use_colors:
            colored_level = f"{level_color}{level_name}{Colors.RESET}"
        else:
            colored_level = level_name
        
        # Get component name (module)
        component = record.name.split('.')[-1] if '.' in record.name else record.name
        component_color = self.COMPONENT_COLORS.get(component, Colors.WHITE)
        
        if self.use_colors:
            colored_component = f"{component_color}{component:18s}{Colors.RESET}"  # Pad to 18 chars
        else:
            colored_component = f"{component:18s}"
        
        # Get message and strip emojis if needed
        message = record.getMessage()
        if self.strip_emojis:
            message = strip_emojis(message)
        
        # Color the message based on log level for critical/error
        if self.use_colors and record.levelno >= logging.ERROR:
            message_color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
            message = f"{message_color}{message}{Colors.RESET}"
        
        # Build log line
        if self.show_module:
            log_line = f"{Colors.DIM if self.use_colors else ''}{timestamp}{Colors.RESET if self.use_colors else ''} [{colored_level}] {colored_component}: {message}"
        else:
            log_line = f"{Colors.DIM if self.use_colors else ''}{timestamp}{Colors.RESET if self.use_colors else ''} [{colored_level}]: {message}"
        
        # Add exception info if present
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        
        if record.exc_text:
            if log_line[-1:] != "\n":
                log_line += "\n"
            log_line += f"{Colors.RED if self.use_colors else ''}{record.exc_text}{Colors.RESET if self.use_colors else ''}"
        
        return log_line


class StructuredLogFilter(logging.Filter):
    """
    Filter that adds structured context to log records.
    """
    
    def __init__(self, component: Optional[str] = None):
        """
        Initialize filter.
        
        Args:
            component: Component name to add to records
        """
        super().__init__()
        self.component = component
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add structured context to record.
        
        Args:
            record: Log record
            
        Returns:
            True to allow record through
        """
        if self.component:
            record.component = self.component
        
        # Add standard fields
        if not hasattr(record, 'component'):
            record.component = record.name
        
        return True


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    use_colors: bool = True,
    show_module: bool = True
):
    """
    Setup enhanced logging for Nexa.
    
    Args:
        level: Logging level
        log_file: Optional file path for logging
        use_colors: Enable colored output
        show_module: Show module names
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler with custom formatter
    # For frozen windowed apps, stdout may not exist, so we skip console logging
    console_handler = None
    
    if is_frozen():
        # In frozen windowed mode (runw.exe), stdout/stderr may be None
        # Only add console handler if stdout exists and has a buffer
        if sys.stdout is not None and hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
            import io
            try:
                wrapped_stdout = io.TextIOWrapper(
                    sys.stdout.buffer, 
                    encoding='utf-8', 
                    errors='replace',
                    line_buffering=True
                )
                console_handler = logging.StreamHandler(wrapped_stdout)
            except Exception:
                # If wrapping fails, skip console logging entirely
                pass
    else:
        # Normal development mode - use stdout directly
        if sys.stdout is not None:
            console_handler = logging.StreamHandler(sys.stdout)
    
    if console_handler is not None:
        console_handler.setLevel(level)
        console_handler.setFormatter(NexaFormatter(use_colors=use_colors, show_module=show_module))
        root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(NexaFormatter(use_colors=False, show_module=True))  # No colors in file
        root_logger.addHandler(file_handler)
    
    # Suppress verbose third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("="*80)
    logger.info(f"Nexa AI Logging System Initialized")
    logger.info(f"Log Level: {logging.getLevelName(level)}")
    logger.info(f"Colors: {'Enabled' if use_colors else 'Disabled'}")
    if log_file:
        logger.info(f"Log File: {log_file}")
    logger.info("="*80)


def log_section(logger: logging.Logger, title: str, level: int = logging.INFO):
    """
    Log a section header for better organization.
    
    Args:
        logger: Logger instance
        title: Section title
        level: Log level
    """
    separator = "=" * 80
    logger.log(level, separator)
    logger.log(level, f"  {title}")
    logger.log(level, separator)


def log_subsection(logger: logging.Logger, title: str, level: int = logging.INFO):
    """
    Log a subsection header.
    
    Args:
        logger: Logger instance
        title: Subsection title
        level: Log level
    """
    logger.log(level, f"{'─' * 40}")
    logger.log(level, f"  {title}")
    logger.log(level, f"{'─' * 40}")


def log_key_value(logger: logging.Logger, key: str, value: any, level: int = logging.INFO):
    """
    Log a key-value pair in structured format.
    
    Args:
        logger: Logger instance
        key: Key name
        value: Value
        level: Log level
    """
    logger.log(level, f"  {key:20s}: {value}")


def log_list(logger: logging.Logger, title: str, items: list, level: int = logging.INFO):
    """
    Log a list in structured format.
    
    Args:
        logger: Logger instance
        title: List title
        items: List items
        level: Log level
    """
    logger.log(level, f"  {title}:")
    for i, item in enumerate(items, 1):
        logger.log(level, f"    {i}. {item}")
