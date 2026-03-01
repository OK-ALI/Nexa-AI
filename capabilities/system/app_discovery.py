"""
App Discovery - Dynamic Application Finder
Discovers all installed applications on Windows from multiple sources:
- Start Menu shortcuts
- Windows Store apps (shell:AppsFolder)
- Registry installed programs
- Common installation paths
"""

import logging
import os
import winreg
from pathlib import Path
from typing import List, Dict, Optional
import subprocess

logger = logging.getLogger(__name__)


class AppDiscovery:
    """Discovers and indexes all installed applications dynamically."""
    
    def __init__(self):
        """Initialize App Discovery."""
        self.app_cache: Dict[str, str] = {}  # {app_name: executable_path}
        self.indexed = False
        logger.info("App Discovery initialized")
    
    def find_app(self, app_name: str) -> Optional[str]:
        """
        Find application by name (case-insensitive).
        
        Args:
            app_name: Application name (e.g., "Microsoft Store", "Alienware Command Center")
            
        Returns:
            Executable path or start command, or None if not found
        """
        # Index apps if not already done
        if not self.indexed:
            logger.info("First app search - indexing all applications...")
            self.index_all_apps()
        
        # Normalize search name
        search_name = app_name.lower().strip()
        
        # Try exact match first
        for cached_name, cached_path in self.app_cache.items():
            if cached_name.lower() == search_name:
                logger.info(f"[OK] Found exact match: {cached_name} -> {cached_path}")
                return cached_path
        
        # Try partial match (contains)
        for cached_name, cached_path in self.app_cache.items():
            if search_name in cached_name.lower() or cached_name.lower() in search_name:
                logger.info(f"[OK] Found partial match: {cached_name} -> {cached_path}")
                return cached_path
        
        # Try word matching (all words must be in app name)
        search_words = search_name.split()
        for cached_name, cached_path in self.app_cache.items():
            cached_lower = cached_name.lower()
            if all(word in cached_lower for word in search_words):
                logger.info(f"[OK] Found word match: {cached_name} -> {cached_path}")
                return cached_path
        
        logger.warning(f"[X] App not found: {app_name}")
        return None
    
    def index_all_apps(self):
        """
        Index all installed applications from multiple sources.
        This is called once on first app search.
        """
        logger.info("Indexing installed applications...")
        
        # Clear cache
        self.app_cache.clear()
        
        # 1. Search Start Menu shortcuts
        self._index_start_menu()
        
        # 2. Search Windows Store apps
        self._index_store_apps()
        
        # 3. Search Registry
        self._index_registry_apps()
        
        self.indexed = True
        logger.info(f"[OK] Indexed {len(self.app_cache)} applications")
    
    def _index_start_menu(self):
        """Index Start Menu shortcuts for all users."""
        logger.info("Indexing Start Menu shortcuts...")
        
        start_menu_paths = [
            # Current user
            Path(os.environ.get('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs',
            # All users
            Path(os.environ.get('PROGRAMDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs',
        ]
        
        for base_path in start_menu_paths:
            if not base_path.exists():
                continue
            
            # Recursively search for .lnk files
            try:
                for shortcut_path in base_path.rglob('*.lnk'):
                    try:
                        app_name = shortcut_path.stem  # Filename without .lnk
                        
                        # Skip common non-app shortcuts
                        skip_keywords = ['uninstall', 'readme', 'help', 'manual', 'documentation']
                        if any(keyword in app_name.lower() for keyword in skip_keywords):
                            continue
                        
                        # Store shortcut path
                        self.app_cache[app_name] = str(shortcut_path)
                        logger.debug(f"  Found: {app_name} -> {shortcut_path}")
                        
                    except Exception as e:
                        logger.debug(f"Error reading shortcut {shortcut_path}: {e}")
                        
            except Exception as e:
                logger.error(f"Error scanning {base_path}: {e}")
        
        logger.info(f"  [OK] Start Menu: {len(self.app_cache)} shortcuts indexed")
    
    def _index_store_apps(self):
        """Index Windows Store apps using PowerShell with PackageFamilyName."""
        logger.info("Indexing Windows Store apps...")
        
        try:
            # Get Store apps with PackageFamilyName for proper launching
            ps_command = """
            Get-AppxPackage | Where-Object {$_.IsFramework -eq $false} | ForEach-Object {
                $appxManifest = Get-AppxPackageManifest $_.PackageFullName
                $apps = $appxManifest.Package.Applications.Application
                
                foreach ($app in $apps) {
                    if ($app.Id) {
                        $appName = $_.Name
                        $familyName = $_.PackageFamilyName
                        $appId = $app.Id
                        $displayName = if ($app.VisualElements.DisplayName) { $app.VisualElements.DisplayName } else { $appName }
                        
                        # Clean display name (remove ms-resource references)
                        if ($displayName -like "ms-resource:*" -or $displayName -like "@{*") {
                            $displayName = $appName -replace "Microsoft\\.", "" -replace "\\.", " "
                        }
                        
                        # Output format: DisplayName|PackageFamilyName!AppId
                        "$displayName|$familyName!$appId"
                    }
                }
            }
            """
            
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                store_app_count = 0
                for line in result.stdout.strip().split('\n'):
                    if '|' in line and '!' in line:
                        parts = line.split('|', 1)
                        if len(parts) == 2:
                            display_name, package_info = parts
                            
                            # Clean up display name
                            display_name = display_name.strip()
                            display_name = display_name.replace('Microsoft.', '').replace('.', ' ')
                            
                            # Store the package info for launching
                            self.app_cache[display_name] = package_info.strip()
                            store_app_count += 1
                            logger.debug(f"  Found Store app: {display_name}")
                
                logger.info(f"  [OK] Store apps: {store_app_count} apps indexed")
            else:
                logger.warning(f"PowerShell Store app query failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.warning("PowerShell Store app query timed out")
        except Exception as e:
            logger.error(f"Error indexing Store apps: {e}")
    
    def _index_registry_apps(self):
        """Index applications from Windows Registry."""
        logger.info("Indexing Registry applications...")
        
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        ]
        
        registry_app_count = 0
        
        for root_key, subkey_path in registry_paths:
            try:
                with winreg.OpenKey(root_key, subkey_path) as key:
                    i = 0
                    while True:
                        try:
                            # Enumerate subkeys (each is an app)
                            app_key_name = winreg.EnumKey(key, i)
                            
                            # Open the app subkey
                            with winreg.OpenKey(key, app_key_name) as app_key:
                                try:
                                    # Get default value (executable path)
                                    exe_path, _ = winreg.QueryValueEx(app_key, "")
                                    
                                    if exe_path and os.path.exists(exe_path):
                                        # Use executable name as app name (without .exe)
                                        app_name = Path(exe_path).stem
                                        
                                        # Skip if already cached (prefer Start Menu names)
                                        if app_name not in self.app_cache:
                                            self.app_cache[app_name] = exe_path
                                            registry_app_count += 1
                                            logger.debug(f"  Found Registry app: {app_name} -> {exe_path}")
                                            
                                except (FileNotFoundError, OSError):
                                    pass
                            
                            i += 1
                            
                        except OSError:
                            # No more subkeys
                            break
                            
            except FileNotFoundError:
                logger.debug(f"Registry path not found: {subkey_path}")
            except Exception as e:
                logger.error(f"Error reading registry {subkey_path}: {e}")
        
        logger.info(f"  [OK] Registry: {registry_app_count} apps indexed")
    
    def launch_app(self, app_name: str) -> bool:
        """
        Launch application by name.
        Handles Windows apps, Store apps, and regular applications.
        
        Args:
            app_name: Application name
            
        Returns:
            True if launched successfully, False otherwise
        """
        # First, check for Windows built-in apps with special URIs
        builtin_launch = self._try_launch_builtin(app_name)
        if builtin_launch:
            return True
        
        # Then try finding the app in our index
        app_path = self.find_app(app_name)
        
        if not app_path:
            logger.error(f"Cannot launch app - not found: {app_name}")
            return False
        
        try:
            logger.info(f"Launching: {app_name} -> {app_path}")
            
            # Method 1: .lnk shortcuts (best for Start Menu apps)
            if app_path.endswith('.lnk'):
                os.startfile(app_path)
                logger.info(f"[OK] Launched shortcut: {app_name}")
                return True
            
            # Method 2: .exe executables
            elif app_path.endswith('.exe'):
                subprocess.Popen([app_path], shell=False, 
                               creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
                logger.info(f"[OK] Launched executable: {app_name}")
                return True
            
            # Method 3: Windows Store app (PackageFamilyName!AppId format)
            elif '!' in app_path:
                # This is a Store app with PackageFamilyName!AppId
                logger.info(f"Launching Store app with package info: {app_path}")
                os.startfile(f"shell:AppsFolder\\{app_path}")
                logger.info(f"[OK] Launched Store app: {app_name}")
                return True
            
            # Method 4: Generic launch attempt
            else:
                os.startfile(app_path)
                logger.info(f"[OK] Launched via startfile: {app_name}")
                return True
                
        except Exception as e:
            logger.warning(f"Standard launch failed, trying alternative methods: {e}")
            
            # Fallback: Try PowerShell Start-Process
            try:
                subprocess.run(
                    ['powershell', '-NoProfile', '-Command', f'Start-Process "{app_path}"'],
                    capture_output=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                logger.info(f"[OK] Launched via PowerShell: {app_name}")
                return True
            except Exception as e2:
                logger.error(f"[X] All launch methods failed for {app_name}: {e2}")
                return False
    
    def _try_launch_builtin(self, app_name: str) -> bool:
        """
        Try to launch Windows built-in apps using ms-settings: or other URIs.
        
        Args:
            app_name: Application name
            
        Returns:
            True if launched, False if not a built-in app
        """
        app_lower = app_name.lower().strip()
        
        # Windows Settings URIs
        builtin_uris = {
            # Settings (include singular form for voice recognition)
            'setting': 'ms-settings:',
            'settings': 'ms-settings:',
            'windows setting': 'ms-settings:',
            'windows settings': 'ms-settings:',
            'system setting': 'ms-settings:',
            'system settings': 'ms-settings:',
            
            # Microsoft Store
            'store': 'ms-windows-store:',
            'microsoft store': 'ms-windows-store:',
            'windows store': 'ms-windows-store:',
            
            # Common Windows apps
            'mail': 'outlookcal:',
            'windows mail': 'outlookcal:',
            'calendar': 'outlookcal:',
            'photos': 'ms-photos:',
            'windows photos': 'ms-photos:',
            'camera': 'microsoft.windows.camera:',
            'windows camera': 'microsoft.windows.camera:',
            'maps': 'bingmaps:',
            'windows maps': 'bingmaps:',
            'weather': 'bingweather:',
            'windows weather': 'bingweather:',
            'news': 'bingnews:',
            'windows news': 'bingnews:',
            'voice recorder': 'ms-callrecording:',
            'windows voice recorder': 'ms-callrecording:',
            'alarm': 'ms-clock:',
            'alarms': 'ms-clock:',
            'clock': 'ms-clock:',
            'windows clock': 'ms-clock:',
            'snipping tool': 'ms-screenclip:',
            'windows snipping tool': 'ms-screenclip:',
            'screen snip': 'ms-screenclip:',
            'feedback hub': 'windows-feedback:',
            'windows feedback': 'windows-feedback:',
            'your phone': 'ms-yourphone:',
            'phone link': 'ms-yourphone:',
            'xbox': 'xbox:',
            'xbox app': 'xbox:',
            'windows security': 'windowsdefender:',
            'security': 'windowsdefender:',
            'defender': 'windowsdefender:',
        }
        
        if app_lower in builtin_uris:
            uri = builtin_uris[app_lower]
            try:
                logger.info(f"Launching Windows app via URI: {app_name} -> {uri}")
                os.startfile(uri)
                logger.info(f"[OK] Launched Windows built-in app: {app_name}")
                return True
            except Exception as e:
                logger.warning(f"Failed to launch via URI {uri}: {e}")
                return False
        
        return False
    
    def refresh_index(self):
        """Force re-indexing of all applications."""
        logger.info("Refreshing app index...")
        self.indexed = False
        self.index_all_apps()
    
    def search_apps(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for applications matching query.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching app names
        """
        if not self.indexed:
            self.index_all_apps()
        
        query_lower = query.lower()
        matches = []
        
        for app_name in self.app_cache.keys():
            if query_lower in app_name.lower():
                matches.append(app_name)
                if len(matches) >= limit:
                    break
        
        return matches
