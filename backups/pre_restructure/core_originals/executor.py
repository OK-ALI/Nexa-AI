""" 
Command Executor - System-Level Task Execution
Handles system commands, app launching, and OS interactions securely.
"""

import logging
import subprocess
import platform
import os
from pathlib import Path
import webbrowser
from datetime import datetime
from typing import Optional, Tuple, List, Dict
import ctypes
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from PySide6.QtCore import QObject, Signal
from capabilities.vision.screen_reader import ScreenReader
from capabilities.system.mouse_controller import MouseController
from capabilities.system.window_manager import WindowManager
from capabilities.system.app_name_mapper import AppNameMapper
from capabilities.system.battery_manager import BatteryManager
from capabilities.vision.notification_reader import NotificationReader
from capabilities.system.app_discovery import AppDiscovery
from capabilities.vision.screenshot_manager import ScreenshotManager
from capabilities.creative.game_manager import GameManager
from capabilities.media.music_manager import MusicManager
from capabilities.web.weather_service import WeatherService
from core.cognition.natural_responses import NaturalResponses
from capabilities.function_registry import FunctionRegistry
from capabilities.web.sharing_service import SharingService
from capabilities.system.volume_controller import VolumeController
from capabilities.system.brightness_controller import BrightnessController
from capabilities.system.wifi_controller import WiFiController
from capabilities.media.media_controller import ContentModeHandler
from capabilities.web.file_share_handler import FileShareHandler
from capabilities.system.app_controller import ApplicationController
from capabilities.system.screen_controller import ScreenController
from capabilities.system.system_info import SystemInfoController
from capabilities.system.file_manager import FileManager
from capabilities.media.youtube_service import YouTubeService
from capabilities.web.web_scraper import WebScraper

logger = logging.getLogger(__name__)


