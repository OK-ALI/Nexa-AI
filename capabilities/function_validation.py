"""
Function Validation Utilities for Nexa Brain
Extracted from brain.py for better modularity and maintainability.

Contains:
- Function call validation (volume, brightness, etc.)
- Error detection and handling
- Parameter range checking
"""

import logging
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger(__name__)


class FunctionValidator:
    """
    Validates function calls before execution.
    Ensures parameters are within valid ranges and operations are safe.
    """
    
    def __init__(self, executor=None, config=None):
        """
        Initialize FunctionValidator.
        
        Args:
            executor: CommandExecutor instance for state checks
            config: Config instance for custom settings
        """
        self.executor = executor
        self.config = config
        
        # Dangerous system processes that should never be closed
        self.dangerous_apps = ['explorer', 'dwm', 'csrss', 'winlogon', 'system', 'svchost']
        
        # Music functions that require active playback
        self.music_requires_playing = [
            'next_song', 'previous_song', 'pause_music', 
            'resume_music', 'stop_music', 'whats_playing'
        ]
        
        # Default error indicators
        self.default_error_indicators = [
            "couldn't find", "could not find", "not found", 
            "failed", "error", "unable to", "can't", "cannot",
            "doesn't exist", "does not exist", "not installed",
            "not running", "is not running", "not available",
            "no such", "invalid", "not recognized",
            "permission denied", "access denied",
            "i don't see", "i couldn't", "i can't",
            "sorry", "unfortunately",
            "try again", "check"
        ]
    
    def validate_function_call(
        self, 
        func_name: str, 
        func_params: Dict[str, Any],
        is_content_mode: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a function call before execution.
        
        Args:
            func_name: Name of the function to call
            func_params: Parameters for the function
            is_content_mode: Whether content mode is active (restricts some functions)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Content mode restrictions
        if is_content_mode:
            restricted_in_content_mode = [
                'shutdown', 'restart', 'sleep', 'lock',
                'close_application', 'force_close'
            ]
            if func_name in restricted_in_content_mode:
                return (False, f"'{func_name}' is not available during content mode")
        # VALIDATION 1: Volume level (0-100)
        if func_name in ['set_volume', 'increase_volume', 'decrease_volume']:
            level = func_params.get('level') or func_params.get('amount')
            if level is not None:
                try:
                    level_int = int(level)
                    if level_int < 0 or level_int > 100:
                        logger.warning(f"⚠️ VALIDATION FAILED: Volume level {level_int} out of range (0-100)")
                        return (False, f"Volume level must be between 0 and 100")
                except (ValueError, TypeError):
                    return (False, f"Invalid volume level: {level}")
        
        # VALIDATION 2: Brightness level (0-100)
        if func_name in ['set_brightness', 'increase_brightness', 'decrease_brightness']:
            level = func_params.get('level') or func_params.get('amount')
            if level is not None:
                try:
                    level_int = int(level)
                    if level_int < 0 or level_int > 100:
                        logger.warning(f"⚠️ VALIDATION FAILED: Brightness level {level_int} out of range (0-100)")
                        return (False, f"Brightness level must be between 0 and 100")
                except (ValueError, TypeError):
                    return (False, f"Invalid brightness level: {level}")
        
        # VALIDATION 3: Prevent dangerous operations
        if func_name == 'close_application':
            app_name = func_params.get('app_name', '').lower()
            if any(dangerous in app_name for dangerous in self.dangerous_apps):
                logger.warning(f"⚠️ VALIDATION FAILED: Attempt to close critical system process '{app_name}'")
                return (False, f"I cannot close '{app_name}' as it's a critical system process")
        
        # VALIDATION 4: Music playback state
        if func_name in self.music_requires_playing and self.executor:
            validation_result = self._validate_music_operation(func_name)
            if validation_result:
                return validation_result
        
        # VALIDATION 5: Shutdown delay validation
        if func_name in ['system_shutdown', 'system_restart', 'schedule_shutdown', 'schedule_restart']:
            delay = func_params.get('delay_seconds') or func_params.get('minutes')
            if delay is not None:
                try:
                    delay_val = int(delay)
                    if delay_val < 0:
                        return (False, "Delay cannot be negative")
                    if delay_val > 86400:  # 24 hours
                        return (False, "Delay cannot exceed 24 hours")
                except (ValueError, TypeError):
                    return (False, f"Invalid delay value: {delay}")
        
        # All validations passed
        logger.debug(f"✅ VALIDATION PASSED: {func_name} with params {func_params}")
        return (True, None)
    
    def _validate_music_operation(self, func_name: str) -> Optional[Tuple[bool, str]]:
        """
        Validate music operations require correct playback state.
        
        Args:
            func_name: Music function to validate
            
        Returns:
            Tuple of (False, error_message) if invalid, None if valid
        """
        if not hasattr(self.executor, 'music_manager'):
            return None
        
        music_manager = self.executor.music_manager
        is_playing = music_manager.is_playing
        
        # Special case: resume_music requires music to be paused
        if func_name == 'resume_music':
            is_paused = music_manager.is_paused
            if not is_paused:
                logger.warning(f"⚠️ VALIDATION FAILED: Music is not paused, cannot resume")
                return (False, "Music is not paused. It's either playing or stopped.")
        
        # All other music operations require music to be playing
        elif not is_playing:
            logger.warning(f"⚠️ VALIDATION FAILED: {func_name} requires music to be playing")
            
            if func_name == 'whats_playing':
                return (False, "No music is currently playing. Would you like me to play something?")
            elif func_name in ['next_song', 'previous_song']:
                return (False, "No music is currently playing. Say 'play music' to start playback first.")
            elif func_name == 'pause_music':
                return (False, "There's no music playing to pause")
            elif func_name == 'stop_music':
                return (False, "There's no music playing to stop")
            else:
                return (False, f"Music is not currently playing")
        
        return None
    
    def get_error_indicators(self) -> List[str]:
        """
        Get list of error indicator phrases.
        
        Returns:
            List[str]: Error indicator phrases
        """
        # Check if config has custom error indicators
        if self.config and hasattr(self.config, 'error_indicators'):
            custom_indicators = getattr(self.config, 'error_indicators', [])
            if custom_indicators:
                logger.debug(f"✅ Loaded {len(custom_indicators)} custom error indicators from config")
                return custom_indicators
        
        return self.default_error_indicators
    
    def is_error_result(self, result: Any) -> bool:
        """
        Determine if a function result indicates an error.
        
        Args:
            result: Result from function execution
            
        Returns:
            bool: True if result indicates an error
        """
        if result is None:
            return True
        
        if isinstance(result, bool) and not result:
            return True
        
        result_str = str(result).lower()
        error_indicators = self.get_error_indicators()
        
        return any(indicator in result_str for indicator in error_indicators)
    
    def is_information_function(self, func_name: str) -> bool:
        """
        Check if a function is an information/query function (doesn't modify state).
        
        Args:
            func_name: Name of the function
            
        Returns:
            bool: True if function is informational
        """
        info_functions = [
            'get_current_time', 'get_current_date', 
            'get_battery_status', 'get_battery_percentage',
            'get_current_volume', 'get_current_brightness',
            'get_weather', 'get_forecast',
            'get_wifi_status', 'list_wifi_networks',
            'get_running_applications', 'get_installed_applications',
            'is_application_running', 'get_active_window',
            'list_games', 'list_music', 'list_music_library', 'whats_playing',
            'music_library_stats', 'get_playback_mode',
            'get_gpu_usage', 'get_power_plan', 'list_power_plans',
            'get_bluetooth_status', 'list_bluetooth_devices',
            'read_notifications', 'read_screen_content', 'describe_screen',
            'what_do_you_know', 'get_memory_stats',
            'play_music',  # Returns question prompt when no song specified
        ]
        
        return func_name in info_functions
    
    def get_function_category(self, func_name: str) -> str:
        """
        Get the category of a function for grouping/logging.
        
        Args:
            func_name: Name of the function
            
        Returns:
            str: Category name
        """
        categories = {
            'system': ['get_current_time', 'get_current_date', 'get_battery_status', 
                       'get_battery_percentage', 'get_gpu_usage', 'lock_screen',
                       'system_sleep', 'system_hibernate', 'system_restart', 
                       'system_shutdown', 'schedule_shutdown', 'schedule_restart',
                       'cancel_shutdown', 'get_power_plan', 'list_power_plans', 'set_power_plan',
                       'enable_battery_saver', 'disable_battery_saver'],
            'volume': ['set_volume', 'get_current_volume', 'increase_volume', 
                       'decrease_volume', 'mute_volume', 'unmute_volume'],
            'brightness': ['set_brightness', 'get_current_brightness', 
                          'increase_brightness', 'decrease_brightness'],
            'apps': ['open_application', 'close_application', 'close_active_window',
                    'get_running_applications', 'get_installed_applications', 
                    'is_application_running', 'refresh_installed_apps', 'exit_nexa'],
            'window': ['minimize_window', 'maximize_window', 'restore_window', 'get_active_window'],
            'wifi': ['get_wifi_status', 'disconnect_wifi', 'connect_wifi', 
                    'list_wifi_networks', 'get_saved_wifi_profiles'],
            'bluetooth': ['get_bluetooth_status', 'list_bluetooth_devices', 
                         'open_bluetooth_settings', 'enable_bluetooth', 'disable_bluetooth'],
            'music': ['play_music', 'play_random_music', 'pause_music', 'resume_music',
                     'stop_music', 'next_song', 'previous_song', 'whats_playing',
                     'list_music', 'music_library_stats', 'suggest_music',
                     'enable_shuffle', 'disable_shuffle', 'set_repeat_mode', 
                     'get_playback_mode', 'play_all_library'],
            'games': ['launch_game', 'list_games', 'open_folder', 'find_folder'],
            'weather': ['get_weather', 'get_forecast'],
            'web': ['search_web'],
            'screenshot': ['take_screenshot', 'take_screenshot_clipboard', 'open_screenshots_folder'],
            'clipboard': ['select_all_text', 'copy_selected_text', 'paste_clipboard', 
                         'cut_selected_text', 'delete_selected_text', 'copy_file_to_clipboard'],
            'content': ['enter_content_mode', 'exit_content_mode', 'mark_content_ready',
                       'refine_text', 'create_pdf', 'format_bold', 'format_italic',
                       'format_underline', 'format_align', 'set_font', 'set_font_size',
                       'increase_font_size', 'decrease_font_size', 'create_bullet_list',
                       'create_numbered_list', 'increase_indent', 'decrease_indent', 'clear_formatting'],
            'sharing': ['share_file', 'share_to_whatsapp', 'share_to_phone', 
                       'share_via_phone_link', 'upload_to_drive'],
            'theme': ['switch_theme', 'set_dark_theme', 'set_light_theme'],
            'memory': ['remember_this', 'forget_about', 'what_do_you_know', 
                      'get_memory_stats', 'show_memory_panel'],
            'settings': ['toggle_airplane_mode', 'enable_night_light', 'disable_night_light',
                        'toggle_night_light', 'open_accessibility_settings', 'open_display_project',
                        'open_cast_settings', 'open_nearby_share', 'check_windows_update', 
                        'open_focus_assist']
        }
        
        for category, functions in categories.items():
            if func_name in functions:
                return category
        
        return 'other'


# Singleton instance
_function_validator = None

def get_function_validator(executor=None, config=None) -> FunctionValidator:
    """Get or create singleton FunctionValidator instance."""
    global _function_validator
    if _function_validator is None:
        _function_validator = FunctionValidator(executor, config)
    elif executor is not None:
        _function_validator.executor = executor
    if config is not None:
        _function_validator.config = config
    return _function_validator
