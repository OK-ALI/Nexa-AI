"""
Weather Service for Nexa AI Assistant

Provides weather information using OpenWeatherMap API with:
- Windows location detection (automatic city detection)
- Current weather conditions
- 5-day weather forecast
- Intelligent caching (30 min TTL)
- Offline fallback support
- Multi-city support

API: OpenWeatherMap (https://openweathermap.org/api)
Free tier: 1,000 calls/day, 5-day forecast
"""

import requests
import subprocess
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Weather service with automatic location detection and caching.
    """
    
    def __init__(self, api_key: str, default_location: str = None, cache_duration_minutes: int = 30, config=None):
        """
        Initialize weather service.
        
        Args:
            api_key: OpenWeatherMap API key
            default_location: Default location (e.g., "Karachi,PK")
            cache_duration_minutes: How long to cache weather data (default 30 min)
            config: Configuration object with data_dir path
        """
        self.api_key = api_key
        self.default_location = default_location
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
        # Cache storage - use config's data_dir for proper AppData location
        if config and hasattr(config, 'data_dir'):
            self.cache_dir = config.data_dir / "weather_cache"
        else:
            # Fallback for standalone usage
            self.cache_dir = Path("data/weather_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load last known location from persistent cache
        self._last_known_location = self._load_last_known_location()
        
        logger.info(f"Weather service initialized (default: {default_location}, last known: {self._last_known_location})")
    
    def get_weather(self, location: Optional[str] = None) -> str:
        """
        Get current weather for a location.
        
        Args:
            location: City name (e.g., "Tokyo", "London,UK"). If None, auto-detects.
            
        Returns:
            Natural language weather description
        """
        try:
            # Determine location
            location = self._resolve_location(location)
            
            if not location:
                return "I need to know your location. Where are you? You can also set a default location in settings."
            
            logger.info(f"Getting weather for: {location}")
            
            # Check cache first
            cached_data = self._get_from_cache(location, 'current')
            if cached_data:
                logger.debug(f"Using cached weather for {location}")
                return self._format_current_weather(cached_data, location, from_cache=True)
            
            # Fetch fresh data from API
            weather_data = self._fetch_current_weather(location)
            
            if not weather_data:
                return f"I couldn't get weather information for {location}. Please check the location name."
            
            # Cache the data
            self._save_to_cache(location, 'current', weather_data)
            
            # Format response
            return self._format_current_weather(weather_data, location)
            
        except Exception as e:
            logger.error(f"Error getting weather: {e}", exc_info=True)
            return "I encountered an error checking the weather. Please try again."
    
    def get_forecast(self, location: Optional[str] = None, days: int = 3) -> str:
        """
        Get weather forecast for next N days.
        
        Args:
            location: City name. If None, auto-detects.
            days: Number of days (1-5, default 3)
            
        Returns:
            Natural language forecast description
        """
        try:
            # Determine location
            location = self._resolve_location(location)
            
            if not location:
                return "I need to know your location to get the forecast."
            
            # Clamp days to 1-5
            days = max(1, min(5, days))
            
            logger.info(f"Getting {days}-day forecast for: {location}")
            
            # Check cache
            cached_data = self._get_from_cache(location, 'forecast')
            if cached_data:
                logger.debug(f"Using cached forecast for {location}")
                return self._format_forecast(cached_data, location, days, from_cache=True)
            
            # Fetch fresh forecast
            forecast_data = self._fetch_forecast(location, days)
            
            if not forecast_data:
                return f"I couldn't get the forecast for {location}."
            
            # Cache the data
            self._save_to_cache(location, 'forecast', forecast_data)
            
            # Format response
            return self._format_forecast(forecast_data, location, days)
            
        except Exception as e:
            logger.error(f"Error getting forecast: {e}", exc_info=True)
            return "I encountered an error getting the forecast. Please try again."
    
    def _resolve_location(self, location: Optional[str]) -> Optional[str]:
        """
        Resolve location priority:
        1. User specified (e.g., "weather in Tokyo")
        2. Windows Location Services (auto-detect)
        3. Last known location (from previous successful detection)
        4. Default from config
        
        Args:
            location: User-specified location
            
        Returns:
            Resolved location string or None
        """
        # 1. User specified location (highest priority)
        if location:
            return location.strip()
        
        # 2. Try Windows location detection
        windows_location = self._get_windows_location()
        if windows_location:
            logger.info(f"Auto-detected location from Windows: {windows_location}")
            # Save as last known location for future fallback
            self._save_last_known_location(windows_location)
            return windows_location
        
        # 3. Use last known location (from previous successful detection)
        if self._last_known_location:
            logger.info(f"Using last known location: {self._last_known_location}")
            return self._last_known_location
        
        # 4. Use default from config
        if self.default_location:
            logger.debug(f"Using default location: {self.default_location}")
            return self.default_location
        
        # 5. No location available
        return None
    
    def _load_last_known_location(self) -> Optional[str]:
        """Load last known location from cache file."""
        try:
            cache_file = self.cache_dir / "last_known_location.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    return data.get('location')
        except Exception as e:
            logger.debug(f"Could not load last known location: {e}")
        return None
    
    def _save_last_known_location(self, location: str) -> None:
        """Save last known location to cache file for persistence across restarts."""
        try:
            cache_file = self.cache_dir / "last_known_location.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'location': location,
                    'saved_at': datetime.now().isoformat()
                }, f, indent=2)
            self._last_known_location = location
            logger.debug(f"Saved last known location: {location}")
        except Exception as e:
            logger.warning(f"Could not save last known location: {e}")
    
    def _get_windows_location(self) -> Optional[str]:
        """
        Get location from Windows Location Services.
        Caches the result for the session to avoid repeated slow lookups.
        
        Returns:
            City name (e.g., "Karachi") or None if unavailable
        """
        # Check if we already have a cached location from this session
        if hasattr(self, '_cached_windows_location'):
            if self._cached_windows_location:
                logger.debug(f"Using cached Windows location: {self._cached_windows_location}")
                return self._cached_windows_location
            else:
                # We already tried and failed - don't retry
                return None
        
        try:
            logger.info("🌍 Detecting location from Windows Location Services...")
            
            # PowerShell command to get location
            # Increased wait time for GeoWatcher to acquire position
            ps_command = '''
            Add-Type -AssemblyName System.Device
            $GeoWatcher = New-Object System.Device.Location.GeoCoordinateWatcher
            $GeoWatcher.Start()
            $timeout = 0
            while ($GeoWatcher.Position.Location.IsUnknown -and $timeout -lt 4000) {
                Start-Sleep -Milliseconds 500
                $timeout += 500
            }
            $coord = $GeoWatcher.Position.Location
            if ($coord.IsUnknown) { 
                Write-Output "UNKNOWN" 
            } else { 
                Write-Output "$($coord.Latitude),$($coord.Longitude)" 
            }
            $GeoWatcher.Stop()
            '''
            
            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=10  # Increased timeout for busy systems
            )
            
            output = result.stdout.strip()
            
            if output == "UNKNOWN" or not output:
                logger.debug("Windows location not available (service disabled or unavailable)")
                self._cached_windows_location = None
                return None
            
            # Parse latitude, longitude
            lat, lon = map(float, output.split(','))
            logger.info(f"📍 Windows location coordinates: {lat}, {lon}")
            
            # Reverse geocode to get city name
            city = self._reverse_geocode(lat, lon)
            
            # Cache the result for this session
            self._cached_windows_location = city
            logger.info(f"✅ Location cached: {city}")
            
            return city
            
        except subprocess.TimeoutExpired:
            logger.warning("Windows location detection timed out")
            self._cached_windows_location = None
            return None
        except Exception as e:
            logger.debug(f"Windows location detection failed: {e}")
            self._cached_windows_location = None
            return None
    
    def _reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Convert coordinates to city name using OpenWeatherMap reverse geocoding.
        Extracts the major city name, avoiding overly specific neighborhood names.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            City name or None
        """
        try:
            url = f"http://api.openweathermap.org/geo/1.0/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'limit': 5,
                'appid': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return None
            
            first_result = data[0]
            country = first_result.get('country', '')
            state = first_result.get('state', '')
            name = first_result.get('name', '')
            
            # Keywords that indicate a location is too specific (neighborhood/district)
            neighborhood_keywords = [
                'Tehsil', 'Town', 'District', 'Division', 'Colony', 'Block', 
                'Sector', 'Model', 'Cantonment', 'Cantt', 'Society', 'Housing',
                'Garden', 'Park', 'Extension', 'Phase', 'Scheme', 'Township'
            ]
            
            # Check if the name is too specific (a neighborhood)
            is_neighborhood = any(keyword.lower() in name.lower() for keyword in neighborhood_keywords)
            
            if is_neighborhood and state:
                # Try to find the major city from state or use state as fallback
                # Common Pakistani cities that might be in state field
                major_cities = ['Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Faisalabad', 
                               'Peshawar', 'Quetta', 'Multan', 'Hyderabad', 'Sialkot']
                
                # Check if state contains a major city name
                for city in major_cities:
                    if city.lower() in state.lower():
                        logger.info(f"Detected neighborhood '{name}', using major city: {city}")
                        return f"{city},{country}" if country else city
                
                # If state looks like a city (doesn't contain province keywords), use it
                province_keywords = ['Punjab', 'Sindh', 'Balochistan', 'Khyber', 'KPK', 'Islamabad Capital']
                if not any(prov.lower() in state.lower() for prov in province_keywords):
                    logger.info(f"Detected neighborhood '{name}', using state as city: {state}")
                    return f"{state},{country}" if country else state
                
                # Search for nearby cities using forward geocoding
                city_name = self._find_nearest_city(lat, lon, country)
                if city_name:
                    return city_name
            
            # If not a neighborhood or no better option found, use the original name
            location = f"{name},{country}" if country else name
            logger.info(f"Reverse geocoded to: {location}")
            return location
            
        except Exception as e:
            logger.warning(f"Reverse geocoding failed: {e}")
            return None
    
    def _find_nearest_city(self, lat: float, lon: float, country: str) -> Optional[str]:
        """
        Find the nearest major city by searching for cities near coordinates.
        Uses a grid search approach with direct geocoding.
        
        Args:
            lat: Latitude
            lon: Longitude
            country: Country code (e.g., 'PK')
            
        Returns:
            City name with country or None
        """
        try:
            # Map country codes to major cities for common cases
            country_major_cities = {
                'PK': ['Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Faisalabad', 
                       'Peshawar', 'Multan', 'Hyderabad', 'Gujranwala', 'Sialkot'],
                'IN': ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata', 
                       'Hyderabad', 'Ahmedabad', 'Pune', 'Jaipur', 'Lucknow'],
                'US': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix',
                       'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'Austin'],
                'GB': ['London', 'Birmingham', 'Manchester', 'Leeds', 'Liverpool',
                       'Glasgow', 'Bristol', 'Edinburgh', 'Sheffield', 'Cardiff'],
            }
            
            cities_to_check = country_major_cities.get(country, [])
            
            if not cities_to_check:
                return None
            
            # Find the closest major city by coordinates
            closest_city = None
            min_distance = float('inf')
            
            for city in cities_to_check:
                try:
                    # Get coordinates for this city
                    url = f"http://api.openweathermap.org/geo/1.0/direct"
                    params = {
                        'q': f"{city},{country}",
                        'limit': 1,
                        'appid': self.api_key
                    }
                    
                    response = requests.get(url, params=params, timeout=3)
                    if response.status_code != 200:
                        continue
                    
                    city_data = response.json()
                    if not city_data:
                        continue
                    
                    city_lat = city_data[0]['lat']
                    city_lon = city_data[0]['lon']
                    
                    # Calculate rough distance (Euclidean, good enough for comparison)
                    distance = ((lat - city_lat) ** 2 + (lon - city_lon) ** 2) ** 0.5
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_city = city
                        
                except Exception:
                    continue
            
            if closest_city and min_distance < 1.0:  # Within ~100km
                logger.info(f"Found nearest major city: {closest_city}")
                return f"{closest_city},{country}"
            
            return None
            
        except Exception as e:
            logger.debug(f"Nearest city search failed: {e}")
            return None
    
    def _fetch_current_weather(self, location: str) -> Optional[Dict[str, Any]]:
        """
        Fetch current weather from OpenWeatherMap API.
        
        Args:
            location: City name
            
        Returns:
            Weather data dict or None
        """
        try:
            url = f"{self.base_url}/weather"
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric'  # Celsius
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Fetched weather data for {location}")
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Location not found: {location}")
            else:
                logger.error(f"HTTP error fetching weather: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return None
    
    def _fetch_forecast(self, location: str, days: int) -> Optional[Dict[str, Any]]:
        """
        Fetch weather forecast from OpenWeatherMap API.
        
        Args:
            location: City name
            days: Number of days
            
        Returns:
            Forecast data dict or None
        """
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': days * 8  # 8 forecasts per day (3-hour intervals)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Fetched {days}-day forecast for {location}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching forecast: {e}")
            return None
    
    def _format_current_weather(self, data: Dict[str, Any], location: str, from_cache: bool = False) -> str:
        """
        Format current weather data into natural language.
        
        Args:
            data: Weather data from API
            location: Location name
            from_cache: Whether data is from cache
            
        Returns:
            Natural language description
        """
        try:
            temp = round(data['main']['temp'])
            feels_like = round(data['main']['feels_like'])
            humidity = data['main']['humidity']
            description = data['weather'][0]['description']
            wind_speed = round(data['wind']['speed'], 1)
            
            # Build response
            response = f"Current weather in {location}: {description}, {temp}°C"
            
            if abs(temp - feels_like) >= 3:
                response += f", feels like {feels_like}°C"
            
            response += f". Humidity {humidity}%, wind speed {wind_speed} meters per second."
            
            if from_cache:
                response += " (Updated a few minutes ago)"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting weather: {e}")
            return "I got the weather data but couldn't format it properly."
    
    def _format_forecast(self, data: Dict[str, Any], location: str, days: int, from_cache: bool = False) -> str:
        """
        Format forecast data into natural language.
        
        Args:
            data: Forecast data from API
            location: Location name
            days: Number of days
            from_cache: Whether data is from cache
            
        Returns:
            Natural language forecast
        """
        try:
            forecast_list = data['list']
            
            # Group by day (take one forecast per day - around noon)
            daily_forecasts = []
            current_day = None
            
            for item in forecast_list:
                dt = datetime.fromtimestamp(item['dt'])
                day = dt.date()
                
                # Take the forecast closest to noon (12:00)
                if current_day != day and 9 <= dt.hour <= 15:
                    temp = round(item['main']['temp'])
                    description = item['weather'][0]['description']
                    daily_forecasts.append({
                        'day': dt.strftime('%A'),
                        'date': dt.strftime('%B %d'),
                        'temp': temp,
                        'description': description
                    })
                    current_day = day
                    
                    if len(daily_forecasts) >= days:
                        break
            
            # Build response
            response = f"Weather forecast for {location}: "
            
            for i, forecast in enumerate(daily_forecasts):
                if i == 0:
                    day_label = "Today" if forecast['day'] == datetime.now().strftime('%A') else "Tomorrow"
                else:
                    day_label = forecast['day']
                
                response += f"{day_label} - {forecast['description']}, {forecast['temp']}°C. "
            
            if from_cache:
                response += "(Forecast from a few minutes ago)"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error formatting forecast: {e}")
            return "I got the forecast but couldn't format it properly."
    
    def _get_from_cache(self, location: str, data_type: str) -> Optional[Dict[str, Any]]:
        """
        Get weather data from cache if valid.
        
        Args:
            location: Location name
            data_type: 'current' or 'forecast'
            
        Returns:
            Cached data or None if expired/missing
        """
        try:
            cache_file = self.cache_dir / f"{location.replace(',', '_')}_{data_type}.json"
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_entry = json.load(f)
            
            # Check expiration
            cached_at = datetime.fromisoformat(cache_entry['cached_at'])
            if datetime.now() - cached_at > self.cache_duration:
                logger.debug(f"Cache expired for {location} {data_type}")
                return None
            
            logger.debug(f"Cache hit for {location} {data_type}")
            return cache_entry['data']
            
        except Exception as e:
            logger.debug(f"Cache read failed: {e}")
            return None
    
    def _save_to_cache(self, location: str, data_type: str, data: Dict[str, Any]) -> None:
        """
        Save weather data to cache.
        
        Args:
            location: Location name
            data_type: 'current' or 'forecast'
            data: Weather data to cache
        """
        try:
            cache_file = self.cache_dir / f"{location.replace(',', '_')}_{data_type}.json"
            
            cache_entry = {
                'location': location,
                'data_type': data_type,
                'cached_at': datetime.now().isoformat(),
                'data': data
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2)
            
            logger.debug(f"Cached {data_type} weather for {location}")
            
        except Exception as e:
            logger.warning(f"Failed to cache weather data: {e}")
