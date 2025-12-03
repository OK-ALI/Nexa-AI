"""
Theme Manager - Load and manage Nexa UI themes
Handles theme switching and saves user preferences
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class ThemeManager(QObject):
    """
    Manages UI themes for Nexa.
    Loads themes from Themes/themes.json and saves user preference.
    """
    
    # Signal emitted when theme changes
    theme_changed = Signal(str)  # theme_name
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize theme manager.
        
        Args:
            config_path: Path to config directory (default: project_root/config)
        """
        super().__init__()
        
        # Paths
        self.project_root = Path(__file__).parent.parent
        self.themes_file = self.project_root / "Themes" / "themes.json"
        self.config_path = config_path or self.project_root / "config"
        self.prefs_file = self.config_path / "ui_preferences.json"
        
        # Loaded themes
        self.themes: Dict[str, Dict[str, Any]] = {}
        self.current_theme_name: str = "dark"
        
        # Load themes and user preference
        self._load_themes()
        self._load_user_preference()
    
    def _load_themes(self):
        """Load themes from themes.json"""
        try:
            if not self.themes_file.exists():
                logger.error(f"❌ Themes file not found: {self.themes_file}")
                self._create_default_themes()
                return
            
            with open(self.themes_file, 'r', encoding='utf-8') as f:
                self.themes = json.load(f)
            
            logger.info(f"✅ Loaded {len(self.themes)} themes: {list(self.themes.keys())}")
        
        except Exception as e:
            logger.error(f"❌ Failed to load themes: {e}")
            self._create_default_themes()
    
    def _create_default_themes(self):
        """Create default dark theme if themes.json is missing"""
        self.themes = {
            "dark": {
                "name": "Dark Theme",
                "background": {"gradient_start": "#0A0F19", "gradient_end": "#050A12"},
                "text": {"primary": "#FFFFFF", "secondary": "#00D4FF"},
                "title": {"main": "#00D4FF", "subtitle": "#0088CC"},
                "buttons": {"background": "rgba(50, 70, 100, 100)", "text": "#00D4FF"},
                "orb": {"listening": "#00D4FF", "thinking": "#9F7FFF", "responding": "#00FF96"},
                "status": {"active": "#00D4FF", "inactive": "rgba(0, 136, 204, 80)"}
            }
        }
        logger.warning("⚠️ Using default dark theme")
    
    def _load_user_preference(self):
        """Load user's theme preference from ui_preferences.json"""
        try:
            if self.prefs_file.exists():
                # Check if file is empty
                if self.prefs_file.stat().st_size == 0:
                    logger.info("📋 Preferences file is empty, using default 'dark'")
                    return
                
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        logger.info("📋 Preferences file is empty, using default 'dark'")
                        return
                    
                    prefs = json.loads(content)
                    saved_theme = prefs.get("theme", "dark")
                    
                    if saved_theme in self.themes:
                        self.current_theme_name = saved_theme
                        logger.info(f"📋 Loaded user theme preference: {saved_theme}")
                    else:
                        logger.warning(f"⚠️ Saved theme '{saved_theme}' not found, using 'dark'")
            else:
                logger.info("📋 No theme preference found, using default 'dark'")
        
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Invalid JSON in preferences file: {e}. Using default 'dark'")
            # Recreate the file with default theme
            self._save_user_preference()
        except Exception as e:
            logger.error(f"❌ Failed to load theme preference: {e}")
    
    def _save_user_preference(self):
        """Save current theme to ui_preferences.json"""
        try:
            # Ensure config directory exists
            self.config_path.mkdir(parents=True, exist_ok=True)
            
            # Load existing preferences or create new
            prefs = {}
            if self.prefs_file.exists() and self.prefs_file.stat().st_size > 0:
                try:
                    with open(self.prefs_file, 'r', encoding='utf-8') as f:
                        prefs = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("⚠️ Corrupted preferences file, creating new one")
                    prefs = {}
            
            # Update theme
            prefs["theme"] = self.current_theme_name
            
            # Save
            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, indent=2)
            
            logger.info(f"💾 Saved theme preference: {self.current_theme_name}")
        
        except Exception as e:
            logger.error(f"❌ Failed to save theme preference: {e}")
    
    def get_current_theme(self) -> Dict[str, Any]:
        """
        Get the current theme dictionary.
        
        Returns:
            Theme configuration dictionary
        """
        return self.themes.get(self.current_theme_name, self.themes.get("dark", {}))
    
    def get_theme_name(self) -> str:
        """Get current theme name"""
        return self.current_theme_name
    
    def get_available_themes(self) -> list:
        """Get list of available theme names"""
        return list(self.themes.keys())
    
    def set_theme(self, theme_name: str, save: bool = True) -> bool:
        """
        Switch to a different theme.
        
        Args:
            theme_name: Name of theme to switch to ('dark' or 'light')
            save: Whether to save preference to disk
        
        Returns:
            True if theme was changed, False if theme not found
        """
        if theme_name not in self.themes:
            logger.error(f"❌ Theme '{theme_name}' not found")
            return False
        
        old_theme = self.current_theme_name
        self.current_theme_name = theme_name
        
        if save:
            self._save_user_preference()
        
        logger.info(f"🎨 Theme changed: {old_theme} → {theme_name}")
        self.theme_changed.emit(theme_name)
        
        return True
    
    def toggle_theme(self) -> str:
        """
        Toggle between dark and light themes.
        
        Returns:
            New theme name
        """
        if self.current_theme_name == "dark":
            self.set_theme("light")
            return "light"
        else:
            self.set_theme("dark")
            return "dark"
    
    def get_color(self, *keys: str, default: str = "#FFFFFF") -> str:
        """
        Get a color value from current theme using dot notation.
        
        Args:
            *keys: Keys to traverse (e.g., 'text', 'primary')
            default: Default color if key not found
        
        Returns:
            Color string
        
        Example:
            get_color('text', 'primary')  # Returns "#FFFFFF" in dark theme
            get_color('buttons', 'background')  # Returns button background color
        """
        theme = self.get_current_theme()
        
        try:
            value = theme
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            logger.warning(f"⚠️ Color not found: {'.'.join(keys)}, using default")
            return default


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get or create global theme manager instance"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def get_current_theme() -> Dict[str, Any]:
    """Convenience function to get current theme"""
    return get_theme_manager().get_current_theme()


def get_color(*keys: str, default: str = "#FFFFFF") -> str:
    """Convenience function to get a theme color"""
    return get_theme_manager().get_color(*keys, default=default)
