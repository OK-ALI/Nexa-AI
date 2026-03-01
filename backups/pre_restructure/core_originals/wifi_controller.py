"""
WiFi Controller - Wireless Network Management
Handles WiFi operations: status, connect, disconnect, list networks, get profiles.
Extracted from executor.py for better modularity.
"""

import logging
import subprocess
import platform

logger = logging.getLogger(__name__)


class WiFiController:
    """
    Manages WiFi using Windows netsh commands.
    Provides methods for checking status, connecting, and listing networks.
    """
    
    def __init__(self):
        """Initialize WiFi controller."""
        self.os_name = platform.system()
        logger.debug("WiFiController initialized")
    
    def get_wifi_status(self) -> str:
        """
        Get current WiFi connection status.
        
        Returns:
            WiFi status message
        """
        try:
            if self.os_name == "Windows":
                result = subprocess.run(
                    'netsh wlan show interfaces',
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    
                    # Parse connection status
                    if "State" in output:
                        for line in output.split('\n'):
                            if 'State' in line:
                                state = line.split(':')[1].strip()
                                if state == "connected":
                                    # Get network name
                                    for l in output.split('\n'):
                                        if 'SSID' in l and 'BSSID' not in l:
                                            ssid = l.split(':')[1].strip()
                                            return f"Connected to {ssid}"
                                else:
                                    return f"WiFi is {state}"
                    return "WiFi adapter not found or disabled"
                else:
                    return "Could not get WiFi status"
            
            return "WiFi management only available on Windows"
            
        except Exception as e:
            logger.error(f"Error getting WiFi status: {e}")
            return f"Failed to get WiFi status: {str(e)}"
    
    def disconnect_wifi(self) -> str:
        """
        Disconnect from current WiFi network.
        
        Returns:
            Result message
        """
        from core.cognition.natural_responses import NaturalResponses
        
        try:
            if self.os_name == "Windows":
                result = subprocess.run(
                    'netsh wlan disconnect',
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0:
                    logger.info("Disconnected from WiFi")
                    return NaturalResponses.wifi_disconnected()
                else:
                    return "Could not disconnect WiFi. Make sure WiFi is enabled."
            
            return "WiFi management only available on Windows"
            
        except Exception as e:
            logger.error(f"Error disconnecting WiFi: {e}")
            return NaturalResponses.error()
    
    def connect_wifi(self, network_name: str) -> str:
        """
        Connect to a WiFi network.
        
        Args:
            network_name: Name of the WiFi network (SSID)
            
        Returns:
            Result message
        """
        from core.cognition.natural_responses import NaturalResponses
        
        try:
            if self.os_name == "Windows":
                command = f'netsh wlan connect name="{network_name}"'
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
                
                if result.returncode == 0 or "successfully" in result.stdout.lower():
                    logger.info(f"Connected to {network_name}")
                    return NaturalResponses.wifi_connected(network_name)
                else:
                    return f"Could not connect to {network_name}. Make sure the network is in range and saved."
            
            return "WiFi management only available on Windows"
            
        except Exception as e:
            logger.error(f"Error connecting to WiFi: {e}")
            return NaturalResponses.error()
    
    def list_wifi_networks(self) -> str:
        """
        List available WiFi networks.
        
        Returns:
            List of networks or error message
        """
        try:
            if self.os_name == "Windows":
                result = subprocess.run(
                    'netsh wlan show networks',
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    networks = []
                    
                    for line in output.split('\n'):
                        # Match format: "SSID 1 : NetworkName" or "SSID 12 : NetworkName"
                        if line.strip().startswith('SSID') and ':' in line:
                            # Extract everything after the colon
                            ssid = line.split(':', 1)[1].strip()
                            if ssid and ssid != "":
                                networks.append(ssid)
                    
                    if networks:
                        # Remove duplicates and sort
                        networks = sorted(list(set(networks)))
                        network_list = ", ".join(networks)
                        return f"Available networks: {network_list}"
                    else:
                        return "No WiFi networks found"
                else:
                    return "Could not scan for networks"
            
            return "WiFi management only available on Windows"
            
        except Exception as e:
            logger.error(f"Error listing WiFi networks: {e}")
            return f"Failed to list networks: {str(e)}"
    
    def get_saved_wifi_profiles(self) -> str:
        """
        Get list of saved WiFi network profiles.
        
        Returns:
            Saved network profiles or error message
        """
        try:
            if self.os_name == "Windows":
                result = subprocess.run(
                    'netsh wlan show profiles',
                    capture_output=True,
                    text=True,
                    encoding='utf-8',  # Fix Unicode error
                    errors='ignore',   # Ignore problematic characters
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    
                    # Handle case where output is None
                    if not output:
                        return "No WiFi profiles found"
                    
                    profiles = []
                    
                    for line in output.split('\n'):
                        if 'All User Profile' in line or 'User Profile' in line:
                            # Extract profile name after colon
                            if ':' in line:
                                profile_name = line.split(':')[1].strip()
                                if profile_name:
                                    profiles.append(profile_name)
                    
                    if profiles:
                        # Return the first (most recently used) profile
                        return f"Last used network: {profiles[0]}"
                    else:
                        return "No saved WiFi profiles found"
                else:
                    return "Could not get WiFi profiles"
            
            return "WiFi management only available on Windows"
            
        except Exception as e:
            logger.error(f"Error getting WiFi profiles: {e}")
            return f"Failed to get profiles: {str(e)}"
