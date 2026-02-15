"""
System Control Module for Nexa AI Assistant

Phase 16: System Control Expansion
Provides Windows system control functions including:
- Power Management (sleep, hibernate, shutdown, restart)
- Power Plans (balanced, high performance, power saver)
- Battery Saver mode
- Bluetooth management
- Quick Settings (airplane mode, night light, etc.)

This module was extracted from executor.py for better organization.
"""

import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SystemControl:
    """
    Windows system control functions.
    Handles power management, power plans, bluetooth, and quick settings.
    """
    
    def __init__(self):
        """Initialize system control module."""
        logger.info("SystemControl module initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTEM POWER CONTROL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def lock_screen(self) -> str:
        """
        Lock the Windows workstation.
        Voice commands: "lock screen", "lock computer", "lock my PC"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🔒 Locking screen...")
            result = subprocess.run(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return "Screen locked."
            else:
                return "Failed to lock screen."
        except Exception as e:
            logger.error(f"Lock screen error: {e}")
            return f"Could not lock screen: {str(e)}"
    
    def system_sleep(self) -> str:
        """
        Put the computer to sleep.
        Voice commands: "sleep", "put computer to sleep", "go to sleep"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("💤 Putting system to sleep...")
            result = subprocess.run(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "Putting computer to sleep..."
        except Exception as e:
            logger.error(f"Sleep error: {e}")
            return f"Could not put system to sleep: {str(e)}"
    
    def system_hibernate(self) -> str:
        """
        Hibernate the computer (saves state to disk).
        Voice commands: "hibernate", "hibernate computer"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🛏️ Hibernating system...")
            result = subprocess.run(
                ["shutdown", "/h"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return "Hibernating computer..."
            else:
                return "Hibernation failed. It may not be enabled on this system."
        except Exception as e:
            logger.error(f"Hibernate error: {e}")
            return f"Could not hibernate: {str(e)}"
    
    def system_restart(self, delay_seconds: int = 0) -> str:
        """
        Restart the computer.
        Voice commands: "restart", "restart computer", "reboot"
        
        Args:
            delay_seconds: Seconds to wait before restart (0 = immediate)
            
        Returns:
            str: Confirmation message
        """
        try:
            logger.info(f"🔄 Scheduling system restart in {delay_seconds} seconds...")
            result = subprocess.run(
                ["shutdown", "/r", "/t", str(delay_seconds)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                if delay_seconds > 0:
                    return f"Computer will restart in {delay_seconds} seconds. Say 'cancel shutdown' to abort."
                else:
                    return "Restarting computer now..."
            else:
                return f"Restart failed: {result.stderr}"
        except Exception as e:
            logger.error(f"Restart error: {e}")
            return f"Could not restart: {str(e)}"
    
    def system_shutdown(self, delay_seconds: int = 0) -> str:
        """
        Shutdown the computer.
        Voice commands: "shutdown computer", "turn off computer", "power off"
        
        Args:
            delay_seconds: Seconds to wait before shutdown (0 = immediate)
            
        Returns:
            str: Confirmation message
        """
        try:
            logger.info(f"⏻ Scheduling system shutdown in {delay_seconds} seconds...")
            result = subprocess.run(
                ["shutdown", "/s", "/t", str(delay_seconds)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                if delay_seconds > 0:
                    return f"Computer will shutdown in {delay_seconds} seconds. Say 'cancel shutdown' to abort."
                else:
                    return "Shutting down computer now..."
            else:
                return f"Shutdown failed: {result.stderr}"
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            return f"Could not shutdown: {str(e)}"
    
    def schedule_shutdown(self, minutes: int = 30) -> str:
        """
        Schedule a shutdown after specified minutes.
        Voice commands: "shutdown in 30 minutes", "schedule shutdown", "turn off in an hour"
        
        Args:
            minutes: Minutes until shutdown (default 30)
            
        Returns:
            str: Confirmation message
        """
        try:
            seconds = minutes * 60
            logger.info(f"⏰ Scheduling shutdown in {minutes} minutes ({seconds} seconds)...")
            result = subprocess.run(
                ["shutdown", "/s", "/t", str(seconds)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return f"Computer will shutdown in {minutes} minutes. Say 'cancel shutdown' to abort."
            else:
                return f"Could not schedule shutdown: {result.stderr}"
        except Exception as e:
            logger.error(f"Schedule shutdown error: {e}")
            return f"Could not schedule shutdown: {str(e)}"
    
    def schedule_restart(self, minutes: int = 5) -> str:
        """
        Schedule a restart after specified minutes.
        Voice commands: "restart in 5 minutes", "schedule restart", "reboot in 10 minutes"
        
        Args:
            minutes: Minutes until restart (default 5)
            
        Returns:
            str: Confirmation message
        """
        try:
            seconds = minutes * 60
            logger.info(f"⏰ Scheduling restart in {minutes} minutes ({seconds} seconds)...")
            result = subprocess.run(
                ["shutdown", "/r", "/t", str(seconds)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return f"Computer will restart in {minutes} minutes. Say 'cancel shutdown' to abort."
            else:
                return f"Could not schedule restart: {result.stderr}"
        except Exception as e:
            logger.error(f"Schedule restart error: {e}")
            return f"Could not schedule restart: {str(e)}"
    
    def cancel_shutdown(self) -> str:
        """
        Cancel a scheduled shutdown or restart.
        Voice commands: "cancel shutdown", "abort shutdown", "stop shutdown", "cancel restart"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("❌ Cancelling scheduled shutdown...")
            result = subprocess.run(
                ["shutdown", "/a"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return "Shutdown cancelled."
            else:
                return "No shutdown was scheduled, or could not cancel."
        except Exception as e:
            logger.error(f"Cancel shutdown error: {e}")
            return f"Could not cancel shutdown: {str(e)}"

    # ═══════════════════════════════════════════════════════════════════════════
    # POWER PLANS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_power_plan(self) -> str:
        """
        Get the current active power plan.
        Voice commands: "what power plan", "current power plan", "power mode"
        
        Returns:
            str: Current power plan name
        """
        try:
            logger.info("⚡ Getting current power plan...")
            result = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                if "(" in output and ")" in output:
                    plan_name = output.split("(")[-1].replace(")", "").strip()
                    return f"Current power plan: {plan_name}"
                return f"Current power plan: {output}"
            else:
                return "Could not get power plan."
        except Exception as e:
            logger.error(f"Get power plan error: {e}")
            return f"Could not get power plan: {str(e)}"
    
    def list_power_plans(self) -> str:
        """
        List all available power plans.
        Voice commands: "list power plans", "show power plans", "available power modes"
        
        Returns:
            str: List of power plans
        """
        try:
            logger.info("📋 Listing power plans...")
            result = subprocess.run(
                ["powercfg", "/list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                plans = []
                for line in lines:
                    if "(" in line and ")" in line:
                        plan_name = line.split("(")[-1].replace(")", "").strip()
                        if "*" in line:
                            plans.append(f"• {plan_name} (active)")
                        else:
                            plans.append(f"• {plan_name}")
                
                if plans:
                    return "Available power plans:\n" + "\n".join(plans)
                return "No power plans found."
            else:
                return "Could not list power plans."
        except Exception as e:
            logger.error(f"List power plans error: {e}")
            return f"Could not list power plans: {str(e)}"
    
    def set_power_plan(self, plan: str) -> str:
        """
        Switch to a different power plan.
        Voice commands: "set power plan to balanced", "high performance mode", "power saver mode"
        
        Args:
            plan: Plan name - 'balanced', 'high_performance', 'power_saver', or 'ultimate'
            
        Returns:
            str: Confirmation message
        """
        try:
            plan_guids = {
                "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
                "high_performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
                "high performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
                "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
                "power saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
                "ultimate": "e9a42b02-d5df-448d-aa00-03f14749eb61",
                "ultimate_performance": "e9a42b02-d5df-448d-aa00-03f14749eb61",
                "ultimate performance": "e9a42b02-d5df-448d-aa00-03f14749eb61",
            }
            
            plan_lower = plan.lower().strip()
            
            if plan_lower in plan_guids:
                guid = plan_guids[plan_lower]
            else:
                guid = plan_lower
            
            logger.info(f"⚡ Setting power plan to: {plan}...")
            result = subprocess.run(
                ["powercfg", "/setactive", guid],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return f"Power plan changed to {plan}."
            else:
                return f"Could not set power plan '{plan}'. Use 'balanced', 'high_performance', 'power_saver', or 'ultimate'."
        except Exception as e:
            logger.error(f"Set power plan error: {e}")
            return f"Could not set power plan: {str(e)}"

    # ═══════════════════════════════════════════════════════════════════════════
    # BATTERY SAVER
    # ═══════════════════════════════════════════════════════════════════════════
    
    def enable_battery_saver(self) -> str:
        """
        Enable battery saver mode.
        Voice commands: "enable battery saver", "turn on battery saver", "save battery"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🔋 Enabling battery saver...")
            # Use PowerShell to enable battery saver
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-WmiObject -Namespace root/wmi -Class BatteryStatus).PowerOnline; " +
                 "powercfg /setdcvalueindex SCHEME_CURRENT SUB_ENERGYSAVER ESBATTTHRESHOLD 100"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Also try the settings URI as fallback
            subprocess.Popen(["start", "ms-settings:batterysaver"], shell=True)
            return "Battery saver settings opened. You can enable it there."
        except Exception as e:
            logger.error(f"Battery saver error: {e}")
            return f"Could not enable battery saver: {str(e)}"
    
    def disable_battery_saver(self) -> str:
        """
        Disable battery saver mode.
        Voice commands: "disable battery saver", "turn off battery saver"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🔋 Disabling battery saver...")
            subprocess.Popen(["start", "ms-settings:batterysaver"], shell=True)
            return "Battery saver settings opened. You can disable it there."
        except Exception as e:
            logger.error(f"Battery saver error: {e}")
            return f"Could not disable battery saver: {str(e)}"

    # ═══════════════════════════════════════════════════════════════════════════
    # BLUETOOTH
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_bluetooth_status(self) -> str:
        """
        Get Bluetooth status (on/off and connected devices).
        Voice commands: "bluetooth status", "is bluetooth on", "bluetooth info"
        
        Returns:
            str: Bluetooth status information
        """
        try:
            logger.info("🔵 Getting Bluetooth status...")
            
            result = subprocess.run(
                ["powershell", "-Command", 
                 "Get-PnpDevice -Class Bluetooth | Where-Object Status -eq 'OK' | Select-Object FriendlyName, Status | Format-List"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                devices = result.stdout.strip()
                return f"Bluetooth is ON.\n\nDevices:\n{devices}"
            else:
                result2 = subprocess.run(
                    ["powershell", "-Command", 
                     "Get-PnpDevice -Class Bluetooth | Select-Object FriendlyName, Status | Format-List"],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                if result2.stdout.strip():
                    return f"Bluetooth adapter found but may be disabled.\n{result2.stdout.strip()}"
                return "No Bluetooth adapter found or Bluetooth is OFF."
        except Exception as e:
            logger.error(f"Bluetooth status error: {e}")
            return f"Could not get Bluetooth status: {str(e)}"
    
    def list_bluetooth_devices(self) -> str:
        """
        List all paired Bluetooth devices.
        Voice commands: "list bluetooth devices", "show paired devices", "bluetooth devices"
        
        Returns:
            str: List of paired Bluetooth devices
        """
        try:
            logger.info("📋 Listing Bluetooth devices...")
            
            result = subprocess.run(
                ["powershell", "-Command", 
                 "Get-PnpDevice -Class Bluetooth | Where-Object Status -eq 'OK' | Select-Object FriendlyName | Format-Table -HideTableHeaders"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                devices = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]
                if devices:
                    device_list = "\n".join([f"• {d}" for d in devices])
                    return f"Paired Bluetooth devices:\n{device_list}"
                return "No Bluetooth devices found."
            else:
                return "No Bluetooth devices found or Bluetooth is OFF."
        except Exception as e:
            logger.error(f"List Bluetooth devices error: {e}")
            return f"Could not list Bluetooth devices: {str(e)}"
    
    def open_bluetooth_settings(self) -> str:
        """
        Open Windows Bluetooth settings.
        Voice commands: "open bluetooth settings", "bluetooth settings", "pair bluetooth",
                       "connect to my earbuds", "connect bluetooth"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("⚙️ Opening Bluetooth settings...")
            subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)
            return "Opening Bluetooth settings. You can pair or connect to devices there."
        except Exception as e:
            logger.error(f"Open Bluetooth settings error: {e}")
            return f"Could not open Bluetooth settings: {str(e)}"
    
    def enable_bluetooth(self) -> str:
        """
        Enable Bluetooth adapter.
        Voice commands: "enable bluetooth", "turn on bluetooth", "bluetooth on"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🔵 Enabling Bluetooth...")
            # Use PowerShell to enable all Bluetooth adapters
            ps_command = '''
            $adapters = Get-PnpDevice -Class Bluetooth | Where-Object { $_.FriendlyName -like "*Bluetooth*" -and $_.Status -eq "Error" }
            if ($adapters) {
                foreach ($adapter in $adapters) {
                    Enable-PnpDevice -InstanceId $adapter.InstanceId -Confirm:$false
                }
                Write-Output "Bluetooth enabled"
            } else {
                # Check if already enabled
                $enabled = Get-PnpDevice -Class Bluetooth | Where-Object { $_.Status -eq "OK" }
                if ($enabled) {
                    Write-Output "Bluetooth already enabled"
                } else {
                    Write-Output "No Bluetooth adapter found"
                }
            }
            '''
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if "enabled" in result.stdout.lower():
                return "Bluetooth enabled."
            elif "already" in result.stdout.lower():
                return "Bluetooth is already on."
            elif "not found" in result.stdout.lower():
                return "No Bluetooth adapter found."
            else:
                # Fallback: open settings
                subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)
                return f"Opening Bluetooth settings. {result.stderr if result.stderr else ''}"
        except Exception as e:
            logger.error(f"Enable Bluetooth error: {e}")
            subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)
            return f"Opening Bluetooth settings. Error: {str(e)}"
    
    def disable_bluetooth(self) -> str:
        """
        Disable Bluetooth adapter.
        Voice commands: "disable bluetooth", "turn off bluetooth", "bluetooth off"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🔵 Disabling Bluetooth...")
            # Use PowerShell to disable all Bluetooth adapters
            ps_command = '''
            $adapters = Get-PnpDevice -Class Bluetooth | Where-Object { $_.FriendlyName -like "*Bluetooth*" -and $_.Status -eq "OK" }
            if ($adapters) {
                foreach ($adapter in $adapters) {
                    Disable-PnpDevice -InstanceId $adapter.InstanceId -Confirm:$false
                }
                Write-Output "Bluetooth disabled"
            } else {
                # Check if already disabled
                $disabled = Get-PnpDevice -Class Bluetooth | Where-Object { $_.Status -eq "Error" }
                if ($disabled) {
                    Write-Output "Bluetooth already disabled"
                } else {
                    Write-Output "No Bluetooth adapter found"
                }
            }
            '''
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if "disabled" in result.stdout.lower():
                return "Bluetooth disabled."
            elif "already" in result.stdout.lower():
                return "Bluetooth is already off."
            elif "not found" in result.stdout.lower():
                return "No Bluetooth adapter found."
            else:
                # Fallback: open settings
                subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)
                return f"Opening Bluetooth settings. {result.stderr if result.stderr else ''}"
        except Exception as e:
            logger.error(f"Disable Bluetooth error: {e}")
            subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)
            return f"Opening Bluetooth settings. Error: {str(e)}"

    # ═══════════════════════════════════════════════════════════════════════════
    # QUICK SETTINGS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def toggle_airplane_mode(self) -> str:
        """
        Open airplane mode settings.
        Voice commands: "airplane mode", "flight mode", "toggle airplane mode"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("✈️ Opening airplane mode settings...")
            subprocess.Popen(["start", "ms-settings:network-airplanemode"], shell=True)
            return "Opening airplane mode settings."
        except Exception as e:
            logger.error(f"Airplane mode error: {e}")
            return f"Could not open airplane mode settings: {str(e)}"
    
    def enable_night_light(self) -> str:
        """
        Enable Night Light (blue light filter).
        Voice commands: "enable night light", "turn on night light", "blue light filter on"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🌙 Enabling Night Light...")
            # Use PowerShell to enable Night Light via registry
            ps_command = '''
            $path = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\CloudStore\\Store\\DefaultAccount\\Current\\default`$windows.data.bluelightreduction.bluelightreductionstate\\windows.data.bluelightreduction.bluelightreductionstate"
            if (Test-Path $path) {
                $data = (Get-ItemProperty -Path $path).Data
                if ($data -ne $null -and $data.Length -ge 24) {
                    $data[18] = 0x15
                    $data[23] = 0x10
                    Set-ItemProperty -Path $path -Name "Data" -Value $data
                    Write-Output "Night Light enabled"
                } else {
                    Write-Output "Registry data format unexpected"
                }
            } else {
                Write-Output "Night Light registry key not found"
            }
            '''
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "enabled" in result.stdout.lower():
                return "Night Light enabled. Your screen will now have a warmer color."
            else:
                # Fallback: open settings
                subprocess.Popen(["start", "ms-settings:nightlight"], shell=True)
                return "Could not toggle Night Light directly. Opening settings..."
        except Exception as e:
            logger.error(f"Night Light enable error: {e}")
            subprocess.Popen(["start", "ms-settings:nightlight"], shell=True)
            return f"Opening Night Light settings. Error: {str(e)}"
    
    def disable_night_light(self) -> str:
        """
        Disable Night Light (blue light filter).
        Voice commands: "disable night light", "turn off night light", "night light off"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🌙 Disabling Night Light...")
            # Use PowerShell to disable Night Light via registry
            ps_command = '''
            $path = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\CloudStore\\Store\\DefaultAccount\\Current\\default`$windows.data.bluelightreduction.bluelightreductionstate\\windows.data.bluelightreduction.bluelightreductionstate"
            if (Test-Path $path) {
                $data = (Get-ItemProperty -Path $path).Data
                if ($data -ne $null -and $data.Length -ge 24) {
                    $data[18] = 0x13
                    $data[23] = 0x10
                    Set-ItemProperty -Path $path -Name "Data" -Value $data
                    Write-Output "Night Light disabled"
                } else {
                    Write-Output "Registry data format unexpected"
                }
            } else {
                Write-Output "Night Light registry key not found"
            }
            '''
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "disabled" in result.stdout.lower():
                return "Night Light disabled. Screen color is back to normal."
            else:
                # Fallback: open settings
                subprocess.Popen(["start", "ms-settings:nightlight"], shell=True)
                return "Could not toggle Night Light directly. Opening settings..."
        except Exception as e:
            logger.error(f"Night Light disable error: {e}")
            subprocess.Popen(["start", "ms-settings:nightlight"], shell=True)
            return f"Opening Night Light settings. Error: {str(e)}"
    
    def toggle_night_light(self) -> str:
        """
        Open night light settings (for manual toggle).
        Voice commands: "night light settings"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🌙 Opening night light settings...")
            subprocess.Popen(["start", "ms-settings:nightlight"], shell=True)
            return "Opening night light settings."
        except Exception as e:
            logger.error(f"Night light error: {e}")
            return f"Could not open night light settings: {str(e)}"
    
    def open_accessibility_settings(self) -> str:
        """
        Open Windows accessibility settings.
        Voice commands: "accessibility settings", "ease of access", "accessibility"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("♿ Opening accessibility settings...")
            subprocess.Popen(["start", "ms-settings:easeofaccess"], shell=True)
            return "Opening accessibility settings."
        except Exception as e:
            logger.error(f"Accessibility settings error: {e}")
            return f"Could not open accessibility settings: {str(e)}"
    
    def open_display_project(self) -> str:
        """
        Open display project settings (extend, duplicate, second screen).
        Voice commands: "project settings", "extend display", "duplicate screen", "second screen"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🖥️ Opening display project settings...")
            subprocess.Popen(["start", "ms-settings:project"], shell=True)
            return "Opening display project settings."
        except Exception as e:
            logger.error(f"Display project error: {e}")
            return f"Could not open display project settings: {str(e)}"
    
    def open_cast_settings(self) -> str:
        """
        Open cast/connect settings for wireless displays.
        Voice commands: "cast settings", "connect to TV", "wireless display", "miracast"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("📺 Opening cast settings...")
            subprocess.Popen(["start", "ms-settings:connecteddevices"], shell=True)
            return "Opening cast and connected devices settings."
        except Exception as e:
            logger.error(f"Cast settings error: {e}")
            return f"Could not open cast settings: {str(e)}"
    
    def open_nearby_share(self) -> str:
        """
        Open nearby sharing settings.
        Voice commands: "nearby share", "nearby sharing", "share nearby"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("📱 Opening nearby sharing settings...")
            subprocess.Popen(["start", "ms-settings:crossdevice"], shell=True)
            return "Opening nearby sharing settings."
        except Exception as e:
            logger.error(f"Nearby share error: {e}")
            return f"Could not open nearby sharing settings: {str(e)}"
    
    def check_windows_update(self) -> str:
        """
        Open Windows Update to check for updates.
        Voice commands: "check for updates", "windows update", "update windows", "check updates"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🔄 Opening Windows Update...")
            subprocess.Popen(["start", "ms-settings:windowsupdate"], shell=True)
            return "Opening Windows Update. Checking for updates..."
        except Exception as e:
            logger.error(f"Windows Update error: {e}")
            return f"Could not open Windows Update: {str(e)}"
    
    def open_focus_assist(self) -> str:
        """
        Open focus assist / do not disturb settings.
        Voice commands: "focus assist", "do not disturb", "quiet hours", "focus mode"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🔕 Opening focus assist settings...")
            subprocess.Popen(["start", "ms-settings:quiethours"], shell=True)
            return "Opening focus assist settings."
        except Exception as e:
            logger.error(f"Focus assist error: {e}")
            return f"Could not open focus assist settings: {str(e)}"
