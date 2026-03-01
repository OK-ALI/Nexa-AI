"""
Game Manager - Game Detection & Launch System
Phase 12: Detects and launches games from Steam, Epic Games, GOG, and standalone installations.
Also provides folder search and opening functionality.
"""

import logging
import os
import json
import re
import winreg
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import subprocess

logger = logging.getLogger(__name__)


class GameManager:
    """
    Manages game detection, indexing, and launching from multiple platforms.
    Also handles folder search and opening.
    """
    
    def __init__(self):
        """Initialize Game Manager."""
        self.games_cache: Dict[str, Dict] = {}  # {game_name: {platform, path, launch_cmd}}
        self.folders_cache: Dict[str, str] = {}  # {folder_name: full_path}
        self.indexed = False
        self.folders_indexed = False
        
        logger.info("Game Manager initialized")
    
    # ========================================
    # GAME DETECTION & LAUNCH
    # ========================================
    
    def find_game(self, game_name: str) -> Optional[Dict]:
        """
        Find a game by name across all platforms.
        
        Args:
            game_name: Game name (e.g., "Counter-Strike", "Fortnite")
            
        Returns:
            Game info dict {name, platform, path, launch_cmd} or None
        """
        # Index games if not already done
        if not self.indexed:
            logger.info("First game search - indexing all games...")
            self.index_all_games()
        
        # Normalize search name
        search_name = game_name.lower().strip()
        
        # Try exact match first
        for cached_name, game_info in self.games_cache.items():
            if cached_name.lower() == search_name:
                logger.info(f"✅ Found exact match: {cached_name} ({game_info['platform']})")
                return game_info
        
        # Try partial match (contains)
        for cached_name, game_info in self.games_cache.items():
            if search_name in cached_name.lower() or cached_name.lower() in search_name:
                logger.info(f"✅ Found partial match: {cached_name} ({game_info['platform']})")
                return game_info
        
        # Try word matching (all words must be in game name)
        search_words = search_name.split()
        for cached_name, game_info in self.games_cache.items():
            cached_lower = cached_name.lower()
            if all(word in cached_lower for word in search_words):
                logger.info(f"✅ Found word match: {cached_name} ({game_info['platform']})")
                return game_info
        
        logger.warning(f"❌ Game not found: {game_name}")
        return None
    
    def launch_game(self, game_name: str) -> Tuple[bool, str]:
        """
        Launch a game by name.
        
        Args:
            game_name: Game name to launch
            
        Returns:
            (success: bool, message: str)
        """
        game_info = self.find_game(game_name)
        
        if not game_info:
            return False, f"Game '{game_name}' not found. Try 'list my games' to see available games."
        
        try:
            launch_cmd = game_info['launch_cmd']
            platform = game_info['platform']
            
            logger.info(f"🎮 Launching {game_info['name']} ({platform})")
            logger.info(f"   Command: {launch_cmd}")
            
            # Launch the game
            if platform == "Steam":
                # Steam URL protocol
                subprocess.Popen(['cmd', '/c', 'start', '', launch_cmd], shell=False)
            elif platform == "Epic":
                # Epic Games launcher protocol
                subprocess.Popen(['cmd', '/c', 'start', '', launch_cmd], shell=False)
            else:
                # Direct executable launch
                subprocess.Popen(launch_cmd, shell=True)
            
            return True, f"Launching {game_info['name']} from {platform}"
        
        except Exception as e:
            logger.error(f"❌ Failed to launch game: {e}")
            return False, f"Failed to launch {game_info['name']}: {str(e)}"
    
    def list_games(self, platform: Optional[str] = None) -> List[str]:
        """
        List all detected games, optionally filtered by platform.
        
        Args:
            platform: Filter by platform (Steam, Epic, GOG, Standalone) or None for all
            
        Returns:
            List of game names
        """
        # Index games if not already done
        if not self.indexed:
            self.index_all_games()
        
        games = []
        for game_name, game_info in self.games_cache.items():
            if platform is None or game_info['platform'].lower() == platform.lower():
                games.append(f"{game_name} ({game_info['platform']})")
        
        return sorted(games)
    
    def index_all_games(self):
        """
        Index all games from all platforms.
        This is called once on first game search or list request.
        """
        logger.info("🔍 Indexing installed games from all platforms...")
        
        # Clear cache
        self.games_cache.clear()
        
        # Index each platform
        steam_count = self._index_steam_games()
        epic_count = self._index_epic_games()
        gog_count = self._index_gog_games()
        standalone_count = self._index_standalone_games()
        
        total = steam_count + epic_count + gog_count + standalone_count
        
        logger.info(f"✅ Indexed {total} games:")
        logger.info(f"   - Steam: {steam_count}")
        logger.info(f"   - Epic Games: {epic_count}")
        logger.info(f"   - GOG: {gog_count}")
        logger.info(f"   - Standalone: {standalone_count}")
        
        self.indexed = True
    
    # ========================================
    # STEAM GAME DETECTION
    # ========================================
    
    def _index_steam_games(self) -> int:
        """
        Index Steam games by parsing libraryfolders.vdf and app manifests.
        
        Returns:
            Number of Steam games found
        """
        count = 0
        
        try:
            # Find Steam installation path from registry
            steam_path = self._get_steam_path()
            if not steam_path:
                logger.warning("Steam installation not found")
                return 0
            
            logger.info(f"🎮 Found Steam at: {steam_path}")
            
            # Parse libraryfolders.vdf to find all library locations
            library_folders = self._parse_steam_library_folders(steam_path)
            logger.info(f"   Found {len(library_folders)} Steam library folders")
            
            # Parse each library folder for installed games
            for library_path in library_folders:
                steamapps_path = Path(library_path) / "steamapps"
                if not steamapps_path.exists():
                    continue
                
                # Find all .acf manifest files
                for acf_file in steamapps_path.glob("appmanifest_*.acf"):
                    game_info = self._parse_steam_manifest(acf_file, library_path)
                    if game_info:
                        self.games_cache[game_info['name']] = game_info
                        count += 1
            
            logger.info(f"✅ Indexed {count} Steam games")
        
        except Exception as e:
            logger.error(f"❌ Error indexing Steam games: {e}")
        
        return count
    
    def _get_steam_path(self) -> Optional[str]:
        """Get Steam installation path from registry."""
        try:
            # Try 64-bit registry first
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                r"SOFTWARE\WOW6432Node\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            return steam_path
        except:
            try:
                # Try 32-bit registry
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                    r"SOFTWARE\Valve\Steam")
                steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
                winreg.CloseKey(key)
                return steam_path
            except:
                return None
    
    def _parse_steam_library_folders(self, steam_path: str) -> List[str]:
        """
        Parse Steam's libraryfolders.vdf to find all game library locations.
        
        Args:
            steam_path: Steam installation path
            
        Returns:
            List of library folder paths
        """
        libraries = [steam_path]  # Default library is Steam installation path
        
        try:
            vdf_path = Path(steam_path) / "steamapps" / "libraryfolders.vdf"
            if not vdf_path.exists():
                return libraries
            
            # Parse VDF file (simple key-value format)
            with open(vdf_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all "path" entries
            # Format: "path"		"D:\\SteamLibrary"
            path_pattern = r'"path"\s+"([^"]+)"'
            matches = re.findall(path_pattern, content)
            
            for match in matches:
                # Normalize path (replace double backslashes)
                normalized_path = match.replace('\\\\', '\\')
                if os.path.exists(normalized_path):
                    libraries.append(normalized_path)
            
            # Remove duplicates
            libraries = list(set(libraries))
        
        except Exception as e:
            logger.error(f"❌ Error parsing libraryfolders.vdf: {e}")
        
        return libraries
    
    def _parse_steam_manifest(self, acf_path: Path, library_path: str) -> Optional[Dict]:
        """
        Parse a Steam app manifest (.acf) file to extract game info.
        
        Args:
            acf_path: Path to appmanifest_*.acf file
            library_path: Steam library path
            
        Returns:
            Game info dict or None
        """
        try:
            with open(acf_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract app ID from filename (appmanifest_<appid>.acf)
            app_id = acf_path.stem.replace('appmanifest_', '')
            
            # Extract game name
            name_match = re.search(r'"name"\s+"([^"]+)"', content)
            if not name_match:
                return None
            
            game_name = name_match.group(1)
            
            # Filter out non-game Steam utilities and redistributables
            non_game_keywords = [
                'steamworks common redistributables',
                'steam linux runtime',
                'proton',
                'steam controller configs',
                'steamvr',
                'steam audio',
                'directx',
                'vcredist',
                'dotnet',
                '.net framework'
            ]
            
            game_name_lower = game_name.lower()
            if any(keyword in game_name_lower for keyword in non_game_keywords):
                logger.debug(f"   Skipping non-game: {game_name}")
                return None
            
            # Extract install dir
            installdir_match = re.search(r'"installdir"\s+"([^"]+)"', content)
            if not installdir_match:
                return None
            
            install_dir = installdir_match.group(1)
            
            # Build full game path
            game_path = Path(library_path) / "steamapps" / "common" / install_dir
            
            # Create Steam launch URL
            launch_cmd = f"steam://rungameid/{app_id}"
            
            return {
                'name': game_name,
                'platform': 'Steam',
                'path': str(game_path),
                'launch_cmd': launch_cmd,
                'app_id': app_id
            }
        
        except Exception as e:
            logger.error(f"❌ Error parsing {acf_path.name}: {e}")
            return None
    
    # ========================================
    # EPIC GAMES DETECTION
    # ========================================
    
    def _index_epic_games(self) -> int:
        """
        Index Epic Games by parsing manifest files.
        
        Returns:
            Number of Epic games found
        """
        count = 0
        
        try:
            # Epic Games manifest location
            manifests_path = Path(os.environ.get('PROGRAMDATA', 'C:\\ProgramData')) / \
                           "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"
            
            if not manifests_path.exists():
                logger.warning("Epic Games manifests not found")
                return 0
            
            logger.info(f"🎮 Searching Epic Games manifests at: {manifests_path}")
            
            # Parse each .item manifest file
            for manifest_file in manifests_path.glob("*.item"):
                game_info = self._parse_epic_manifest(manifest_file)
                if game_info:
                    self.games_cache[game_info['name']] = game_info
                    count += 1
            
            logger.info(f"✅ Indexed {count} Epic Games")
        
        except Exception as e:
            logger.error(f"❌ Error indexing Epic Games: {e}")
        
        return count
    
    def _parse_epic_manifest(self, manifest_path: Path) -> Optional[Dict]:
        """
        Parse an Epic Games manifest file (.item).
        
        Args:
            manifest_path: Path to .item manifest file
            
        Returns:
            Game info dict or None
        """
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract game info
            game_name = data.get('DisplayName') or data.get('LaunchExecutable', '').replace('.exe', '')
            if not game_name:
                return None
            
            install_location = data.get('InstallLocation')
            if not install_location or not os.path.exists(install_location):
                return None
            
            # Get catalog namespace and item ID for launch URL
            namespace = data.get('CatalogNamespace', '')
            item_id = data.get('CatalogItemId', '')
            app_name = data.get('AppName', '')
            
            # Create Epic Games launcher URL
            if app_name:
                launch_cmd = f"com.epicgames.launcher://apps/{app_name}?action=launch&silent=true"
            else:
                # Fallback to direct exe launch
                launch_exe = data.get('LaunchExecutable')
                if launch_exe:
                    launch_cmd = str(Path(install_location) / launch_exe)
                else:
                    return None
            
            return {
                'name': game_name,
                'platform': 'Epic',
                'path': install_location,
                'launch_cmd': launch_cmd,
                'app_name': app_name
            }
        
        except Exception as e:
            logger.error(f"❌ Error parsing {manifest_path.name}: {e}")
            return None
    
    # ========================================
    # GOG GAMES DETECTION
    # ========================================
    
    def _index_gog_games(self) -> int:
        """
        Index GOG games from registry.
        
        Returns:
            Number of GOG games found
        """
        count = 0
        
        try:
            # GOG games are registered in the uninstall registry
            base_keys = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\GOG.com\Games"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\GOG.com\Games"),
            ]
            
            for root_key, subkey_path in base_keys:
                try:
                    games_key = winreg.OpenKey(root_key, subkey_path)
                    
                    # Enumerate all game subkeys
                    i = 0
                    while True:
                        try:
                            game_id = winreg.EnumKey(games_key, i)
                            game_info = self._parse_gog_game(root_key, subkey_path, game_id)
                            if game_info:
                                self.games_cache[game_info['name']] = game_info
                                count += 1
                            i += 1
                        except OSError:
                            break
                    
                    winreg.CloseKey(games_key)
                
                except FileNotFoundError:
                    continue
            
            logger.info(f"✅ Indexed {count} GOG games")
        
        except Exception as e:
            logger.error(f"❌ Error indexing GOG games: {e}")
        
        return count
    
    def _parse_gog_game(self, root_key, base_path: str, game_id: str) -> Optional[Dict]:
        """Parse a single GOG game from registry."""
        try:
            game_key_path = f"{base_path}\\{game_id}"
            game_key = winreg.OpenKey(root_key, game_key_path)
            
            # Get game name
            game_name, _ = winreg.QueryValueEx(game_key, "gameName")
            
            # Get executable path
            exe_path, _ = winreg.QueryValueEx(game_key, "exe")
            
            # Get working directory
            try:
                work_dir, _ = winreg.QueryValueEx(game_key, "workingDir")
            except:
                work_dir = str(Path(exe_path).parent)
            
            winreg.CloseKey(game_key)
            
            # Verify exe exists
            if not os.path.exists(exe_path):
                return None
            
            return {
                'name': game_name,
                'platform': 'GOG',
                'path': work_dir,
                'launch_cmd': f'"{exe_path}"',
                'game_id': game_id
            }
        
        except Exception as e:
            logger.debug(f"Could not parse GOG game {game_id}: {e}")
            return None
    
    # ========================================
    # STANDALONE GAMES DETECTION
    # ========================================
    
    def _index_standalone_games(self) -> int:
        """
        Intelligently index standalone games using heuristics and file analysis.
        Supports games anywhere on the system (pirated/cracked games in Games folder, etc.)
        Uses AI-like logic instead of rigid blacklists.
        
        Returns:
            Number of standalone games found
        """
        count = 0
        
        try:
            # Scan multiple locations where users typically install games
            game_locations = [
                Path("C:/Program Files/"),
                Path("C:/Program Files (x86)/"),
                Path.home() / "Games",  # Common for pirated/cracked games
                Path.home() / "Downloads",  # Sometimes games are run from here
                Path.home() / "Desktop",  # Quick access games
            ]
            
            # Check additional drives (D:, E:, F:, etc.) for Games folders
            for drive_letter in ['D', 'E', 'F', 'G']:
                games_path = Path(f"{drive_letter}:/Games")
                if games_path.exists():
                    game_locations.append(games_path)
            
            # Remove None entries and filter existing locations
            game_locations = [loc for loc in game_locations if loc and loc.exists()]
            
            logger.info(f"🔍 Scanning for standalone games in {len(game_locations)} locations...")
            for loc in game_locations:
                logger.debug(f"   Checking: {loc}")
            
            for game_dir in game_locations:
                try:
                    logger.debug(f"   📂 Scanning: {game_dir}")
                    folder_count = 0
                    
                    # Scan top-level folders (depth=1 for performance)
                    for folder in game_dir.iterdir():
                        if not folder.is_dir():
                            continue
                        
                        folder_count += 1
                        logger.debug(f"      Checking folder: {folder.name}")
                        
                        # Skip obvious system folders
                        if self._is_system_folder(folder):
                            logger.debug(f"      ❌ Skipped (system folder): {folder.name}")
                            continue
                        
                        # Look for game executables in this folder
                        game_exe = self._find_game_executable(folder)
                        
                        if game_exe:
                            game_name = folder.name  # Use folder name (user-friendly)
                            
                            # Skip if already indexed from Steam/Epic/GOG
                            if game_name in self.games_cache:
                                logger.debug(f"      ⏭️ Skipped (already in cache): {game_name}")
                                continue
                            
                            self.games_cache[game_name] = {
                                'name': game_name,
                                'platform': 'Standalone',
                                'path': str(game_exe.parent),
                                'launch_cmd': f'"{game_exe}"'
                            }
                            count += 1
                            logger.info(f"      ✅ Found standalone game: {game_name} → {game_exe}")
                        else:
                            logger.debug(f"      ❌ No valid game exe found in: {folder.name}")
                    
                    logger.debug(f"   Scanned {folder_count} folders in {game_dir}")
                
                except PermissionError:
                    # Skip folders we don't have permission to access
                    logger.debug(f"   Permission denied for: {game_dir}")
                    continue
                except Exception as e:
                    logger.warning(f"   Error scanning {game_dir}: {e}")
                    continue
            
            logger.info(f"✅ Indexed {count} standalone games")
        
        except Exception as e:
            logger.error(f"❌ Error indexing standalone games: {e}")
        
        return count
    
    def _is_system_folder(self, folder: Path) -> bool:
        """
        Check if folder is likely a system/utility folder (not a game).
        Uses intelligent heuristics instead of hardcoded blacklists.
        """
        folder_name = folder.name.lower()
        
        # System folders (obvious)
        system_indicators = ['windows', 'microsoft', 'common files', 'windowspowershell']
        if any(folder_name.startswith(indicator) for indicator in system_indicators):
            return True
        
        # Special folders
        special_folders = {'steamworks common redistributables', 'windows apps', 'windows defender'}
        if folder_name in special_folders:
            return True
        
        return False
    
    def _find_game_executable(self, folder: Path) -> Optional[Path]:
        """
        Intelligently find the main game executable in a folder.
        Uses heuristics and file analysis instead of rigid rules.
        
        Args:
            folder: Folder to search
            
        Returns:
            Path to game executable or None
        """
        # Locations to check (in order of priority)
        search_locations = [
            folder,  # Root folder
            folder / 'bin',  # bin/ subfolder
            folder / 'Binaries' / 'Win64',  # Unreal Engine games
            folder / 'Binaries' / 'Win32',
            folder / 'game',  # Some games use "game" folder
        ]
        
        all_exes = []
        for location in search_locations:
            if location.exists():
                exes_in_location = list(location.glob('*.exe'))
                all_exes.extend(exes_in_location)
                if exes_in_location:
                    logger.debug(f"         Found {len(exes_in_location)} .exe files in {location.name}")
        
        if not all_exes:
            logger.debug(f"         No .exe files found in {folder.name}")
            return None
        
        logger.debug(f"         Scoring {len(all_exes)} executables in {folder.name}")
        
        # Score each exe to find the most likely game executable
        scored_exes = []
        for exe in all_exes:
            score = self._score_executable(exe, folder)
            if score > 0:  # Only consider positive scores
                scored_exes.append((score, exe))
                logger.debug(f"         ✅ {exe.name}: score={score}")
            else:
                logger.debug(f"         ❌ {exe.name}: score={score} (rejected)")
        
        if not scored_exes:
            logger.debug(f"         No executables passed scoring threshold in {folder.name}")
            return None
        
        # Return highest-scored exe
        scored_exes.sort(reverse=True, key=lambda x: x[0])
        best_exe = scored_exes[0]
        logger.debug(f"         🎯 Best match: {best_exe[1].name} (score={best_exe[0]})")
        return best_exe[1]
    
    def _score_executable(self, exe: Path, parent_folder: Path) -> int:
        """
        Score an executable to determine if it's likely a game.
        Higher score = more likely to be a game.
        STRICT SCORING: Returns 0 for utilities/tools, requires 15+ to be considered a game.
        
        Args:
            exe: Path to executable
            parent_folder: Parent game folder
            
        Returns:
            Score (0 = not a game, 15+ = likely a game, 30+ = definitely a game)
        """
        score = 0
        exe_name = exe.stem.lower()
        folder_name = parent_folder.name.lower()
        
        # NEGATIVE indicators (definitely not a game)
        # If ANY of these match, immediately return 0
        not_game_patterns = [
            # Installers/Updaters
            'uninstall', 'uninst', 'setup', 'install', 'installer',
            'update', 'updater', 'patch', 'patcher',
            # Config/Settings
            'config', 'configure', 'settings', 'options',
            # Error handling
            'crash', 'report', 'reporter', 'error', 'diagnostic',
            # Redistributables
            'redist', 'vcredist', 'directx', '_redist', 'redistributable',
            # System services
            'helper', 'service', 'daemon', 'monitor', 'background',
            # Remote access/VPN
            'anydesk', 'teamviewer', 'remotedesktop', 'rdp',
            'radmin', 'vpn', 'hamachi', 'zerotier',
            # Development tools
            'git', 'svn', 'mercurial', 'subversion',
            'visual studio', 'vscode', 'vs_', 'devenv', 'msbuild', 'cmake',
            # Web servers/databases
            'iis', 'iisexpress', 'apache', 'nginx', 'mysql', 'postgres',
            # System utilities
            'taskmgr', 'regedit', 'cmd', 'powershell', 'notepad',
            # Compression tools
            'winrar', '7zip', '7z', 'winzip', 'rar',
            # Browsers
            'chrome', 'firefox', 'edge', 'safari', 'opera', 'browser',
            # Cheat/Modding tools (these are NOT games themselves)
            'cheat', 'trainer', 'modifier', 'hack', 'injector',
            # Launchers (main platforms)
            'steam', 'origin', 'uplay', 'epic', 'gog', 'battle.net',
            # Frameworks/Runtimes
            'dotnet', 'java', 'python', 'node', '.net', 'runtime',
            # OS/Subsystems
            'wsl', 'windows', 'ubuntu', 'debian', 'linux',
        ]
        
        # Check exe name against patterns
        for pattern in not_game_patterns:
            if pattern in exe_name:
                return 0  # Definitely not a game
        
        # Check FOLDER name too (catches "Cheat Engine\cheatengine.exe")
        folder_exclusions = [
            'cheat', 'vpn', 'winrar', 'dotnet', 'wsl', 'git',
            'anydesk', 'teamviewer', 'radmin', 'iis',
        ]
        for pattern in folder_exclusions:
            if pattern in folder_name:
                return 0  # Folder itself is a utility
        for pattern in folder_exclusions:
            if pattern in folder_name:
                return 0  # Folder itself is a utility
        
        # POSITIVE indicators (likely a game) - STRICT REQUIREMENTS
        
        # 1. Exe name matches folder name (+25 points - VERY strong indicator)
        folder_clean = folder_name.replace(' ', '').replace('-', '').replace('_', '')
        exe_clean = exe_name.replace(' ', '').replace('-', '').replace('_', '').replace('x64', '').replace('64', '')
        
        if exe_clean == folder_clean:
            score += 25  # Exact match after cleaning
        elif exe_clean in folder_clean or folder_clean in exe_clean:
            score += 15  # Partial match
        
        # 2. File size (games are LARGE, utilities are usually small)
        try:
            file_size_mb = exe.stat().st_size / (1024 * 1024)
            if file_size_mb > 100:
                score += 20  # Very large = likely a game
            elif file_size_mb > 50:
                score += 15
            elif file_size_mb > 20:
                score += 10
            elif file_size_mb < 5:
                score -= 5  # Very small = probably NOT a game
        except:
            pass
        
        # 3. Game-related keywords in exe name (+10 points)
        game_keywords = ['game', 'play']
        for keyword in game_keywords:
            if keyword in exe_name and 'launcher' not in exe_name:
                score += 10
        
        # 4. Common game exe patterns (+20 points)
        if exe_name.endswith(('win64-shipping', 'win32-shipping', '-win64', '-win32')):
            score += 20  # Unreal Engine shipping build (definitely a game)
        
        # 5. Check for game-related files in the folder (STRONG indicator)
        game_file_indicators = [
            '*.pak',      # Unreal Engine data files
            '*.unity3d',  # Unity data files
            '*.assets',   # Unity assets
            '*.rpf',      # Rockstar packed file (GTA, RDR)
            '*.big',      # EA big files
        ]
        
        game_data_count = 0
        for pattern in game_file_indicators:
            game_data_count += len(list(parent_folder.glob(pattern)))
        
        if game_data_count > 5:
            score += 20  # Strong evidence of a game
        elif game_data_count > 0:
            score += 10  # Some game data files
        
        # 6. Check for many DLLs (games have complex dependencies)
        dll_count = len(list(parent_folder.glob('*.dll')))
        if dll_count > 50:
            score += 10  # Many DLLs = complex app (likely game)
        elif dll_count > 20:
            score += 5
        
        # 7. Folder is in a "Games" directory (+20 points - STRONG indicator for pirated games)
        folder_path_lower = str(parent_folder).lower()
        if '\\games\\' in folder_path_lower or '/games/' in folder_path_lower:
            score += 20  # Explicitly in Games folder (user's pirated games location)
        
        # 8. Check for "Binaries" folder (Unreal Engine games)
        if (parent_folder / 'Binaries').exists():
            score += 15
        
        # MINIMUM THRESHOLD: Need at least 15 points to be considered a game
        # Lowered from 20 to catch more pirated/cracked games in Games folder
        if score < 15:
            return 0  # Not confident enough that this is a game
        
        return score
    
    # ========================================
    # FOLDER SEARCH & MANAGEMENT
    # ========================================
    
    def find_folder(self, folder_name: str) -> Optional[str]:
        """
        Find a folder by name with multi-strategy resolution (ENHANCED).
        
        Tries multiple strategies to find Windows folders:
        1. Windows Known Folders (Shell folders)
        2. Environment variables
        3. Cached folder index
        4. Common path patterns
        
        Args:
            folder_name: Folder name to search for
            
        Returns:
            Full path to folder or None
        """
        # Normalize search name
        search_name = folder_name.lower().strip()
        
        # STRATEGY 1: Windows Known Folders (most reliable)
        known_folder_path = self._get_windows_known_folder(search_name)
        if known_folder_path and os.path.exists(known_folder_path):
            logger.info(f"✅ Found via Windows Known Folders: {search_name} → {known_folder_path}")
            return known_folder_path
        
        # STRATEGY 2: Environment Variables
        env_path = self._get_folder_from_env(search_name)
        if env_path and os.path.exists(env_path):
            logger.info(f"✅ Found via environment variable: {search_name} → {env_path}")
            return env_path
        
        # STRATEGY 3: Cached folder index
        if not self.folders_indexed:
            logger.info("First folder search - indexing common folders...")
            self.index_folders()
        
        # Try exact match in cache
        for cached_name, cached_path in self.folders_cache.items():
            if cached_name.lower() == search_name:
                if os.path.exists(cached_path):
                    logger.info(f"✅ Found exact folder match in cache: {cached_name} → {cached_path}")
                    return cached_path
        
        # Try partial match in cache
        for cached_name, cached_path in self.folders_cache.items():
            if search_name in cached_name.lower() or cached_name.lower() in search_name:
                if os.path.exists(cached_path):
                    logger.info(f"✅ Found partial folder match in cache: {cached_name} → {cached_path}")
                    return cached_path
        
        # STRATEGY 4: Common path patterns (last resort)
        common_paths = [
            Path.home() / search_name,
            Path.home() / search_name.capitalize(),
            Path(f"C:/{search_name}"),
            Path(f"C:/{search_name.capitalize()}")
        ]
        
        for path in common_paths:
            if path.exists():
                logger.info(f"✅ Found via common path pattern: {search_name} → {str(path)}")
                return str(path)
        
        logger.warning(f"❌ Folder not found after all strategies: {folder_name}")
        return None
    
    def _get_windows_known_folder(self, folder_name: str) -> Optional[str]:
        """
        Get Windows known folder paths using environment variables (reliable cross-version).
        
        Args:
            folder_name: Folder name (e.g., 'documents', 'downloads', 'pictures')
            
        Returns:
            Full path or None
        """
        try:
            import os
            
            # Map common folder names to environment variables or known paths
            folder_mappings = {
                'documents': os.path.expandvars('%USERPROFILE%\\Documents'),
                'downloads': os.path.expandvars('%USERPROFILE%\\Downloads'),
                'desktop': os.path.expandvars('%USERPROFILE%\\Desktop'),
                'pictures': os.path.expandvars('%USERPROFILE%\\Pictures'),
                'videos': os.path.expandvars('%USERPROFILE%\\Videos'),
                'music': os.path.expandvars('%USERPROFILE%\\Music'),
                'onedrive': os.path.expandvars('%OneDrive%'),
                'appdata': os.path.expandvars('%APPDATA%'),
                'localappdata': os.path.expandvars('%LOCALAPPDATA%'),
                'temp': os.path.expandvars('%TEMP%'),
                'public': os.path.expandvars('%PUBLIC%'),
            }
            
            folder_key = folder_name.lower()
            if folder_key in folder_mappings:
                return folder_mappings[folder_key]
            
            return None
        except Exception as e:
            logger.debug(f"Failed to get Windows known folder: {e}")
            return None
    
    def _get_folder_from_env(self, folder_name: str) -> Optional[str]:
        """
        Try to resolve folder using environment variables.
        
        Args:
            folder_name: Folder name
            
        Returns:
            Full path or None
        """
        try:
            # Try direct environment variable
            env_var = folder_name.upper()
            if env_var in os.environ:
                return os.environ[env_var]
            
            # Try with % prefix
            expanded = os.path.expandvars(f'%{env_var}%')
            if expanded != f'%{env_var}%':  # Variable was expanded
                return expanded
            
            return None
        except Exception as e:
            logger.debug(f"Failed to get folder from environment: {e}")
            return None
    
    def open_folder(self, folder_name: str) -> Tuple[bool, str]:
        """
        Open a folder in File Explorer (ENHANCED with better error messages).
        
        Args:
            folder_name: Folder name or path
            
        Returns:
            (success: bool, message: str)
        """
        # Check if it's a direct path
        if os.path.exists(folder_name):
            try:
                subprocess.Popen(['explorer', folder_name])
                return True, f"Opening folder: {folder_name}"
            except Exception as e:
                return False, f"Failed to open folder: {str(e)}"
        
        # Search for folder by name using multi-strategy resolution
        folder_path = self.find_folder(folder_name)
        
        if not folder_path:
            # Provide helpful error message with suggestions
            similar_folders = self._get_similar_folder_names(folder_name)
            if similar_folders:
                suggestions = ", ".join(similar_folders[:3])
                return False, f"Folder '{folder_name}' not found. Did you mean: {suggestions}?"
            else:
                return False, f"Folder '{folder_name}' not found in common locations."
        
        try:
            subprocess.Popen(['explorer', folder_path])
            return True, f"Opening {folder_name} folder"
        
        except Exception as e:
            logger.error(f"❌ Failed to open folder: {e}")
            return False, f"Failed to open folder at {folder_path}: {str(e)}"
    
    def _get_similar_folder_names(self, folder_name: str) -> list:
        """
        Get similar folder names for suggestions.
        
        Args:
            folder_name: The folder name that wasn't found
            
        Returns:
            List of similar folder names
        """
        if not self.folders_indexed:
            self.index_folders()
        
        search_lower = folder_name.lower()
        similar = []
        
        for cached_name in self.folders_cache.keys():
            cached_lower = cached_name.lower()
            # Check if there's any overlap
            if any(word in cached_lower for word in search_lower.split()) or \
               any(word in search_lower for word in cached_lower.split()):
                similar.append(cached_name)
        
        return similar
    
    def index_folders(self):
        """
        Index common folders for quick search.
        Focuses on user folders and common locations.
        """
        logger.info("🔍 Indexing common folders...")
        
        self.folders_cache.clear()
        
        # Common user folders
        user_folders = {
            'Documents': str(Path.home() / 'Documents'),
            'Downloads': str(Path.home() / 'Downloads'),
            'Desktop': str(Path.home() / 'Desktop'),
            'Pictures': str(Path.home() / 'Pictures'),
            'Videos': str(Path.home() / 'Videos'),
            'Music': str(Path.home() / 'Music'),
            'Games': str(Path.home() / 'Games'),  # User's pirated/cracked games folder
        }
        
        for name, path in user_folders.items():
            if os.path.exists(path):
                self.folders_cache[name] = path
        
        # Check additional drives for Games folders
        for drive_letter in ['C', 'D', 'E', 'F', 'G']:
            games_path = Path(f"{drive_letter}:/Games")
            if games_path.exists():
                self.folders_cache[f"{drive_letter} Games"] = str(games_path)
        
        # Projects and common development folders
        dev_folders = [
            Path.home() / 'Projects',
            Path('C:/Projects'),
            Path('D:/Projects'),
            Path.home() / 'Code',
            Path.home() / 'Development',
        ]
        
        for folder in dev_folders:
            if folder.exists():
                self.folders_cache[folder.name] = str(folder)
                
                # Index immediate subfolders (one level deep)
                try:
                    for subfolder in folder.iterdir():
                        if subfolder.is_dir():
                            self.folders_cache[subfolder.name] = str(subfolder)
                except PermissionError:
                    pass
        
        self.folders_indexed = True
        logger.info(f"✅ Indexed {len(self.folders_cache)} folders")
