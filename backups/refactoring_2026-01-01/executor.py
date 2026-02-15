""" 
Command Executor - System-Level Task Execution
Handles system commands, app launching, and OS interactions securely.
"""

import logging
import subprocess
import platform
import os
import webbrowser
from datetime import datetime
from typing import Optional, Tuple, List, Dict
import ctypes
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from PySide6.QtCore import QObject, Signal
from .screen_reader import ScreenReader
from .mouse_controller import MouseController
from .window_manager import WindowManager
from .app_name_mapper import AppNameMapper
from .battery_manager import BatteryManager
from .notification_reader import NotificationReader
from .app_discovery import AppDiscovery
from .screenshot_manager import ScreenshotManager
from .game_manager import GameManager
from .music_manager import MusicManager
from .weather_service import WeatherService
from .natural_responses import NaturalResponses
from .function_registry import FunctionRegistry
from .sharing_service import SharingService

logger = logging.getLogger(__name__)


class CommandExecutor(QObject):
    """
    Executes system-level commands and tasks securely.
    Provides controlled access to OS functions.
    Inherits from QObject to support signals for thread-safe GUI operations.
    """
    
    # Signal to request content window closure (thread-safe)
    close_content_window_requested = Signal()
    
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
        
        # Content Mode tracking
        self._content_mode_exiting = False  # Flag to track exit in progress
        
        # Cache for installed applications (populated on demand)
        self._installed_apps_cache = None
        
        # Cache for volume interface to prevent COM resource leaks
        self._volume_interface = None
        
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
        self.function_registry = FunctionRegistry(self)
        
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
                from .llm_manager import LLMMode
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
        logger.info(f"Opening application: {app_name}")
        
        try:
            if self.os_name == "Windows":
                app_lower = app_name.lower().strip()
                
                # Step 1: Try built-in Windows commands first (always work)
                builtin_apps = {
                    'notepad': 'notepad.exe',
                    'calculator': 'calc.exe',
                    'calc': 'calc.exe',
                    'paint': 'mspaint.exe',
                    'wordpad': 'write.exe',
                    'explorer': 'explorer.exe',
                    'file explorer': 'explorer.exe',
                    'task manager': 'taskmgr.exe',
                    'taskmgr': 'taskmgr.exe',
                    'cmd': 'cmd.exe',
                    'command prompt': 'cmd.exe',
                    'powershell': 'powershell.exe',
                    'control panel': 'control.exe',
                    'control': 'control.exe',
                    'settings': 'ms-settings:',
                }
                
                if app_lower in builtin_apps:
                    executable = builtin_apps[app_lower]
                    try:
                        # Launch and verify
                        process = subprocess.Popen(
                            executable, 
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        # Give it a moment to fail if it will (0.1s)
                        import time
                        time.sleep(0.1)
                        
                        # Check if process failed immediately
                        if process.poll() is not None and process.returncode != 0:
                            logger.error(f"Builtin app {app_name} failed with code {process.returncode}")
                            return NaturalResponses.error()
                        
                        logger.info(f"✅ Launched builtin app: {executable}")
                        return NaturalResponses.app_opened(app_name)
                    except Exception as launch_error:
                        logger.error(f"Failed to launch {app_name}: {launch_error}")
                        return NaturalResponses.error()
                
                # Step 2: Use dynamic app discovery (NEW!)
                logger.info(f"Using dynamic discovery to find: {app_name}")
                success = self.app_discovery.launch_app(app_name)
                
                if success:
                    return NaturalResponses.app_opened(app_name)
                else:
                    # App not found - try fallback methods
                    logger.warning(f"App discovery failed for: {app_name}")
                    
                    # Step 3: Try as direct executable name (fallback)
                    common_names = [
                        f'{app_lower}.exe',
                        f'{app_lower.replace(" ", "")}.exe',
                        f'{app_lower.replace(" ", "-")}.exe',
                    ]
                    
                    for exe_name in common_names:
                        try:
                            # Launch and verify
                            process = subprocess.Popen(
                                exe_name, 
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                            # Give it a moment to fail if it will
                            import time
                            time.sleep(0.1)
                            
                            # Check if process failed immediately
                            if process.poll() is not None and process.returncode != 0:
                                logger.debug(f"Fallback {exe_name} failed with code {process.returncode}")
                                continue
                            
                            logger.info(f"✅ Launched via fallback: {exe_name}")
                            return NaturalResponses.app_opened(app_name)
                        except Exception as fallback_error:
                            logger.debug(f"Fallback failed for {exe_name}: {fallback_error}")
                            continue
                    
                    # Nothing worked - app not found
                    logger.error(f"❌ Cannot find app: {app_name}")
                    return NaturalResponses.app_not_found(app_name)
            
            else:  # Linux/Mac
                subprocess.Popen([app_name])
                return NaturalResponses.app_opened(app_name)
        
        except Exception as e:
            logger.error(f"Error opening application: {e}")
            return NaturalResponses.error()
    
    def _find_installed_app(self, app_name: str) -> Optional[str]:
        """
        DEPRECATED: Replaced by AppDiscovery class.
        This method is kept for backward compatibility but is no longer used.
        
        Use self.app_discovery.find_app() instead.
        
        Args:
            app_name: Application name to search for
            
        Returns:
            Full path to executable if found, None otherwise
        """
        try:
            import winreg
            
            app_lower = app_name.lower().strip()
            
            # Common name mappings for better matching
            name_variants = [
                app_lower,
                app_lower.replace(" ", ""),
                app_lower.replace(" ", "-"),
                app_lower.replace("-", ""),
            ]
            
            # Add specific known mappings (enhanced for third-party apps)
            mappings = {
                'chrome': ['chrome', 'google chrome', 'googlechrome'],
                'google chrome': ['chrome', 'google chrome'],
                'firefox': ['firefox', 'mozilla firefox'],
                'edge': ['edge', 'msedge', 'microsoft edge'],
                'microsoft edge': ['edge', 'msedge'],
                'word': ['winword', 'word', 'microsoft word'],
                'excel': ['excel', 'microsoft excel'],
                'powerpoint': ['powerpnt', 'powerpoint'],
                'outlook': ['outlook', 'microsoft outlook'],
                'teams': ['teams', 'microsoft teams', 'msteams'],
                'vscode': ['code', 'vscode', 'visual studio code'],
                'vs code': ['code', 'vscode'],
                'visual studio code': ['code', 'vscode'],
                'spotify': ['spotify'],
                'discord': ['discord'],
                'notepad++': ['notepad++', 'notepadplusplus'],
                'chatgpt': ['chatgpt', 'chat gpt', 'openai'],
                'chat gpt': ['chatgpt', 'chat gpt'],
                'steam': ['steam'],
                'obs': ['obs', 'obs studio', 'obsstudio'],
                'obs studio': ['obs', 'obs studio'],
                'slack': ['slack'],
                'zoom': ['zoom'],
            }
            
            if app_lower in mappings:
                name_variants.extend(mappings[app_lower])
            
            # Search in Windows Registry (Uninstall keys) - Enhanced with HKCU
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            
            for hkey, registry_path in registry_paths:
                try:
                    key = winreg.OpenKey(hkey, registry_path)
                    
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey = winreg.OpenKey(key, subkey_name)
                            
                            try:
                                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                display_name_lower = display_name.lower()
                                
                                # Check if any variant matches
                                for variant in name_variants:
                                    if variant in display_name_lower:
                                        try:
                                            # Try to get InstallLocation first
                                            try:
                                                install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                                if install_location and os.path.exists(install_location):
                                                    # Search for main exe in install location
                                                    for file in os.listdir(install_location):
                                                        if file.lower().endswith('.exe'):
                                                            # Prefer the exe that matches the app name
                                                            file_lower = file.lower().replace('.exe', '')
                                                            if any(v in file_lower for v in name_variants):
                                                                full_path = os.path.join(install_location, file)
                                                                logger.info(f"Found {app_name} via registry InstallLocation: {full_path}")
                                                                return full_path
                                                    
                                                    # If no matching exe, return first exe that's not uninstall
                                                    for file in os.listdir(install_location):
                                                        if file.lower().endswith('.exe') and 'uninstall' not in file.lower():
                                                            full_path = os.path.join(install_location, file)
                                                            logger.info(f"Found {app_name} via registry (first exe): {full_path}")
                                                            return full_path
                                            except:
                                                pass
                                            
                                            # Try DisplayIcon (but filter out uninstall.exe)
                                            try:
                                                icon_path = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                                                if icon_path and icon_path.lower().endswith('.exe'):
                                                    icon_path = icon_path.split(',')[0].strip('"')
                                                    
                                                    # Skip uninstall.exe, try to find the real exe
                                                    if 'uninstall' in icon_path.lower():
                                                        install_dir = os.path.dirname(icon_path)
                                                        if os.path.exists(install_dir):
                                                            # Look for main exe in same directory
                                                            for file in os.listdir(install_dir):
                                                                if file.lower().endswith('.exe'):
                                                                    file_lower = file.lower().replace('.exe', '')
                                                                    if any(v in file_lower for v in name_variants) and 'uninstall' not in file_lower:
                                                                        real_path = os.path.join(install_dir, file)
                                                                        logger.info(f"Found {app_name} via registry (real exe): {real_path}")
                                                                        return real_path
                                                    else:
                                                        if os.path.exists(icon_path):
                                                            logger.info(f"Found {app_name} via registry DisplayIcon: {icon_path}")
                                                            return icon_path
                                            except:
                                                pass
                                        except:
                                            pass
                            except:
                                pass
                            
                            winreg.CloseKey(subkey)
                        except:
                            continue
                    
                    winreg.CloseKey(key)
                except:
                    continue
            
            # Search common installation directories (Enhanced with WindowsApps)
            common_paths = [
                os.path.expandvars(r"%ProgramFiles%"),
                os.path.expandvars(r"%ProgramFiles(x86)%"),
                os.path.expandvars(r"%LocalAppData%\Programs"),
                os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps"),  # Microsoft Store apps
                os.path.expandvars(r"%AppData%"),
            ]
            
            for base_path in common_paths:
                if not os.path.exists(base_path):
                    continue
                
                try:
                    for root, dirs, files in os.walk(base_path):
                        # Limit depth to avoid scanning entire drive
                        depth = root[len(base_path):].count(os.sep)
                        if depth > 2:
                            continue
                        
                        for file in files:
                            if file.lower().endswith('.exe'):
                                file_lower = file.lower().replace('.exe', '')
                                for variant in name_variants:
                                    if variant in file_lower or file_lower in variant:
                                        exe_path = os.path.join(root, file)
                                        # Skip uninstall executables
                                        if 'uninstall' not in exe_path.lower():
                                            logger.info(f"Found {app_name} via filesystem search: {exe_path}")
                                            return exe_path
                except:
                    continue
            
            # Try Start Menu shortcuts as last resort
            start_menu_paths = [
                os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
                os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
            ]
            
            for start_menu in start_menu_paths:
                if not os.path.exists(start_menu):
                    continue
                
                try:
                    for root, dirs, files in os.walk(start_menu):
                        for file in files:
                            if file.lower().endswith('.lnk'):
                                file_lower = file.lower().replace('.lnk', '')
                                for variant in name_variants:
                                    if variant in file_lower:
                                        lnk_path = os.path.join(root, file)
                                        # Try to resolve shortcut to actual exe
                                        try:
                                            import win32com.client
                                            shell = win32com.client.Dispatch("WScript.Shell")
                                            shortcut = shell.CreateShortCut(lnk_path)
                                            target_path = shortcut.Targetpath
                                            if target_path and os.path.exists(target_path) and target_path.lower().endswith('.exe'):
                                                logger.info(f"Found {app_name} via Start Menu shortcut: {target_path}")
                                                return target_path
                                        except:
                                            pass
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding installed app: {e}")
            return None
    
    def get_current_time(self) -> str:
        """
        Get current time in natural language.
        
        Returns:
            Time string (time only, no date - natural formatting without zeros)
        """
        now = datetime.now()
        # Natural time formatting: "3:45 PM" not "03:45 PM"
        hour = now.hour % 12
        if hour == 0:
            hour = 12
        minute = now.minute
        period = "AM" if now.hour < 12 else "PM"
        
        return f"It's {hour}:{minute:02d} {period}."
    
    def get_current_date(self) -> str:
        """
        Get current date in natural language.
        
        Returns:
            Date string (date only, no time - natural formatting without zeros)
        """
        now = datetime.now()
        # Natural date formatting: "November 9" not "November 09"
        return f"Today is {now.strftime('%A, %B')} {now.day}, {now.year}."
    
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
                from core.app_name_mapper import AppNameMapper
                
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
        """
        Check if a specific application is currently running.
        Now supports friendly names like "Microsoft Edge" → "msedge".
        
        Args:
            app_name: Application name to check (friendly or process name)
            
        Returns:
            True if running, False otherwise
        """
        try:
            if self.os_name == "Windows":
                import psutil
                
                # Get all variants of the app name
                variants = self.app_mapper.get_all_variants(app_name)
                
                for proc in psutil.process_iter(['name']):
                    try:
                        proc_name = proc.info.get('name', '')
                        if not proc_name:
                            continue
                        
                        proc_name_lower = proc_name.lower().replace('.exe', '')
                        
                        # Check against all variants
                        for variant in variants:
                            variant_lower = variant.lower().replace('.exe', '')
                            if variant_lower and proc_name_lower and (variant_lower == proc_name_lower or 
                                                                       variant_lower in proc_name_lower or 
                                                                       proc_name_lower in variant_lower):
                                logger.info(f"Found running: {proc_name} (searched for: {app_name})")
                                return True
                    except:
                        continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if app running: {e}")
            return False
    
    def close_application(self, app_name: str) -> str:
        """
        Close a running application by name (ENHANCED with active window fallback).
        Now supports friendly names like "Microsoft Edge" → "msedge".
        FIX W-14: If app not found by name, closes active window (for user-opened apps).
        
        Args:
            app_name: Application name to close (friendly or process name)
            
        Returns:
            Result message
        """
        try:
            if self.os_name == "Windows":
                import psutil
                
                # Get all variants of the app name
                variants = self.app_mapper.get_all_variants(app_name)
                closed_count = 0
                closed_processes = []
                
                for proc in psutil.process_iter(['name', 'pid']):
                    try:
                        proc_name = proc.info['name'].lower().replace('.exe', '')
                        
                        # Check against all variants
                        for variant in variants:
                            variant_lower = variant.lower().replace('.exe', '')
                            if variant_lower in proc_name or proc_name in variant_lower:
                                proc.terminate()
                                closed_processes.append(proc_name)
                                closed_count += 1
                                break  # Don't double-count
                    except:
                        continue
                
                if closed_count > 0:
                    logger.info(f"Closed {closed_count} instance(s): {', '.join(set(closed_processes))}")
                    return NaturalResponses.app_closed(app_name)
                else:
                    # FIX W-14: App not found by name - try active window fallback
                    # This handles cases like "close this" or "close chrome" when user opened it manually
                    logger.info(f"⚠️ {app_name} not found in processes, trying active window fallback...")
                    
                    # Check if active window matches the app name
                    window_info = self.window_manager.get_active_window_info()
                    if window_info:
                        _, title, process_name = window_info
                        process_lower = process_name.lower().replace('.exe', '')
                        
                        # Check if active window's process matches the app we're trying to close
                        for variant in variants:
                            variant_lower = variant.lower().replace('.exe', '')
                            if variant_lower in process_lower or process_lower in variant_lower or variant_lower in title.lower():
                                # Active window matches! Close it
                                result = self.window_manager.close_active_window()
                                logger.info(f"✅ Closed active window via fallback: {title}")
                                return result
                    
                    # Active window doesn't match, return not running
                    logger.warning(f"{app_name} is not running (tried: {', '.join(variants)})")
                    return NaturalResponses.app_not_running(app_name)
            
            return "Application closing only available on Windows"
            
        except Exception as e:
            logger.error(f"Error closing application: {e}")
            return f"Failed to close {app_name}: {str(e)}"
    
    def get_system_info(self) -> str:
        """
        Get basic system information.
        
        Returns:
            System info string
        """
        info = {
            'OS': platform.system(),
            'Version': platform.version(),
            'Machine': platform.machine(),
            'Processor': platform.processor()
        }
        
        info_str = "\n".join([f"{key}: {value}" for key, value in info.items()])
        return f"System Information:\n{info_str}"
    
    # ============================================================
    # VOLUME CONTROL (Native Windows - No nircmd needed!)
    # ============================================================
    
    def _get_volume_interface(self):
        """Get Windows audio interface using COM. Internal method. Cached to prevent resource leaks."""
        if self._volume_interface is not None:
            return self._volume_interface
            
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            self._volume_interface = volume  # Cache for reuse
            return volume
        except Exception as e:
            logger.error(f"Failed to get volume interface: {e}")
            return None
    
    def _get_volume_value(self) -> int:
        """
        Get current volume level as integer (0-100).
        Used internally for calculations.
        
        Returns:
            Volume level as integer (0-100), or -1 on error
        """
        try:
            volume = self._get_volume_interface()
            if volume:
                current_vol = volume.GetMasterVolumeLevelScalar()
                return int(current_vol * 100)
            return -1
        except Exception as e:
            logger.error(f"Error getting volume value: {e}")
            return -1
    
    def get_current_volume(self) -> str:
        """
        Get current system volume level and mute status.
        
        Returns:
            Human-readable string with volume level and mute status
        """
        try:
            volume = self._get_volume_interface()
            if volume:
                current_vol = volume.GetMasterVolumeLevelScalar()
                is_muted = volume.GetMute()
                volume_level = int(current_vol * 100)
                
                if is_muted:
                    return f"Volume is currently muted (set to {volume_level}%)"
                else:
                    return f"Volume is at {volume_level}%"
            return "Unable to get volume level"
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            return "Error getting volume level"
    
    def set_volume(self, level: int) -> str:
        """
        Set system volume to specific level.
        
        Args:
            level: Volume level (0-100)
            
        Returns:
            Result message
        """
        try:
            level = max(0, min(100, level))  # Clamp between 0-100
            volume = self._get_volume_interface()
            
            if volume:
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                logger.info(f"Volume set to {level}%")
                return NaturalResponses.volume_set(level)
            else:
                return "I couldn't access the volume controls"
                
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return "Sorry, I had trouble adjusting the volume"
    
    def increase_volume(self, amount: int = 10) -> str:
        """
        Increase volume by amount.
        
        Args:
            amount: Percentage to increase (default 10)
            
        Returns:
            Result message
        """
        current_vol = self._get_volume_value()
        if current_vol == -1:
            return "I couldn't get the current volume level"
        
        new_vol = min(100, current_vol + amount)
        if new_vol == current_vol:
            return "Volume is already at maximum"
        
        self.set_volume(new_vol)
        return NaturalResponses.volume_up()
    
    def decrease_volume(self, amount: int = 10) -> str:
        """
        Decrease volume by amount.
        
        Args:
            amount: Percentage to decrease (default 10)
            
        Returns:
            Result message
        """
        current_vol = self._get_volume_value()
        if current_vol == -1:
            return "I couldn't get the current volume level"
        
        new_vol = max(0, current_vol - amount)
        if new_vol == current_vol:
            return "Volume is already at minimum"
            
        self.set_volume(new_vol)
        return NaturalResponses.volume_down()
    
    def mute_volume(self) -> str:
        """
        Mute system volume.
        
        Returns:
            Result message
        """
        try:
            volume = self._get_volume_interface()
            if volume:
                volume.SetMute(1, None)
                logger.info("Volume muted")
                return NaturalResponses.volume_mute()
            return "I couldn't access the volume controls"
        except Exception as e:
            logger.error(f"Error muting volume: {e}")
            return NaturalResponses.error()
    
    def unmute_volume(self) -> str:
        """
        Unmute system volume.
        
        Returns:
            Result message
        """
        try:
            volume = self._get_volume_interface()
            if volume:
                volume.SetMute(0, None)
                logger.info("Volume unmuted")
                return NaturalResponses.volume_unmute()
            return "I couldn't access the volume controls"
        except Exception as e:
            logger.error(f"Error unmuting volume: {e}")
            return NaturalResponses.error()
    
    def toggle_mute(self) -> str:
        """
        Toggle mute status.
        
        Returns:
            Result message
        """
        _, is_muted = self.get_current_volume()
        if is_muted:
            return self.unmute_volume()
        else:
            return self.mute_volume()
    
    # ============================================================
    # BRIGHTNESS CONTROL (Native Windows)
    # ============================================================
    
    def get_current_brightness(self) -> str:
        """
        Get current screen brightness level.
        
        Returns:
            Human-readable string with brightness level
        """
        try:
            brightness_value = self._get_brightness_value()
            if brightness_value >= 0:
                return f"Screen brightness is at {brightness_value}%"
            return "Unable to get brightness level"
        except Exception as e:
            logger.error(f"Error getting brightness: {e}")
            return "Error getting brightness level"
    
    def _get_brightness_value(self) -> int:
        """
        Get current brightness as numeric value.
        
        Returns:
            Brightness value (0-100) or -1 on error
        """
        try:
            if self.os_name == "Windows":
                result = subprocess.run(
                    'powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness',
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    return int(result.stdout.strip())
            return -1
        except Exception as e:
            logger.error(f"Error getting brightness value: {e}")
            return -1
    
    def set_brightness(self, level: int) -> str:
        """
        Set screen brightness to specific level.
        
        Args:
            level: Brightness level (0-100)
            
        Returns:
            Result message
        """
        try:
            level = max(0, min(100, level))  # Clamp between 0-100
            
            if self.os_name == "Windows":
                command = f'powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})'
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0:
                    logger.info(f"Brightness set to {level}%")
                    return NaturalResponses.brightness_set(level)
                else:
                    return "Could not change brightness. Your display might not support this feature."
            
            return "Brightness control only available on Windows"
            
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
            return NaturalResponses.error()
    
    def increase_brightness(self, amount: int = 10) -> str:
        """
        Increase brightness by amount.
        
        Args:
            amount: Percentage to increase (default 10)
            
        Returns:
            Result message
        """
        current = self._get_brightness_value()
        if current == -1:
            return "I couldn't get the current brightness level"
        
        new_level = min(100, current + amount)
        if new_level == current:
            return "Brightness is already at maximum"
            
        self.set_brightness(new_level)
        return NaturalResponses.brightness_up()
    
    def decrease_brightness(self, amount: int = 10) -> str:
        """
        Decrease brightness by amount.
        
        Args:
            amount: Percentage to decrease (default 10)
            
        Returns:
            Result message
        """
        current = self._get_brightness_value()
        if current == -1:
            return "I couldn't get the current brightness level"
        
        new_level = max(0, current - amount)
        if new_level == current:
            return "Brightness is already at minimum"
            
        self.set_brightness(new_level)
        return NaturalResponses.brightness_down()
    
    # ============================================================
    # WIFI MANAGEMENT (Native Windows netsh)
    # ============================================================
    
    def get_wifi_status(self) -> str:
        """
        Get current WiFi connection status.
        
        Returns:
            WiFi status message
        """
        try:
            if self.os_name == "Windows":
                result = subprocess.run(
                    'netsh wlan show interfaces',
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    
                    # Parse connection status
                    if "State" in output:
                        for line in output.split('\n'):
                            if 'State' in line:
                                state = line.split(':')[1].strip()
                                if state == "connected":
                                    # Get network name
                                    for l in output.split('\n'):
                                        if 'SSID' in l and 'BSSID' not in l:
                                            ssid = l.split(':')[1].strip()
                                            return f"Connected to {ssid}"
                                else:
                                    return f"WiFi is {state}"
                    return "WiFi adapter not found or disabled"
                else:
                    return "Could not get WiFi status"
            
            return "WiFi management only available on Windows"
            
        except Exception as e:
            logger.error(f"Error getting WiFi status: {e}")
            return f"Failed to get WiFi status: {str(e)}"
    
    def disconnect_wifi(self) -> str:
        """
        Disconnect from current WiFi network.
        
        Returns:
            Result message
        """
        try:
            if self.os_name == "Windows":
                result = subprocess.run(
                    'netsh wlan disconnect',
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0:
                    logger.info("Disconnected from WiFi")
                    return NaturalResponses.wifi_disconnected()
                else:
                    return "Could not disconnect WiFi. Make sure WiFi is enabled."
            
            return "WiFi management only available on Windows"
            
        except Exception as e:
            logger.error(f"Error disconnecting WiFi: {e}")
            return NaturalResponses.error()
    
    def connect_wifi(self, network_name: str) -> str:
        """
        Connect to a WiFi network.
        
        Args:
            network_name: Name of the WiFi network (SSID)
            
        Returns:
            Result message
        """
        try:
            if self.os_name == "Windows":
                command = f'netsh wlan connect name="{network_name}"'
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
                
                if result.returncode == 0 or "successfully" in result.stdout.lower():
                    logger.info(f"Connected to {network_name}")
                    return NaturalResponses.wifi_connected(network_name)
                else:
                    return f"Could not connect to {network_name}. Make sure the network is in range and saved."
            
            return "WiFi management only available on Windows"
            
        except Exception as e:
            logger.error(f"Error connecting to WiFi: {e}")
            return NaturalResponses.error()
    
    def list_wifi_networks(self) -> str:
        """
        List available WiFi networks.
        
        Returns:
            List of networks or error message
        """
        try:
            if self.os_name == "Windows":
                result = subprocess.run(
                    'netsh wlan show networks',
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    networks = []
                    
                    for line in output.split('\n'):
                        # Match format: "SSID 1 : NetworkName" or "SSID 12 : NetworkName"
                        if line.strip().startswith('SSID') and ':' in line:
                            # Extract everything after the colon
                            ssid = line.split(':', 1)[1].strip()
                            if ssid and ssid != "":
                                networks.append(ssid)
                    
                    if networks:
                        # Remove duplicates and sort
                        networks = sorted(list(set(networks)))
                        network_list = ", ".join(networks)
                        return f"Available networks: {network_list}"
                    else:
                        return "No WiFi networks found"
                else:
                    return "Could not scan for networks"
            
            return "WiFi management only available on Windows"
            
        except Exception as e:
            logger.error(f"Error listing WiFi networks: {e}")
            return f"Failed to list networks: {str(e)}"
    
    def get_saved_wifi_profiles(self) -> str:
        """
        Get list of saved WiFi network profiles.
        
        Returns:
            Saved network profiles or error message
        """
        try:
            if self.os_name == "Windows":
                result = subprocess.run(
                    'netsh wlan show profiles',
                    capture_output=True,
                    text=True,
                    encoding='utf-8',  # Fix Unicode error
                    errors='ignore',   # Ignore problematic characters
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    
                    # Handle case where output is None
                    if not output:
                        return "No WiFi profiles found"
                    
                    profiles = []
                    
                    for line in output.split('\n'):
                        if 'All User Profile' in line or 'User Profile' in line:
                            # Extract profile name after colon
                            if ':' in line:
                                profile_name = line.split(':')[1].strip()
                                if profile_name:
                                    profiles.append(profile_name)
                    
                    if profiles:
                        # Return the first (most recently used) profile
                        return f"Last used network: {profiles[0]}"
                    else:
                        return "No saved WiFi profiles found"
                else:
                    return "Could not get WiFi profiles"
            
            return "WiFi management only available on Windows"
            
        except Exception as e:
            logger.error(f"Error getting WiFi profiles: {e}")
            return f"Failed to get profiles: {str(e)}"
    
    # ========================== SMART TEXT SELECTION (Phase 3.5) ==========================
    
    def find_and_select_text(self, query: str) -> str:
        """
        Find text on screen using Gemini Vision and select it.
        
        Args:
            query: Natural language query (e.g., "find the email", "locate word hello")
            
        Returns:
            Success message or error
        """
        try:
            logger.info(f"🔍 Finding and selecting: {query}")
            
            # Find text using Gemini Vision
            result = self.screen_reader.find_text_on_screen(query, active_window_only=True)
            
            if not result:
                return f"Could not find '{query}' on screen"
            
            # Select the text
            success = self.mouse.select_text_region(
                result['x'], 
                result['y'], 
                result['width'], 
                result['height']
            )
            
            if success:
                return f"Selected '{result['text']}'"
            else:
                return f"Found '{result['text']}' but failed to select it"
                
        except Exception as e:
            logger.error(f"Error in find_and_select_text: {e}")
            return f"Failed to find and select text: {str(e)}"
    
    def find_and_copy_text(self, query: str) -> str:
        """
        Find text on screen and copy it to clipboard.
        
        Args:
            query: Natural language query
            
        Returns:
            Success message with copied text
        """
        try:
            logger.info(f"🔍 Finding and copying: {query}")
            
            # Find text
            result = self.screen_reader.find_text_on_screen(query, active_window_only=True)
            
            if not result:
                return f"Could not find '{query}' on screen"
            
            # Select the text
            if self.mouse.select_text_region(result['x'], result['y'], result['width'], result['height']):
                # Copy it
                import time
                time.sleep(0.2)  # Wait for selection
                self.mouse.copy_selection()
                return f"Copied '{result['text']}' to clipboard"
            else:
                return f"Found '{result['text']}' but failed to copy it"
                
        except Exception as e:
            logger.error(f"Error in find_and_copy_text: {e}")
            return f"Failed to find and copy text: {str(e)}"
    
    def find_and_delete_text(self, query: str) -> str:
        """
        Find text on screen and delete it.
        
        Args:
            query: Natural language query
            
        Returns:
            Success message
        """
        try:
            logger.info(f"🔍 Finding and deleting: {query}")
            
            # Find text
            result = self.screen_reader.find_text_on_screen(query, active_window_only=True)
            
            if not result:
                return f"Could not find '{query}' on screen"
            
            # Select the text
            if self.mouse.select_text_region(result['x'], result['y'], result['width'], result['height']):
                # Delete it
                import time
                time.sleep(0.2)  # Wait for selection
                self.mouse.delete_selection()
                return f"Deleted '{result['text']}'"
            else:
                return f"Found '{result['text']}' but failed to delete it"
                
        except Exception as e:
            logger.error(f"Error in find_and_delete_text: {e}")
            return f"Failed to find and delete text: {str(e)}"
    
    def read_screen_content(self) -> str:
        """
        Read all text visible on screen using Gemini Vision.
        
        Returns:
            All visible text or error message
        """
        try:
            logger.info("📄 Reading screen content")
            content = self.screen_reader.read_screen_content(active_window_only=True)
            
            if content:
                # Truncate for voice response
                if len(content) > 200:
                    return f"Screen content: {content[:200]}... and more"
                else:
                    return f"Screen content: {content}"
            else:
                return "Could not read screen content"
                
        except Exception as e:
            logger.error(f"Error reading screen: {e}")
            return f"Failed to read screen: {str(e)}"
    
    def describe_screen(self) -> str:
        """
        Get AI description of what's on screen.
        
        Returns:
            Natural language description
        """
        try:
            logger.info("🖼️ Describing screen")
            description = self.screen_reader.describe_screen(active_window_only=True)
            
            if description:
                return description
            else:
                return "Could not describe screen"
                
        except Exception as e:
            logger.error(f"Error describing screen: {e}")
            return f"Failed to describe screen: {str(e)}"
    
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
        """
        Get comprehensive battery status.
        
        Returns:
            Battery status message
        """
        logger.info("Getting battery status")
        return self.battery_manager.get_simple_status()
    
    def get_battery_percentage(self) -> str:
        """
        Get battery percentage only.
        
        Returns:
            Battery percentage message
        """
        percent = self.battery_manager.get_battery_percentage()
        return f"Battery is at {percent}%"
    
    def is_battery_charging(self) -> str:
        """
        Check if battery is charging.
        
        Returns:
            Charging status message
        """
        is_charging = self.battery_manager.is_charging()
        if is_charging:
            return "Battery is currently charging"
        else:
            return "Battery is not charging (running on battery)"
    
    def get_battery_time_remaining(self) -> str:
        """
        Get battery time remaining.
        
        Returns:
            Time remaining message
        """
        status = self.battery_manager.get_battery_status()
        time_left = status.get('time_left_text')
        percent = status.get('percent', 0)
        is_charging = status.get('charging', False)
        
        if time_left:
            if is_charging:
                return f"{time_left} until fully charged"
            else:
                return f"{time_left} of battery remaining"
        else:
            # Windows doesn't provide time estimate - give percentage-based info
            if is_charging:
                if percent >= 95:
                    return "Almost fully charged"
                elif percent >= 80:
                    return "Charging, about 15 to 30 minutes until full"
                else:
                    remaining_percent = 100 - percent
                    # Rough estimate: ~1% per minute charging
                    estimated_minutes = remaining_percent
                    if estimated_minutes < 60:
                        return f"Charging, approximately {estimated_minutes} minutes until full"
                    else:
                        estimated_hours = estimated_minutes // 60
                        return f"Charging, approximately {estimated_hours} hour{'s' if estimated_hours != 1 else ''} until full"
            else:
                # On battery - estimate based on percentage
                if percent >= 80:
                    return "Battery high, several hours remaining"
                elif percent >= 50:
                    return "Battery medium, a few hours remaining"
                elif percent >= 20:
                    return "Battery moderate, about an hour or two remaining"
                else:
                    return f"Battery low at {percent}%, please charge soon"
    
    def get_gpu_usage(self) -> str:
        """
        Get current GPU usage and memory statistics.
        
        Returns:
            GPU usage message with VRAM info
        """
        logger.info("Getting GPU usage")
        
        if not hasattr(self, 'gpu_monitor') or self.gpu_monitor is None:
            return "GPU monitoring is not available on this system"
        
        usage = self.gpu_monitor.get_current_usage()
        
        if usage is None:
            return "Unable to retrieve GPU usage. Make sure you have an NVIDIA GPU and drivers installed"
        
        used_mb, total_mb, usage_percent = usage
        used_gb = used_mb / 1024
        total_gb = total_mb / 1024
        
        # Create natural response
        if usage_percent < 20:
            status = "very low"
        elif usage_percent < 40:
            status = "low"
        elif usage_percent < 60:
            status = "moderate"
        elif usage_percent < 80:
            status = "high"
        else:
            status = "very high"
        
        return (f"GPU memory usage is {status} at {usage_percent:.1f}%. "
                f"Using {used_gb:.1f} GB out of {total_gb:.1f} GB total VRAM")
    
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
        """
        Take a screenshot of the entire screen.
        
        Args:
            copy_to_clipboard: If True, also copy to clipboard
            
        Returns:
            str: Result message with file path
        """
        try:
            logger.info("Taking screenshot...")
            success, message, file_path = self.screenshot_manager.take_screenshot(
                save_to_clipboard=copy_to_clipboard
            )
            
            if success:
                # Track screenshot for smart sharing
                if file_path:
                    self.last_screenshot = Path(file_path)
                    self.last_used_file = Path(file_path)
                    logger.debug(f"📌 Tracked last screenshot: {Path(file_path).name}")
                
                logger.info(f"✅ Screenshot captured: {file_path}")
                return message
            else:
                return message
                
        except Exception as e:
            error_msg = f"Error taking screenshot: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def open_screenshots_folder(self) -> str:
        """
        Open the screenshots folder in File Explorer.
        
        Returns:
            str: Result message
        """
        try:
            success = self.screenshot_manager.open_screenshots_folder()
            if success:
                return "Opening screenshots folder"
            else:
                return "Failed to open screenshots folder"
        except Exception as e:
            error_msg = f"Error opening screenshots folder: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
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
    # CONTENT MODE - Text Refinement & PDF Generation
    # ======================================================================
    
    def enter_content_mode(self) -> str:
        """
        Enter Content Mode - Opens Content Box window for text editing and PDF generation.
        
        Returns:
            str: Status message
        """
        try:
            from core.brain import NexaState
            
            # Check if already in content mode
            if hasattr(self, 'content_window') and self.content_window is not None:
                if self.content_window.isVisible():
                    self.content_window.raise_()
                    self.content_window.activateWindow()
                    return "Content Mode is already active."
            
            # Initialize text refiner and PDF generator if not already done
            if not hasattr(self, 'text_refiner'):
                from core.text_refiner import TextRefiner
                # Get llm_manager from brain (set by brain.py after initialization)
                if hasattr(self, 'brain') and self.brain:
                    self.text_refiner = TextRefiner(self.brain.llm_manager)
                else:
                    return "Cannot enter Content Mode: LLM Manager not available"
            
            if not hasattr(self, 'pdf_generator'):
                from core.pdf_generator import PDFGenerator
                self.pdf_generator = PDFGenerator()
            
            # Reset exit flag when entering Content Mode
            self._content_mode_exiting = False
            
            # Request window creation from main UI thread via signal
            if self.window and hasattr(self.window, 'content_mode_requested'):
                # Emit signal to create window in main thread
                self.window.content_mode_requested.emit(self)
                logger.info("📝 Content window creation requested via signal")
            else:
                logger.warning("⚠️ Cannot create content window: UI window not available or signal not connected")
                return "Cannot open Content Mode window: UI not properly initialized"
            
            # Update brain state if brain is available
            if hasattr(self, 'brain') and self.brain:
                self.brain._change_state(NexaState.CONTENT_MODE)
            
            logger.info("📝 Entered Content Mode")
            return "Content Mode activated. You can now edit text, refine content, and create PDFs."
            
        except ImportError as e:
            error_msg = f"Content Mode components not available: {str(e)}"
            logger.error(error_msg)
            return f"Cannot enter Content Mode: Missing dependencies. {str(e)}"
        except Exception as e:
            error_msg = f"Error entering Content Mode: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def exit_content_mode(self) -> str:
        """
        Exit Content Mode - Closes Content Box window and returns to normal operation.
        Uses Signal/Slot mechanism for thread-safe GUI operations.
        
        Returns:
            str: Status message
        """
        try:
            from core.brain import NexaState
            
            # Set exit flag FIRST (so Content Mode check returns False immediately)
            self._content_mode_exiting = True
            
            # Update brain state back to IDLE
            if hasattr(self, 'brain') and self.brain:
                self.brain._change_state(NexaState.IDLE)
            
            # Close content window if it exists
            if hasattr(self, 'content_window') and self.content_window is not None:
                logger.info(f"🚪 Emitting close_content_window_requested signal (window visible: {self.content_window.isVisible()})")
                
                # Emit signal - will be handled in main thread by connected slot
                self.close_content_window_requested.emit()
                logger.info("✅ Signal emitted, window will close in main thread")
            else:
                self._content_mode_exiting = False
                logger.warning("⚠️ No content window to close")
            
            logger.info("🚪 Content Mode exit initiated")
            return "Content Mode closed. Returning to normal operation."
            
        except Exception as e:
            error_msg = f"Error exiting Content Mode: {str(e)}"
            logger.error(error_msg)
            self._content_mode_exiting = False
            return error_msg
    
    def refine_text(self, mode: str, text: Optional[str] = None) -> str:
        """
        Refine text content using AI.
        
        Args:
            mode: Refinement mode (formal, shorter, grammar_only, improve, summarize, casual)
            text: Optional text to refine (if None, uses content from Content Box window)
            
        Returns:
            str: Refined text or error message
        """
        try:
            # CRITICAL FIX: Get text from Content Box if not provided OR if empty string
            # AI sometimes passes empty string "", we need to treat it same as None
            if not text or not text.strip():
                if hasattr(self, 'content_window') and self.content_window is not None:
                    # Check content status before processing
                    content_status = self.content_window.get_content_status()
                    word_count = self.content_window.get_word_count()
                    
                    if content_status == "empty":
                        return "The content editor is empty. Please paste or type your content first."
                    elif content_status == "not_ready":
                        min_words = self.content_window.MIN_WORDS
                        return f"Content is too short. Please add more text (minimum {min_words} words, you have {word_count})."
                    elif content_status == "exceeds_limit":
                        max_words = self.content_window.MAX_WORDS
                        return f"Content is too long ({word_count} words). Please shorten it to under {max_words} words before refining."
                    
                    text = self.content_window.get_text()
                else:
                    return "No text to refine. Please provide text or use Content Mode."
            
            # Final check after retrieval
            if not text or not text.strip():
                return "Cannot refine empty text."
            
            # Initialize text refiner if needed
            if not hasattr(self, 'text_refiner'):
                from core.text_refiner import TextRefiner
                if hasattr(self, 'brain') and self.brain:
                    self.text_refiner = TextRefiner(self.brain.llm_manager)
                else:
                    return "Text refiner not available"
            
            # Refine the text
            logger.info(f"✨ Refining text with mode: {mode}")
            refined_text, llm_mode = self.text_refiner.refine_text(text, mode)
            
            # Update Content Box window if it exists (skip validation for Nexa's output)
            if hasattr(self, 'content_window') and self.content_window is not None:
                self.content_window.set_text(refined_text, skip_validation=True)
                self.content_window.set_status(f"✓ Text refined using {llm_mode} model", 3000)
            
            logger.info(f"✅ Text refined successfully ({len(refined_text)} chars)")
            return refined_text
            
        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"⚠️ Invalid refinement request: {error_msg}")
            if hasattr(self, 'content_window') and self.content_window is not None:
                self.content_window.set_status(error_msg, 5000, error=True)
            return error_msg
        except Exception as e:
            error_msg = f"Error refining text: {str(e)}"
            logger.error(error_msg)
            if hasattr(self, 'content_window') and self.content_window is not None:
                self.content_window.set_status(error_msg, 5000, error=True)
            return error_msg
    
    def create_pdf(self, pdf_format: str = "simple_text", filename: Optional[str] = None, 
                   text: Optional[str] = None, title: Optional[str] = None) -> str:
        """
        Create a PDF document from text content.
        
        Args:
            pdf_format: PDF format (simple_text, with_bullets, formatted_paragraphs)
            filename: Optional filename (auto-generated if None)
            text: Optional text content (if None, uses content from Content Box window)
            title: Optional document title
            
        Returns:
            str: Success message with file path or error message
        """
        try:
            # CRITICAL FIX: Get text from Content Box if not provided OR if empty string
            # AI sometimes passes empty string "", we need to treat it same as None
            if not text or not text.strip():
                if hasattr(self, 'content_window') and self.content_window is not None:
                    # Check content status before processing
                    content_status = self.content_window.get_content_status()
                    word_count = self.content_window.get_word_count()
                    
                    if content_status == "empty":
                        return "The content editor is empty. Please paste or type your content first."
                    elif content_status == "not_ready":
                        min_words = self.content_window.MIN_WORDS
                        return f"Content is too short to create a PDF. Please add more text (minimum {min_words} words, you have {word_count})."
                    elif content_status == "exceeds_limit":
                        max_words = self.content_window.MAX_WORDS
                        return f"Content is too long ({word_count} words). Please shorten it to under {max_words} words before creating PDF."
                    
                    # Get HTML content to preserve formatting (Phase 14)
                    text = self.content_window.get_html()
                else:
                    return "No text to export. Please provide text or use Content Mode."
            
            # Final check after retrieval
            if not text or not text.strip():
                return "Cannot create PDF from empty text."
            
            # Initialize PDF generator if needed
            if not hasattr(self, 'pdf_generator'):
                from core.pdf_generator import PDFGenerator
                self.pdf_generator = PDFGenerator()
            
            # Prepare metadata for PDF header
            metadata = {
                'name': self.config.user_name if hasattr(self.config, 'user_name') else 'Student',
                'id': getattr(self.config, 'student_id', None),
                'course': getattr(self.config, 'course_name', None),
                'date': None  # Auto-generate current date
            }
            
            # CRITICAL FIX: Convert empty string filename to None (AI sometimes passes "")
            if filename is not None and not filename.strip():
                filename = None
                logger.debug("📝 Empty filename provided, will auto-generate")
            
            # Create the PDF
            logger.info(f"📄 Creating PDF - Format: {pdf_format}, Filename: {filename or 'auto'}")
            pdf_path, success = self.pdf_generator.create_pdf(
                text=text,
                filename=filename,
                pdf_format=pdf_format,
                title=title,
                metadata=metadata
            )
            
            if success:
                # Track this PDF for smart sharing
                self.last_created_pdf = pdf_path
                self.last_used_file = pdf_path
                logger.debug(f"📌 Tracked last created PDF: {pdf_path.name}")
                
                # Update Content Box window status
                if hasattr(self, 'content_window') and self.content_window is not None:
                    self.content_window.set_status(f"✓ PDF created: {pdf_path.name}", 5000)
                
                # Open PDF folder
                import subprocess
                import platform
                if platform.system() == "Windows":
                    subprocess.Popen(f'explorer /select,"{pdf_path}"')
                
                logger.info(f"✅ PDF created successfully: {pdf_path}")
                return f"PDF created successfully: {pdf_path.name}. Saved in {pdf_path.parent}"
            else:
                return "PDF creation failed."
                
        except ImportError as e:
            error_msg = f"PDF generation not available: {str(e)}. Install with: pip install reportlab"
            logger.error(error_msg)
            if hasattr(self, 'content_window') and self.content_window is not None:
                self.content_window.set_status("ReportLab not installed", 5000, error=True)
            return error_msg
        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"⚠️ Invalid PDF request: {error_msg}")
            if hasattr(self, 'content_window') and self.content_window is not None:
                self.content_window.set_status(error_msg, 5000, error=True)
            return error_msg
        except Exception as e:
            error_msg = f"Error creating PDF: {str(e)}"
            logger.error(error_msg)
            if hasattr(self, 'content_window') and self.content_window is not None:
                self.content_window.set_status(error_msg, 5000, error=True)
            return error_msg
    
    def _on_content_window_closed(self):
        """Handle Content Box window close event."""
        logger.info("🚪 Content Box window closed by user")
        self.exit_content_mode()
    
    def _on_refine_requested(self, mode: str, text: str):
        """
        Handle refine request from Content Box window.
        
        Args:
            mode: Refinement mode
            text: Text to refine
        """
        try:
            self.refine_text(mode, text)
        except Exception as e:
            logger.error(f"Error handling refine request: {e}")
            if hasattr(self, 'content_window') and self.content_window is not None:
                self.content_window.set_status(f"Refinement failed: {str(e)}", 5000, error=True)
    
    def _on_pdf_requested(self, pdf_format: str, filename: str, text: str):
        """
        Handle PDF creation request from Content Box window.
        
        Args:
            pdf_format: PDF format
            filename: Filename
            text: Text content
        """
        try:
            self.create_pdf(pdf_format, filename, text)
        except Exception as e:
            logger.error(f"Error handling PDF request: {e}")
            if hasattr(self, 'content_window') and self.content_window is not None:
                self.content_window.set_status(f"PDF creation failed: {str(e)}", 5000, error=True)
    
    def _on_content_ready(self, text: str):
        """
        Handle content ready signal from Content Box window.
        User has clicked "Ready" button or said voice command to indicate content is ready.
        
        Args:
            text: The content that's ready for processing
        """
        logger.info(f"✓ Content marked as ready by user ({len(text)} chars)")
        
        # Store that content is ready for next voice command
        if hasattr(self, 'content_window') and self.content_window is not None:
            self.content_window.set_status("✓ Ready - Now you can say refinement commands", 3000)
        
        # Optionally: Speak confirmation
        if hasattr(self, 'brain') and self.brain:
            try:
                self.brain._speak_response("Content received. What would you like me to do with it?")
            except Exception as e:
                logger.debug(f"Could not speak confirmation: {e}")
    
    def mark_content_ready(self) -> str:
        """
        Voice command handler: Mark content as ready for processing.
        User can say "I'm ready", "Done pasting", "Content ready", etc.
        
        Returns:
            str: Confirmation message
        """
        try:
            if hasattr(self, 'content_window') and self.content_window is not None:
                text = self.content_window.get_text()
                if text and text.strip():
                    self._on_content_ready(text)
                    return "Got it! Content is ready. You can now tell me what to do with it."
                else:
                    return "There's no content in the editor yet. Please paste or type your content first."
            else:
                return "Content Mode is not active. Please open Content Mode first."
        except Exception as e:
            error_msg = f"Error marking content ready: {str(e)}"
            logger.error(error_msg)
            return error_msg

    # ========================================================================
    # PHASE 15 - FILE SHARING
    # Multi-platform file sharing (WhatsApp, Nearby Share, Phone Link, Google Drive, Clipboard)
    # ========================================================================
    
    def _resolve_file_path(self, file_path: Optional[str]) -> Optional[str]:
        """
        Smart file path resolution - handles:
        - Full paths (C:\\path\\file.pdf)
        - Relative paths (Desktop\\file.pdf)
        - Just filename (file.pdf) - searches Downloads, Desktop, Documents
        - Empty/None - uses last created PDF or screenshot
        - Keywords: "last pdf", "last screenshot", "this", "it"
        - Placeholder paths from AI - falls back to last file
        
        Args:
            file_path: User-provided file path (can be None/partial/full)
            
        Returns:
            Resolved absolute path or None if not found
        """
        # Case 0: Detect AI placeholder paths and treat as "use last file"
        if file_path:
            placeholder_indicators = [
                '/path/to/',
                '[username]',
                'path\\to\\',
                'C:\\\\Users',  # Double-escaped (from AI JSON)
                'C:\\\\\\\\Users',  # Quad-escaped
            ]
            if any(indicator in file_path for indicator in placeholder_indicators):
                logger.info(f"📌 Detected AI placeholder path, using last file instead: {file_path}")
                file_path = None  # Treat as empty to trigger last file logic
        
        # Case 1: Empty or keywords → use last created file
        if not file_path or file_path.lower() in ['this', 'it', 'last', 'last file', 'recent']:
            if self.last_used_file and self.last_used_file.exists():
                logger.info(f"📌 Using last file: {self.last_used_file}")
                return str(self.last_used_file)
            return None
        
        # Keywords for specific file types
        if 'pdf' in file_path.lower() and ('last' in file_path.lower() or 'recent' in file_path.lower()):
            if self.last_created_pdf and self.last_created_pdf.exists():
                logger.info(f"📌 Using last PDF: {self.last_created_pdf}")
                return str(self.last_created_pdf)
        
        if 'screenshot' in file_path.lower() and ('last' in file_path.lower() or 'recent' in file_path.lower()):
            if self.last_screenshot and self.last_screenshot.exists():
                logger.info(f"📌 Using last screenshot: {self.last_screenshot}")
                return str(self.last_screenshot)
        
        # Case 2: Full path provided
        path = Path(file_path)
        if path.is_absolute() and path.exists():
            return str(path)
        
        # Case 3: Just filename or relative path - search common locations
        home = Path.home()
        search_dirs = [
            home / "Downloads",
            home / "Desktop",
            home / "Documents",
            home / "Documents" / "Nexa PDFs",  # Our PDF output folder
            home / "Pictures" / "Nexa Screenshots"  # Our screenshots folder
        ]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            
            # Try exact match
            candidate = search_dir / file_path
            if candidate.exists():
                logger.info(f"📌 Found file: {candidate}")
                return str(candidate)
            
            # Try case-insensitive search
            try:
                for file in search_dir.iterdir():
                    if file.name.lower() == Path(file_path).name.lower():
                        logger.info(f"📌 Found file (case-insensitive): {file}")
                        return str(file)
            except:
                continue
        
        return None
    
    def share_file(self, file_path: Optional[str] = None) -> str:
        """
        Open Windows Share dialog with file attached.
        User selects share target (WhatsApp, Nearby Share, Email, etc.)
        
        Smart path resolution:
        - Say "share it" → uses last created PDF/screenshot
        - Say "share document.pdf" → searches Downloads/Desktop/Documents
        - Say full path → uses exact path
        
        Args:
            file_path: Path to file (optional - uses last file if not provided)
            
        Returns:
            Status message
        """
        try:
            logger.info(f"📤 share_file called with: {file_path}")
            resolved_path = self._resolve_file_path(file_path)
            
            if not resolved_path:
                # Provide helpful error based on context
                if self.last_created_pdf:
                    return f"I couldn't find that file. Try saying 'share last PDF' - I see you created {self.last_created_pdf.name}"
                elif self.last_screenshot:
                    return f"I couldn't find that file. Try saying 'share last screenshot' - I see you created one recently"
                else:
                    return "I couldn't find a file to share. Please create a PDF first, take a screenshot, or specify a filename."
            
            logger.info(f"📤 Resolved path: {resolved_path}")
            result = self.sharing_service.open_windows_share_dialog(resolved_path)
            
            if result.get('success'):
                logger.info(f"✅ Share dialog opened successfully")
                return result['message']
            else:
                logger.error(f"❌ Share dialog failed: {result}")
                return f"Error: {result.get('message', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Share file error: {e}", exc_info=True)
            return f"Could not share file: {e}"
    
    def share_to_whatsapp(self, file_path: Optional[str] = None) -> str:
        """
        Share file via WhatsApp.
        Opens share dialog with WhatsApp as option (if installed).
        
        Args:
            file_path: Path to file (optional - uses last file if not provided)
            
        Returns:
            Status message
        """
        try:
            resolved_path = self._resolve_file_path(file_path)
            if not resolved_path:
                return "I couldn't find that file. Please create a PDF first or specify the filename."
            
            result = self.sharing_service.share_to_whatsapp(resolved_path)
            if result.get('success'):
                msg = result['message']
                note = result.get('note', '')
                return f"{msg}\n{note}" if note else msg
            else:
                return f"Error: {result.get('message', 'Unknown error')}"
        except Exception as e:
            logger.error(f"WhatsApp share error: {e}")
            return f"Could not share to WhatsApp: {e}"
    
    def share_to_phone_nearby(self, file_path: Optional[str] = None) -> str:
        """
        Share file to phone via Windows Nearby Share.
        Wireless transfer via WiFi/Bluetooth.
        
        Args:
            file_path: Path to file (optional - uses last file if not provided)
            
        Returns:
            Status message
        """
        try:
            resolved_path = self._resolve_file_path(file_path)
            if not resolved_path:
                return "I couldn't find that file. Please create a PDF first or specify the filename."
            
            result = self.sharing_service.share_to_phone_nearby(resolved_path)
            if result.get('success'):
                msg = result['message']
                note = result.get('note', '')
                return f"{msg}\n{note}" if note else msg
            else:
                return f"Error: {result.get('message', 'Unknown error')}"
        except Exception as e:
            logger.error(f"Nearby Share error: {e}")
            return f"Could not share via Nearby Share: {e}"
    
    def share_via_phone_link(self, file_path: Optional[str] = None) -> str:
        """
        Share file via Phone Link to paired device.
        
        Args:
            file_path: Path to file (optional - uses last file if not provided)
            
        Returns:
            Status message
        """
        try:
            resolved_path = self._resolve_file_path(file_path)
            if not resolved_path:
                return "I couldn't find that file. Please create a PDF first or specify the filename."
            
            result = self.sharing_service.share_to_phone_link(resolved_path)
            if result.get('success'):
                msg = result['message']
                note = result.get('note', '')
                warning = result.get('warning', '')
                return f"{msg}\n{note or warning}"
            else:
                return f"Error: {result.get('message', 'Unknown error')}"
        except Exception as e:
            logger.error(f"Phone Link error: {e}")
            return f"Could not share via Phone Link: {e}"
    
    def upload_to_google_drive(self, file_path: Optional[str] = None, folder: str = "Nexa Shared") -> str:
        """
        Upload file to Google Drive.
        Copies file to synced Google Drive folder.
        
        Args:
            file_path: Path to file (optional - uses last file if not provided)
            folder: Subfolder name (default: "Nexa Shared")
            
        Returns:
            Status message
        """
        try:
            resolved_path = self._resolve_file_path(file_path)
            if not resolved_path:
                return "I couldn't find that file. Please create a PDF first or specify the filename."
            
            result = self.sharing_service.copy_to_google_drive(resolved_path, folder)
            if result.get('success'):
                return f"{result['message']}\n{result.get('note', '')}"
            else:
                return f"Error: {result.get('message', 'Google Drive not available')}"
        except Exception as e:
            logger.error(f"Google Drive upload error: {e}")
            return f"Could not upload to Google Drive: {e}"
    
    def copy_file_to_clipboard_action(self, file_path: Optional[str] = None) -> str:
        """
        Copy file to clipboard for pasting.
        User can paste in File Explorer, email, chat apps, etc.
        
        Args:
            file_path: Path to file (optional - uses last file if not provided)
            
        Returns:
            Status message
        """
        try:
            resolved_path = self._resolve_file_path(file_path)
            if not resolved_path:
                return "I couldn't find that file. Please create a PDF first or specify the filename."
            
            result = self.sharing_service.copy_file_to_clipboard(resolved_path)
            if result.get('success'):
                return f"{result['message']}\n{result.get('instructions', '')}"
            else:
                return f"Error: {result.get('message', 'Unknown error')}"
        except Exception as e:
            logger.error(f"Clipboard copy error: {e}")
            return f"Could not copy to clipboard: {e}"
    
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
    # PHASE 16: SYSTEM POWER CONTROL, POWER PLANS, BLUETOOTH
    # → MOVED TO: core/system_control.py (December 2024)
    # Functions: lock_screen, system_sleep, hibernate, restart, shutdown,
    #            schedule_shutdown, cancel_shutdown, get_power_plan, list_power_plans,
    #            set_power_plan, get_bluetooth_status, list_bluetooth_devices,
    #            open_bluetooth_settings
    # ═══════════════════════════════════════════════════════════════════════════

