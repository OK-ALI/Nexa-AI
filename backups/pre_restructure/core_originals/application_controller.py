"""
Application Controller - Application Launch and Management

Handles opening, closing, and managing applications.
Uses AppDiscovery for dynamic app finding and AppNameMapper for name normalization.
"""

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ApplicationController:
    """
    Controller for application management operations.
    
    Handles:
    - Opening applications by name
    - Closing running applications  
    - Finding installed applications
    - Checking if applications are running
    """
    
    # Built-in Windows apps that always work
    BUILTIN_APPS = {
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
    
    def __init__(self, app_discovery=None, app_mapper=None, window_manager=None):
        """
        Initialize Application Controller.
        
        Args:
            app_discovery: AppDiscovery instance for finding apps
            app_mapper: AppNameMapper instance for name normalization
            window_manager: WindowManager instance for window operations
        """
        self.app_discovery = app_discovery
        self.app_mapper = app_mapper
        self.window_manager = window_manager
        self.os_name = platform.system()
        
        logger.info("🚀 Application Controller initialized")
    
    def open_application(self, app_name: str) -> Dict[str, Any]:
        """
        Open an application by name - DYNAMICALLY finds installed apps.
        Uses AppDiscovery to search Start Menu, Store apps, Registry, and common paths.
        
        Args:
            app_name: Application name (e.g., 'notepad', 'Microsoft Store', 'Alienware Command Center')
            
        Returns:
            Dict with 'success' and 'message' keys
        """
        logger.info(f"Opening application: {app_name}")
        
        try:
            if self.os_name == "Windows":
                app_lower = app_name.lower().strip()
                
                # Step 1: Try built-in Windows commands first (always work)
                if app_lower in self.BUILTIN_APPS:
                    executable = self.BUILTIN_APPS[app_lower]
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
                            return {'success': False, 'message': f"Failed to open {app_name}"}
                        
                        logger.info(f"✅ Launched builtin app: {executable}")
                        return {'success': True, 'app_name': app_name}
                    except Exception as launch_error:
                        logger.error(f"Failed to launch {app_name}: {launch_error}")
                        return {'success': False, 'message': str(launch_error)}
                
                # Step 2: Use dynamic app discovery (NEW!)
                if self.app_discovery:
                    logger.info(f"Using dynamic discovery to find: {app_name}")
                    success = self.app_discovery.launch_app(app_name)
                    
                    if success:
                        return {'success': True, 'app_name': app_name}
                    else:
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
                        return {'success': True, 'app_name': app_name}
                    except Exception as fallback_error:
                        logger.debug(f"Fallback failed for {exe_name}: {fallback_error}")
                        continue
                
                # Nothing worked - app not found
                logger.error(f"❌ Cannot find app: {app_name}")
                return {'success': False, 'not_found': True, 'app_name': app_name}
            
            else:  # Linux/Mac
                subprocess.Popen([app_name])
                return {'success': True, 'app_name': app_name}
        
        except Exception as e:
            logger.error(f"Error opening application: {e}")
            return {'success': False, 'message': str(e)}
    
    def close_application(self, app_name: str) -> Dict[str, Any]:
        """
        Close a running application by name (ENHANCED with active window fallback).
        Now supports friendly names like "Microsoft Edge" → "msedge".
        FIX W-14: If app not found by name, closes active window (for user-opened apps).
        
        Args:
            app_name: Application name to close (friendly or process name)
            
        Returns:
            Dict with 'success' and 'message' keys
        """
        try:
            if self.os_name == "Windows":
                import psutil
                
                # Get all variants of the app name
                variants = self._get_app_variants(app_name)
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
                    return {'success': True, 'app_name': app_name, 'count': closed_count}
                else:
                    # FIX W-14: App not found by name - try active window fallback
                    logger.info(f"⚠️ {app_name} not found in processes, trying active window fallback...")
                    
                    # Check if active window matches the app name
                    if self.window_manager:
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
                                    return {'success': True, 'app_name': app_name, 'via_window': True}
                    
                    # Active window doesn't match, return not running
                    logger.warning(f"{app_name} is not running (tried: {', '.join(variants)})")
                    return {'success': False, 'not_running': True, 'app_name': app_name}
            
            return {'success': False, 'message': "Application closing only available on Windows"}
            
        except Exception as e:
            logger.error(f"Error closing application: {e}")
            return {'success': False, 'message': str(e)}
    
    def is_application_running(self, app_name: str) -> bool:
        """
        Check if an application is currently running.
        
        Args:
            app_name: Application name to check
            
        Returns:
            True if running, False otherwise
        """
        try:
            if self.os_name != "Windows":
                return False
            
            import psutil
            
            # Get all variants of the app name
            variants = self._get_app_variants(app_name)
            
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower().replace('.exe', '')
                    
                    for variant in variants:
                        variant_lower = variant.lower().replace('.exe', '')
                        if variant_lower in proc_name or proc_name in variant_lower:
                            logger.info(f"✓ {app_name} is running (matched: {proc_name})")
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if app running: {e}")
            return False
    
    def _get_app_variants(self, app_name: str) -> List[str]:
        """
        Get all name variants for an application.
        Uses AppNameMapper if available, otherwise creates basic variants.
        
        Args:
            app_name: Application name
            
        Returns:
            List of name variants to search for
        """
        if self.app_mapper:
            return self.app_mapper.get_all_variants(app_name)
        
        # Basic fallback variants
        app_lower = app_name.lower().strip()
        return [
            app_lower,
            app_lower.replace(" ", ""),
            app_lower.replace(" ", "-"),
            app_lower.replace("-", ""),
            f"{app_lower}.exe",
        ]
    
    def find_installed_app(self, app_name: str) -> Optional[str]:
        """
        Find the installation path of an application.
        Uses AppDiscovery if available.
        
        Args:
            app_name: Application name to search for
            
        Returns:
            Full path to executable if found, None otherwise
        """
        if self.app_discovery:
            result = self.app_discovery.find_app(app_name)
            if result:
                return str(result)
        
        # Legacy fallback - search common locations
        return self._legacy_find_app(app_name)
    
    def _legacy_find_app(self, app_name: str) -> Optional[str]:
        """
        Legacy method to find apps via registry and filesystem search.
        
        Args:
            app_name: Application name to search for
            
        Returns:
            Full path to executable if found, None otherwise
        """
        try:
            if self.os_name != "Windows":
                return None
            
            import winreg
            
            app_lower = app_name.lower().strip()
            name_variants = [
                app_lower,
                app_lower.replace(" ", ""),
                app_lower.replace(" ", "-"),
                app_lower.replace("-", ""),
            ]
            
            # Search in Windows Registry (Uninstall keys)
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
                                
                                for variant in name_variants:
                                    if variant in display_name_lower:
                                        # Try to get InstallLocation
                                        try:
                                            install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                            if install_location and os.path.exists(install_location):
                                                # Search for main exe
                                                for file in os.listdir(install_location):
                                                    if file.lower().endswith('.exe'):
                                                        file_lower = file.lower().replace('.exe', '')
                                                        if any(v in file_lower for v in name_variants):
                                                            return os.path.join(install_location, file)
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
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding installed app: {e}")
            return None


# Singleton instance for easy access
_controller_instance: Optional[ApplicationController] = None


def get_application_controller(app_discovery=None, app_mapper=None, window_manager=None) -> ApplicationController:
    """
    Get or create the singleton ApplicationController instance.
    
    Args:
        app_discovery: AppDiscovery instance
        app_mapper: AppNameMapper instance
        window_manager: WindowManager instance
        
    Returns:
        ApplicationController instance
    """
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = ApplicationController(
            app_discovery=app_discovery,
            app_mapper=app_mapper,
            window_manager=window_manager
        )
    return _controller_instance
