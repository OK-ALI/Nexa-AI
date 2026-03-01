"""
Window Manager - Phase 4
Handles window manipulation operations (minimize, maximize, restore, hide, show).
Completely isolated module - does not affect existing Phase 1-3.5 features.
"""

import logging
import win32gui
import win32con
import win32process
import psutil
from typing import Optional, List, Tuple
from core.cognition.natural_responses import NaturalResponses

logger = logging.getLogger(__name__)


class WindowManager:
    """
    Manages window operations using Windows API.
    Separate from application launching/closing (Phase 2).
    """
    
    def __init__(self):
        """Initialize Window Manager."""
        logger.info("Window Manager initialized")
    
    def _find_window_by_title_partial(self, partial_title: str, include_minimized: bool = True) -> Optional[int]:
        """
        Find window handle by partial title match.
        
        Args:
            partial_title: Partial window title to search for
            include_minimized: Whether to include minimized windows (default: True)
            
        Returns:
            Window handle (HWND) or None if not found
        """
        partial_lower = partial_title.lower()
        found_hwnd = None
        
        def callback(hwnd, _):
            nonlocal found_hwnd
            try:
                # Check if window is visible OR if we're including minimized windows
                if win32gui.IsWindowVisible(hwnd) or include_minimized:
                    title = win32gui.GetWindowText(hwnd)
                    if partial_lower in title.lower():
                        # If including minimized, accept any match
                        # Otherwise, check it's not minimized
                        if include_minimized:
                            found_hwnd = hwnd
                            return False  # Stop enumeration
                        else:
                            # Check if not minimized
                            placement = win32gui.GetWindowPlacement(hwnd)
                            if placement[1] != win32con.SW_SHOWMINIMIZED:
                                found_hwnd = hwnd
                                return False
            except:
                pass
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except:
            pass  # Ignore enum errors
        return found_hwnd
    
    def _find_window_by_process_name(self, process_name: str, include_hidden: bool = False, include_minimized: bool = True) -> Optional[int]:
        """
        Find window handle by process name.
        
        Args:
            process_name: Process name (e.g., "chrome", "notepad")
            include_hidden: Whether to include hidden windows
            include_minimized: Whether to include minimized windows (default: True)
            
        Returns:
            Window handle (HWND) or None if not found
        """
        process_lower = process_name.lower().replace('.exe', '')
        found_hwnd = None
        
        def callback(hwnd, _):
            nonlocal found_hwnd
            # Check visibility only if not including hidden windows
            if not include_hidden and not win32gui.IsWindowVisible(hwnd):
                return True
            
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                proc_name = proc.name().lower().replace('.exe', '')
                
                if process_lower in proc_name or proc_name in process_lower:
                    # Make sure it has a title (main window)
                    title = win32gui.GetWindowText(hwnd)
                    if title or include_hidden:
                        # Check if we should skip minimized windows
                        if not include_minimized:
                            placement = win32gui.GetWindowPlacement(hwnd)
                            if placement[1] == win32con.SW_SHOWMINIMIZED:
                                return True  # Skip minimized, continue search
                        
                        found_hwnd = hwnd
                        return False  # Stop enumeration
            except:
                pass
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
        except:
            pass  # Ignore enum errors
        return found_hwnd
    
    def _find_window(self, identifier: str, include_hidden: bool = False, include_minimized: bool = True) -> Optional[int]:
        """
        Smart window finder - tries both title and process name (ENHANCED).
        Now supports friendly app names (Chrome, Discord, etc.) and minimized windows.
        
        Args:
            identifier: Window title, process name, or friendly app name
            include_hidden: Whether to include hidden windows
            include_minimized: Whether to include minimized windows (default: True)
            
        Returns:
            Window handle (HWND) or None if not found
        """
        # Try by title first
        hwnd = self._find_window_by_title_partial(identifier, include_minimized=include_minimized)
        if hwnd:
            return hwnd
        
        # Try by process name directly
        hwnd = self._find_window_by_process_name(identifier, include_hidden=include_hidden, include_minimized=include_minimized)
        if hwnd:
            return hwnd
        
        # Try mapping friendly name to process name (Chrome → chrome.exe)
        try:
            from capabilities.system.app_name_mapper import AppNameMapper
            mapper = AppNameMapper()
            
            # Get the technical name for friendly name
            mapped_name = None
            for proc_name, friendly_name in mapper.app_name_map.items():
                if friendly_name.lower() == identifier.lower():
                    mapped_name = proc_name.replace('.exe', '')
                    break
            
            if mapped_name:
                hwnd = self._find_window_by_process_name(mapped_name, include_hidden=include_hidden, include_minimized=include_minimized)
                if hwnd:
                    return hwnd
        except Exception as e:
            logger.debug(f"Could not map app name: {e}")
        
        return None
    
    def minimize_window(self, identifier: str) -> str:
        """
        Minimize a window (ENHANCED with validation).
        
        Args:
            identifier: Window title, process name, or friendly app name
            
        Returns:
            Result message
        """
        try:
            hwnd = self._find_window(identifier)
            
            if not hwnd:
                return NaturalResponses.not_found()
            
            # Validate window handle before operating
            if not win32gui.IsWindow(hwnd):
                return NaturalResponses.error()
            
            # Get title before minimizing
            window_title = win32gui.GetWindowText(hwnd) or identifier
            
            # Minimize using SW_MINIMIZE (6)
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            
            # Verify the minimize succeeded
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                logger.info(f"✅ Minimized window: {window_title}")
                return NaturalResponses.window_minimized()
            else:
                logger.warning(f"⚠️ Minimize command sent but state unchanged for: {window_title}")
                return NaturalResponses.window_minimized()  # Still respond naturally
            
        except Exception as e:
            logger.error(f"❌ Error minimizing window: {e}")
            return NaturalResponses.error()
    
    def maximize_window(self, identifier: str) -> str:
        """
        Maximize a window (ENHANCED with validation).
        
        Args:
            identifier: Window title, process name, or friendly app name
            
        Returns:
            Result message
        """
        try:
            hwnd = self._find_window(identifier)
            
            if not hwnd:
                return NaturalResponses.not_found()
            
            # Validate window handle
            if not win32gui.IsWindow(hwnd):
                return NaturalResponses.error()
            
            # Get title before maximizing
            window_title = win32gui.GetWindowText(hwnd) or identifier
            
            # If minimized, restore first then maximize
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # Maximize using SW_MAXIMIZE (3)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            
            # Verify the maximize succeeded
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMAXIMIZED:
                logger.info(f"✅ Maximized window: {window_title}")
                return NaturalResponses.window_maximized()
            else:
                logger.warning(f"⚠️ Maximize command sent but state unchanged for: {window_title}")
                return NaturalResponses.window_maximized()  # Still respond naturally
            
        except Exception as e:
            logger.error(f"❌ Error maximizing window: {e}")
            return NaturalResponses.error()
    
    def restore_window(self, identifier: str) -> str:
        """
        Restore a window to normal size (from minimized or maximized) - ENHANCED.
        
        Args:
            identifier: Window title, process name, or friendly app name
            
        Returns:
            Result message
        """
        try:
            hwnd = self._find_window(identifier, include_hidden=True)
            
            if not hwnd:
                return NaturalResponses.not_found()
            
            # Validate window handle
            if not win32gui.IsWindow(hwnd):
                return NaturalResponses.error()
            
            # Get title before restoring
            window_title = win32gui.GetWindowText(hwnd) or identifier
            
            # Restore using SW_RESTORE (9)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # Bring to foreground if it was hidden
            try:
                win32gui.SetForegroundWindow(hwnd)
            except:
                pass  # May fail due to Windows restrictions
            
            # Verify the restore succeeded
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWNORMAL:
                logger.info(f"✅ Restored window: {window_title}")
                return NaturalResponses.window_restored()
            else:
                logger.warning(f"⚠️ Restore command sent but state unchanged for: {window_title}")
                return NaturalResponses.window_restored()  # Still respond naturally
            
        except Exception as e:
            logger.error(f"❌ Error restoring window: {e}")
            return NaturalResponses.error()
    
    def hide_window(self, identifier: str) -> str:
        """
        Hide a window (process keeps running, window invisible).
        
        Args:
            identifier: Window title or process name
            
        Returns:
            Result message
        """
        try:
            hwnd = self._find_window(identifier)
            
            if not hwnd:
                return NaturalResponses.not_found()
            
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            window_title = win32gui.GetWindowText(hwnd)
            logger.info(f"Hidden window: {window_title}")
            return NaturalResponses.success()
            
        except Exception as e:
            logger.error(f"Error hiding window: {e}")
            return NaturalResponses.error()
    
    def show_window(self, identifier: str) -> str:
        """
        Show a hidden window.
        
        Args:
            identifier: Window title or process name
            
        Returns:
            Result message
        """
        try:
            # Include hidden windows in search
            hwnd = self._find_window(identifier, include_hidden=True)
            
            if not hwnd:
                return NaturalResponses.not_found()
            
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # Also restore it
            window_title = win32gui.GetWindowText(hwnd)
            logger.info(f"Shown window: {window_title}")
            return NaturalResponses.success()
            
        except Exception as e:
            logger.error(f"Error showing window: {e}")
            return NaturalResponses.error()
            return NaturalResponses.error()
    
    def get_active_window_title(self) -> str:
        """
        Get the title of the currently active window.
        
        Returns:
            Window title or error message
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            return title if title else "No active window"
        except Exception as e:
            logger.error(f"Error getting active window: {e}")
            return f"Error: {str(e)}"
    
    def list_visible_windows(self) -> List[Tuple[str, int]]:
        """
        List all visible windows with their handles.
        
        Returns:
            List of (title, hwnd) tuples
        """
        windows = []
        
        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # Only include windows with titles
                    windows.append((title, hwnd))
            return True
        
        try:
            win32gui.EnumWindows(callback, None)
            return windows
        except Exception as e:
            logger.error(f"Error listing windows: {e}")
            return []
    
    def get_window_state(self, identifier: str) -> str:
        """
        Get the current state of a window (minimized, maximized, normal, hidden).
        
        Args:
            identifier: Window title or process name
            
        Returns:
            Window state description
        """
        try:
            hwnd = self._find_window(identifier)
            
            if not hwnd:
                return f"Could not find window: {identifier}"
            
            placement = win32gui.GetWindowPlacement(hwnd)
            state = placement[1]
            
            state_map = {
                win32con.SW_SHOWMINIMIZED: "minimized",
                win32con.SW_SHOWMAXIMIZED: "maximized",
                win32con.SW_SHOWNORMAL: "normal",
                win32con.SW_HIDE: "hidden"
            }
            
            window_title = win32gui.GetWindowText(hwnd)
            state_name = state_map.get(state, "unknown")
            
            return f"{window_title} is {state_name}"
            
        except Exception as e:
            logger.error(f"Error getting window state: {e}")
            return f"Failed to get state for {identifier}: {str(e)}"
    
    def window_exists(self, identifier: str) -> bool:
        """
        Check if a window exists (visible or hidden).
        
        Args:
            identifier: Window title, process name, or friendly app name
            
        Returns:
            True if window exists, False otherwise
        """
        try:
            hwnd = self._find_window(identifier, include_hidden=True)
            return hwnd is not None
        except Exception as e:
            logger.error(f"Error checking window existence: {e}")
            return False
    
    def get_active_window_info(self) -> Optional[Tuple[int, str, str]]:
        """
        Get information about the currently active/foreground window.
        
        Returns:
            Tuple of (hwnd, window_title, process_name) or None if error
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or hwnd == 0:
                return None
            
            # Get window title
            title = win32gui.GetWindowText(hwnd)
            
            # Get process name
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            process_name = proc.name()
            
            return (hwnd, title, process_name)
        except Exception as e:
            logger.error(f"Error getting active window info: {e}")
            return None
    
    def close_active_window(self) -> str:
        """
        Close the currently active/foreground window.
        Useful for "close this" commands when user opened the app manually.
        
        Returns:
            Result message
        """
        try:
            window_info = self.get_active_window_info()
            if not window_info:
                return "No active window found to close"
            
            hwnd, title, process_name = window_info
            
            # Send WM_CLOSE message to gracefully close the window
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            
            logger.info(f"✅ Closed active window: {title} ({process_name})")
            return f"Closed {title}"
            
        except Exception as e:
            logger.error(f"❌ Error closing active window: {e}")
            return f"Failed to close active window: {str(e)}"
