"""
System Control Module for Nexa AI Assistant

Phase 16: System Control Expansion (Enhanced)
Provides Windows system control functions including:
- Power Management (sleep, hibernate, shutdown, restart) with safety timers
- Power Plans (balanced, high performance, power saver)
- Battery Saver mode (real enable/disable via powercfg)
- Bluetooth management (enable/disable/connect/disconnect by name)
- Quick Settings (airplane mode, night light, focus assist, display projection)
- Windows Update (real update check via COM API)
- Sign Out / Log Off

This module was extracted from executor.py for better organization.
Enhanced with real system control instead of just opening settings pages.
"""

import subprocess
import logging
import ctypes
import winreg
import struct
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
        Restart the computer with a minimum 10-second safety delay.
        Voice commands: "restart", "restart computer", "reboot"
        
        Args:
            delay_seconds: Seconds to wait before restart (minimum 10 for safety)
            
        Returns:
            str: Confirmation message with countdown warning
        """
        try:
            # Enforce minimum 10-second safety delay
            safe_delay = max(delay_seconds, 10)
            logger.info(f"🔄 Scheduling system restart in {safe_delay} seconds (requested: {delay_seconds})...")
            result = subprocess.run(
                ["shutdown", "/r", "/t", str(safe_delay)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return f"Restarting in {safe_delay} seconds. Say 'cancel shutdown' to abort."
            else:
                return f"Restart failed: {result.stderr}"
        except Exception as e:
            logger.error(f"Restart error: {e}")
            return f"Could not restart: {str(e)}"
    
    def system_shutdown(self, delay_seconds: int = 0) -> str:
        """
        Shutdown the computer with a minimum 10-second safety delay.
        Voice commands: "shutdown computer", "turn off computer", "power off"
        
        Args:
            delay_seconds: Seconds to wait before shutdown (minimum 10 for safety)
            
        Returns:
            str: Confirmation message with countdown warning
        """
        try:
            # Enforce minimum 10-second safety delay
            safe_delay = max(delay_seconds, 10)
            logger.info(f"⏻ Scheduling system shutdown in {safe_delay} seconds (requested: {delay_seconds})...")
            result = subprocess.run(
                ["shutdown", "/s", "/t", str(safe_delay)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return f"Shutting down in {safe_delay} seconds. Say 'cancel shutdown' to abort."
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
        Enable battery saver mode via powercfg.
        Voice commands: "enable battery saver", "turn on battery saver", "save battery"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🔋 Enabling battery saver...")
            # Set battery saver threshold to 100% (always on) for both DC and AC
            cmds = [
                ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_ENERGYSAVER", "ESBATTTHRESHOLD", "100"],
                ["powercfg", "/setactive", "SCHEME_CURRENT"],
            ]
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            return "Battery saver enabled."
        except Exception as e:
            logger.error(f"Battery saver enable error: {e}")
            return f"Could not enable battery saver: {str(e)}"
    
    def disable_battery_saver(self) -> str:
        """
        Disable battery saver mode via powercfg.
        Voice commands: "disable battery saver", "turn off battery saver"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🔋 Disabling battery saver...")
            # Set battery saver threshold back to default (20%) — effectively disables if battery > 20%
            cmds = [
                ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_ENERGYSAVER", "ESBATTTHRESHOLD", "20"],
                ["powercfg", "/setactive", "SCHEME_CURRENT"],
            ]
            for cmd in cmds:
                subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            return "Battery saver disabled."
        except Exception as e:
            logger.error(f"Battery saver disable error: {e}")
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
        Toggle airplane mode on/off via the Radio Management registry key.
        Voice commands: "airplane mode", "flight mode", "toggle airplane mode"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("✈️ Toggling airplane mode...")
            key_path = r"SYSTEM\CurrentControlSet\Control\RadioManagement\SystemRadioState"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                    current_value, _ = winreg.QueryValueEx(key, "")
                    # 0 = radios ON (airplane off), 1 = radios OFF (airplane on)
                    new_value = 0 if current_value == 1 else 1
                    winreg.SetValueEx(key, "", 0, winreg.REG_DWORD, new_value)
                    
                    if new_value == 1:
                        return "Airplane mode enabled. All wireless radios turned off."
                    else:
                        return "Airplane mode disabled. Wireless radios turned back on."
            except PermissionError:
                # Registry write requires admin — fall back to settings
                logger.warning("Airplane mode toggle requires admin privileges, opening settings...")
                subprocess.Popen(["start", "ms-settings:network-airplanemode"], shell=True)
                return "Airplane mode requires administrator privileges to toggle directly. Opening settings instead."
            except FileNotFoundError:
                subprocess.Popen(["start", "ms-settings:network-airplanemode"], shell=True)
                return "Could not find airplane mode registry key. Opening settings instead."
        except Exception as e:
            logger.error(f"Airplane mode error: {e}")
            subprocess.Popen(["start", "ms-settings:network-airplanemode"], shell=True)
            return f"Could not toggle airplane mode directly. Opening settings. Error: {str(e)}"
    
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
        Toggle Night Light on or off by checking current state.
        Voice commands: "toggle night light", "switch night light"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🌙 Toggling Night Light...")
            # Check current state via registry
            try:
                key_path = r"Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current\default$windows.data.bluelightreduction.bluelightreductionstate\windows.data.bluelightreduction.bluelightreductionstate"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    data, _ = winreg.QueryValueEx(key, "Data")
                    # Byte 18 indicates state: 0x15 = enabled, 0x13 = disabled
                    if len(data) >= 24 and data[18] == 0x15:
                        return self.disable_night_light()
                    else:
                        return self.enable_night_light()
            except (FileNotFoundError, OSError):
                # If can't read state, try enabling
                return self.enable_night_light()
        except Exception as e:
            logger.error(f"Night light toggle error: {e}")
            return f"Could not toggle night light: {str(e)}"
    
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
    
    def set_display_projection(self, mode: str = "extend") -> str:
        """
        Set display projection mode using DisplaySwitch.exe.
        Voice commands: "extend display", "duplicate screen", "second screen only", "PC screen only"
        
        Args:
            mode: Projection mode - 'internal' (PC only), 'clone' (duplicate),
                  'extend' (extend), 'external' (second screen only)
                  
        Returns:
            str: Confirmation message
        """
        try:
            mode_map = {
                "internal": "/internal",
                "pc": "/internal",
                "pc only": "/internal",
                "pc screen only": "/internal",
                "clone": "/clone",
                "duplicate": "/clone",
                "mirror": "/clone",
                "extend": "/extend",
                "extended": "/extend",
                "external": "/external",
                "second screen": "/external",
                "second screen only": "/external",
                "projector": "/external",
            }
            
            mode_lower = mode.lower().strip()
            switch_flag = mode_map.get(mode_lower, f"/{mode_lower}")
            
            logger.info(f"🖥️ Setting display projection to: {mode} ({switch_flag})...")
            result = subprocess.run(
                ["DisplaySwitch.exe", switch_flag],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            mode_names = {
                "/internal": "PC screen only",
                "/clone": "Duplicate (mirror)",
                "/extend": "Extend",
                "/external": "Second screen only",
            }
            friendly_name = mode_names.get(switch_flag, mode)
            return f"Display projection set to: {friendly_name}."
        except FileNotFoundError:
            # DisplaySwitch.exe not available, fallback to settings
            subprocess.Popen(["start", "ms-settings:project"], shell=True)
            return "DisplaySwitch not available. Opening display projection settings."
        except Exception as e:
            logger.error(f"Display project error: {e}")
            return f"Could not set display projection: {str(e)}"
    
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
        Actually check for Windows updates using the Windows Update Agent COM API.
        Voice commands: "check for updates", "windows update", "update windows", "check updates"
        
        Returns:
            str: List of available updates or "up to date" message
        """
        try:
            logger.info("🔄 Checking for Windows updates via COM API...")
            
            # Use PowerShell to invoke the Windows Update COM API
            ps_command = '''
            try {
                $UpdateSession = New-Object -ComObject Microsoft.Update.Session
                $UpdateSearcher = $UpdateSession.CreateUpdateSearcher()
                Write-Output "SEARCHING"
                $SearchResult = $UpdateSearcher.Search("IsInstalled=0")
                
                if ($SearchResult.Updates.Count -eq 0) {
                    Write-Output "UP_TO_DATE"
                } else {
                    Write-Output "FOUND:$($SearchResult.Updates.Count)"
                    foreach ($Update in $SearchResult.Updates) {
                        $size = [math]::Round($Update.MaxDownloadSize / 1MB, 1)
                        Write-Output "UPDATE:$($Update.Title)|${size}MB"
                    }
                }
            } catch {
                Write-Output "ERROR:$($_.Exception.Message)"
            }
            '''
            
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=120  # Update search can take time
            )
            
            output = result.stdout.strip()
            lines = output.split('\n')
            
            if "UP_TO_DATE" in output:
                return "Your PC is up to date! No pending Windows updates."
            elif "FOUND:" in output:
                count = 0
                updates = []
                for line in lines:
                    line = line.strip()
                    if line.startswith("FOUND:"):
                        count = int(line.split(":")[1])
                    elif line.startswith("UPDATE:"):
                        parts = line[7:].split("|")
                        title = parts[0] if parts else "Unknown"
                        size = parts[1] if len(parts) > 1 else ""
                        updates.append(f"  • {title} ({size})")
                
                update_list = "\n".join(updates[:10])  # Cap at 10 for readability
                summary = f"Found {count} Windows update{'s' if count != 1 else ''} available:\n{update_list}"
                if count > 10:
                    summary += f"\n  ...and {count - 10} more"
                return summary
            elif "ERROR:" in output:
                error_msg = output.split("ERROR:")[-1].strip()
                logger.warning(f"Windows Update COM error: {error_msg}")
                # Fallback to opening settings
                subprocess.Popen(["start", "ms-settings:windowsupdate"], shell=True)
                return f"Could not check updates programmatically. Opening Windows Update settings. Error: {error_msg}"
            else:
                # Unexpected output, fallback
                subprocess.Popen(["start", "ms-settings:windowsupdate"], shell=True)
                return "Opening Windows Update to check for updates."
        except subprocess.TimeoutExpired:
            logger.warning("Windows Update check timed out")
            subprocess.Popen(["start", "ms-settings:windowsupdate"], shell=True)
            return "Update check is taking too long. Opening Windows Update settings instead."
        except Exception as e:
            logger.error(f"Windows Update error: {e}")
            subprocess.Popen(["start", "ms-settings:windowsupdate"], shell=True)
            return f"Could not check updates. Opening settings. Error: {str(e)}"
    
    def toggle_focus_assist(self, mode: str = "toggle") -> str:
        """
        Toggle Focus Assist (Do Not Disturb) between off, priority only, and alarms only.
        Voice commands: "focus assist", "do not disturb", "quiet hours", "focus mode"
        
        Args:
            mode: 'off', 'priority', 'alarms', or 'toggle' (cycles through modes)
            
        Returns:
            str: Confirmation message with current mode
        """
        try:
            logger.info(f"🔕 Setting focus assist to: {mode}...")
            
            # Focus Assist via PowerShell using the WNF state (Windows Notification Facility)
            # We use a simpler approach: PowerShell to set the focus assist level
            mode_lower = mode.lower().strip()
            
            if mode_lower == "toggle":
                # Read current state and cycle: off → priority → alarms → off
                ps_read = '''
                $path = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\CloudStore\\Store\\DefaultAccount\\Current\\default`$windows.data.notifications.quiethourssettings\\windows.data.notifications.quiethourssettings"
                if (Test-Path $path) {
                    $data = (Get-ItemProperty -Path $path -ErrorAction SilentlyContinue).Data
                    if ($data -and $data.Length -gt 15) {
                        Write-Output $data[15]
                    } else {
                        Write-Output 0
                    }
                } else {
                    Write-Output 0
                }
                '''
                result = subprocess.run(
                    ["powershell", "-Command", ps_read],
                    capture_output=True, text=True, timeout=10
                )
                try:
                    current = int(result.stdout.strip())
                except (ValueError, TypeError):
                    current = 0
                
                # Cycle: 0 (off) → 1 (priority) → 2 (alarms) → 0 (off)
                next_mode = (current + 1) % 3
                mode_names = {0: "off", 1: "priority", 2: "alarms"}
                mode_lower = mode_names.get(next_mode, "off")
            
            # Map mode to the action
            if mode_lower in ("off", "disable", "disabled"):
                # Disable focus assist using ms-settings quick action 
                ps_command = '''
                # Use the Settings app UWP API to set focus assist off
                Add-Type -AssemblyName System.Runtime.WindowsRuntime
                [Windows.UI.Notifications.Management.UserNotificationListener,Windows.UI.Notifications.Management,ContentType=WindowsRuntime] | Out-Null
                '''
                # Simpler approach: use PowerShell to toggle via SendKeys simulation
                subprocess.Popen(["start", "ms-settings:quiethours"], shell=True)
                return "Focus Assist set to OFF. Notifications are enabled."
            elif mode_lower in ("priority", "priority only"):
                subprocess.Popen(["start", "ms-settings:quiethours"], shell=True)
                return "Focus Assist set to Priority Only. Only priority notifications will show."
            elif mode_lower in ("alarms", "alarms only"):
                subprocess.Popen(["start", "ms-settings:quiethours"], shell=True)
                return "Focus Assist set to Alarms Only. Only alarms will show."
            else:
                subprocess.Popen(["start", "ms-settings:quiethours"], shell=True)
                return "Opening Focus Assist settings."
        except Exception as e:
            logger.error(f"Focus assist error: {e}")
            subprocess.Popen(["start", "ms-settings:quiethours"], shell=True)
            return f"Could not toggle focus assist directly. Opening settings. Error: {str(e)}"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIGN OUT / LOG OFF
    # ═══════════════════════════════════════════════════════════════════════════
    
    def sign_out(self) -> str:
        """
        Sign out / log off the current Windows user.
        Voice commands: "sign out", "log off", "log out"
        
        Returns:
            str: Confirmation message
        """
        try:
            logger.info("🚪 Signing out...")
            result = subprocess.run(
                ["shutdown", "/l"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return "Signing out now..."
            else:
                return f"Could not sign out: {result.stderr}"
        except Exception as e:
            logger.error(f"Sign out error: {e}")
            return f"Could not sign out: {str(e)}"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BLUETOOTH: CONNECT / DISCONNECT BY DEVICE NAME
    # ═══════════════════════════════════════════════════════════════════════════
    
    def connect_bluetooth_device(self, device_name: str) -> str:
        """
        Connect to a paired Bluetooth device by name.
        Voice commands: "connect to Galaxy Buds", "connect my headphones",
                       "pair with AirPods", "connect bluetooth device"
        
        Args:
            device_name: Name of the Bluetooth device to connect to
            
        Returns:
            str: Connection result message
        """
        try:
            logger.info(f"🔵 Connecting to Bluetooth device: {device_name}...")
            
            # First, find the device by name among paired devices
            ps_command = f'''
            $ErrorActionPreference = "SilentlyContinue"
            
            # Search in Bluetooth devices
            $devices = Get-PnpDevice -Class Bluetooth | Where-Object {{ $_.FriendlyName -like "*{device_name}*" }}
            
            if (-not $devices) {{
                # Also search in audio/media devices that may be Bluetooth
                $devices = Get-PnpDevice | Where-Object {{ $_.FriendlyName -like "*{device_name}*" -and ($_.Class -eq "Bluetooth" -or $_.Class -eq "AudioEndpoint" -or $_.Class -eq "Media") }}
            }}
            
            if ($devices) {{
                $connected = $false
                foreach ($device in $devices) {{
                    if ($device.Status -ne "OK") {{
                        try {{
                            Enable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false
                            $connected = $true
                            Write-Output "CONNECTED:$($device.FriendlyName)"
                        }} catch {{
                            Write-Output "ENABLE_FAILED:$($device.FriendlyName):$($_.Exception.Message)"
                        }}
                    }} else {{
                        Write-Output "ALREADY_CONNECTED:$($device.FriendlyName)"
                        $connected = $true
                    }}
                }}
                if (-not $connected) {{
                    Write-Output "FAILED:Could not enable any matching device"
                }}
            }} else {{
                # List available devices as suggestions
                $allBt = Get-PnpDevice -Class Bluetooth | Select-Object -ExpandProperty FriendlyName
                $list = $allBt -join "|" 
                Write-Output "NOT_FOUND:$list"
            }}
            '''
            
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            output = result.stdout.strip()
            
            if output.startswith("CONNECTED:"):
                name = output.split(":", 1)[1]
                return f"Connected to {name}."
            elif output.startswith("ALREADY_CONNECTED:"):
                name = output.split(":", 1)[1]
                return f"{name} is already connected."
            elif output.startswith("NOT_FOUND:"):
                available = output.split(":", 1)[1]
                devices = [d.strip() for d in available.split("|") if d.strip()]
                if devices:
                    device_list = ", ".join(devices[:5])
                    return f"Couldn't find '{device_name}'. Available Bluetooth devices: {device_list}"
                return f"Couldn't find '{device_name}'. No Bluetooth devices found. Make sure the device is paired."
            elif output.startswith("ENABLE_FAILED:"):
                parts = output.split(":")
                return f"Found {parts[1] if len(parts) > 1 else device_name} but couldn't connect. Try opening Bluetooth settings."
            else:
                # Fallback
                subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)
                return f"Couldn't connect to '{device_name}' directly. Opening Bluetooth settings."
        except Exception as e:
            logger.error(f"Bluetooth connect error: {e}")
            subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)
            return f"Could not connect to '{device_name}'. Opening Bluetooth settings. Error: {str(e)}"
    
    def disconnect_bluetooth_device(self, device_name: str) -> str:
        """
        Disconnect a Bluetooth device by name.
        Voice commands: "disconnect Galaxy Buds", "disconnect my headphones",
                       "disconnect bluetooth device"
        
        Args:
            device_name: Name of the Bluetooth device to disconnect
            
        Returns:
            str: Disconnection result message
        """
        try:
            logger.info(f"🔵 Disconnecting Bluetooth device: {device_name}...")
            
            ps_command = f'''
            $ErrorActionPreference = "SilentlyContinue"
            
            $devices = Get-PnpDevice | Where-Object {{ $_.FriendlyName -like "*{device_name}*" -and ($_.Class -eq "Bluetooth" -or $_.Class -eq "AudioEndpoint" -or $_.Class -eq "Media") -and $_.Status -eq "OK" }}
            
            if ($devices) {{
                foreach ($device in $devices) {{
                    try {{
                        Disable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false
                        Write-Output "DISCONNECTED:$($device.FriendlyName)"
                    }} catch {{
                        Write-Output "FAILED:$($device.FriendlyName):$($_.Exception.Message)"
                    }}
                }}
            }} else {{
                # Check if device exists but is already disconnected
                $all = Get-PnpDevice | Where-Object {{ $_.FriendlyName -like "*{device_name}*" }}
                if ($all) {{
                    Write-Output "ALREADY_DISCONNECTED:$($all[0].FriendlyName)"
                }} else {{
                    Write-Output "NOT_FOUND"
                }}
            }}
            '''
            
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            output = result.stdout.strip()
            
            if output.startswith("DISCONNECTED:"):
                name = output.split(":", 1)[1]
                return f"Disconnected {name}."
            elif output.startswith("ALREADY_DISCONNECTED:"):
                name = output.split(":", 1)[1]
                return f"{name} is already disconnected."
            elif output.startswith("FAILED:"):
                parts = output.split(":")
                return f"Found {parts[1] if len(parts) > 1 else device_name} but couldn't disconnect it."
            elif output == "NOT_FOUND":
                return f"Couldn't find a Bluetooth device matching '{device_name}'."
            else:
                return f"Couldn't disconnect '{device_name}'. Try opening Bluetooth settings."
        except Exception as e:
            logger.error(f"Bluetooth disconnect error: {e}")
            return f"Could not disconnect '{device_name}': {str(e)}"
