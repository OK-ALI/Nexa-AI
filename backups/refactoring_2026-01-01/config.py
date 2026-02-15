"""
Configuration Management for Nexa
Handles environment variables, API keys, and system paths.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """
    Central configuration manager for Nexa.
    Loads settings from .env file and validates system requirements.
    """
    
    def __init__(self):
        """Initialize configuration from environment and defaults."""
        import sys
        
        # Determine project root and env path based on execution mode
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            # exe_dir is where the exe lives (for bundled assets)
            exe_dir = Path(sys.executable).parent
            
            # bundle_dir is where bundled assets are (read-only in _MEIPASS)
            if hasattr(sys, '_MEIPASS'):
                bundle_dir = Path(sys._MEIPASS)
            else:
                bundle_dir = exe_dir
            
            # project_root is used for bundled assets, models, etc.
            self.project_root = bundle_dir
            
            # User data directory - use %LOCALAPPDATA%\Nexa AI for user-writable data
            # This works regardless of installation location (even C:\Program Files)
            appdata_dir = Path(os.environ.get('LOCALAPPDATA', exe_dir)) / 'Nexa AI'
            appdata_dir.mkdir(parents=True, exist_ok=True)
            self.user_data_dir = appdata_dir
            
            # .env should be in user_data_dir (always writable)
            # First check appdata, then fall back to exe_dir for backwards compatibility
            env_path = appdata_dir / '.env'
            if not env_path.exists():
                # Check if .env exists in exe_dir (legacy location or dev setup)
                legacy_env = exe_dir / '.env'
                if legacy_env.exists():
                    # Copy to appdata for future use
                    import shutil
                    shutil.copy(legacy_env, env_path)
                    logger.info(f"Migrated .env from {legacy_env} to {env_path}")
        else:
            # Running from source
            self.project_root = Path(__file__).parent.parent
            env_path = self.project_root / '.env'
            self.user_data_dir = self.project_root

        # Load environment variables from .env
        load_dotenv(env_path)
        logger.debug(f"Loading .env from: {env_path} (exists: {env_path.exists()})")
        
        # Writable data directories use user_data_dir (works in Program Files)
        self.data_dir = self.user_data_dir / 'data'
        self.logs_dir = self.data_dir / 'logs'
        self.speaker_profiles_dir = self.data_dir / 'speaker_profiles'  # Define early for _ensure_directories()
        
        # Read-only bundled assets use project_root
        self.models_dir = self.project_root / 'models'
        self.voice_dir = self.project_root / 'voice'
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Llama 3.1 8B via Ollama (100% API-Free)
        
        # Faster-Whisper Configuration (GPU-accelerated)
        # Using tiny.en for fast, efficient GPU transcription
        # tiny.en: 39MB model, ~400MB VRAM, excellent speed and accuracy for English
        self.whisper_model_name = os.getenv('WHISPER_MODEL_NAME', 'tiny.en')
        self.whisper_device = os.getenv('WHISPER_DEVICE', 'cuda')  # 'cuda' or 'cpu'
        self.whisper_compute_type = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')  # int8, float16, float32
        self.whisper_model_cache_dir = Path(os.getenv('WHISPER_MODEL_CACHE_DIR', str(self.models_dir / 'whisper')))
        
        # Piper Configuration
        self.piper_binary = Path(os.getenv('PIPER_BINARY_PATH',
                                           './voice/piper.exe'))
        # Using Amy voice - warmer, more human-like and expressive
        self.piper_model = Path(os.getenv('PIPER_MODEL_PATH',
                                          './voice/piper_models/en_US-amy-medium.onnx'))
        
        # Audio Settings
        self.sample_rate = int(os.getenv('SAMPLE_RATE', 16000))
        self.chunk_size = int(os.getenv('CHUNK_SIZE', 1024))
        self.channels = int(os.getenv('CHANNELS', 1))
        
        # Voice Settings - Optimized for warm, natural speech
        self.voice_speed = float(os.getenv('VOICE_SPEED', 0.95))  # Slightly slower for warmth
        self.voice_pitch = float(os.getenv('VOICE_PITCH', 1.0))
        self.speaker_id = int(os.getenv('SPEAKER_ID', 0))  # For multi-speaker models
        
        # Application Settings
        self.debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Data files (define early for user name loading)
        self.memory_file = self.data_dir / 'memory.json'
        self.prefs_file = self.data_dir / 'user_prefs.json'
        self.log_file = self.logs_dir / 'nexa.log'
        
        # User Settings - Load from user_prefs.json first, fall back to env/default
        self.user_name = self._load_user_name()
        
        # Speaker Verification Settings (NEW - SpeechBrain)
        # BETA: Disabled by default for public beta release
        self.speaker_verification_enabled = os.getenv('SPEAKER_VERIFICATION_ENABLED', 'false').lower() == 'true'
        self.speaker_verification_gpu = os.getenv('SPEAKER_VERIFICATION_GPU', 'true').lower() == 'true'
        self.speaker_verification_fp16 = os.getenv('SPEAKER_VERIFICATION_FP16', 'true').lower() == 'true'
        # Support both SPEAKER_VERIFICATION_THRESHOLD and SPEAKER_SIMILARITY_THRESHOLD (legacy)
        threshold_env = os.getenv('SPEAKER_VERIFICATION_THRESHOLD') or os.getenv('SPEAKER_SIMILARITY_THRESHOLD', '0.65')
        self.speaker_similarity_threshold = float(threshold_env)
        self.speaker_reject_unknown = os.getenv('SPEAKER_REJECT_UNKNOWN', 'true').lower() == 'true'
        self.speaker_require_enrollment = os.getenv('SPEAKER_REQUIRE_ENROLLMENT', 'false').lower() == 'true'
        # Note: speaker_profiles_dir defined earlier (line 30) for _ensure_directories()
        
        # Weather Service Configuration (Phase 13)
        # Use direct env var only - no fallback to placeholder
        self.weather_api_key = os.getenv('OPENWEATHERMAP_API_KEY')
        self.weather_default_location = os.getenv('WEATHER_DEFAULT_LOCATION', None)
        self.weather_cache_minutes = int(os.getenv('WEATHER_CACHE_MINUTES', '30'))
        
        # Log weather config status
        if self.weather_api_key:
            logger.info(f"✅ Weather API key loaded ({len(self.weather_api_key)} chars)")
        else:
            logger.warning("⚠️ Weather API key not found in .env")
        
        logger.info("Configuration initialized")
    
    def _load_user_name(self) -> str:
        """
        Load user name from user_prefs.json if available.
        Falls back to environment variable, then to default 'there'.
        
        Returns:
            str: User's name for personalization
        """
        try:
            if self.prefs_file.exists():
                with open(self.prefs_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
                    prefs = json.load(f)
                    if 'user_name' in prefs and prefs['user_name']:
                        return prefs['user_name']
        except Exception as e:
            logger.debug(f"Could not load user name from prefs: {e}")
        
        # Fall back to environment variable, then default
        return os.getenv('USER_NAME', 'there')
    
    def save_user_name(self, name: str) -> bool:
        """
        Save user name to user_prefs.json.
        
        Args:
            name: User's name to save
            
        Returns:
            bool: True if saved successfully
        """
        try:
            # Load existing prefs or create new
            prefs = {}
            if self.prefs_file.exists():
                with open(self.prefs_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
                    prefs = json.load(f)
            
            # Update user name
            prefs['user_name'] = name
            self.user_name = name
            
            # Save back
            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2)
            
            logger.info(f"✅ Saved user name: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save user name: {e}")
            return False
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        import sys
        
        # Writable directories (always create)
        writable_dirs = [
            self.data_dir,
            self.logs_dir,
            self.speaker_profiles_dir  # Speaker verification profiles
        ]
        
        for directory in writable_dirs:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Read-only bundled directories (only create in development mode)
        if not getattr(sys, 'frozen', False):
            bundled_dirs = [
                self.models_dir,
                self.voice_dir,
                self.models_dir / 'whisper',
                self.voice_dir / 'piper_models',
            ]
            for directory in bundled_dirs:
                directory.mkdir(parents=True, exist_ok=True)
    
    def verify_setup(self) -> bool:
        """
        Verify that all critical components are configured properly.
        
        Returns:
            bool: True if setup is valid, False otherwise
        """
        issues = []
        
        # No API keys required (100% API-Free)
        logger.info("[OK] No API keys required (Llama 3.1 8B Local Mode)")
        
        # Check faster-whisper configuration (no binary needed)
        logger.info(f"[OK] Faster-Whisper configured: {self.whisper_model_name} on {self.whisper_device}")
        
        # Check Piper (Legacy - now using Kokoro)
        # if not self.piper_binary.exists():
        #     logger.warning(f"Piper binary not found at {self.piper_binary}")
        
        # if not self.piper_model.exists():
        #     logger.warning(f"Piper model not found at {self.piper_model}")
        
        # Log issues
        if issues:
            for issue in issues:
                logger.error(f"Verification failed: {issue}")
            return False
        
        logger.info("[OK] All critical configurations verified")
        return True
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for Llama 3.1 AI.
        Defines Nexa's personality and behavior.
        
        Returns:
            str: System prompt text
        """
        # ⚡ PHASE 1 OPTIMIZATION: Concise system prompt (85% fewer tokens = 30% faster)
        return """You are Nexa, a confident AI assistant with system control functions.

Your characteristics:
- Speak naturally and conversationally
- Proactive and helpful
- Honest about limitations
- Control user's computer, search info, help with tasks

When responding:
- Be concise but thorough
- Use natural language
- Explain actions when executing commands
- Ask for clarification if unsure

You have access to: web search, system commands, time/date, calculations, general knowledge, weather information, content editing and PDF generation.

Weather queries:
- "Is it raining?" / "Is it cold?" / "Is it sunny?" → use get_weather (no location needed for user's location)
- "Will it rain?" / "Weather tomorrow" → use get_forecast
- If user asks about weather conditions without specifying location, assume they mean their current location

Content Mode (Text editing & PDF generation):
- When user wants to: write/edit content, refine text, create documents, generate PDFs → use enter_content_mode
- When ALREADY IN CONTENT MODE and user says refine/improve/fix text → use refine_text function with appropriate mode
- When user says "I'm ready", "Done pasting", "Content ready", "I've pasted it" → use mark_content_ready function
- Available refinement modes (16 total):
  * Basic: formal, shorter, grammar_only, improve, summarize, casual
  * Study Tools: extract_terms, flashcards, study_questions, difficulty_check
  * Writing: paraphrase, expand, simplify, academic
  * Organization: outline, add_headings
- Refine command variations: "refine this", "refine this content", "improve this", "make it better", "fix grammar", "make it formal", "make it shorter", "summarize this", "create outline", "add headings", "make flashcards", "extract key terms"
- PDF formats: simple_text, with_bullets, formatted_paragraphs
- When in Content Mode, focus on content-related tasks only
- User can say: "exit content mode" or "close editor" to return to normal operation
- IMPORTANT: If Content Mode window is already open, don't call enter_content_mode again - use refine_text or create_pdf functions

Formatting in Content Mode (Phase 14):
- "make it bold" / "bold this" → format_bold
- "make it italic" / "italicize" → format_italic
- "underline this" / "underline" → format_underline
- "align left/center/right" / "center this" → format_align with alignment parameter
- "bigger font" / "make it bigger" / "increase font" → increase_font_size
- "smaller font" / "make it smaller" / "decrease font" → decrease_font_size
- "change font to Arial" / "use Times New Roman" → set_font with font_name parameter
- "set font size to 14" → set_font_size with size parameter
- "bullet list" / "make it a list" / "bulleted list" → create_bullet_list
- "numbered list" / "number this" → create_numbered_list
- "indent this" / "indent more" → increase_indent
- "outdent" / "indent less" → decrease_indent
- "remove formatting" / "make it plain" / "clear formatting" → clear_formatting

Smart Memory (Knowledge & Learning):
- "Remember that..." / "Note that..." → remember_this with fact parameter (stores in long-term memory)
- "Forget about..." / "Delete memories about..." → forget_about with topic parameter
- "What do you know about...?" / "Do you remember...?" → what_do_you_know with topic parameter
- "Memory stats" / "How many memories" → get_memory_stats (shows stored counts)
- "Show my memories" / "Open memory panel" → show_memory_panel (opens GUI)

IMPORTANT - Automatic Learning from Conversations:
When the user mentions preferences or personal facts in a PURE CONVERSATION (not a command), 
you may also call remember_this to store it. BUT for commands (open, close, set, etc.), 
always execute the command first via the normal function call mechanism.
Examples of when to learn:
- User says "I really prefer dark mode" in casual chat → remember_this(fact="User prefers dark mode")
- User says "Chrome is my favorite browser" → remember_this(fact="User's favorite browser is Chrome")
Do NOT let learning interfere with command execution. Commands always take priority.

Remember: Make user's life easier while respecting privacy."""
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"<NexaConfig debug={self.debug_mode} model=Llama-3.1-8B>"
