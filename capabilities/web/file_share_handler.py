"""
File Share Handler - Multi-Platform File Sharing
Handles file sharing: Windows Share dialog, WhatsApp, Nearby Share, Phone Link, Google Drive, Clipboard.
Extracted from executor.py for better modularity.
"""

import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class FileShareHandler:
    """
    Manages file sharing across multiple platforms.
    Provides smart file path resolution and multiple share targets.
    """
    
    def __init__(self, config, sharing_service, executor_ref):
        """
        Initialize File Share handler.
        
        Args:
            config: Configuration object
            sharing_service: SharingService instance
            executor_ref: Reference to CommandExecutor for accessing shared resources
        """
        self.config = config
        self.sharing_service = sharing_service
        self.executor = executor_ref
        
        logger.debug("FileShareHandler initialized")
    
    @property
    def last_created_pdf(self) -> Optional[Path]:
        """Access last created PDF from executor."""
        return getattr(self.executor, 'last_created_pdf', None)
    
    @property
    def last_screenshot(self) -> Optional[Path]:
        """Access last screenshot from executor."""
        return getattr(self.executor, 'last_screenshot', None)
    
    @property
    def last_used_file(self) -> Optional[Path]:
        """Access last used file from executor."""
        return getattr(self.executor, 'last_used_file', None)
    
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
    
    def _get_helpful_error(self) -> str:
        """Generate helpful error message based on context."""
        if self.last_created_pdf:
            return f"I couldn't find that file. Try saying 'share last PDF' - I see you created {self.last_created_pdf.name}"
        elif self.last_screenshot:
            return f"I couldn't find that file. Try saying 'share last screenshot' - I see you created one recently"
        else:
            return "I couldn't find a file to share. Please create a PDF first, take a screenshot, or specify a filename."
    
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
                return self._get_helpful_error()
            
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
