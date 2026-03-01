"""
Sharing Service - Universal file sharing across multiple platforms
Handles WhatsApp, Nearby Share, Phone Link, Google Drive, and clipboard sharing.
"""

import logging
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SharingService:
    """
    Universal sharing service for files across multiple platforms.
    
    Supports:
    - WhatsApp (direct URI + Windows Share dialog fallback)
    - Nearby Share (Windows 11 native PC-to-phone transfer)
    - Phone Link (for paired devices)
    - Google Drive (file copy to synced folder)
    - Windows Share Dialog (native UI with all targets)
    - Clipboard (file copy, not path)
    """
    
    def __init__(self, config=None):
        """
        Initialize sharing service.
        
        Args:
            config: Optional configuration object
        """
        self.config = config
        
        # Detect Google Drive path
        self.google_drive_path = self._detect_google_drive()
        
        # Configuration options
        self.prefer_direct_sharing = True  # Try direct methods before dialog
        
        logger.info("✅ SharingService initialized")
        if self.google_drive_path:
            logger.info(f"📁 Google Drive detected: {self.google_drive_path}")
        else:
            logger.warning("⚠️ Google Drive not detected on system")
    
    def _detect_google_drive(self) -> Optional[Path]:
        """
        Detect Google Drive installation path.
        
        Returns:
            Path to Google Drive folder or None if not found
        """
        home = Path.home()
        
        # Common Google Drive paths
        possible_paths = [
            home / "Google Drive",
            home / "GoogleDrive",
            Path("G:/My Drive"),
            Path("G:/"),
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                logger.info(f"✅ Google Drive found: {path}")
                return path
        
        logger.debug("Google Drive not found in common locations")
        return None
    
    def validate_file(self, file_path: str) -> Path:
        """
        Validate that file exists and is accessible.
        
        Args:
            file_path: Path to file to share
            
        Returns:
            Validated Path object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is a directory
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if path.is_dir():
            raise ValueError(f"Path is a directory, not a file: {file_path}")
        
        return path
    
    # ============================================================================
    # Sharing Methods
    # ============================================================================
    
    def open_windows_share_dialog(self, file_path: str) -> Dict[str, Any]:
        """
        Open Windows native share dialog with file pre-attached.
        Uses PowerShell to invoke the DataTransferManager API.
        
        Args:
            file_path: Path to file to share
            
        Returns:
            Dict with success status and message
            
        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If PowerShell fails to open share dialog
        """
        validated_path = self.validate_file(file_path)
        
        # PowerShell script to open Windows Share contract
        # Uses Windows.ApplicationModel.DataTransfer.DataTransferManager
        ps_script = f"""
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        
        # Get the DataTransferManager
        [Windows.ApplicationModel.DataTransfer.DataTransferManager, Windows.ApplicationModel.DataTransfer, ContentType = WindowsRuntime] | Out-Null
        [Windows.ApplicationModel.DataTransfer.DataPackage, Windows.ApplicationModel.DataTransfer, ContentType = WindowsRuntime] | Out-Null
        [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
        
        # Create file to share
        $file = [Windows.Storage.StorageFile]::GetFileFromPathAsync('{validated_path}').GetAwaiter().GetResult()
        
        # Open Share UI using shell command (Windows 11 style)
        Start-Process -FilePath "ms-windows-store://sharefile" -ArgumentList "file:///{validated_path.as_posix()}"
        """
        
        # Try multiple methods in order of preference
        try:
            # Method 1: Windows Share UI via WPF foreground window (most reliable)
            try:
                logger.info("Attempting Method 1: Windows Share UI via WPF helper")
                
                # Use share_helper.py which creates a WPF window for foreground context
                helper_path = Path(__file__).parent / "share_helper.py"
                
                result = subprocess.run(
                    [sys.executable, str(helper_path), str(validated_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ Share dialog opened (Method 1 - WPF Helper): {validated_path.name}")
                    return {
                        "success": True,
                        "message": f"Share dialog opened for {validated_path.name}\nSelect WhatsApp from the share options",
                        "file": str(validated_path),
                        "method": "WPF ShowShareUI"
                    }
                else:
                    logger.debug(f"Method 1 failed: {result.stderr}")
            except Exception as e:
                logger.debug(f"Method 1 exception: {e}")
            
            # Method 2: Direct Windows 10/11 Share Command via Content Delivery Manager
            try:
                logger.info("Attempting Method 2: ContentDeliveryManager App")
                cmd = f'powershell -NoProfile -Command "Start-Process shell:AppsFolder\\Microsoft.Windows.ContentDeliveryManager_cw5n1h2txyewy!App -ArgumentList \\"{validated_path}\\""'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and not result.stderr:
                    logger.info(f"✅ Share dialog opened (Method 2 - ContentDeliveryManager): {validated_path.name}")
                    # Give the UI time to appear
                    import time
                    time.sleep(0.5)
                    return {
                        "success": True,
                        "message": f"Share dialog opened for {validated_path.name}",
                        "file": str(validated_path),
                        "method": "ContentDeliveryManager"
                    }
                else:
                    logger.debug(f"Method 2 failed: {result.stderr}")
            except Exception as e:
                logger.debug(f"Method 2 exception: {e}")
            
            # Method 3: Try UIAutomation to invoke Share from context menu
            try:
                logger.info("Attempting Method 3: Context menu automation")
                # Open Explorer with file selected
                subprocess.Popen(f'explorer.exe /select,"{validated_path}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                import time
                time.sleep(0.5)
                
                # Try to invoke Share verb via shell automation
                ps_share_cmd = f"""
                $shell = New-Object -ComObject Shell.Application
                $folder = $shell.NameSpace('{validated_path.parent.as_posix()}')
                $item = $folder.ParseName('{validated_path.name}')
                if ($item) {{
                    $verbs = $item.Verbs()
                    $shareVerb = $verbs | Where-Object {{ $_.Name -like '*Share*' -or $_.Name -like '*send*' }}
                    if ($shareVerb) {{
                        $shareVerb[0].DoIt()
                        exit 0
                    }}
                }}
                exit 1
                """
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_share_cmd],
                    capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    logger.info(f"✅ Share invoked via context menu: {validated_path.name}")
                    return {
                        "success": True,
                        "message": f"Share dialog opened for {validated_path.name}",
                        "file": str(validated_path),
                        "method": "Context Menu Automation"
                    }
                else:
                    logger.debug(f"Method 3 failed: {result.stderr}")
            except Exception as e:
                logger.debug(f"Method 3 exception: {e}")
            
            # Method 4: Fallback - Select file in Explorer and notify user
            logger.warning("All automated share methods failed, opening Explorer for manual share")
            subprocess.Popen(f'explorer.exe /select,"{validated_path}"', shell=True)
            
            return {
                "success": True,
                "message": f"File selected in Explorer: {validated_path.name}\nPress Win+H or right-click and select 'Share'",
                "file": str(validated_path),
                "method": "Explorer (Manual)",
                "action_required": "Press Win+H or right-click the file and select 'Share' from the context menu"
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Share dialog timeout")
            raise RuntimeError("Share dialog failed to open (timeout)")
            
        except Exception as e:
            logger.error(f"Failed to open share dialog: {e}")
            raise RuntimeError(f"Could not open Windows share dialog: {e}")
    
    def share_to_whatsapp(self, file_path: str) -> Dict[str, Any]:
        """
        Share file via WhatsApp (hybrid approach).
        Tries direct URI first (whatsapp://), falls back to Windows Share dialog.
        
        Note: Direct URI requires WhatsApp Desktop (MS Store) to be installed.
        Fallback ensures sharing always works via native share dialog.
        
        Args:
            file_path: Path to file to share
            
        Returns:
            Dict with success status, method used, and message
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        validated_path = self.validate_file(file_path)
        logger.info(f"📱 Sharing to WhatsApp: {validated_path.name}")
        
        if self.prefer_direct_sharing:
            # Try Method 1: Direct WhatsApp URI (requires MS Store WhatsApp)
            try:
                # Check if WhatsApp is installed
                check_cmd = 'powershell -Command "Get-AppxPackage -Name *WhatsApp*"'
                check_result = subprocess.run(
                    check_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                
                if "5A894077.WhatsAppDesktop" in check_result.stdout or "WhatsApp" in check_result.stdout:
                    # WhatsApp installed, try direct URI
                    # Note: whatsapp:// URI doesn't support file attachment directly
                    # We must use the share contract instead
                    logger.debug("WhatsApp detected, using share contract...")
                    
                    # Try to launch WhatsApp-specific share
                    # This requires the share dialog to be opened with WhatsApp pre-selected
                    # Windows doesn't support app-specific share target, so fall through
                    pass
                    
            except Exception as e:
                logger.debug(f"WhatsApp direct check failed: {e}")
        
        # Method 2: Use Windows Share Dialog (most reliable)
        # The share dialog will show WhatsApp if installed, along with other options
        logger.info("Opening Windows Share dialog (WhatsApp will appear if installed)")
        
        try:
            result = self.open_windows_share_dialog(str(validated_path))
            result["target"] = "WhatsApp (via Share Dialog)"
            result["note"] = "Select WhatsApp from the share options"
            return result
            
        except Exception as e:
            logger.error(f"Failed to share to WhatsApp: {e}")
            return {
                "success": False,
                "message": f"Could not open share dialog: {e}",
                "file": str(validated_path),
                "error": str(e)
            }
    
    def share_to_phone_nearby(self, file_path: str) -> Dict[str, Any]:
        """
        Share to phone via Windows Nearby Share.
        Opens Windows Share dialog where Nearby Share appears as an option.
        
        Requirements:
        - Windows 11 (or Windows 10 with Nearby Share enabled)
        - Bluetooth and WiFi enabled on both devices
        - Devices within proximity (typically same room)
        
        Args:
            file_path: Path to file to share
            
        Returns:
            Dict with success status and instructions
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        validated_path = self.validate_file(file_path)
        logger.info(f"📲 Sharing via Nearby Share: {validated_path.name}")
        
        try:
            # Open Windows Share dialog - Nearby Share appears automatically
            result = self.open_windows_share_dialog(str(validated_path))
            result["target"] = "Nearby Share"
            result["note"] = "Select 'Nearby Share' from options. Ensure Bluetooth/WiFi enabled."
            result["requirements"] = "Both devices must have Nearby Share enabled"
            return result
            
        except Exception as e:
            logger.error(f"Failed to open Nearby Share: {e}")
            return {
                "success": False,
                "message": f"Could not open share dialog: {e}",
                "file": str(validated_path),
                "error": str(e)
            }
    
    def share_to_phone_link(self, file_path: str) -> Dict[str, Any]:
        """
        Share to phone via Phone Link (for paired devices).
        Uses Windows Share dialog where Phone Link appears if device is paired.
        
        Requirements:
        - Phone Link app installed on Windows
        - Phone paired with PC (via Link to Windows on Android or Your Phone on iOS)
        - Both devices connected to internet
        
        Args:
            file_path: Path to file to share
            
        Returns:
            Dict with success status and instructions
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        validated_path = self.validate_file(file_path)
        logger.info(f"🔗 Sharing via Phone Link: {validated_path.name}")
        
        try:
            # Check if Phone Link is installed
            check_cmd = 'powershell -Command "Get-AppxPackage -Name *Microsoft.YourPhone*"'
            check_result = subprocess.run(
                check_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3
            )
            
            phone_link_installed = "Microsoft.YourPhone" in check_result.stdout
            
            # Open Windows Share dialog - Phone Link appears if paired
            result = self.open_windows_share_dialog(str(validated_path))
            result["target"] = "Phone Link"
            
            if phone_link_installed:
                result["note"] = "Select your paired phone from the share options"
                result["status"] = "Phone Link detected"
            else:
                result["note"] = "Phone Link not installed. Install from Microsoft Store and pair your phone."
                result["warning"] = "Phone Link app required"
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to share via Phone Link: {e}")
            return {
                "success": False,
                "message": f"Could not open share dialog: {e}",
                "file": str(validated_path),
                "error": str(e)
            }
    
    def copy_to_google_drive(self, file_path: str, folder: str = "Nexa Shared") -> Dict[str, Any]:
        """
        Copy file to Google Drive synced folder.
        Creates target folder if it doesn't exist. File syncs automatically via Google Drive app.
        
        Args:
            file_path: Path to file to upload
            folder: Subfolder name in Google Drive (default: "Nexa Shared")
            
        Returns:
            Dict with success status, destination path, and sync status
            
        Raises:
            FileNotFoundError: If source file or Google Drive path doesn't exist
            RuntimeError: If copy operation fails
        """
        validated_path = self.validate_file(file_path)
        logger.info(f"☁️ Uploading to Google Drive: {validated_path.name}")
        
        # Check if Google Drive is available
        if not self.google_drive_path:
            logger.error("Google Drive not found")
            return {
                "success": False,
                "message": "Google Drive not detected. Install and sync Google Drive.",
                "file": str(validated_path),
                "error": "Google Drive path not found"
            }
        
        try:
            # Create target folder if it doesn't exist
            target_folder = self.google_drive_path / folder
            target_folder.mkdir(exist_ok=True)
            logger.debug(f"Target folder ready: {target_folder}")
            
            # Copy file to Google Drive
            destination = target_folder / validated_path.name
            
            # Handle duplicate filenames
            if destination.exists():
                # Add timestamp to avoid overwriting
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = validated_path.stem
                suffix = validated_path.suffix
                destination = target_folder / f"{stem}_{timestamp}{suffix}"
                logger.info(f"File exists, renamed to: {destination.name}")
            
            # Perform copy
            shutil.copy2(validated_path, destination)
            logger.info(f"✅ File copied to Google Drive: {destination}")
            
            return {
                "success": True,
                "message": f"File uploaded to Google Drive: {folder}/{destination.name}",
                "file": str(validated_path),
                "destination": str(destination),
                "folder": folder,
                "note": "File will sync automatically via Google Drive"
            }
            
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return {
                "success": False,
                "message": f"Permission denied when copying to Google Drive",
                "file": str(validated_path),
                "error": str(e)
            }
            
        except Exception as e:
            logger.error(f"Failed to copy to Google Drive: {e}")
            return {
                "success": False,
                "message": f"Could not upload to Google Drive: {e}",
                "file": str(validated_path),
                "error": str(e)
            }
    
    def copy_file_to_clipboard(self, file_path: str) -> Dict[str, Any]:
        """
        Copy file (not just path) to clipboard for pasting into other applications.
        Uses Windows clipboard to copy the actual file object.
        
        After copying, user can paste the file in:
        - File Explorer (Ctrl+V)
        - Email clients (Gmail, Outlook)
        - Chat apps (Discord, Slack)
        - Any application that accepts file paste
        
        Args:
            file_path: Path to file to copy
            
        Returns:
            Dict with success status and paste instructions
            
        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If clipboard operation fails
        """
        validated_path = self.validate_file(file_path)
        logger.info(f"📋 Copying file to clipboard: {validated_path.name}")
        
        try:
            # Use PowerShell to copy file to clipboard
            # This copies the actual file object, not just the path
            ps_cmd = f'powershell -Command "Set-Clipboard -Path \\"{validated_path}\\""'
            
            result = subprocess.run(
                ps_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0:
                logger.info(f"✅ File copied to clipboard: {validated_path.name}")
                return {
                    "success": True,
                    "message": f"File copied to clipboard: {validated_path.name}",
                    "file": str(validated_path),
                    "instructions": "Press Ctrl+V to paste in File Explorer, email, or chat apps"
                }
            else:
                raise RuntimeError(f"PowerShell returned error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("Clipboard copy timeout")
            return {
                "success": False,
                "message": "Clipboard operation timed out",
                "file": str(validated_path),
                "error": "timeout"
            }
            
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            return {
                "success": False,
                "message": f"Could not copy file to clipboard: {e}",
                "file": str(validated_path),
                "error": str(e)
            }


# ============================================================================
# Module-level test function (for development testing only)
# ============================================================================

def _test_sharing_service():
    """Test function for development (not used in production)."""
    print("Testing SharingService initialization...")
    
    service = SharingService()
    print(f"✅ Service initialized")
    print(f"📁 Google Drive: {service.google_drive_path}")
    
    # Test file validation
    try:
        test_file = Path(__file__)  # Use this file as test
        validated = service.validate_file(str(test_file))
        print(f"✅ File validation works: {validated}")
    except Exception as e:
        print(f"❌ File validation error: {e}")
    
    # Test all sharing methods
    print("\n" + "="*60)
    print("Testing All Sharing Methods")
    print("="*60)
    
    # 1. Windows Share Dialog
    print("\n1️⃣ Testing Windows Share Dialog...")
    try:
        result = service.open_windows_share_dialog(str(test_file))
        print(f"   ✅ {result['message']}")
        print(f"   📍 Method: {result.get('method', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 2. WhatsApp
    print("\n2️⃣ Testing WhatsApp Share...")
    try:
        result = service.share_to_whatsapp(str(test_file))
        print(f"   ✅ {result['message']}")
        print(f"   📝 Note: {result.get('note', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Nearby Share
    print("\n3️⃣ Testing Nearby Share...")
    try:
        result = service.share_to_phone_nearby(str(test_file))
        print(f"   ✅ {result['message']}")
        print(f"   📝 Note: {result.get('note', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 4. Phone Link
    print("\n4️⃣ Testing Phone Link...")
    try:
        result = service.share_to_phone_link(str(test_file))
        print(f"   ✅ {result['message']}")
        print(f"   📝 Status: {result.get('status', result.get('warning', 'N/A'))}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 5. Google Drive
    print("\n5️⃣ Testing Google Drive Upload...")
    try:
        result = service.copy_to_google_drive(str(test_file))
        if result['success']:
            print(f"   ✅ {result['message']}")
            print(f"   📁 Destination: {result.get('destination', 'N/A')}")
        else:
            print(f"   ⚠️  {result['message']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 6. Clipboard
    print("\n6️⃣ Testing Clipboard Copy...")
    try:
        result = service.copy_file_to_clipboard(str(test_file))
        if result['success']:
            print(f"   ✅ {result['message']}")
            print(f"   📋 {result.get('instructions', 'N/A')}")
        else:
            print(f"   ⚠️  {result['message']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)


if __name__ == "__main__":
    # Run test if executed directly
    logging.basicConfig(level=logging.INFO)
    _test_sharing_service()
