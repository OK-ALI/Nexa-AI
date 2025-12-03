"""
Function Registry - Dynamic Function Calling for Nexa
Maps function names to executor methods for AI-driven command execution.
"""

import logging
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)


class FunctionRegistry:
    """
    Registry of all available functions that Gemma3 can call.
    Enables dynamic function execution based on AI reasoning instead of hardcoded keywords.
    """
    
    def __init__(self, executor):
        """
        Initialize function registry with executor.
        
        Args:
            executor: CommandExecutor instance with all system functions
        """
        self.executor = executor
        self.functions: Dict[str, Dict[str, Any]] = {}
        self._register_all_functions()
        logger.info(f"Function Registry initialized with {len(self.functions)} functions")
    
    def register(self, name: str, function: Callable, description: str, parameters: Dict[str, str]):
        """
        Register a function in the catalog.
        
        Args:
            name: Function name (e.g., 'open_application')
            function: Callable function/method
            description: What the function does
            parameters: Dict of param_name: param_description
        """
        self.functions[name] = {
            "function": function,
            "description": description,
            "parameters": parameters
        }
        logger.debug(f"Registered function: {name}")
    
    def _register_all_functions(self):
        """Register all executor methods as callable functions."""
        
        # ===== TIME & SYSTEM INFO =====
        self.register(
            "get_current_time",
            self.executor.get_current_time,
            "Get the current time (hour and minute only)",
            {}
        )
        
        self.register(
            "get_current_date",
            self.executor.get_current_date,
            "Get the current date (day, month, year only)",
            {}
        )
        
        # ===== BATTERY =====
        self.register(
            "get_battery_status",
            self.executor.get_battery_status,
            "Get full battery status (charging, percentage, time remaining)",
            {}
        )
        
        self.register(
            "get_battery_percentage",
            self.executor.get_battery_percentage,
            "Get just the battery percentage",
            {}
        )
        
        # ===== GPU MONITORING =====
        self.register(
            "get_gpu_usage",
            self.executor.get_gpu_usage,
            "Get current GPU memory usage and VRAM statistics",
            {}
        )
        
        # ===== WEATHER =====
        self.register(
            "get_weather",
            self.executor.get_weather,
            "Get current weather for a location (auto-detects if no location specified)",
            {"location": "City name (optional, e.g., 'Tokyo', 'London,UK'). Leave empty for auto-detection."}
        )
        
        self.register(
            "get_forecast",
            self.executor.get_forecast,
            "Get weather forecast for next N days (1-5 days)",
            {
                "location": "City name (optional). Leave empty for auto-detection.",
                "days": "Number of forecast days (1-5, default 3)"
            }
        )
        
        # ===== WEB SEARCH =====
        self.register(
            "search_web",
            self.executor.search_web,
            "Search the web using default browser - opens Google search with query",
            {"query": "The search query to look up on the web"}
        )
        
        # ===== CONVERSATION MANAGEMENT =====
        self.register(
            "clear_conversation_history",
            self.executor.clear_conversation_history,
            "Clear all conversation history (forget previous conversations)",
            {}
        )
        
        # ===== NETWORK & WIFI MANAGEMENT =====
        self.register(
            "get_wifi_status",
            self.executor.get_wifi_status,
            "Get current WiFi connection status",
            {}
        )
        
        self.register(
            "disconnect_wifi",
            self.executor.disconnect_wifi,
            "Disconnect from current WiFi network (go offline)",
            {}
        )
        
        self.register(
            "connect_wifi",
            self.executor.connect_wifi,
            "Connect to a WiFi network by name",
            {"network_name": "Name of WiFi network (SSID) to connect to"}
        )
        
        self.register(
            "list_wifi_networks",
            self.executor.list_wifi_networks,
            "List all available WiFi networks in range",
            {}
        )
        
        self.register(
            "get_saved_wifi_profiles",
            self.executor.get_saved_wifi_profiles,
            "List all saved WiFi profiles/networks",
            {}
        )
        
        # ===== APPLICATION MANAGEMENT =====
        self.register(
            "open_application",
            self.executor.open_application,
            "Open/launch any installed application by name",
            {"app_name": "Name of application (e.g., 'chrome', 'calculator', 'notepad')"}
        )
        
        self.register(
            "close_application",
            self.executor.close_application,
            "Close/terminate a running application (enhanced: falls back to active window if app not found)",
            {"app_name": "Name of application to close"}
        )
        
        self.register(
            "close_active_window",
            self.executor.window_manager.close_active_window,
            "Close the currently active/foreground window (for 'close this' commands)",
            {}
        )
        
        self.register(
            "get_running_applications",
            lambda is_follow_up=False: self.executor.get_running_applications(is_follow_up=is_follow_up),
            "List all currently running applications (background processes with windows)",
            {}
        )
        
        self.register(
            "get_installed_applications",
            lambda search_query=None, limit=20: self.executor.get_installed_applications(search_query=search_query, limit=limit),
            "List all installed applications on the system (from Start Menu, Store, Registry). Use for 'list installed apps', 'what apps do I have', 'show my applications'",
            {
                "search_query": "Optional: filter apps by keyword (e.g., 'video', 'game', 'microsoft')",
                "limit": "Maximum number to list (default: 20)"
            }
        )
        
        self.register(
            "refresh_installed_apps",
            self.executor.refresh_installed_apps,
            "Force re-scan of installed applications. Use when user says 'refresh apps', 'rescan apps', or when newly installed app is not found",
            {}
        )
        
        self.register(
            "is_application_running",
            self.executor.is_application_running,
            "Check if specific application is currently running",
            {"app_name": "Name of application to check"}
        )
        
        # ===== VOLUME CONTROL =====
        self.register(
            "set_volume",
            self.executor.set_volume,
            "Set system volume to specific level (0-100)",
            {"level": "Volume level 0-100"}
        )
        
        self.register(
            "get_current_volume",
            self.executor.get_current_volume,
            "Get the current system volume level and mute status",
            {}
        )
        
        self.register(
            "increase_volume",
            self.executor.increase_volume,
            "Increase volume by specified amount",
            {"amount": "Amount to increase (default 10)"}
        )
        
        self.register(
            "decrease_volume",
            self.executor.decrease_volume,
            "Decrease volume by specified amount",
            {"amount": "Amount to decrease (default 10)"}
        )
        
        self.register(
            "mute_volume",
            self.executor.mute_volume,
            "Mute system volume",
            {}
        )
        
        self.register(
            "unmute_volume",
            self.executor.unmute_volume,
            "Unmute system volume",
            {}
        )
        
        # ===== BRIGHTNESS CONTROL =====
        self.register(
            "set_brightness",
            self.executor.set_brightness,
            "Set screen brightness to specific level (0-100)",
            {"level": "Brightness level 0-100"}
        )
        
        self.register(
            "get_current_brightness",
            self.executor.get_current_brightness,
            "Get the current screen brightness level (0-100)",
            {}
        )
        
        self.register(
            "increase_brightness",
            self.executor.increase_brightness,
            "Increase brightness by specified amount",
            {"amount": "Amount to increase (default 10)"}
        )
        
        self.register(
            "decrease_brightness",
            self.executor.decrease_brightness,
            "Decrease brightness by specified amount",
            {"amount": "Amount to decrease (default 10)"}
        )
        
        # ===== SCREEN READING (VISION) =====
        self.register(
            "read_screen_content",
            self.executor.read_screen_content,
            "Read all text visible on screen using vision/OCR",
            {}
        )
        
        self.register(
            "describe_screen",
            self.executor.describe_screen,
            "Get AI description of what's currently on screen",
            {}
        )
        
        # ===== WINDOW MANAGEMENT =====
        self.register(
            "minimize_window",
            lambda app_name: self.executor.window_manager.minimize_window(app_name),
            "Minimize a window by application name",
            {"app_name": "Application name or 'active' for current window"}
        )
        
        self.register(
            "maximize_window",
            lambda app_name: self.executor.window_manager.maximize_window(app_name),
            "Maximize a window by application name",
            {"app_name": "Application name or 'active' for current window"}
        )
        
        self.register(
            "restore_window",
            lambda app_name: self.executor.window_manager.restore_window(app_name),
            "Restore window to normal size",
            {"app_name": "Application name"}
        )
        
        self.register(
            "get_active_window",
            lambda: self.executor.window_manager.get_active_window_title(),
            "Get title of currently active window",
            {}
        )
        
        # ===== WIFI =====
        self.register(
            "get_wifi_status",
            self.executor.get_wifi_status,
            "Check WiFi connection status and network name",
            {}
        )
        
        self.register(
            "disconnect_wifi",
            self.executor.disconnect_wifi,
            "Disconnect from current WiFi network",
            {}
        )
        
        self.register(
            "list_wifi_networks",
            self.executor.list_wifi_networks,
            "List available WiFi networks nearby",
            {}
        )
        
        # ===== SCREENSHOTS =====
        self.register(
            "take_screenshot",
            lambda custom_name=None: self.executor.screenshot_manager.take_screenshot(custom_name=custom_name),
            "Take a screenshot and save to Pictures/Nexa Screenshots (optionally with custom name)",
            {"custom_name": "Optional: custom filename for the screenshot (e.g., 'meeting notes', 'bug report')"}
        )
        
        self.register(
            "take_screenshot_clipboard",
            lambda custom_name=None: self.executor.screenshot_manager.take_screenshot(save_to_clipboard=True, custom_name=custom_name),
            "Take screenshot and copy to clipboard (optionally with custom name)",
            {"custom_name": "Optional: custom filename for the screenshot"}
        )
        
        self.register(
            "open_screenshots_folder",
            lambda: self.executor.screenshot_manager.open_screenshots_folder(),
            "Open the Nexa screenshots folder in File Explorer",
            {}
        )
        
        # ===== GAMES =====
        self.register(
            "launch_game",
            lambda game_name: self.executor.game_manager.launch_game(game_name),
            "Launch a game from any platform (Steam, Epic, GOG, etc.)",
            {"game_name": "Name of the game to launch"}
        )
        
        self.register(
            "list_games",
            lambda platform=None, is_follow_up=False: self.executor.list_games(platform=platform, is_follow_up=is_follow_up),
            "List all detected games from all platforms (or filter by platform: Steam, Epic, GOG)",
            {"platform": "Optional: platform name to filter (Steam, Epic, GOG, Standalone) or None for all"}
        )
        
        self.register(
            "open_folder",
            self.executor.open_folder,
            "Open a folder by name (e.g., games, downloads, documents)",
            {"folder_name": "Folder name to open"}
        )
        
        self.register(
            "find_folder",
            self.executor.find_folder,
            "Find a folder's location by name",
            {"folder_name": "Folder name to find"}
        )
        
        # ===== MUSIC CONTROL =====
        self.register(
            "play_music",
            lambda song_name=None: self.executor.music_manager.play_song(song_name=song_name) if song_name else self.executor.music_manager.play_random(),
            "Play music (random if no song specified, or play specific song by name)",
            {"song_name": "Optional: specific song name to play"}
        )
        
        self.register(
            "play_random_music",
            self.executor.music_manager.play_random,
            "Play a random song from music library",
            {}
        )
        
        self.register(
            "list_music",
            lambda limit=None: "\n".join(self.executor.music_manager.list_songs(limit=limit)) if limit else "\n".join(self.executor.music_manager.list_songs()),
            "List all songs in music library (optionally limit number)",
            {"limit": "Optional: maximum number of songs to list"}
        )
        
        self.register(
            "pause_music",
            self.executor.music_manager.pause,
            "Pause currently playing music",
            {}
        )
        
        self.register(
            "resume_music",
            self.executor.music_manager.resume,
            "Resume paused music (also: continue, unpause, play again)",
            {}
        )
        
        self.register(
            "stop_music",
            self.executor.music_manager.stop,
            "Stop music playback completely",
            {}
        )
        
        self.register(
            "next_song",
            self.executor.music_manager.next_song,
            "Play next song in library",
            {}
        )
        
        self.register(
            "previous_song",
            self.executor.music_manager.previous_song,
            "Play previous song in library",
            {}
        )
        
        self.register(
            "whats_playing",
            self.executor.music_manager.get_current_track,
            "Get information about currently playing song",
            {}
        )
        
        self.register(
            "music_library_stats",
            self.executor.music_manager.get_library_stats,
            "Get music library statistics (total songs, artists, playtime)",
            {}
        )
        
        self.register(
            "suggest_music",
            lambda count=5, based_on_current=False: self.executor.music_manager.suggest_music(count=count, based_on_current=based_on_current),
            "Suggest random songs from library or similar to current track",
            {
                "count": "Number of songs to suggest (default: 5)",
                "based_on_current": "True to suggest similar to currently playing track (default: False)"
            }
        )
        
        self.register(
            "enable_shuffle",
            self.executor.music_manager.enable_shuffle,
            "Enable shuffle mode - play songs in random order",
            {}
        )
        
        self.register(
            "disable_shuffle",
            self.executor.music_manager.disable_shuffle,
            "Disable shuffle mode - return to sequential playback",
            {}
        )
        
        self.register(
            "set_repeat_mode",
            self.executor.music_manager.set_repeat_mode,
            "Set repeat mode: 'off' (no repeat), 'one' (repeat current song), or 'all' (repeat library)",
            {"mode": "Repeat mode: 'off', 'one', or 'all'"}
        )
        
        self.register(
            "get_playback_mode",
            self.executor.music_manager.get_playback_mode,
            "Get current playback mode (shuffle and repeat status)",
            {}
        )
        
        self.register(
            "play_all_library",
            lambda shuffle=False: self.executor.music_manager.play_all_library(shuffle=shuffle),
            "Play entire music library from beginning (optionally in shuffle mode)",
            {"shuffle": "True to play in random order, False for sequential (default: False)"}
        )
        
        # ===== THEME/UI CONTROL =====
        self.register(
            "switch_theme",
            lambda: self.executor.window.switch_theme() if self.executor.window else "UI not available",
            "Toggle between dark and light theme",
            {}
        )
        
        self.register(
            "set_dark_theme",
            lambda: self.executor.window.switch_theme('dark') if self.executor.window else "UI not available",
            "Switch to dark theme",
            {}
        )
        
        self.register(
            "set_light_theme",
            lambda: self.executor.window.switch_theme('light') if self.executor.window else "UI not available",
            "Switch to light theme",
            {}
        )
        
        # ===== NOTIFICATIONS =====
        self.register(
            "read_notifications",
            self.executor.read_notifications,
            "Read notifications from Windows Action Center",
            {}
        )
        
        # ===== TEXT/CLIPBOARD =====
        self.register(
            "select_all_text",
            self.executor.select_all_text,
            "Select all text (Ctrl+A)",
            {}
        )
        
        self.register(
            "copy_selected_text",
            self.executor.copy_selected,
            "Copy selected text to clipboard (Ctrl+C)",
            {}
        )
        
        self.register(
            "paste_clipboard",
            self.executor.paste_clipboard,
            "Paste clipboard content (Ctrl+V)",
            {}
        )
        
        self.register(
            "cut_selected_text",
            self.executor.cut_selected,
            "Cut selected text to clipboard (Ctrl+X)",
            {}
        )
        
        self.register(
            "delete_selected_text",
            self.executor.delete_selected,
            "Delete currently selected text (Delete key)",
            {}
        )
        
        # ===== CONTENT MODE - Text Refinement & PDF Generation =====
        self.register(
            "enter_content_mode",
            self.executor.enter_content_mode,
            "Enter Content Mode - Opens Content Box window for text editing, refinement, and PDF generation",
            {}
        )
        
        self.register(
            "exit_content_mode",
            self.executor.exit_content_mode,
            "Exit Content Mode - Closes Content Box window and returns to normal operation",
            {}
        )
        
        self.register(
            "mark_content_ready",
            self.executor.mark_content_ready,
            "Mark content as ready - User confirms they've finished pasting/typing content and it's ready for processing. Use when user says: 'I'm ready', 'Done pasting', 'Content ready', 'I've pasted it', etc.",
            {}
        )
        
        self.register(
            "refine_text",
            self.executor.refine_text,
            "Refine or transform text using AI. COMPREHENSIVE MODES: "
            "STUDY TOOLS: extract_terms (key vocabulary), flashcards (Q&A cards), study_questions (test questions), difficulty_check (reading level). "
            "WRITING: formal, shorter, grammar_only, improve, summarize, casual, paraphrase (rewrite), expand (add detail), simplify (easier), academic (scholarly). "
            "ORGANIZATION: outline (hierarchical), add_headings (section titles). "
            "This is the ONLY function for ALL text operations - use the mode parameter!",
            {
                "mode": "REQUIRED: Mode - formal, shorter, grammar_only, improve, summarize, casual, extract_terms, flashcards, study_questions, difficulty_check, paraphrase, expand, simplify, academic, outline, add_headings",
                "text": "Text to process (optional if Content Mode is active)"
            }
        )
        
        self.register(
            "create_pdf",
            self.executor.create_pdf,
            "Create PDF document from text - Formats: simple_text (plain), with_bullets (bulleted list), formatted_paragraphs (advanced formatting with headings)",
            {
                "pdf_format": "PDF format: 'simple_text', 'with_bullets', or 'formatted_paragraphs' (default: simple_text)",
                "filename": "Optional filename (auto-generated if not provided)",
                "text": "Text content (optional if Content Mode is active)",
                "title": "Optional document title"
            }
        )
        
        # ===== CONTENT MODE - FORMATTING (Phase 14) =====
        self.register(
            "format_bold",
            lambda: self.executor.content_box.formatter.toggle_bold() if self.executor.content_box else "Content Mode not active",
            "Apply or remove bold formatting to selected text or at cursor position",
            {}
        )
        
        self.register(
            "format_italic",
            lambda: self.executor.content_box.formatter.toggle_italic() if self.executor.content_box else "Content Mode not active",
            "Apply or remove italic formatting to selected text or at cursor position",
            {}
        )
        
        self.register(
            "format_underline",
            lambda: self.executor.content_box.formatter.toggle_underline() if self.executor.content_box else "Content Mode not active",
            "Apply or remove underline formatting to selected text or at cursor position",
            {}
        )
        
        self.register(
            "format_align",
            lambda alignment: self.executor.content_box.formatter.set_alignment(alignment) if self.executor.content_box else "Content Mode not active",
            "Set text alignment - left, center, right, or justify",
            {"alignment": "Alignment type: 'left', 'center', 'right', or 'justify'"}
        )
        
        self.register(
            "set_font",
            lambda font_name: self.executor.content_box.formatter.set_font_family(font_name) if self.executor.content_box else "Content Mode not active",
            "Change font family (e.g., Arial, Times New Roman, Courier)",
            {"font_name": "Font family name"}
        )
        
        self.register(
            "set_font_size",
            lambda size: self.executor.content_box.formatter.set_font_size(size) if self.executor.content_box else "Content Mode not active",
            "Set font size in points (8-24)",
            {"size": "Font size in points (8-24)"}
        )
        
        self.register(
            "increase_font_size",
            lambda: self.executor.content_box.formatter.increase_font_size() if self.executor.content_box else "Content Mode not active",
            "Make font bigger (increase by 2pt)",
            {}
        )
        
        self.register(
            "decrease_font_size",
            lambda: self.executor.content_box.formatter.decrease_font_size() if self.executor.content_box else "Content Mode not active",
            "Make font smaller (decrease by 2pt)",
            {}
        )
        
        self.register(
            "create_bullet_list",
            lambda: self.executor.content_box.formatter.create_bullet_list() if self.executor.content_box else "Content Mode not active",
            "Create bulleted list from selected paragraphs",
            {}
        )
        
        self.register(
            "create_numbered_list",
            lambda: self.executor.content_box.formatter.create_numbered_list() if self.executor.content_box else "Content Mode not active",
            "Create numbered list from selected paragraphs",
            {}
        )
        
        self.register(
            "increase_indent",
            lambda: self.executor.content_box.formatter.increase_indent() if self.executor.content_box else "Content Mode not active",
            "Increase paragraph indentation",
            {}
        )
        
        self.register(
            "decrease_indent",
            lambda: self.executor.content_box.formatter.decrease_indent() if self.executor.content_box else "Content Mode not active",
            "Decrease paragraph indentation",
            {}
        )
        
        self.register(
            "clear_formatting",
            lambda: self.executor.content_box.formatter.clear_formatting() if self.executor.content_box else "Content Mode not active",
            "Remove all formatting from selected text (make it plain text)",
            {}
        )
        
        # ===== NEXA APPLICATION CONTROL =====
        self.register(
            "exit_nexa",
            self.executor.exit_nexa,
            "Exit/close/shutdown Nexa application. Voice commands: 'exit nexa', 'close nexa', 'shutdown nexa', 'quit nexa', 'goodbye nexa', 'bye nexa'",
            {}
        )
    
    # Functions that require internet connection (blocked in offline mode)
    # Messages are user-friendly with clear instructions on how to enable
    INTERNET_REQUIRED_FUNCTIONS = {
        "get_weather": "I can't check the weather right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "get_forecast": "I can't get the forecast right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "search_web": "I can't search the web right now because I'm in offline mode. Say 'go online' to enable internet features.",
    }
    
    def _is_offline_mode(self) -> bool:
        """Check if we're currently in offline mode."""
        try:
            # Access llm_manager through executor -> brain -> llm_manager
            if hasattr(self.executor, 'brain') and self.executor.brain:
                from .llm_manager import LLMMode
                llm_manager = self.executor.brain.llm_manager
                if llm_manager:
                    current_mode = llm_manager.get_current_mode()
                    return current_mode == LLMMode.OFFLINE
        except Exception as e:
            logger.debug(f"Error checking offline mode: {e}")
        return False  # Default to online if we can't determine
    
    def call(self, function_name: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute a function by name with parameters.
        
        Args:
            function_name: Name of function to call
            parameters: Dict of parameter values
            
        Returns:
            Function result as string
        """
        if function_name not in self.functions:
            logger.error(f"Unknown function: {function_name}")
            return f"Error: Unknown function '{function_name}'"
        
        # Check if this function requires internet and we're offline
        if function_name in self.INTERNET_REQUIRED_FUNCTIONS:
            if self._is_offline_mode():
                blocked_msg = self.INTERNET_REQUIRED_FUNCTIONS[function_name]
                logger.warning(f"🔒 Function '{function_name}' blocked - offline mode")
                return blocked_msg
        
        func_info = self.functions[function_name]
        func = func_info["function"]
        
        try:
            # Call function with or without parameters
            if parameters:
                logger.debug(f"Calling {function_name} with params: {parameters}")
                result = func(**parameters)
            else:
                logger.debug(f"Calling {function_name} (no params)")
                result = func()
            
            return str(result) if result is not None else "Done"
            
        except Exception as e:
            logger.error(f"Error calling {function_name}: {e}", exc_info=True)
            return f"Error executing {function_name}: {str(e)}"
    
    def get_catalog(self, format_type: str = "detailed") -> str:
        """
        Get function catalog for AI prompt.
        
        Args:
            format_type: 'detailed' or 'compact'
            
        Returns:
            Formatted string of available functions
        """
        if format_type == "compact":
            # Short version for faster prompts
            return ", ".join(self.functions.keys())
        
        # Detailed version with descriptions
        catalog = []
        for name, info in self.functions.items():
            if info["parameters"]:
                params_list = [f"{k}: {v}" for k, v in info["parameters"].items()]
                params_str = ", ".join(params_list)
                catalog.append(f"- {name}({params_str}) - {info['description']}")
            else:
                catalog.append(f"- {name}() - {info['description']}")
        
        return "\n".join(catalog)
    
    def list_functions(self) -> list:
        """Get list of all registered function names."""
        return list(self.functions.keys())
    
    def has_function(self, function_name: str) -> bool:
        """Check if function is registered."""
        return function_name in self.functions
    
    def get_function_description(self, function_name: str) -> Optional[str]:
        """
        Return the human-readable description for a registered function.

        Args:
            function_name: Name of the registered function

        Returns:
            Description string if found, otherwise None
        """
        info = self.functions.get(function_name)
        if not info:
            logger.debug(f"get_function_description: function not found: {function_name}")
            return None
        return info.get("description")

    def get_function_info(self, function_name: str) -> Optional[Dict[str, Any]]:
        """
        Return the full info dict for a registered function (function callable, description, parameters).

        Args:
            function_name: Name of the registered function

        Returns:
            Dict with keys 'function', 'description', 'parameters' or None if not found
        """
        return self.functions.get(function_name)
