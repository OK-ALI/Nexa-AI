"""
Application Name Mapper
Maps common/friendly application names to their actual process names.
Solves the issue where "Close Microsoft Edge" doesn't work because the process is "msedge.exe".
"""

import logging

logger = logging.getLogger(__name__)


class AppNameMapper:
    """Maps friendly application names to actual process/executable names."""
    
    # Comprehensive mapping of common app names to their process names
    APP_NAME_MAP = {
        # Browsers
        "edge": "msedge",
        "microsoft edge": "msedge",
        "chrome": "chrome",
        "google chrome": "chrome",
        "firefox": "firefox",
        "mozilla firefox": "firefox",
        "brave": "brave",
        "opera": "opera",
        "safari": "safari",
        
        # Microsoft Office
        "word": "winword",
        "microsoft word": "winword",
        "excel": "excel",
        "microsoft excel": "excel",
        "powerpoint": "powerpnt",
        "microsoft powerpoint": "powerpnt",
        "outlook": "outlook",
        "microsoft outlook": "outlook",
        "onenote": "onenote",
        "microsoft onenote": "onenote",
        "teams": "teams",
        "microsoft teams": "teams",
        
        # Communication
        "discord": "discord",
        "slack": "slack",
        "zoom": "zoom",
        "skype": "skype",
        "telegram": "telegram",
        "whatsapp": "whatsapp",
        
        # Media
        "spotify": "spotify",
        "vlc": "vlc",
        "media player": "vlc",
        "itunes": "itunes",
        "windows media player": "wmplayer",
        
        # Development
        "vscode": "code",
        "visual studio code": "code",
        "visual studio": "devenv",
        "pycharm": "pycharm64",
        "sublime": "sublime_text",
        "sublime text": "sublime_text",
        "notepad++": "notepad++",
        "atom": "atom",
        
        # System
        "notepad": "notepad",
        "calculator": "calculator",
        "calc": "calculator",
        "paint": "mspaint",
        "task manager": "taskmgr",
        "file explorer": "explorer",
        "explorer": "explorer",
        "command prompt": "cmd",
        "cmd": "cmd",
        "powershell": "powershell",
        "terminal": "windowsterminal",
        "windows terminal": "windowsterminal",
        
        # Gaming
        "steam": "steam",
        "epic games": "epicgameslauncher",
        "epic": "epicgameslauncher",
        "origin": "origin",
        "uplay": "uplay",
        "battle.net": "battle.net",
        "battlenet": "battle.net",
        
        # Adobe
        "photoshop": "photoshop",
        "illustrator": "illustrator",
        "premiere": "premiere",
        "after effects": "afterfx",
        "acrobat": "acrobat",
        "adobe reader": "acrord32",
        
        # Other
        "chrome remote desktop": "remoting_host",
        "anydesk": "anydesk",
        "teamviewer": "teamviewer",
        "obs": "obs64",
        "obs studio": "obs64",
        "7zip": "7zfm",
        "winrar": "winrar",
        "gimp": "gimp",
    }
    
    # Alternative search terms for app opening (for Start Menu search)
    APP_SEARCH_TERMS = {
        "edge": ["Microsoft Edge", "Edge"],
        "chrome": ["Google Chrome", "Chrome"],
        "firefox": ["Mozilla Firefox", "Firefox"],
        "word": ["Microsoft Word", "Word"],
        "excel": ["Microsoft Excel", "Excel"],
        "powerpoint": ["Microsoft PowerPoint", "PowerPoint"],
        "outlook": ["Microsoft Outlook", "Outlook"],
        "teams": ["Microsoft Teams", "Teams"],
        "vscode": ["Visual Studio Code", "VS Code", "Code"],
        "calculator": ["Calculator"],
        "notepad": ["Notepad"],
        "paint": ["Paint"],
    }
    
    def __init__(self):
        """Initialize the mapper."""
        logger.info("Application Name Mapper initialized")
    
    def normalize_app_name(self, app_name: str) -> str:
        """
        Convert friendly app name to process name.
        
        Args:
            app_name: Friendly application name (e.g., "Microsoft Edge")
            
        Returns:
            Process name (e.g., "msedge") or original if no mapping found
        """
        app_lower = app_name.lower().strip().replace('.exe', '')
        
        # Check if it's in our mapping
        if app_lower in self.APP_NAME_MAP:
            normalized = self.APP_NAME_MAP[app_lower]
            logger.info(f"Mapped '{app_name}' → '{normalized}'")
            return normalized
        
        # Return original if no mapping found
        return app_lower
    
    def get_search_terms(self, app_name: str) -> list:
        """
        Get alternative search terms for app opening.
        
        Args:
            app_name: Application name
            
        Returns:
            List of search terms to try
        """
        app_lower = app_name.lower().strip().replace('.exe', '')
        
        # Return predefined search terms if available
        if app_lower in self.APP_SEARCH_TERMS:
            return self.APP_SEARCH_TERMS[app_lower]
        
        # Otherwise return original name
        return [app_name]
    
    def get_all_variants(self, app_name: str) -> list:
        """
        Get all possible name variants for an app.
        
        Args:
            app_name: Application name
            
        Returns:
            List of all variants (normalized, original, with .exe)
        """
        app_lower = app_name.lower().strip().replace('.exe', '')
        variants = [app_lower]
        
        # Add normalized version
        normalized = self.normalize_app_name(app_name)
        if normalized not in variants:
            variants.append(normalized)
        
        # Add .exe versions
        for variant in list(variants):
            if not variant.endswith('.exe'):
                variants.append(f"{variant}.exe")
        
        return variants
