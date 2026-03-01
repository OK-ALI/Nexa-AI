"""
System Info Controller - System Information and Status

Handles system information queries including:
- Time and date
- Battery status
- GPU usage
- System information (CPU, RAM, Disk, OS)
"""

import logging
import platform
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Try to import psutil for detailed system info
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("⚠️ psutil not available - limited system info")


class SystemInfoController:
    """
    Controller for system information operations.
    
    Handles:
    - Current time and date
    - Battery status
    - GPU usage
    - System specifications
    """
    
    def __init__(self, battery_manager=None, gpu_monitor=None):
        """
        Initialize System Info Controller.
        
        Args:
            battery_manager: BatteryManager instance
            gpu_monitor: GPUMonitor instance
        """
        self.battery_manager = battery_manager
        self.gpu_monitor = gpu_monitor
        
        logger.info("ℹ️ System Info Controller initialized")
    
    # =========================================================================
    # Time and Date
    # =========================================================================
    
    def get_current_time(self) -> str:
        """
        Get current time in natural language.
        
        Returns:
            Time string (time only, no date - natural formatting without zeros)
        """
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # Determine AM/PM
        period = "AM" if hour < 12 else "PM"
        
        # Convert to 12-hour format
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        
        # Format naturally without leading zeros
        if minute == 0:
            return f"It's {display_hour} {period}"
        else:
            return f"It's {display_hour}:{minute:02d} {period}"
    
    def get_current_date(self) -> str:
        """
        Get current date in natural language.
        
        Returns:
            Date string (date only, no time)
        """
        now = datetime.now()
        return f"Today is {now.strftime('%A, %B %d, %Y')}"
    
    def get_datetime(self) -> str:
        """
        Get current date and time together.
        
        Returns:
            Combined date and time string
        """
        return f"{self.get_current_date()}. {self.get_current_time()}"
    
    # =========================================================================
    # Battery Status
    # =========================================================================
    
    def get_battery_status(self) -> str:
        """
        Get comprehensive battery status.
        
        Returns:
            Battery status message
        """
        if not self.battery_manager:
            return "Battery monitoring not available"
        
        logger.info("Getting battery status")
        return self.battery_manager.get_simple_status()
    
    def get_battery_percentage(self) -> int:
        """
        Get battery percentage only.
        
        Returns:
            Battery percentage (0-100)
        """
        if not self.battery_manager:
            return 0
        return self.battery_manager.get_battery_percentage()
    
    def is_battery_charging(self) -> bool:
        """
        Check if battery is charging.
        
        Returns:
            True if charging, False otherwise
        """
        if not self.battery_manager:
            return False
        return self.battery_manager.is_charging()
    
    def get_battery_time_remaining(self) -> str:
        """
        Get battery time remaining.
        
        Returns:
            Time remaining message
        """
        if not self.battery_manager:
            return "Battery monitoring not available"
        
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
    
    # =========================================================================
    # GPU Usage
    # =========================================================================
    
    def get_gpu_usage(self) -> Dict[str, Any]:
        """
        Get current GPU usage and memory statistics.
        
        Returns:
            Dict with 'success', 'usage_percent', 'used_gb', 'total_gb', 'status' keys
        """
        logger.info("Getting GPU usage")
        
        if self.gpu_monitor is None:
            return {
                'success': False,
                'message': "GPU monitoring is not available on this system"
            }
        
        usage = self.gpu_monitor.get_current_usage()
        
        if usage is None:
            return {
                'success': False,
                'message': "Unable to retrieve GPU usage. Make sure you have an NVIDIA GPU and drivers installed"
            }
        
        used_mb, total_mb, usage_percent = usage
        used_gb = used_mb / 1024
        total_gb = total_mb / 1024
        
        # Determine status
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
        
        return {
            'success': True,
            'usage_percent': usage_percent,
            'used_gb': used_gb,
            'total_gb': total_gb,
            'status': status
        }
    
    def get_gpu_usage_message(self) -> str:
        """
        Get GPU usage as a natural language message.
        
        Returns:
            GPU usage message with VRAM info
        """
        result = self.get_gpu_usage()
        
        if not result.get('success'):
            return result.get('message', "GPU information not available")
        
        return (f"GPU memory usage is {result['status']} at {result['usage_percent']:.1f}%. "
                f"Using {result['used_gb']:.1f} GB out of {result['total_gb']:.1f} GB total VRAM")
    
    # =========================================================================
    # System Information
    # =========================================================================
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get comprehensive system information.
        
        Returns:
            Dict with OS, CPU, RAM, Disk, and GPU info
        """
        info = {
            'os': f"{platform.system()} {platform.release()}",
            'os_version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
        }
        
        # Add detailed info if psutil available
        if PSUTIL_AVAILABLE:
            try:
                # CPU info
                cpu_count = psutil.cpu_count(logical=True)
                cpu_physical = psutil.cpu_count(logical=False)
                cpu_percent = psutil.cpu_percent(interval=0.1)
                info['cpu_cores'] = f"{cpu_physical} physical, {cpu_count} logical"
                info['cpu_usage'] = f"{cpu_percent}%"
                
                # RAM info
                mem = psutil.virtual_memory()
                total_gb = mem.total / (1024**3)
                used_gb = mem.used / (1024**3)
                available_gb = mem.available / (1024**3)
                info['ram_total'] = f"{total_gb:.1f} GB"
                info['ram_used'] = f"{used_gb:.1f} GB ({mem.percent}%)"
                info['ram_available'] = f"{available_gb:.1f} GB"
                
                # Disk info (main drive - Windows uses C:, others use /)
                disk_path = 'C:\\' if platform.system() == 'Windows' else '/'
                disk = psutil.disk_usage(disk_path)
                disk_total = disk.total / (1024**3)
                disk_used = disk.used / (1024**3)
                disk_free = disk.free / (1024**3)
                info['disk_total'] = f"{disk_total:.0f} GB"
                info['disk_used'] = f"{disk_used:.0f} GB ({disk.percent}%)"
                info['disk_free'] = f"{disk_free:.0f} GB"
                
            except Exception as e:
                logger.warning(f"⚠️ Error getting detailed system info: {e}")
        
        # Add GPU info if available
        if self.gpu_monitor:
            try:
                gpu_info = self.get_gpu_usage()
                info['gpu_name'] = gpu_info.get('name', 'Unknown')
                info['gpu_vram'] = f"{gpu_info.get('total_gb', 0):.1f} GB"
                info['gpu_usage'] = f"{gpu_info.get('usage_percent', 0):.1f}%"
            except Exception:
                pass
        
        return info
    
    def get_system_info_message(self) -> str:
        """
        Get system information as a natural language response.
        
        Returns:
            Formatted system info string for voice response
        """
        info = self.get_system_info()
        
        # Build natural language response
        parts = []
        
        # OS
        parts.append(f"You're running {info.get('os', 'Unknown OS')}")
        
        # CPU
        if 'cpu_cores' in info:
            parts.append(f"Your processor has {info['cpu_cores']} cores")
            if 'cpu_usage' in info:
                parts.append(f"currently at {info['cpu_usage']} usage")
        elif info.get('processor'):
            parts.append(f"with a {info['processor']} processor")
        
        # RAM
        if 'ram_total' in info:
            parts.append(f"You have {info['ram_total']} of RAM")
            if 'ram_used' in info:
                parts.append(f"using {info['ram_used']}")
        
        # Disk
        if 'disk_total' in info:
            parts.append(f"Your main drive has {info['disk_total']} total with {info['disk_free']} free")
        
        # GPU
        if 'gpu_name' in info:
            parts.append(f"Your GPU is a {info['gpu_name']} with {info.get('gpu_vram', 'unknown')} VRAM")
        
        return ". ".join(parts) + "."
    
    def get_pc_specs(self) -> str:
        """
        Alias for get_system_info_message - for natural language queries.
        
        Returns:
            System specs as natural language
        """
        return self.get_system_info_message()


# Singleton instance for easy access
_controller_instance: Optional[SystemInfoController] = None


def get_system_info_controller(battery_manager=None, gpu_monitor=None) -> SystemInfoController:
    """
    Get or create the singleton SystemInfoController instance.
    
    Args:
        battery_manager: BatteryManager instance
        gpu_monitor: GPUMonitor instance
        
    Returns:
        SystemInfoController instance
    """
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = SystemInfoController(
            battery_manager=battery_manager,
            gpu_monitor=gpu_monitor
        )
    return _controller_instance