class CommandExecutor(QObject):
    """
    Executes system-level commands and tasks securely.
    Provides controlled access to OS functions.
    Inherits from QObject to support signals for thread-safe GUI operations.
    """
    
    # Signal to request content window closure (thread-safe)
    close_content_window_requested = Signal()
    
    # Signal to launch NVP (NEXA Vision Player) on the GUI thread
    # Args: file_path, title, channel, duration, video_url, video_id, formats_json
    launch_nvp_requested = Signal(str, str, str, str, str, str, str)
    
    # Signal to launch NVP for local video playback
    # Args: file_path, title
    launch_nvp_local_requested = Signal(str, str)
    
    def __init__(self, config, context_manager=None, gpu_monitor=None):
        """
        Initialize command executor with configuration.
        
        Args:
            config: Configuration object
            context_manager: ContextManager instance for smart follow-ups (optional)
            gpu_monitor: GPUMonitor instance for GPU usage queries (optional)
        """
        super().__init__()  # Initialize QObject for signal support
        
        self.config = config
        self.os_name = platform.system()
        self.context_manager = context_manager  # For smart TTS follow-ups
        self.window = None  # Reference to NexaModernWindow (set by brain after creation)
        self.gpu_monitor = gpu_monitor  # GPU monitor for usage queries
        
        # Cache for installed applications (populated on demand)
        self._installed_apps_cache = None
        
        # Initialize app name mapper for friendly name recognition
        self.app_mapper = AppNameMapper()
        
        # Initialize dynamic app discovery for finding ANY installed app
        self.app_discovery = AppDiscovery()
        
        # Initialize battery manager for battery status
        self.battery_manager = BatteryManager()
        
        # Initialize screen reader and mouse controller for Phase 3.5
        self.screen_reader = ScreenReader(config)
        # Note: llm_manager will be set by brain.py after initialization
        self.mouse = MouseController()
        
        # Initialize notification reader (uses screen_reader and mouse)
        self.notification_reader = NotificationReader(self.screen_reader, self.mouse)
        
        # Initialize window manager for Phase 4
        self.window_manager = WindowManager()
        
        # Initialize screenshot manager for Phase 5
        self.screenshot_manager = ScreenshotManager(config)
        
        # Initialize game manager for Phase 12
        self.game_manager = GameManager()
        
        # Initialize file manager for Phase 21 (file operations & organization)
        self.file_manager = FileManager()
        
        # Initialize YouTube service for Phase 18 (online-only)
        self.youtube_service = YouTubeService(config)
        
        # Wire NVP (NEXA Vision Player) callback for embedded playback
        def _on_play_video(file_path, title, channel, duration, video_url, video_id, formats):
            import json
            formats_json = json.dumps(formats) if formats else '[]'
            self.launch_nvp_requested.emit(
                file_path, title, channel, duration, video_url, video_id or '', formats_json
            )
        self.youtube_service.on_play_video = _on_play_video
        logger.info("YouTube service initialized (NVP enabled)")
        
        # Initialize web scraper for Phase 18 (enhanced web search - online-only)
        self.web_scraper = WebScraper(config)
        logger.info("Web scraper initialized")
        
        # Initialize music manager for local music playback
        self.music_manager = MusicManager()
        
        # Initialize sharing service for Phase 15 (multi-platform file sharing)
        self.sharing_service = SharingService(config)
        logger.info("Sharing service initialized")
        
        # Track recently created/used files for smart sharing
        self.last_created_pdf: Optional[Path] = None
        self.last_screenshot: Optional[Path] = None
        self.last_used_file: Optional[Path] = None
        
        # Initialize weather service for weather information
        api_key = config.weather_api_key if hasattr(config, 'weather_api_key') else None
        default_location = config.weather_default_location if hasattr(config, 'weather_default_location') else None
        cache_minutes = config.weather_cache_minutes if hasattr(config, 'weather_cache_minutes') else 30
        
        if api_key:
            self.weather_service = WeatherService(
                api_key=api_key,
                default_location=default_location,
                cache_duration_minutes=cache_minutes,
                config=config  # Pass config for proper data directory
            )
            logger.info("Weather service initialized")
        else:
            self.weather_service = None
            logger.warning("Weather service disabled (no API key)")
        
        # Initialize function registry for dynamic command execution
        # Pass context_manager for Smart Memory skill tracking
        self.function_registry = FunctionRegistry(self, context_manager=self.context_manager)
        
        # ================================================================
        # EXTRACTED CONTROLLERS (Refactored from executor.py)
        # ================================================================
        
        # Volume controller for audio management
        self.volume_controller = VolumeController()
        
        # Brightness controller for screen brightness
        self.brightness_controller = BrightnessController()
        
        # WiFi controller for network management
        self.wifi_controller = WiFiController()
        
        # Content Mode handler for text editing and PDF generation
        self.content_mode_handler = ContentModeHandler(config, self)
        
        # File share handler for multi-platform sharing
        self.file_share_handler = FileShareHandler(config, self.sharing_service, self)
        
        # Application controller for app management
        self.application_controller = ApplicationController(
            app_discovery=self.app_discovery,
            app_mapper=self.app_mapper,
            window_manager=self.window_manager
        )
        
        # Screen controller for screenshots and screen reading
        self.screen_controller = ScreenController(
            screen_reader=self.screen_reader,
            screenshot_manager=self.screenshot_manager,
            mouse_controller=self.mouse
        )
        
        # System info controller for time, date, battery, GPU
        self.system_info_controller = SystemInfoController(
            battery_manager=self.battery_manager,
            gpu_monitor=self.gpu_monitor
        )
        
        logger.info(f"Command Executor initialized (OS: {self.os_name})")
        logger.info(f"Function Registry: {len(self.function_registry.functions)} functions available")
    
    def _check_offline_mode(self) -> bool:
        """
        Check if we're currently in offline mode.
        Used to block internet-requiring features in offline mode.
        
        Returns:
            True if in offline mode, False otherwise
        """
        try:
            if hasattr(self, 'brain') and self.brain and hasattr(self.brain, 'llm_manager'):
                from capabilities.llm.llm_manager import LLMMode
                return self.brain.llm_manager.get_current_mode() == LLMMode.OFFLINE
        except Exception as e:
            logger.debug(f"Error checking offline mode: {e}")
        return False
    
    def execute_command(self, command: str) -> Optional[str]:
        """
        Execute a system command safely.
        
        Args:
            command: Command to execute
            
        Returns:
            Command output or error message
        """
        logger.info(f"Executing command: {command}")
        
        try:
            # Security check - whitelist approach would be better for production
            if self._is_safe_command(command):
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                return result.stdout if result.returncode == 0 else result.stderr
            else:
                logger.warning(f"Command rejected for security: {command}")
                return "Command rejected for security reasons."
        
        except subprocess.TimeoutExpired:
            return "Command execution timed out."
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return f"Error: {str(e)}"
    
    def _is_safe_command(self, command: str) -> bool:
        """
        Check if command is safe to execute.
        Allows system control commands but blocks destructive operations.
        
        Args:
            command: Command to check
            
        Returns:
            bool: True if safe
        """
        # Blacklist only DESTRUCTIVE commands that permanently delete/modify data
        dangerous_patterns = [
            'rm -rf /',           # Linux recursive force delete
            'del /f /q /s',       # Windows force delete all
            'format ',            # Format drive
            'diskpart',           # Disk partitioning
            'shutdown /s',        # Shutdown system
            'shutdown -s',        # Alt shutdown
            'reg delete',         # Delete registry keys
            'rmdir /s /q',        # Remove directory recursively
            'rd /s /q',           # Alt remove directory
            'cipher /w',          # Wipe free space
            'wmic',               # WMI commands can be dangerous
        ]
        
        command_lower = command.lower()
        
        # Check for dangerous patterns
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                logger.warning(f"Blocked dangerous command: {command}")
                return False
        
        # Allow everything else (netsh, nircmd, powershell, etc.)
        logger.debug(f"Command approved as safe: {command[:100]}")
        return True
    
    def open_application(self, app_name: str) -> str:
        """
        Open an application by name - DYNAMICALLY finds installed apps.
        Uses AppDiscovery to search Start Menu, Store apps, Registry, and common paths.
        
        Args:
            app_name: Application name (e.g., 'notepad', 'Microsoft Store', 'Alienware Command Center')
            
        Returns:
            Result message
        """
        result = self.application_controller.open_application(app_name)
        
        if result.get('success'):
            return NaturalResponses.app_opened(app_name)
        elif result.get('not_found'):
            return NaturalResponses.app_not_found(app_name)
        else:
            return NaturalResponses.error()
    
    def _find_installed_app(self, app_name: str) -> Optional[str]:
        """
        DEPRECATED: Replaced by AppDiscovery class.
        Use self.app_discovery.find_app() or application_controller instead.
        """
        return self.application_controller.find_installed_app(app_name)
    
    def get_current_time(self) -> str:
        """Get current time in natural language."""
        return self.system_info_controller.get_current_time()
    
    def get_current_date(self) -> str:
        """Get current date in natural language."""
        return self.system_info_controller.get_current_date()
    
    def search_web(self, query: str) -> str:
        """
        Open web browser with search query - USES DEFAULT BROWSER.
        Requires online mode (internet connection).
        
        Args:
            query: Search query
            
        Returns:
            Result message
        """
        # Check offline mode - web search requires internet
        if self._check_offline_mode():
            logger.warning("🔒 Web search blocked - offline mode")
            return "I can't search the web right now because I'm in offline mode. Say 'go online' or 'switch to online mode' to enable internet features, then try again."
        
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            # Use webbrowser module - automatically uses system default browser
            webbrowser.open(search_url)
            
            # Try to detect which browser was opened
            default_browser = self._get_default_browser()
            if default_browser:
                return f"Searching for '{query}' in {default_browser}"
            else:
                return f"Searching for '{query}' in your default browser"
        
        except Exception as e:
            logger.error(f"Error opening web search: {e}")
            return "Failed to open web search."
    
    def _get_default_browser(self) -> Optional[str]:
        """
        Get the name of the default web browser.
        
        Returns:
            Browser name or None
        """
        try:
            if self.os_name == "Windows":
                import winreg
                
                # Check user choice
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                        r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice")
                    prog_id = winreg.QueryValueEx(key, "ProgId")[0]
                    winreg.CloseKey(key)
                    
                    # Map ProgId to browser name
                    if 'chrome' in prog_id.lower():
                        return 'Chrome'
                    elif 'firefox' in prog_id.lower():
                        return 'Firefox'
                    elif 'edge' in prog_id.lower():
                        return 'Edge'
                    elif 'brave' in prog_id.lower():
                        return 'Brave'
                    elif 'opera' in prog_id.lower():
                        return 'Opera'
                except:
                    pass
            
            return None
        except:
            return None
    
    # ================================================================
    # YOUTUBE INTEGRATION (Phase 18 - Online Only)
    # ================================================================
    
    def play_youtube(self, query: str) -> str:
        """Play a YouTube video by name or URL."""
        return self.youtube_service.play_youtube(query)
    
    def play_local_video(self, query: str = "") -> str:
        """
        Play a local video/movie from the movie library (D:\\Movie).
        
        Scans movie folders, fuzzy-matches the query to find the right file,
        and launches NVP in local mode. If no query given, picks a random movie.
        
        Args:
            query: Movie name or partial title to search for (optional)
            
        Returns:
            Status message
        """
        from ui.nexa_vision_player import NexaVisionPlayer
        import random as _rand
        
        if query:
            movie_path = NexaVisionPlayer.find_movie(query)
        else:
            # No query — pick a random movie from the library
            movies = NexaVisionPlayer.scan_movie_library()
            if movies:
                movie = _rand.choice(movies)
                movie_path = movie['path']
            else:
                movie_path = None
        
        if movie_path:
            title = Path(movie_path).stem.replace('.', ' ').replace('_', ' ')
            self.launch_nvp_local_requested.emit(movie_path, title)
            return f"Playing '{title}' on NEXA Vision Player"
        else:
            if query:
                return f"Couldn't find a movie matching '{query}' in the library. Check D:\\Movie folder."
            else:
                return "No movies found in D:\\Movie library."
    
    def search_youtube(self, query: str, count: int = 5) -> str:
        """Search YouTube and return results."""
        return self.youtube_service.search_youtube(query, count)
    
    def play_youtube_result(self, number: int) -> str:
        """Play a video from the last search results by number."""
        return self.youtube_service.play_youtube_result(number)
    
    def get_video_info(self, query: str = "") -> str:
        """Get detailed info about a YouTube video."""
        return self.youtube_service.get_video_info(query)
    
    def download_youtube(self, query: str, audio_only: bool = False, quality: str = "1080p") -> str:
        """Download a YouTube video or audio."""
        return self.youtube_service.download_youtube(query, audio_only, quality)
    
    def download_youtube_video(self, query: str, quality: str = "1080p") -> str:
        """Download a YouTube video in specified quality."""
        return self.youtube_service.download_youtube_video(query, quality)
    
    def download_youtube_audio(self, query: str) -> str:
        """Download audio (MP3) from a YouTube video."""
        return self.youtube_service.download_youtube_audio(query)
    
    def get_download_status(self) -> str:
        """Get current download progress status."""
        return self.youtube_service.get_download_status()
    
    def get_youtube_queue(self) -> str:
        """Get the current YouTube playback queue."""
        return self.youtube_service.get_youtube_queue()
    
    def clear_youtube_queue(self) -> str:
        """Clear the YouTube playback queue."""
        return self.youtube_service.clear_youtube_queue()
    
    # ================================================================
    # ENHANCED WEB SEARCH (Phase 18 - Online Only)
    # ================================================================
    
    def smart_search(self, query: str) -> str:
        """Search the web and return actual content (not just open browser)."""
        return self.web_scraper.smart_search(query)
    
    def scrape_url(self, url: str) -> str:
        """Scrape a specific URL and return its text content."""
        return self.web_scraper.scrape_url(url)
    
    def get_running_applications(self, is_follow_up: bool = False) -> str:
        """
        Get list of currently running applications (with user-friendly names).
        
        Args:
            is_follow_up: If True, return detailed list with friendly names
        
        Returns:
            Formatted list of running apps with friendly names (Chrome, not chrome.exe)
        """
        try:
            if self.os_name == "Windows":
                import psutil
                from capabilities.system.app_name_mapper import AppNameMapper
                
                # Initialize app name mapper for friendly names
                mapper = AppNameMapper()
                
                # System processes to filter out (FIXED - more precise filtering)
                system_blacklist = {
                    'system', 'svchost', 'dwm', 'csrss', 'conhost', 'runtimebroker', 
                    'searchindexer', 'searchhost', 'fontdrvhost', 'backgroundtaskhost',
                    'sihost', 'taskhostw', 'spoolsv', 'lsass', 'services', 'smss',
                    'winlogon', 'wininit', 'audiodg', 'ctfmon',
                    'dllhost', 'wudfhost', 'securityhealthservice',
                    'yourphone', 'textinputhost', 'shellexperiencehost',
                    'startmenuexperiencehost', 'searchapp', 'windowsinternal',
                    'applicationframehost', 'systemsettings', 'lockapp'
                }
                
                # Get processes with windows (GUI applications)
                running_processes = {}  # {friendly_name: process_name}
                total_processed = 0
                filtered_count = 0
                
                for proc in psutil.process_iter(['name', 'exe']):
                    try:
                        proc_name = proc.info['name']
                        
                        if not proc_name:
                            continue
                        
                        total_processed += 1
                        
                        # Clean up name
                        clean_name = proc_name.replace('.exe', '').replace('.EXE', '').lower()
                        
                        # CRITICAL: More precise system process filtering
                        # Exact match in blacklist
                        if clean_name in system_blacklist:
                            filtered_count += 1
                            continue
                        
                        # Specific Windows system prefixes only (not all "win")
                        if clean_name.startswith(('svchost', 'dwm', 'csrss', 'winlogon', 'wininit')):
                            filtered_count += 1
                            continue
                        
                        # Filter out obvious system components (check exe path, not name)
                        exe_path = proc.info.get('exe', '') or ''
                        if exe_path and ('system32' in exe_path.lower() or 'windows\\system' in exe_path.lower()):
                            filtered_count += 1
                            continue
                        
                        # Map to friendly name using app_name_mapper
                        friendly_name = mapper.normalize_app_name(proc_name)
                        
                        # Skip if mapper returns empty/None
                        if not friendly_name or friendly_name.strip() == '':
                            filtered_count += 1
                            continue
                        
                        # Deduplicate (multiple chrome.exe → one "Chrome" entry)
                        running_processes[friendly_name] = proc_name
                        
                    except:
                        continue
                
                # Debug logging
                logger.info(f"📊 Processed {total_processed} processes, filtered {filtered_count}, found {len(running_processes)} apps")
                
                if running_processes:
                    # Sort alphabetically for better TTS
                    sorted_apps = sorted(running_processes.keys())
                    logger.info(f"✅ Running apps: {sorted_apps[:10]}")
                    
                    # For follow-ups, give detailed list. For initial query, give count + short list
                    if is_follow_up or len(sorted_apps) <= 8:
                        app_list = ", ".join(sorted_apps)
                        return f"Running applications: {app_list}"
                    else:
                        # Initial query: show count + top 8
                        app_list = ", ".join(sorted_apps[:8])
                        return f"You have {len(sorted_apps)} applications running. Top apps: {app_list}. Say 'which ones?' to see all."
                else:
                    logger.warning(f"⚠️ No apps found after filtering {filtered_count} system processes from {total_processed} total")
                    return "No user applications currently running."
            
            return "Application listing only available on Windows"
            
        except Exception as e:
            logger.error(f"Error getting running apps: {e}")
            return f"Failed to get running applications: {str(e)}"
    
    def get_installed_applications(self, search_query: str = None, limit: int = 20) -> str:
        """
        Get list of installed applications on the system.
        Uses dynamic app discovery to find all installed apps from:
        - Start Menu shortcuts
        - Windows Store apps
        - Registry installed programs
        
        Args:
            search_query: Optional search filter (e.g., "video" to find video apps)
            limit: Maximum number of apps to list (default: 20)
            
        Returns:
            Formatted list of installed applications
        """
        try:
            # Ensure app discovery has indexed
            if not self.app_discovery.indexed:
                logger.info("📦 Indexing installed applications...")
                self.app_discovery.index_all_apps()
            
            # Get all installed apps
            all_apps = list(self.app_discovery.app_cache.keys())
            
            # Filter by search query if provided
            if search_query:
                search_lower = search_query.lower()
                filtered_apps = [app for app in all_apps if search_lower in app.lower()]
                all_apps = filtered_apps
            
            if not all_apps:
                if search_query:
                    return f"I couldn't find any installed applications matching '{search_query}'."
                return "I couldn't find any installed applications."
            
            # Sort alphabetically
            sorted_apps = sorted(all_apps, key=str.lower)
            
            # Limit results
            total_count = len(sorted_apps)
            if limit and total_count > limit:
                sorted_apps = sorted_apps[:limit]
            
            # Clean up app names (remove common suffixes/prefixes)
            clean_apps = []
            for app in sorted_apps:
                # Skip obvious non-apps
                if any(skip in app.lower() for skip in ['uninstall', 'readme', 'help', 'license']):
                    continue
                clean_apps.append(app)
            
            # Format response
            if search_query:
                if len(clean_apps) == 1:
                    return f"I found one app matching '{search_query}': {clean_apps[0]}"
                elif len(clean_apps) <= 10:
                    app_list = ", ".join(clean_apps)
                    return f"I found {len(clean_apps)} apps matching '{search_query}': {app_list}"
                else:
                    app_list = ", ".join(clean_apps[:10])
                    return f"I found {len(clean_apps)} apps matching '{search_query}'. Here are the first 10: {app_list}. Say 'more' to see more."
            else:
                if len(clean_apps) <= 15:
                    app_list = ", ".join(clean_apps)
                    return f"You have {total_count} installed applications. Here they are: {app_list}"
                else:
                    app_list = ", ".join(clean_apps[:15])
                    return f"You have {total_count} installed applications. Here are 15: {app_list}. Say 'search apps' followed by a keyword to find specific ones."
        
        except Exception as e:
            logger.error(f"Error getting installed apps: {e}")
            return f"Failed to get installed applications: {str(e)}"
    
    def refresh_installed_apps(self) -> str:
        """
        Force re-scan of installed applications.
        Useful when new apps are installed or to pick up changes.
        
        Returns:
            Status message with count of apps found
        """
        try:
            logger.info("🔄 Refreshing installed applications index...")
            self.app_discovery.refresh_index()
            count = len(self.app_discovery.app_cache)
            return f"Refreshed! I found {count} installed applications."
        except Exception as e:
            logger.error(f"Error refreshing app index: {e}")
            return f"Failed to refresh app list: {str(e)}"
    
    def is_application_running(self, app_name: str) -> bool:
        """Check if a specific application is currently running."""
        return self.application_controller.is_application_running(app_name)
    
    def close_application(self, app_name: str) -> str:
        """
        Close a running application by name.
        Supports friendly names and active window fallback.
        """
        result = self.application_controller.close_application(app_name)
        
        if result.get('success'):
            return NaturalResponses.app_closed(app_name)
        elif result.get('not_running'):
            return NaturalResponses.app_not_running(app_name)
        else:
            return result.get('message', f"Failed to close {app_name}")
    
    def get_system_info(self) -> str:
        """
        Get comprehensive system information.
        
        Returns:
            System info as natural language string
        """
        if self.system_info_controller:
            return self.system_info_controller.get_system_info_message()
        
        # Fallback if controller not available
        info = {
            'OS': platform.system(),
            'Version': platform.version(),
            'Machine': platform.machine(),
            'Processor': platform.processor()
        }
        return "System Information: " + ", ".join([f"{k}: {v}" for k, v in info.items()])
    
    def get_pc_specs(self) -> str:
        """
        Get PC specifications as natural language.
        Alias for get_system_info.
        
        Returns:
            PC specs string
        """
        return self.get_system_info()
    
    # ============================================================
    # VOLUME CONTROL - Delegated to VolumeController
    # ============================================================
    
    def get_current_volume(self) -> str:
        """Get current system volume level and mute status."""
        return self.volume_controller.get_current_volume()
    
    def set_volume(self, level: int) -> str:
        """Set system volume to specific level (0-100)."""
        return self.volume_controller.set_volume(level)
    
    def increase_volume(self, amount: int = 10) -> str:
        """Increase volume by amount (default 10%)."""
        return self.volume_controller.increase_volume(amount)
    
    def decrease_volume(self, amount: int = 10) -> str:
        """Decrease volume by amount (default 10%)."""
        return self.volume_controller.decrease_volume(amount)
    
    def mute_volume(self) -> str:
        """Mute system volume."""
        return self.volume_controller.mute_volume()
    
    def unmute_volume(self) -> str:
        """Unmute system volume."""
        return self.volume_controller.unmute_volume()
    
    def toggle_mute(self) -> str:
        """Toggle mute status."""
        return self.volume_controller.toggle_mute()
    
    # ============================================================
    # BRIGHTNESS CONTROL - Delegated to BrightnessController
    # ============================================================
    
    def get_current_brightness(self) -> str:
        """Get current screen brightness level."""
        return self.brightness_controller.get_current_brightness()
    
    def set_brightness(self, level: int) -> str:
        """Set screen brightness to specific level (0-100)."""
        return self.brightness_controller.set_brightness(level)
    
    def increase_brightness(self, amount: int = 10) -> str:
        """Increase brightness by amount (default 10%)."""
        return self.brightness_controller.increase_brightness(amount)
    
    def decrease_brightness(self, amount: int = 10) -> str:
        """Decrease brightness by amount (default 10%)."""
        return self.brightness_controller.decrease_brightness(amount)
    
    # ============================================================
    # WIFI MANAGEMENT - Delegated to WiFiController
    # ============================================================
    
    def get_wifi_status(self) -> str:
        """Get current WiFi connection status."""
        return self.wifi_controller.get_wifi_status()
    
    def disconnect_wifi(self) -> str:
        """Disconnect from current WiFi network."""
        return self.wifi_controller.disconnect_wifi()
    
    def connect_wifi(self, network_name: str) -> str:
        """Connect to a WiFi network by name."""
        return self.wifi_controller.connect_wifi(network_name)
    
    def list_wifi_networks(self) -> str:
        """List available WiFi networks."""
        return self.wifi_controller.list_wifi_networks()
    
    def get_saved_wifi_profiles(self) -> str:
        """Get list of saved WiFi network profiles."""
        return self.wifi_controller.get_saved_wifi_profiles()
    
    # ========================== SMART TEXT SELECTION (Phase 3.5) ==========================
    
    def find_and_select_text(self, query: str) -> str:
        """Find text on screen using Vision and select it."""
        result = self.screen_controller.find_and_select_text(query)
        return result.get('message', f"Failed to find '{query}'")
    
    def find_and_copy_text(self, query: str) -> str:
        """Find text on screen and copy it to clipboard."""
        result = self.screen_controller.find_and_copy_text(query)
        return result.get('message', f"Failed to find '{query}'")
    
    def find_and_delete_text(self, query: str) -> str:
        """Find text on screen and delete it."""
        result = self.screen_controller.find_and_delete_text(query)
        return result.get('message', f"Failed to find '{query}'")
    
    def read_screen_content(self) -> str:
        """Read all text visible on screen using Vision."""
        content = self.screen_controller.read_screen_content()
        if content:
            if len(content) > 200:
                return f"Screen content: {content[:200]}... and more"
            return f"Screen content: {content}"
        return "Could not read screen content"
    
    def describe_screen(self) -> str:
        """Get AI description of what's on screen."""
        description = self.screen_controller.describe_screen()
        return description or "Could not describe screen"
    
    def select_all_text(self) -> str:
        """
        Select all text using Ctrl+A.
        
        Returns:
            Success message
        """
        try:
            self.mouse.select_all()
            return "Selected all text"
        except Exception as e:
            logger.error(f"Error selecting all: {e}")
            return f"Failed to select all: {str(e)}"
    
    def copy_selected(self) -> str:
        """
        Copy currently selected text (Ctrl+C).
        
        Returns:
            Success message
        """
        try:
            self.mouse.copy_selection()
            return "Copied selected text to clipboard"
        except Exception as e:
            logger.error(f"Error copying: {e}")
            return f"Failed to copy: {str(e)}"
    
    def paste_clipboard(self) -> str:
        """
        Paste clipboard content (Ctrl+V).
        
        Returns:
            Success message
        """
        try:
            self.mouse.paste()
            return "Pasted clipboard content"
        except Exception as e:
            logger.error(f"Error pasting: {e}")
            return f"Failed to paste: {str(e)}"
    
    def cut_selected(self) -> str:
        """
        Cut selected text (Ctrl+X).
        
        Returns:
            Success message
        """
        try:
            self.mouse.cut_selection()
            return "Cut selected text to clipboard"
        except Exception as e:
            logger.error(f"Error cutting: {e}")
            return f"Failed to cut: {str(e)}"
    
    def delete_selected(self) -> str:
        """
        Delete selected text (Delete key).
        
        Returns:
            Success message
        """
        try:
            self.mouse.delete_selection()
            return "Deleted selected text"
        except Exception as e:
            logger.error(f"Error deleting: {e}")
            return f"Failed to delete: {str(e)}"
    
    # ==================== Phase 4: Window Management ====================
    
    def minimize_window(self, identifier: str) -> str:
        """
        Minimize a window by title or process name.
        
        Args:
            identifier: Window title or process name
            
        Returns:
            Result message
        """
        logger.info(f"Minimizing window: {identifier}")
        return self.window_manager.minimize_window(identifier)
    
    def maximize_window(self, identifier: str) -> str:
        """
        Maximize a window by title or process name.
        
        Args:
            identifier: Window title or process name
            
        Returns:
            Result message
        """
        logger.info(f"Maximizing window: {identifier}")
        return self.window_manager.maximize_window(identifier)
    
    def restore_window(self, identifier: str) -> str:
        """
        Restore a window to normal size (from minimized/maximized).
        
        Args:
            identifier: Window title or process name
            
        Returns:
            Result message
        """
        logger.info(f"Restoring window: {identifier}")
        return self.window_manager.restore_window(identifier)
    
    def hide_window(self, identifier: str) -> str:
        """
        Hide a window (process keeps running).
        
        Args:
            identifier: Window title or process name
            
        Returns:
            Result message
        """
        logger.info(f"Hiding window: {identifier}")
        return self.window_manager.hide_window(identifier)
    
    def show_window(self, identifier: str) -> str:
        """
        Show a hidden window.
        
        Args:
            identifier: Window title or process name
            
        Returns:
            Result message
        """
        logger.info(f"Showing window: {identifier}")
        return self.window_manager.show_window(identifier)
    
    def window_exists(self, identifier: str) -> bool:
        """
        Check if a window exists.
        
        Args:
            identifier: Window title, process name, or friendly app name
            
        Returns:
            True if window exists, False otherwise
        """
        return self.window_manager.window_exists(identifier)
    
    def get_active_window(self) -> str:
        """
        Get the title of the currently active window.
        
        Returns:
            Active window title
        """
        return self.window_manager.get_active_window_title()
    
    def get_window_state(self, identifier: str) -> str:
        """
        Get the current state of a window.
        
        Args:
            identifier: Window title or process name
            
        Returns:
            Window state description
        """
        return self.window_manager.get_window_state(identifier)
    
    # ==================== Battery Status ====================
    
    def get_battery_status(self) -> str:
        """Get comprehensive battery status."""
        return self.system_info_controller.get_battery_status()
    
    def get_battery_percentage(self) -> str:
        """Get battery percentage only."""
        percent = self.system_info_controller.get_battery_percentage()
        return f"Battery is at {percent}%"
    
    def is_battery_charging(self) -> str:
        """Check if battery is charging."""
        is_charging = self.system_info_controller.is_battery_charging()
        if is_charging:
            return "Battery is currently charging"
        else:
            return "Battery is not charging (running on battery)"
    
    def get_battery_time_remaining(self) -> str:
        """Get battery time remaining."""
        return self.system_info_controller.get_battery_time_remaining()
    
    def get_gpu_usage(self) -> str:
        """Get current GPU usage and memory statistics."""
        return self.system_info_controller.get_gpu_usage_message()
    
    # ==================== Weather Information ====================
    
    def get_weather(self, location: Optional[str] = None) -> str:
        """
        Get current weather for a location.
        Requires online mode (internet connection).
        
        Args:
            location: City name (e.g., "Tokyo", "London,UK"). If None, auto-detects.
            
        Returns:
            Natural language weather description
        """
        # Check offline mode - weather requires internet
        if self._check_offline_mode():
            logger.warning("🔒 Weather blocked - offline mode")
            return "I can't check the weather right now because I'm in offline mode. Say 'go online' to enable internet features, then ask me again."
        
        if not self.weather_service:
            return "Weather service is not available. Please configure your OpenWeatherMap API key in settings."
        
        logger.info(f"Getting weather for: {location or 'auto-detected location'}")
        return self.weather_service.get_weather(location)
    
    def get_forecast(self, location: Optional[str] = None, days: int = 3) -> str:
        """
        Get weather forecast for next N days.
        Requires online mode (internet connection).
        
        Args:
            location: City name. If None, auto-detects.
            days: Number of days (1-5, default 3)
            
        Returns:
            Natural language forecast description
        """
        # Check offline mode - forecast requires internet
        if self._check_offline_mode():
            logger.warning("🔒 Weather forecast blocked - offline mode")
            return "I can't get the forecast right now because I'm in offline mode. Say 'go online' to enable internet features, then ask me again."
        
        if not self.weather_service:
            return "Weather forecast is not available. Please configure your OpenWeatherMap API key in settings."
        
        logger.info(f"Getting {days}-day forecast for: {location or 'auto-detected location'}")
        return self.weather_service.get_forecast(location, days)
    
    # =========================
    # Conversation History Methods
    # =========================
    
    def clear_conversation_history(self) -> str:
        """
        Clear all conversation history.
        
        Returns:
            Success message
        """
        try:
            if self.context_manager:
                self.context_manager.clear_history()
                return "I've cleared our conversation history. Starting fresh!"
            else:
                return "Conversation history is not available"
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return f"Failed to clear history: {str(e)}"
    
    # =========================
    # Notification Methods (Bug Fix #3)
    # =========================
    
    def read_notifications(self) -> str:
        """
        Read Windows notifications using mouse + Gemini Vision.
        Opens Action Center, takes screenshot, analyzes with AI.
        
        Returns:
            str: Notification summary for voice response
        """
        try:
            logger.info("Reading notifications...")
            result = self.notification_reader.get_notification_summary()
            logger.info(f"Notification result: {result}")
            return result
        except Exception as e:
            error_msg = f"Error reading notifications: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def check_notifications(self) -> str:
        """
        Check if there are any notifications.
        
        Returns:
            str: Quick notification check response
        """
        try:
            has_notifications = self.notification_reader.has_notifications()
            if has_notifications:
                return self.read_notifications()
            else:
                return "You have no new notifications"
        except Exception as e:
            error_msg = f"Error checking notifications: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    # =========================
    # Screenshot Methods (Phase 5)
    # =========================
    
    def take_screenshot(self, copy_to_clipboard: bool = False) -> str:
        """Take a screenshot of the entire screen."""
        result = self.screen_controller.take_screenshot(copy_to_clipboard)
        
        # Track for smart sharing
        if result.get('success') and result.get('file_path'):
            self.last_screenshot = Path(result['file_path'])
            self.last_used_file = Path(result['file_path'])
        
        return result.get('message', 'Screenshot failed')
    
    def open_screenshots_folder(self) -> str:
        """Open the screenshots folder in File Explorer."""
        success = self.screen_controller.open_screenshots_folder()
        return "Opening screenshots folder" if success else "Failed to open screenshots folder"
    
    def get_screenshot_count(self) -> str:
        """
        Get the number of screenshots taken.
        
        Returns:
            str: Number of screenshots
        """
        try:
            count = self.screenshot_manager.get_screenshot_count()
            if count == 0:
                return "You haven't taken any screenshots yet"
            elif count == 1:
                return "You have 1 screenshot"
            else:
                return f"You have {count} screenshots"
        except Exception as e:
            error_msg = f"Error counting screenshots: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    # ========================================
    # Game Management Methods (Phase 12)
    # ========================================
    
    def launch_game(self, game_name: str) -> str:
        """
        Launch a game by name (Steam, Epic, GOG, or standalone).
        
        Args:
            game_name: Name of the game to launch
            
        Returns:
            str: Result message
        """
        try:
            success, message = self.game_manager.launch_game(game_name)
            return message
        except Exception as e:
            error_msg = f"Error launching game: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def list_games(self, platform: Optional[str] = None, is_follow_up: bool = False) -> str:
        """
        List all detected games with smart TTS support.
        
        Args:
            platform: Filter by platform (Steam, Epic, GOG, Standalone) or None for all
            is_follow_up: If True, return detailed game names (for follow-up questions)
            
        Returns:
            str: Formatted list of games (count only initially, names on follow-up)
        """
        try:
            logger.info(f"🎮 list_games called: platform={platform}, is_follow_up={is_follow_up}")
            games = self.game_manager.list_games(platform)
            
            if not games:
                if platform:
                    return f"No {platform} games found"
                return "No games found. Make sure Steam, Epic Games, or GOG are installed."
            
            logger.info(f"✅ Found {len(games)} games: {games[:3]}")
            
            # SMART TTS: Initial query = count only, Follow-up = game names
            if is_follow_up:
                logger.info(f"🔍 Follow-up detected - returning game names")
                # Follow-up: Return game names WITHOUT platforms
                game_names_only = []
                for game in games:
                    # Extract name before platform marker (e.g., "TEKKEN 8 (Steam)" → "TEKKEN 8")
                    if ' (' in game:
                        name = game.split(' (')[0]
                    else:
                        name = game
                    game_names_only.append(name)
                
                logger.info(f"📝 Game names extracted: {game_names_only}")
                
                # Format for TTS
                if len(game_names_only) <= 5:
                    # Read all names
                    result = ", ".join(game_names_only)
                    logger.info(f"✅ Returning all {len(game_names_only)} game names: {result}")
                    return result
                elif len(game_names_only) <= 10:
                    # Read first 8, mention rest
                    listed = ", ".join(game_names_only[:8])
                    return f"{listed}, and {len(game_names_only) - 8} more"
                else:
                    # Read first 5, summarize rest
                    listed = ", ".join(game_names_only[:5])
                    return f"{listed}, and {len(game_names_only) - 5} more games"
            
            else:
                # Initial query: Just count (no verbose hints)
                count = len(games)
                if platform:
                    response = f"You have {count} {platform} game{'s' if count != 1 else ''} installed."
                else:
                    response = f"You have {count} game{'s' if count != 1 else ''} installed."
                
                # Store context for follow-up (if context_manager available)
                if self.context_manager:
                    self.context_manager.set_last_action('list_games', {
                        'games': games,
                        'count': count,
                        'platform': platform
                    })
                
                return response
        
        except Exception as e:
            error_msg = f"Error listing games: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def list_music(self, limit: int = None, artist: str = None) -> str:
        """
        List songs in music library with follow-up support.
        
        Args:
            limit: Maximum number of songs to list
            artist: Filter by artist name
            
        Returns:
            str: Formatted list of songs
        """
        try:
            # Get song list from music manager
            songs = self.music_manager.list_songs(limit=limit, filter_artist=artist)
            count = len(songs)
            
            if count == 0:
                if artist:
                    return f"No songs found by {artist}"
                return "No songs found in your music library"
            
            # Store for follow-up (e.g., "play the third one")
            if self.context_manager:
                self.context_manager.set_last_action('list_music', {
                    'songs': songs,
                    'count': count,
                    'artist': artist
                })
            
            # Format response
            if count <= 5:
                song_list = ", ".join(songs)
                return f"Found {count} song{'s' if count != 1 else ''}: {song_list}"
            else:
                # Show first 5 with count
                preview = ", ".join(songs[:5])
                return f"Found {count} songs. Here are some: {preview}, and {count - 5} more"
                
        except Exception as e:
            error_msg = f"Error listing music: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def open_folder(self, folder_name: str) -> str:
        """
        Open a folder in File Explorer.
        
        Args:
            folder_name: Folder name or path to open
            
        Returns:
            str: Result message
        """
        try:
            # Special case: "screenshots" refers to Nexa's screenshots folder
            if folder_name.lower() in ['screenshots', 'screenshot']:
                logger.info("🖼️ Special case detected: opening Nexa screenshots folder")
                return self.open_screenshots_folder()
            
            # Otherwise, use game_manager to find folder
            success, message = self.game_manager.open_folder(folder_name)
            return message
        except Exception as e:
            error_msg = f"Error opening folder: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def find_folder(self, folder_name: str) -> str:
        """
        Find a folder by name and report its location.
        
        Args:
            folder_name: Folder name to search for
            
        Returns:
            str: Folder location or error message
        """
        try:
            # Call find_folder from game_manager (returns path string or None)
            folder_path = self.game_manager.find_folder(folder_name)
            
            if folder_path:
                return f"Found {folder_name} at: {folder_path}"
            else:
                return f"Folder '{folder_name}' not found. Try 'open downloads folder' or 'open documents folder'."
        
        except Exception as e:
            error_msg = f"Error finding folder: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    # ======================================================================
    # CONTENT MODE - Delegated to ContentModeHandler
    # ======================================================================
    
    @property
    def _content_mode_exiting(self) -> bool:
        """Check if Content Mode is exiting."""
        return self.content_mode_handler.is_exiting()
    
    @_content_mode_exiting.setter
    def _content_mode_exiting(self, value: bool):
        """Set the exiting flag via handler."""
        self.content_mode_handler._is_exiting = value

    def enter_content_mode(self) -> str:
        """Enter Content Mode - Opens Content Box window for text editing and PDF generation."""
        return self.content_mode_handler.enter_content_mode()
    
    def exit_content_mode(self) -> str:
        """Exit Content Mode - Closes Content Box window."""
        return self.content_mode_handler.exit_content_mode()
    
    def refine_text(self, mode: str, text: Optional[str] = None) -> str:
        """Refine text content using AI."""
        return self.content_mode_handler.refine_text(mode, text)
    
    def create_pdf(self, pdf_format: str = "simple_text", filename: Optional[str] = None, 
                   text: Optional[str] = None, title: Optional[str] = None) -> str:
        """Create a PDF document from text content."""
        return self.content_mode_handler.create_pdf(pdf_format, filename, text, title)
    
    def _on_content_window_closed(self):
        """Handle Content Box window close event."""
        self.content_mode_handler.on_content_window_closed()
    
    def _on_refine_requested(self, mode: str, text: str):
        """Handle refine request from Content Box window."""
        self.content_mode_handler.on_refine_requested(mode, text)
    
    def _on_pdf_requested(self, pdf_format: str, filename: str, text: str):
        """Handle PDF creation request from Content Box window."""
        self.content_mode_handler.on_pdf_requested(pdf_format, filename, text)
    
    def _on_content_ready(self, text: str):
        """Handle content ready signal from Content Box window."""
        self.content_mode_handler.on_content_ready(text)
    
    def mark_content_ready(self) -> str:
        """Voice command: Mark content as ready for processing."""
        return self.content_mode_handler.mark_content_ready()

    # ========================================================================
    # PHASE 15 - FILE SHARING - Delegated to FileShareHandler
    # ========================================================================
    
    def share_file(self, file_path: Optional[str] = None) -> str:
        """Open Windows Share dialog with file attached."""
        return self.file_share_handler.share_file(file_path)
    
    def share_to_whatsapp(self, file_path: Optional[str] = None) -> str:
        """Share file via WhatsApp."""
        return self.file_share_handler.share_to_whatsapp(file_path)
    
    def share_to_phone_nearby(self, file_path: Optional[str] = None) -> str:
        """Share file to phone via Windows Nearby Share."""
        return self.file_share_handler.share_to_phone_nearby(file_path)
    
    def share_via_phone_link(self, file_path: Optional[str] = None) -> str:
        """Share file via Phone Link to paired device."""
        return self.file_share_handler.share_via_phone_link(file_path)
    
    def upload_to_google_drive(self, file_path: Optional[str] = None, folder: str = "Nexa Shared") -> str:
        """Upload file to Google Drive."""
        return self.file_share_handler.upload_to_google_drive(file_path, folder)
    
    def copy_file_to_clipboard_action(self, file_path: Optional[str] = None) -> str:
        """Copy file to clipboard for pasting."""
        return self.file_share_handler.copy_file_to_clipboard_action(file_path)
    
    # ========================================================================
    # APPLICATION CONTROL
    # ========================================================================
    
    def exit_nexa(self) -> str:
        """
        Exit/shutdown Nexa application gracefully.
        Voice commands: "exit nexa", "close nexa", "shutdown nexa", "quit nexa", "goodbye nexa"
        
        Returns:
            str: Goodbye message
        """
        try:
            logger.info("🛑 User requested Nexa shutdown via voice command")
            
            # Speak goodbye
            if hasattr(self, 'brain') and self.brain:
                try:
                    self.brain._speak_response("Goodbye! See you next time.")
                except Exception as e:
                    logger.debug(f"Could not speak goodbye: {e}")
            
            # Schedule application exit after a short delay (allow goodbye to play)
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication
            
            QTimer.singleShot(1500, QApplication.quit)
            
            return "Shutting down Nexa. Goodbye!"
            
        except Exception as e:
            error_msg = f"Error during shutdown: {str(e)}"
            logger.error(error_msg)
            return error_msg

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 29: PROACTIVE ENGAGEMENT
    # Handles user responses to proactive suggestions from the companion module
    # ═══════════════════════════════════════════════════════════════════════════
    
    def accept_proactive_suggestion(self) -> str:
        """
        User accepted a proactive suggestion.
        
        Returns:
            str: Confirmation message
        """
        try:
            from core.companion import get_proactive_engine, get_idle_monitor
            
            engine = get_proactive_engine()
            idle_monitor = get_idle_monitor()
            
            if engine:
                suggestion = engine.get_pending_suggestion()
                if suggestion:
                    engine.record_response(accepted=True)
                    
                    # Record in idle monitor too
                    if idle_monitor:
                        idle_monitor.record_proactive_response(accepted=True)
                    
                    logger.info("Proactive suggestion accepted: %s", suggestion.suggestion_type.value)
                    return "Great! I'll keep that in mind."
                else:
                    return "No pending suggestion to accept."
            else:
                return "Proactive system not active."
                
        except Exception as e:
            logger.error(f"Error accepting proactive: {e}")
            return "Got it!"
    
    def decline_proactive_suggestion(self) -> str:
        """
        User declined a proactive suggestion.
        
        Returns:
            str: Acknowledgment message
        """
        try:
            from core.companion import get_proactive_engine, get_idle_monitor
            
            engine = get_proactive_engine()
            idle_monitor = get_idle_monitor()
            
            if engine:
                suggestion = engine.get_pending_suggestion()
                if suggestion:
                    engine.record_response(accepted=False)
                    
                    # Record in idle monitor too
                    if idle_monitor:
                        idle_monitor.record_proactive_response(accepted=False)
                    
                    logger.info("Proactive suggestion declined: %s", suggestion.suggestion_type.value)
                    return "No problem, I'll be here if you need me."
                else:
                    return "Okay."
            else:
                return "Okay."
                
        except Exception as e:
            logger.error(f"Error declining proactive: {e}")
            return "Okay."

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 16: SYSTEM POWER CONTROL, POWER PLANS, BLUETOOTH
    # → MOVED TO: core/system_control.py (December 2024)
    # Functions: lock_screen, system_sleep, hibernate, restart, shutdown,
    #            schedule_shutdown, cancel_shutdown, get_power_plan, list_power_plans,
    #            set_power_plan, get_bluetooth_status, list_bluetooth_devices,
    #            open_bluetooth_settings
    # ═══════════════════════════════════════════════════════════════════════════

