"""
Function Registry - Dynamic Function Calling for Nexa
Maps function names to executor methods for AI-driven command execution.
"""

import logging
import time
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)


class FunctionRegistry:
    """
    Registry of all available functions that Gemma3 can call.
    Enables dynamic function execution based on AI reasoning instead of hardcoded keywords.
    
    Now includes skill tracking for Smart Memory learning.
    """
    
    def __init__(self, executor, context_manager=None):
        """
        Initialize function registry with executor.
        
        Args:
            executor: CommandExecutor instance with all system functions
            context_manager: ContextManager for Smart Memory skill tracking (optional)
        """
        self.executor = executor
        self.context_manager = context_manager
        self.functions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize SystemControl module for Phase 16+ system control functions
        from capabilities.system.system_control import SystemControl
        self.system_control = SystemControl()
        
        self._register_all_functions()
        logger.info(f"Function Registry initialized with {len(self.functions)} functions")
    
    def register(self, name: str, function: Callable, description: str, parameters: Dict[str, str]):
        """
        Register a function in the catalog.
        
        Args:
            name: Function name (e.g., 'open_application')
            function: Callable function/method
            description: What the function does
            parameters: Dict of param_name: param_description
        """
        self.functions[name] = {
            "function": function,
            "description": description,
            "parameters": parameters
        }
        logger.debug(f"Registered function: {name}")
    
    def _register_all_functions(self):
        """Register all executor methods as callable functions."""
        
        # ===== TIME & SYSTEM INFO =====
        self.register(
            "get_current_time",
            self.executor.get_current_time,
            "Get the current time (hour and minute only)",
            {}
        )
        
        self.register(
            "get_current_date",
            self.executor.get_current_date,
            "Get the current date (day, month, year only)",
            {}
        )
        
        # ===== BATTERY =====
        self.register(
            "get_battery_status",
            self.executor.get_battery_status,
            "Get full battery status (charging, percentage, time remaining)",
            {}
        )
        
        self.register(
            "get_battery_percentage",
            self.executor.get_battery_percentage,
            "Get just the battery percentage",
            {}
        )
        
        # ===== GPU MONITORING =====
        self.register(
            "get_gpu_usage",
            self.executor.get_gpu_usage,
            "Get current GPU memory usage and VRAM statistics",
            {}
        )
        
        # ===== SYSTEM INFORMATION =====
        self.register(
            "get_system_info",
            self.executor.get_system_info,
            "Get comprehensive system information including OS, CPU, RAM, Disk, and GPU specs. Use when user asks about their PC specs, system info, computer details, or hardware.",
            {}
        )
        
        self.register(
            "get_pc_specs",
            self.executor.get_pc_specs,
            "Get PC specifications as natural language response. Use when user asks 'what are my PC specs?', 'tell me about my computer', 'system specifications'",
            {}
        )
        
        # ===== WEATHER =====
        self.register(
            "get_weather",
            self.executor.get_weather,
            "Get current weather for a location (auto-detects if no location specified)",
            {"location": "City name (optional, e.g., 'Tokyo', 'London,UK'). Leave empty for auto-detection."}
        )
        
        self.register(
            "get_forecast",
            self.executor.get_forecast,
            "Get weather forecast for next N days (1-5 days)",
            {
                "location": "City name (optional). Leave empty for auto-detection.",
                "days": "Number of forecast days (1-5, default 3)"
            }
        )
        
        # ===== WEB SEARCH =====
        self.register(
            "search_web",
            self.executor.search_web,
            "Search the web using default browser - opens Google search with query",
            {"query": "The search query to look up on the web"}
        )
        
        # ===== YOUTUBE (Phase 18 - Online Only) =====
        self.register(
            "play_youtube",
            self.executor.play_youtube,
            "Play a YouTube video by name or URL - opens in browser. Use for: 'play [song/video] on youtube', 'youtube [query]'",
            {"query": "Video name, song name, or YouTube URL to play"}
        )
        
        self.register(
            "search_youtube",
            self.executor.search_youtube,
            "Search YouTube and return a list of results (titles, channels, views). Use for: 'search youtube for [query]', 'find videos about [topic]'",
            {"query": "Search query for YouTube"}
        )
        
        self.register(
            "play_youtube_result",
            self.executor.play_youtube_result,
            "Play a video from the last YouTube search results by its number (1-5). Use after search_youtube.",
            {"number": "Result number to play (1-5)"}
        )
        
        self.register(
            "get_video_info",
            self.executor.get_video_info,
            "Get detailed info about a YouTube video (title, channel, views, duration, description)",
            {"query": "Video name or YouTube URL (optional - uses last played if empty)"}
        )
        
        self.register(
            "download_youtube",
            self.executor.download_youtube,
            "Download a YouTube video or audio. Supports quality: 360p, 480p, 720p, 1080p, 1440p, 4k, best. Saves to Videos/Nexa Downloads/",
            {
                "query": "Video name or YouTube URL to download",
                "audio_only": "Set to true to download audio only (MP3). Default: false",
                "quality": "Video quality: 360p, 480p, 720p, 1080p (default), 1440p, 4k, best"
            }
        )
        
        self.register(
            "download_youtube_video",
            self.executor.download_youtube_video,
            "Download a YouTube video in specified quality. Shortcut for download_youtube with video.",
            {
                "query": "Video name or YouTube URL",
                "quality": "Video quality: 360p, 480p, 720p, 1080p (default), 1440p, 4k, best"
            }
        )
        
        self.register(
            "download_youtube_audio",
            self.executor.download_youtube_audio,
            "Download audio (MP3) from a YouTube video. Saves to Videos/Nexa Downloads/",
            {"query": "Video or song name to download as MP3"}
        )
        
        self.register(
            "get_download_status",
            self.executor.get_download_status,
            "Check the current YouTube download progress (percentage, speed, ETA)",
            {}
        )
        
        self.register(
            "get_youtube_queue",
            self.executor.get_youtube_queue,
            "Get the current YouTube playback queue",
            {}
        )
        
        self.register(
            "clear_youtube_queue",
            self.executor.clear_youtube_queue,
            "Clear the YouTube playback queue",
            {}
        )

        self.register(
            "get_video_transcript",
            self.executor.get_video_transcript,
            "Extract and return the auto-generated English captions/transcript of a YouTube video. Use for: 'what does this video say', 'get the transcript of [video]', 'summarise that video'",
            {"query": "Video name or YouTube URL to get the transcript for"}
        )

        self.register(
            "get_trending_videos",
            self.executor.get_trending_videos,
            "Show currently trending videos on YouTube for a region. Returns a numbered list. Use for: 'what's trending on youtube', 'show popular videos', 'trending videos in uk'. After this, user can say 'play result N' to watch one.",
            {
                "region": "Two-letter country code, e.g. US, GB, IN (default: US)",
                "count": "Number of results to return 1-10 (default: 5)"
            }
        )

        self.register(
            "get_channel_videos",
            self.executor.get_channel_videos,
            "List recent uploads from a YouTube channel. Returns a numbered list. Use for: 'show videos from mkbhd', 'what has [channel] uploaded', 'latest from [channel]'. After this, user can say 'play result N' to watch one.",
            {
                "channel_name": "Channel handle or name (e.g. mkbhd, veritasium) — no @ sign needed",
                "count": "Number of videos to list 1-10 (default: 5)"
            }
        )

        self.register(
            "play_youtube_playlist",
            self.executor.play_youtube_playlist,
            "Load a YouTube playlist URL into the queue and play the first video. Use for: 'play this playlist', 'queue this playlist', 'play all videos in [playlist url]'",
            {
                "url": "Full YouTube playlist URL (youtube.com/playlist?list=...)",
                "max_videos": "Maximum videos to load 1-20 (default: 10)"
            }
        )
        
        # ===== LOCAL VIDEO / MOVIES (Works offline + online) =====
        self.register(
            "play_local_video",
            self.executor.play_local_video,
            "Play a local video or movie from the movie library (D:\\Movie). Scans folders to find the movie by name. Use for: 'play that movie', 'play Inception', 'watch a movie', 'play local video'",
            {"query": "Movie name or partial title to search for in the library"}
        )
        
        # ===== ENHANCED WEB SEARCH (Phase 18 - Online Only) =====
        self.register(
            "smart_search",
            self.executor.smart_search,
            "Search the web and return actual text content/answers (scrapes DuckDuckGo + top results). Use when user wants INFORMATION, not just to open browser. E.g. 'what is quantum computing', 'who won the world cup 2024'",
            {"query": "The question or topic to search for and get actual content"}
        )
        
        self.register(
            "scrape_url",
            self.executor.scrape_url,
            "Scrape a specific webpage URL and return its text content. For reading articles, docs, etc.",
            {"url": "The full URL to scrape (e.g. https://example.com/article)"}
        )
        
        # ===== CONVERSATION MANAGEMENT =====
        self.register(
            "clear_conversation_history",
            self.executor.clear_conversation_history,
            "Clear all conversation history (forget previous conversations)",
            {}
        )
        
        # ===== NETWORK & WIFI MANAGEMENT =====
        self.register(
            "get_wifi_status",
            self.executor.get_wifi_status,
            "Get current WiFi connection status",
            {}
        )
        
        self.register(
            "disconnect_wifi",
            self.executor.disconnect_wifi,
            "Disconnect from current WiFi network (go offline)",
            {}
        )
        
        self.register(
            "connect_wifi",
            self.executor.connect_wifi,
            "Connect to a WiFi network by name",
            {"network_name": "Name of WiFi network (SSID) to connect to"}
        )
        
        self.register(
            "list_wifi_networks",
            self.executor.list_wifi_networks,
            "List all available WiFi networks in range",
            {}
        )
        
        self.register(
            "get_saved_wifi_profiles",
            self.executor.get_saved_wifi_profiles,
            "List all saved WiFi profiles/networks",
            {}
        )
        
        # ===== APPLICATION MANAGEMENT =====
        self.register(
            "open_application",
            self.executor.open_application,
            "Open/launch any installed application by name",
            {"app_name": "Name of application (e.g., 'chrome', 'calculator', 'notepad')"}
        )
        
        self.register(
            "close_application",
            self.executor.close_application,
            "Close/terminate a running application (enhanced: falls back to active window if app not found)",
            {"app_name": "Name of application to close"}
        )
        
        self.register(
            "close_active_window",
            self.executor.window_manager.close_active_window,
            "Close the currently active/foreground window (for 'close this' commands)",
            {}
        )
        
        self.register(
            "get_running_applications",
            lambda is_follow_up=False: self.executor.get_running_applications(is_follow_up=is_follow_up),
            "List all currently running applications (background processes with windows)",
            {}
        )
        
        self.register(
            "get_installed_applications",
            lambda search_query=None, limit=20: self.executor.get_installed_applications(search_query=search_query, limit=limit),
            "List all installed applications on the system (from Start Menu, Store, Registry). Use for 'list installed apps', 'what apps do I have', 'show my applications'",
            {
                "search_query": "Optional: filter apps by keyword (e.g., 'video', 'game', 'microsoft')",
                "limit": "Maximum number to list (default: 20)"
            }
        )
        
        self.register(
            "refresh_installed_apps",
            self.executor.refresh_installed_apps,
            "Force re-scan of installed applications. Use when user says 'refresh apps', 'rescan apps', or when newly installed app is not found",
            {}
        )
        
        self.register(
            "is_application_running",
            self.executor.is_application_running,
            "Check if specific application is currently running",
            {"app_name": "Name of application to check"}
        )
        
        # ===== VOLUME CONTROL =====
        self.register(
            "set_volume",
            self.executor.set_volume,
            "Set system volume to specific level (0-100)",
            {"level": "Volume level 0-100"}
        )
        
        self.register(
            "get_current_volume",
            self.executor.get_current_volume,
            "Get the current system volume level and mute status",
            {}
        )
        
        self.register(
            "increase_volume",
            self.executor.increase_volume,
            "Increase volume by specified amount",
            {"amount": "Amount to increase (default 10)"}
        )
        
        self.register(
            "decrease_volume",
            self.executor.decrease_volume,
            "Decrease volume by specified amount",
            {"amount": "Amount to decrease (default 10)"}
        )
        
        self.register(
            "mute_volume",
            self.executor.mute_volume,
            "Mute system volume",
            {}
        )
        
        self.register(
            "unmute_volume",
            self.executor.unmute_volume,
            "Unmute system volume",
            {}
        )
        
        # ===== BRIGHTNESS CONTROL =====
        self.register(
            "set_brightness",
            self.executor.set_brightness,
            "Set screen brightness to specific level (0-100)",
            {"level": "Brightness level 0-100"}
        )
        
        self.register(
            "get_current_brightness",
            self.executor.get_current_brightness,
            "Get the current screen brightness level (0-100)",
            {}
        )
        
        self.register(
            "increase_brightness",
            self.executor.increase_brightness,
            "Increase brightness by specified amount",
            {"amount": "Amount to increase (default 10)"}
        )
        
        self.register(
            "decrease_brightness",
            self.executor.decrease_brightness,
            "Decrease brightness by specified amount",
            {"amount": "Amount to decrease (default 10)"}
        )
        
        # ===== SCREEN READING (VISION) =====
        self.register(
            "read_screen_content",
            self.executor.read_screen_content,
            "Read all text visible on screen using vision/OCR",
            {}
        )
        
        self.register(
            "describe_screen",
            self.executor.describe_screen,
            "Get AI description of what's currently on screen",
            {}
        )
        
        # ===== WINDOW MANAGEMENT =====
        self.register(
            "minimize_window",
            lambda app_name: self.executor.window_manager.minimize_window(app_name),
            "Minimize a window by application name",
            {"app_name": "Application name or 'active' for current window"}
        )
        
        self.register(
            "maximize_window",
            lambda app_name: self.executor.window_manager.maximize_window(app_name),
            "Maximize a window by application name",
            {"app_name": "Application name or 'active' for current window"}
        )
        
        self.register(
            "restore_window",
            lambda app_name: self.executor.window_manager.restore_window(app_name),
            "Restore window to normal size",
            {"app_name": "Application name"}
        )
        
        self.register(
            "get_active_window",
            lambda: self.executor.window_manager.get_active_window_title(),
            "Get title of currently active window",
            {}
        )
        
        # ===== WIFI =====
        self.register(
            "get_wifi_status",
            self.executor.get_wifi_status,
            "Check WiFi connection status and network name",
            {}
        )
        
        self.register(
            "disconnect_wifi",
            self.executor.disconnect_wifi,
            "Disconnect from current WiFi network",
            {}
        )
        
        self.register(
            "list_wifi_networks",
            self.executor.list_wifi_networks,
            "List available WiFi networks nearby",
            {}
        )
        
        # ===== SCREENSHOTS =====
        self.register(
            "take_screenshot",
            lambda custom_name=None: self.executor.screenshot_manager.take_screenshot(custom_name=custom_name),
            "Take a screenshot and save to Pictures/Nexa Screenshots (optionally with custom name)",
            {"custom_name": "Optional: custom filename for the screenshot (e.g., 'meeting notes', 'bug report')"}
        )
        
        self.register(
            "take_screenshot_clipboard",
            lambda custom_name=None: self.executor.screenshot_manager.take_screenshot(save_to_clipboard=True, custom_name=custom_name),
            "Take screenshot and copy to clipboard (optionally with custom name)",
            {"custom_name": "Optional: custom filename for the screenshot"}
        )
        
        self.register(
            "open_screenshots_folder",
            lambda: self.executor.screenshot_manager.open_screenshots_folder(),
            "Open the Nexa screenshots folder in File Explorer",
            {}
        )
        
        # ===== GAMES =====
        self.register(
            "launch_game",
            lambda game_name: self.executor.game_manager.launch_game(game_name),
            "Launch a game from any platform (Steam, Epic, GOG, etc.)",
            {"game_name": "Name of the game to launch"}
        )
        
        self.register(
            "list_games",
            lambda platform=None, is_follow_up=False: self.executor.list_games(platform=platform, is_follow_up=is_follow_up),
            "List INSTALLED GAMES on user's PC from Steam/Epic/GOG. Use ONLY for: 'list games', 'show my games', 'what games are installed?'. ⚠️ NEVER use for: 'favorite games', 'what games I like', 'which game I love' - those are MEMORY RECALL → use what_do_you_know instead!",
            {"platform": "Optional: platform name to filter (Steam, Epic, GOG, Standalone) or None for all"}
        )
        
        self.register(
            "open_folder",
            self.executor.open_folder,
            "Open a folder by name (e.g., games, downloads, documents)",
            {"folder_name": "Folder name to open"}
        )
        
        self.register(
            "find_folder",
            self.executor.find_folder,
            "Find a folder's location by name",
            {"folder_name": "Folder name to find"}
        )
        
        # ===== FILE MANAGEMENT (Phase 21) =====
        self.register(
            "create_file",
            self.executor.file_manager.create_file,
            "Create a new text file with optional content. Use for: 'create a file called notes.txt', 'make a new file'",
            {"file_path": "Path/name for the new file (e.g., 'documents/notes.txt')", "content": "Optional: text content to write into the file"}
        )
        
        self.register(
            "move_file",
            self.executor.file_manager.move_file,
            "Move a file or folder to a new location. Use for: 'move report.pdf to documents', 'move this file to desktop'",
            {"source": "Source file/folder path", "destination": "Destination path or directory"}
        )
        
        self.register(
            "copy_file",
            self.executor.file_manager.copy_file,
            "Copy a file or folder to a new location. Use for: 'copy this file to desktop', 'make a copy of report.pdf'",
            {"source": "Source file/folder path", "destination": "Destination path or directory"}
        )
        
        self.register(
            "delete_file",
            self.executor.file_manager.delete_file,
            "Delete a file or folder (moves to Recycle Bin for safety). Use for: 'delete old_report.pdf', 'remove this file'",
            {"file_path": "Path of file/folder to delete"}
        )
        
        self.register(
            "rename_file",
            self.executor.file_manager.rename_file,
            "Rename a file or folder. Use for: 'rename report.pdf to final_report.pdf', 'change the name of this file'",
            {"file_path": "Current path of the file/folder", "new_name": "New filename (just name, not full path)"}
        )
        
        self.register(
            "search_files",
            self.executor.file_manager.search_files,
            "Search for files by name. Use for: 'find files named report', 'search for pdf files in documents', 'look for photos'",
            {"query": "Search term (e.g., 'report', 'budget')", "location": "Optional: directory to search (default: home folder)", "file_type": "Optional: file extension filter (e.g., 'pdf', 'txt', 'jpg')"}
        )
        
        self.register(
            "get_recent_files",
            self.executor.file_manager.get_recent_files,
            "Show recently modified files in a directory. Use for: 'show recent downloads', 'what did I download recently', 'latest files'",
            {"location": "Optional: directory to check (default: downloads)", "count": "Optional: number of files to show (default: 10)"}
        )
        
        self.register(
            "find_duplicates",
            self.executor.file_manager.find_duplicates,
            "Find duplicate files in a directory. Use for: 'find duplicates in downloads', 'check for duplicate files'",
            {"location": "Optional: directory to check (default: downloads)"}
        )
        
        self.register(
            "organize_files",
            self.executor.file_manager.organize_files,
            "Organize files into category subfolders (Images, Documents, Videos, etc.). Use for: 'organize my downloads', 'sort files in downloads', 'clean up downloads folder'",
            {"location": "Optional: directory to organize (default: downloads)"}
        )
        
        self.register(
            "cleanup_downloads",
            self.executor.file_manager.cleanup_downloads,
            "Analyze the Downloads folder - report old files, large files, and suggest cleanup. Use for: 'clean up downloads', 'analyze my downloads folder', 'what's taking space in downloads'",
            {}
        )
        
        self.register(
            "bulk_rename",
            self.executor.file_manager.bulk_rename,
            "Rename multiple files at once using find-and-replace. Use for: 'rename all files replacing old with new', 'batch rename photos'",
            {"location": "Directory containing files", "pattern": "Text to find in filenames", "replacement": "Text to replace with", "file_type": "Optional: file extension filter (e.g., 'jpg')"}
        )
        
        self.register(
            "compress_files",
            self.executor.file_manager.compress_files,
            "Compress a file or folder into a ZIP archive. Use for: 'zip this folder', 'compress report.pdf', 'create archive of documents'",
            {"source": "File or folder path to compress", "archive_name": "Optional: name for the ZIP file"}
        )
        
        self.register(
            "extract_archive",
            self.executor.file_manager.extract_archive,
            "Extract/unzip a ZIP archive. Use for: 'extract archive.zip', 'unzip this file', 'decompress the zip'",
            {"archive_path": "Path to the ZIP file", "destination": "Optional: extraction directory"}
        )
        
        self.register(
            "get_file_info",
            self.executor.file_manager.get_file_info,
            "Get detailed information about a file or folder (size, type, dates). Use for: 'info about report.pdf', 'how big is this file', 'file details'",
            {"file_path": "Path to the file or folder"}
        )
        
        self.register(
            "list_folder",
            self.executor.file_manager.list_folder,
            "List contents of a folder with details. Use for: 'list files in documents', 'show what's in downloads', 'folder contents'",
            {"location": "Optional: directory to list (default: downloads)", "sort_by": "Optional: sort by 'name', 'size', or 'date' (default: name)"}
        )
        
        # ===== MUSIC CONTROL =====
        self.register(
            "play_music",
            self._play_music_with_prompt,
            "Play music. If no song specified, ASK the user which song they want. Use for: 'play a song', 'play music'. If song name given, play it directly.",
            {"song_name": "Optional: specific song name to play. If empty/None, ASK user what to play."}
        )
        
        self.register(
            "play_random_music",
            self.executor.music_manager.play_random,
            "Play a random song from music library",
            {}
        )
        
        self.register(
            "list_music",
            lambda limit=None, artist=None: self.executor.list_music(limit=int(limit) if limit else None, artist=artist),
            "List songs in music library. Use for: 'list my songs', 'show my music', 'what songs do I have'. Follow-up: 'play the third one'",
            {"limit": "Optional: maximum number of songs to list", "artist": "Optional: filter by artist name"}
        )
        
        # Alias for list_music (LLM sometimes calls this)
        self.register(
            "list_music_library",
            lambda limit=None, artist=None: self.executor.list_music(limit=int(limit) if limit else None, artist=artist),
            "Alias for list_music - List songs in music library",
            {"limit": "Optional: max songs", "artist": "Optional: filter by artist"}
        )
        
        self.register(
            "pause_music",
            self.executor.music_manager.pause,
            "Pause currently playing music",
            {}
        )
        
        self.register(
            "resume_music",
            self.executor.music_manager.resume,
            "Resume paused music (also: continue, unpause, play again)",
            {}
        )
        
        self.register(
            "stop_music",
            self.executor.music_manager.stop,
            "Stop music playback completely",
            {}
        )
        
        self.register(
            "next_song",
            self.executor.music_manager.next_song,
            "Play next song in library",
            {}
        )
        
        self.register(
            "previous_song",
            self.executor.music_manager.previous_song,
            "Play previous song in library",
            {}
        )
        
        self.register(
            "whats_playing",
            self.executor.music_manager.get_current_track,
            "Get information about currently playing song",
            {}
        )
        
        # Aliases for whats_playing (LLM sometimes uses different names)
        self.register(
            "get_current_music",
            self.executor.music_manager.get_current_track,
            "Get currently playing music info",
            {}
        )
        
        self.register(
            "get_current_song_info",
            self.executor.music_manager.get_current_track,
            "Get current song information",
            {}
        )
        
        self.register(
            "music_library_stats",
            self.executor.music_manager.get_library_stats,
            "Get music library statistics (total songs, artists, playtime)",
            {}
        )
        
        self.register(
            "suggest_music",
            lambda count=5, based_on_current=False: self.executor.music_manager.suggest_music(count=count, based_on_current=based_on_current),
            "Suggest random songs from library or similar to current track",
            {
                "count": "Number of songs to suggest (default: 5)",
                "based_on_current": "True to suggest similar to currently playing track (default: False)"
            }
        )
        
        self.register(
            "enable_shuffle",
            self.executor.music_manager.enable_shuffle,
            "Enable shuffle mode - play songs in random order",
            {}
        )
        
        self.register(
            "disable_shuffle",
            self.executor.music_manager.disable_shuffle,
            "Disable shuffle mode - return to sequential playback",
            {}
        )
        
        self.register(
            "set_repeat_mode",
            self.executor.music_manager.set_repeat_mode,
            "Set repeat mode: 'off' (no repeat), 'one' (repeat current song), or 'all' (repeat library)",
            {"mode": "Repeat mode: 'off', 'one', or 'all'"}
        )
        
        self.register(
            "get_playback_mode",
            self.executor.music_manager.get_playback_mode,
            "Get current playback mode (shuffle and repeat status)",
            {}
        )
        
        self.register(
            "play_all_library",
            lambda shuffle=False: self.executor.music_manager.play_all_library(shuffle=shuffle),
            "Play entire music library from beginning (optionally in shuffle mode)",
            {"shuffle": "True to play in random order, False for sequential (default: False)"}
        )
        
        # ===== THEME/UI CONTROL =====
        self.register(
            "switch_theme",
            lambda: self.executor.window.switch_theme() if self.executor.window else "UI not available",
            "Toggle between dark and light theme",
            {}
        )
        
        self.register(
            "set_dark_theme",
            lambda: self.executor.window.switch_theme('dark') if self.executor.window else "UI not available",
            "Switch to dark theme",
            {}
        )
        
        self.register(
            "set_light_theme",
            lambda: self.executor.window.switch_theme('light') if self.executor.window else "UI not available",
            "Switch to light theme",
            {}
        )
        
        # ===== LOCK SCREEN =====
        self.register(
            "lock_nexa",
            lambda: self.executor.window._activate_lock_screen() if self.executor.window else "UI not available",
            "Lock NEXA with password protection. Voice commands: 'lock nexa', 'lock screen', 'lock yourself'",
            {}
        )
        
        # ===== NOTIFICATIONS =====
        self.register(
            "read_notifications",
            self.executor.read_notifications,
            "Read notifications from Windows Action Center",
            {}
        )
        
        # ===== TEXT/CLIPBOARD =====
        self.register(
            "select_all_text",
            self.executor.select_all_text,
            "Select all text (Ctrl+A)",
            {}
        )
        
        self.register(
            "copy_selected_text",
            self.executor.copy_selected,
            "Copy selected text to clipboard (Ctrl+C)",
            {}
        )
        
        self.register(
            "paste_clipboard",
            self.executor.paste_clipboard,
            "Paste clipboard content (Ctrl+V)",
            {}
        )
        
        self.register(
            "cut_selected_text",
            self.executor.cut_selected,
            "Cut selected text to clipboard (Ctrl+X)",
            {}
        )
        
        self.register(
            "delete_selected_text",
            self.executor.delete_selected,
            "Delete currently selected text (Delete key)",
            {}
        )
        
        # ===== CONTENT MODE - Text Refinement & PDF Generation =====
        self.register(
            "enter_content_mode",
            self.executor.enter_content_mode,
            "Enter Content Mode - Opens Content Box window for text editing, refinement, and PDF generation",
            {}
        )
        
        self.register(
            "exit_content_mode",
            self.executor.exit_content_mode,
            "Exit Content Mode - Closes Content Box window and returns to normal operation",
            {}
        )
        
        self.register(
            "mark_content_ready",
            self.executor.mark_content_ready,
            "Mark content as ready - User confirms they've finished pasting/typing content and it's ready for processing. Use when user says: 'I'm ready', 'Done pasting', 'Content ready', 'I've pasted it', etc.",
            {}
        )
        
        self.register(
            "refine_text",
            self.executor.refine_text,
            "Refine or transform text using AI. COMPREHENSIVE MODES: "
            "STUDY TOOLS: extract_terms (key vocabulary), flashcards (Q&A cards), study_questions (test questions), difficulty_check (reading level). "
            "WRITING: formal, shorter, grammar_only, improve, summarize, casual, paraphrase (rewrite), expand (add detail), simplify (easier), academic (scholarly). "
            "ORGANIZATION: outline (hierarchical), add_headings (section titles). "
            "This is the ONLY function for ALL text operations - use the mode parameter!",
            {
                "mode": "REQUIRED: Mode - formal, shorter, grammar_only, improve, summarize, casual, extract_terms, flashcards, study_questions, difficulty_check, paraphrase, expand, simplify, academic, outline, add_headings",
                "text": "Text to process (optional if Content Mode is active)"
            }
        )
        
        self.register(
            "create_pdf",
            self.executor.create_pdf,
            "Create PDF document from text - Formats: simple_text (plain), with_bullets (bulleted list), formatted_paragraphs (advanced formatting with headings)",
            {
                "pdf_format": "PDF format: 'simple_text', 'with_bullets', or 'formatted_paragraphs' (default: simple_text)",
                "filename": "Optional filename (auto-generated if not provided)",
                "text": "Text content (optional if Content Mode is active)",
                "title": "Optional document title"
            }
        )
        
        # ===== CONTENT MODE - FORMATTING (Phase 14) =====
        self.register(
            "format_bold",
            lambda: self.executor.content_window.formatter.toggle_bold() if self.executor.content_window else "Content Mode not active",
            "Apply or remove bold formatting to selected text or at cursor position",
            {}
        )
        
        self.register(
            "format_italic",
            lambda: self.executor.content_window.formatter.toggle_italic() if self.executor.content_window else "Content Mode not active",
            "Apply or remove italic formatting to selected text or at cursor position",
            {}
        )
        
        self.register(
            "format_underline",
            lambda: self.executor.content_window.formatter.toggle_underline() if self.executor.content_window else "Content Mode not active",
            "Apply or remove underline formatting to selected text or at cursor position",
            {}
        )
        
        self.register(
            "format_align",
            lambda alignment: self.executor.content_window.formatter.set_alignment(alignment) if self.executor.content_window else "Content Mode not active",
            "Set text alignment - left, center, right, or justify",
            {"alignment": "Alignment type: 'left', 'center', 'right', or 'justify'"}
        )
        
        self.register(
            "set_font",
            lambda font_name: self.executor.content_window.formatter.set_font_family(font_name) if self.executor.content_window else "Content Mode not active",
            "Change font family (e.g., Arial, Times New Roman, Courier)",
            {"font_name": "Font family name"}
        )
        
        self.register(
            "set_font_size",
            lambda size: self.executor.content_window.formatter.set_font_size(size) if self.executor.content_window else "Content Mode not active",
            "Set font size in points (8-24)",
            {"size": "Font size in points (8-24)"}
        )
        
        self.register(
            "increase_font_size",
            lambda: self.executor.content_window.formatter.increase_font_size() if self.executor.content_window else "Content Mode not active",
            "Make font bigger (increase by 2pt)",
            {}
        )
        
        self.register(
            "decrease_font_size",
            lambda: self.executor.content_window.formatter.decrease_font_size() if self.executor.content_window else "Content Mode not active",
            "Make font smaller (decrease by 2pt)",
            {}
        )
        
        self.register(
            "create_bullet_list",
            lambda: self.executor.content_window.formatter.create_bullet_list() if self.executor.content_window else "Content Mode not active",
            "Create bulleted list from selected paragraphs",
            {}
        )
        
        self.register(
            "create_numbered_list",
            lambda: self.executor.content_window.formatter.create_numbered_list() if self.executor.content_window else "Content Mode not active",
            "Create numbered list from selected paragraphs",
            {}
        )
        
        self.register(
            "increase_indent",
            lambda: self.executor.content_window.formatter.increase_indent() if self.executor.content_window else "Content Mode not active",
            "Increase paragraph indentation",
            {}
        )
        
        self.register(
            "decrease_indent",
            lambda: self.executor.content_window.formatter.decrease_indent() if self.executor.content_window else "Content Mode not active",
            "Decrease paragraph indentation",
            {}
        )
        
        self.register(
            "clear_formatting",
            lambda: self.executor.content_window.formatter.clear_formatting() if self.executor.content_window else "Content Mode not active",
            "Remove all formatting from selected text (make it plain text)",
            {}
        )
        
        # ===== FILE SHARING (Phase 15) =====
        self.register(
            "share_file",
            self.executor.share_file,
            "Open Windows Share dialog with file attached. SMART PATH: Auto-uses last PDF/screenshot if no path given. Say 'share it' or 'share last PDF' or give filename.",
            {
                "file_path": "OPTIONAL: Path/filename (empty = last file, 'report.pdf' searches common folders, full path works too)"
            }
        )
        
        self.register(
            "share_to_whatsapp",
            self.executor.share_to_whatsapp,
            "Share file via WhatsApp. SMART PATH: Auto-uses last PDF/screenshot if no path given. Say 'share on WhatsApp' after creating PDF.",
            {
                "file_path": "OPTIONAL: Path/filename (empty = last file, just filename searches Downloads/Desktop/Documents)"
            }
        )
        
        self.register(
            "share_to_phone",
            self.executor.share_to_phone_nearby,
            "Share file to phone via Windows Nearby Share. SMART PATH: Auto-uses last file. Say 'share to phone' or 'send to my phone'.",
            {
                "file_path": "OPTIONAL: Path/filename (empty = last file)"
            }
        )
        
        self.register(
            "share_via_phone_link",
            self.executor.share_via_phone_link,
            "Share file via Phone Link app to paired phone. SMART PATH: Auto-uses last file. Say 'send via phone link'.",
            {
                "file_path": "OPTIONAL: Path/filename (empty = last file)"
            }
        )
        
        self.register(
            "upload_to_drive",
            self.executor.upload_to_google_drive,
            "Upload file to Google Drive. SMART PATH: Auto-uses last PDF/screenshot. Say 'upload to drive' after creating PDF.",
            {
                "file_path": "OPTIONAL: Path/filename (empty = last file)",
                "folder": "OPTIONAL: Google Drive subfolder name (default: 'Nexa Shared')"
            }
        )
        
        self.register(
            "copy_file_to_clipboard",
            self.executor.copy_file_to_clipboard_action,
            "Copy file to clipboard for pasting. SMART PATH: Auto-uses last file. Say 'copy file' or 'copy it to clipboard'.",
            {
                "file_path": "OPTIONAL: Path/filename (empty = last file)"
            }
        )
        
        # ===== NEXA APPLICATION CONTROL =====
        self.register(
            "exit_nexa",
            self.executor.exit_nexa,
            "Exit/close/shutdown Nexa application. Voice commands: 'exit nexa', 'close nexa', 'shutdown nexa', 'quit nexa', 'goodbye nexa', 'bye nexa'",
            {}
        )
        
        # ===== PHASE 16: SYSTEM POWER CONTROL (via SystemControl module) =====
        self.register(
            "lock_screen",
            self.system_control.lock_screen,
            "Lock the Windows workstation. Voice commands: 'lock screen', 'lock computer', 'lock my PC'",
            {}
        )
        
        self.register(
            "system_sleep",
            self.system_control.system_sleep,
            "Put the computer to sleep. Voice commands: 'sleep', 'put computer to sleep', 'go to sleep'",
            {}
        )
        
        self.register(
            "system_hibernate",
            self.system_control.system_hibernate,
            "Hibernate the computer (saves state to disk). Voice commands: 'hibernate', 'hibernate computer'",
            {}
        )
        
        self.register(
            "system_restart",
            lambda delay_seconds=0: self.system_control.system_restart(delay_seconds=delay_seconds),
            "Restart the computer with a minimum 10-second safety delay. User can cancel by saying 'cancel shutdown'. Voice commands: 'restart', 'restart computer', 'reboot'",
            {"delay_seconds": "Seconds to wait before restart (minimum 10 for safety, default 10)"}
        )
        
        self.register(
            "system_shutdown",
            lambda delay_seconds=0: self.system_control.system_shutdown(delay_seconds=delay_seconds),
            "Shutdown the computer with a minimum 10-second safety delay. User can cancel by saying 'cancel shutdown'. Voice commands: 'shutdown computer', 'turn off computer', 'power off'. NOTE: This is NOT 'shutdown nexa' - use exit_nexa for that.",
            {"delay_seconds": "Seconds to wait before shutdown (minimum 10 for safety, default 10)"}
        )
        
        self.register(
            "schedule_shutdown",
            lambda minutes=30: self.system_control.schedule_shutdown(minutes=minutes),
            "Schedule a shutdown after specified minutes. Voice commands: 'shutdown in 30 minutes', 'schedule shutdown'",
            {"minutes": "Minutes until shutdown (default 30)"}
        )
        
        self.register(
            "schedule_restart",
            lambda minutes=5: self.system_control.schedule_restart(minutes=minutes),
            "Schedule a restart after specified minutes. Voice commands: 'restart in 5 minutes', 'schedule restart'",
            {"minutes": "Minutes until restart (default 5)"}
        )
        
        self.register(
            "cancel_shutdown",
            self.system_control.cancel_shutdown,
            "Cancel a scheduled shutdown or restart. Voice commands: 'cancel shutdown', 'abort shutdown', 'stop shutdown', 'cancel restart'",
            {}
        )
        
        # ===== PHASE 16: POWER PLANS =====
        self.register(
            "get_power_plan",
            self.system_control.get_power_plan,
            "Get the current active power plan. Voice commands: 'what power plan', 'current power plan', 'power mode'",
            {}
        )
        
        self.register(
            "list_power_plans",
            self.system_control.list_power_plans,
            "List all available power plans. Voice commands: 'list power plans', 'show power plans'",
            {}
        )
        
        self.register(
            "set_power_plan",
            lambda plan: self.system_control.set_power_plan(plan=plan),
            "Switch to a different power plan. Voice commands: 'set power plan to balanced', 'high performance mode', 'power saver mode'",
            {"plan": "Plan name: 'balanced', 'high_performance', 'power_saver', or 'ultimate'"}
        )
        
        # ===== PHASE 16: BATTERY SAVER =====
        self.register(
            "enable_battery_saver",
            self.system_control.enable_battery_saver,
            "Enable battery saver mode. Voice commands: 'enable battery saver', 'turn on battery saver', 'save battery'",
            {}
        )
        
        self.register(
            "disable_battery_saver",
            self.system_control.disable_battery_saver,
            "Disable battery saver mode (resets threshold to 20 percent). Voice commands: 'disable battery saver', 'turn off battery saver'",
            {}
        )
        
        # ===== PHASE 16: BLUETOOTH =====
        self.register(
            "get_bluetooth_status",
            self.system_control.get_bluetooth_status,
            "Get Bluetooth status (on/off and connected devices). Voice commands: 'bluetooth status', 'is bluetooth on'",
            {}
        )
        
        self.register(
            "list_bluetooth_devices",
            self.system_control.list_bluetooth_devices,
            "List all paired Bluetooth devices. Voice commands: 'list bluetooth devices', 'show paired devices'",
            {}
        )
        
        self.register(
            "open_bluetooth_settings",
            self.system_control.open_bluetooth_settings,
            "Open Windows Bluetooth settings to pair or manage devices. Voice commands: 'bluetooth settings', 'pair bluetooth', 'connect to my earbuds'",
            {}
        )
        
        self.register(
            "enable_bluetooth",
            self.system_control.enable_bluetooth,
            "Enable Bluetooth adapter. Voice commands: 'enable bluetooth', 'turn on bluetooth', 'bluetooth on'",
            {}
        )
        
        self.register(
            "disable_bluetooth",
            self.system_control.disable_bluetooth,
            "Disable Bluetooth adapter. Voice commands: 'disable bluetooth', 'turn off bluetooth', 'bluetooth off'",
            {}
        )
        
        self.register(
            "connect_bluetooth_device",
            lambda device_name: self.system_control.connect_bluetooth_device(device_name=device_name),
            "Connect to a paired Bluetooth device by name. Voice commands: 'connect to Galaxy Buds', 'connect my headphones', 'connect AirPods'",
            {"device_name": "Name of the Bluetooth device to connect to (e.g., 'Galaxy Buds Pro', 'AirPods', 'JBL Speaker')"}
        )
        
        self.register(
            "disconnect_bluetooth_device",
            lambda device_name: self.system_control.disconnect_bluetooth_device(device_name=device_name),
            "Disconnect a Bluetooth device by name. Voice commands: 'disconnect Galaxy Buds', 'disconnect my headphones'",
            {"device_name": "Name of the Bluetooth device to disconnect"}
        )
        
        # ===== PHASE 16: QUICK SETTINGS =====
        self.register(
            "toggle_airplane_mode",
            self.system_control.toggle_airplane_mode,
            "Toggle airplane mode on or off. Actually toggles via registry, not just settings. Voice commands: 'airplane mode', 'flight mode', 'toggle airplane mode'",
            {}
        )
        
        self.register(
            "enable_night_light",
            self.system_control.enable_night_light,
            "Enable Night Light (blue light filter). Voice commands: 'enable night light', 'turn on night light', 'blue light on'",
            {}
        )
        
        self.register(
            "disable_night_light",
            self.system_control.disable_night_light,
            "Disable Night Light (blue light filter). Voice commands: 'disable night light', 'turn off night light', 'night light off'",
            {}
        )
        
        self.register(
            "toggle_night_light",
            self.system_control.toggle_night_light,
            "Toggle Night Light on or off (checks current state and switches). Voice commands: 'toggle night light', 'switch night light'",
            {}
        )
        
        self.register(
            "open_accessibility_settings",
            self.system_control.open_accessibility_settings,
            "Open Windows accessibility settings. Voice commands: 'accessibility', 'ease of access'",
            {}
        )
        
        self.register(
            "set_display_projection",
            lambda mode="extend": self.system_control.set_display_projection(mode=mode),
            "Set display projection mode (PC only, duplicate, extend, second screen only). Voice commands: 'extend display', 'duplicate screen', 'second screen only', 'PC screen only'",
            {"mode": "Projection mode: 'internal' (PC only), 'clone' (duplicate/mirror), 'extend', 'external' (second screen only)"}
        )
        
        self.register(
            "open_cast_settings",
            self.system_control.open_cast_settings,
            "Open cast settings for wireless displays. Voice commands: 'cast settings', 'connect to TV', 'wireless display', 'miracast'",
            {}
        )
        
        self.register(
            "open_nearby_share",
            self.system_control.open_nearby_share,
            "Open nearby sharing settings. Voice commands: 'nearby share', 'nearby sharing'",
            {}
        )
        
        self.register(
            "check_windows_update",
            self.system_control.check_windows_update,
            "Actually check for pending Windows updates and return update names/counts. Voice commands: 'check for updates', 'windows update', 'update windows', 'any updates available'",
            {}
        )
        
        self.register(
            "toggle_focus_assist",
            lambda mode="toggle": self.system_control.toggle_focus_assist(mode=mode),
            "Toggle Focus Assist / Do Not Disturb. Cycles through Off, Priority Only, Alarms Only. Voice commands: 'focus assist', 'do not disturb', 'focus mode', 'quiet hours'",
            {"mode": "Focus assist mode: 'off', 'priority', 'alarms', or 'toggle' (cycles through, default)"}
        )
        
        self.register(
            "sign_out",
            self.system_control.sign_out,
            "Sign out / log off the current Windows user. Voice commands: 'sign out', 'log off', 'log out'",
            {}
        )
        
        # ===== SMART MEMORY (Phase 19) =====
        self.register(
            "remember_this",
            self._remember_this,
            "Store a fact or preference about the user. IMPORTANT: The 'fact' parameter MUST include FULL CONTEXT — e.g. 'User's name is Ali' NOT just 'Ali', 'User's favorite color is blue' NOT just 'blue'. Voice commands: 'remember that...', 'note that...'",
            {"fact": "The FULL contextual fact to remember (e.g., 'User's name is Ali', 'User's father is Vasim', 'User prefers dark theme') — NEVER just a single word!"}
        )
        
        self.register(
            "forget_about",
            self._forget_about,
            "Forget memories matching a topic. Voice commands: 'forget about...', 'delete memories about...'",
            {"topic": "Topic to forget (e.g., 'my old address')"}
        )
        
        self.register(
            "what_do_you_know",
            self._what_do_you_know,
            "🧠🧠🧠 MEMORY RECALL (USE FOR ALL PERSONAL/RELATIONSHIP QUESTIONS!) 🧠🧠🧠 - MANDATORY for: 'who is [any name]', 'my [any relation]' (friend, brother, sister, mother, girlfriend, cousin, boss, etc.), 'do you know [X]', 'tell me about [person]', 'my birthday', 'favorite X'. NEVER say 'I don't know' about people - ALWAYS call this function FIRST!",
            {"topic": "The person name, relationship type, or info to look up (e.g., 'Saliha', 'brother', 'girlfriend', 'birthday', 'favorite color')"}
        )
        
        self.register(
            "get_memory_stats",
            self._get_memory_stats,
            "Get statistics about stored memories. Voice commands: 'memory stats', 'how many memories'",
            {}
        )
        
        self.register(
            "show_memory_panel",
            self._show_memory_panel,
            "Open the Memory Management panel. Voice commands: 'show my memories', 'open memory panel', 'manage memories'",
            {}
        )
        
        self.register(
            "clear_old_memory",
            self._clear_old_memory,
            "Clear memories older than 30 days. Voice commands: 'clear old memories', 'delete old memories', 'cleanup memory'",
            {}
        )
        
        self.register(
            "clear_all_memory",
            self._clear_all_memory,
            "Clear ALL memories (conversations, knowledge, skills). Voice commands: 'clear all memory', 'wipe memory', 'reset memory', 'forget everything'",
            {}
        )
        
        self.register(
            "list_functions",
            self._list_functions,
            "List all available Nexa functions/capabilities. Use when user asks: 'what can you do', 'show your abilities', 'list functions', 'what are your features'",
            {}
        )
        
        # ===== TTS ENGINE CONTROL =====
        self.register(
            "switch_tts_engine",
            self._switch_tts_engine,
            "Switch TTS voice engine. Options: 'kokoro' (fast, default) or 'coqui' (cloned voice, better emotions). Voice: 'switch to coqui voice', 'use kokoro', 'change voice engine'",
            {"engine": "TTS engine to use: 'kokoro' (fast) or 'coqui' (cloned voice with emotions)"}
        )
        
        self.register(
            "get_tts_engine",
            self._get_tts_engine,
            "Get the current TTS engine being used. Voice: 'what voice engine are you using', 'which TTS engine'",
            {}
        )
        
        # ===== PROACTIVE ENGAGEMENT (Phase 29) =====
        self.register(
            "accept_proactive_suggestion",
            self._accept_proactive_suggestion,
            "User accepts a proactive suggestion. Voice: 'yes', 'sure', 'okay', 'sounds good', 'go ahead' (when responding to a proactive suggestion)",
            {}
        )
        
        self.register(
            "decline_proactive_suggestion",
            self._decline_proactive_suggestion,
            "User declines a proactive suggestion. Voice: 'no thanks', 'not now', 'I'm fine', 'maybe later' (when responding to a proactive suggestion)",
            {}
        )
        
        # ===== EMOTIONAL INTELLIGENCE (Phase 30) =====
        self.register(
            "journal_thought",
            self._journal_thought,
            "Store a user's thought, reflection, or something they want to remember emotionally. Voice: 'remember that I felt...', 'journal this thought...', 'I want to write down...', 'note my feeling...'",
            {"thought": "The user's thought or reflection to journal"}
        )
        
        self.register(
            "track_goal",
            self._track_goal,
            "Start tracking a personal goal or aspiration. Voice: 'I want to learn guitar', 'my goal is to...', 'track my goal...', 'I'm working on...'",
            {"goal_name": "Name of the goal (e.g., 'learn guitar', 'get fit', 'read more')",
             "description": "(Optional) Detailed description of the goal"}
        )
        
        self.register(
            "update_goal",
            self._update_goal,
            "Update progress on a tracked goal. Voice: 'I made progress on...', 'update my goal...', 'I completed my goal...'",
            {"goal_name": "Name of the goal to update",
             "status": "(Optional) New status: 'active', 'paused', 'completed', 'abandoned'",
             "progress_note": "(Optional) Progress note to add"}
        )
        
        self.register(
            "get_my_goals",
            self._get_my_goals,
            "List user's active goals and their status. Voice: 'what are my goals', 'show my goals', 'goal progress'",
            {}
        )
        
        self.register(
            "get_my_mood",
            self._get_my_mood,
            "Get summary of user's recent mood/emotional state. Voice: 'how have I been feeling', 'my mood today', 'mood summary'",
            {}
        )
    
    # Functions that require internet connection (blocked in offline mode)
    # Messages are user-friendly with clear instructions on how to enable
    INTERNET_REQUIRED_FUNCTIONS = {
        "get_weather": "I can't check the weather right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "get_forecast": "I can't get the forecast right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "search_web": "I can't search the web right now because I'm in offline mode. Say 'go online' to enable internet features.",
        # YouTube (Phase 18 - all require internet)
        "play_youtube": "I can't play YouTube videos right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "search_youtube": "I can't search YouTube right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "play_youtube_result": "I can't play YouTube videos right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "get_video_info": "I can't get video info right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "download_youtube": "I can't download from YouTube right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "download_youtube_video": "I can't download videos right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "download_youtube_audio": "I can't download audio right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "get_download_status": "No downloads are active in offline mode. Say 'go online' to enable internet features.",
        "get_youtube_queue": "YouTube queue is not available in offline mode. Say 'go online' to enable internet features.",
        "clear_youtube_queue": "YouTube queue is not available in offline mode. Say 'go online' to enable internet features.",
        "get_video_transcript": "I can't get video transcripts right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "get_trending_videos": "I can't check trending videos right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "get_channel_videos": "I can't browse YouTube channels right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "play_youtube_playlist": "I can't play YouTube playlists right now because I'm in offline mode. Say 'go online' to enable internet features.",
        # Enhanced Web Search (Phase 18)
        "smart_search": "I can't search the web right now because I'm in offline mode. Say 'go online' to enable internet features.",
        "scrape_url": "I can't access web pages right now because I'm in offline mode. Say 'go online' to enable internet features.",
    }
    
    def _is_offline_mode(self) -> bool:
        """Check if we're currently in offline mode."""
        try:
            # Access llm_manager through executor -> brain -> llm_manager
            if hasattr(self.executor, 'brain') and self.executor.brain:
                from capabilities.llm.llm_manager import LLMMode
                llm_manager = self.executor.brain.llm_manager
                if llm_manager:
                    current_mode = llm_manager.get_current_mode()
                    return current_mode == LLMMode.OFFLINE
        except Exception as e:
            logger.debug(f"Error checking offline mode: {e}")
        return False  # Default to online if we can't determine
    
    def call(self, function_name: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Execute a function by name with parameters.
        
        Tracks skill usage in Smart Memory for learning.
        
        Args:
            function_name: Name of function to call
            parameters: Dict of parameter values
            
        Returns:
            Function result as string
        """
        if function_name not in self.functions:
            logger.error(f"Unknown function: {function_name}")
            return f"Error: Unknown function '{function_name}'"
        
        # Check if this function requires internet and we're offline
        if function_name in self.INTERNET_REQUIRED_FUNCTIONS:
            if self._is_offline_mode():
                blocked_msg = self.INTERNET_REQUIRED_FUNCTIONS[function_name]
                logger.warning(f"🔒 Function '{function_name}' blocked - offline mode")
                return blocked_msg
        
        func_info = self.functions[function_name]
        func = func_info["function"]
        
        success = False
        result = None
        
        try:
            # Call function with or without parameters
            if parameters:
                logger.debug(f"Calling {function_name} with params: {parameters}")
                result = func(**parameters)
            else:
                logger.debug(f"Calling {function_name} (no params)")
                result = func()
            
            success = True
            result_str = str(result) if result is not None else "Done"
            
        except Exception as e:
            logger.error(f"Error calling {function_name}: {e}", exc_info=True)
            result_str = f"Error executing {function_name}: {str(e)}"
            success = False
        
        # Track skill in Smart Memory (non-blocking)
        self._track_skill_async(function_name, parameters or {}, success)
        
        return result_str
    
    def _track_skill_async(self, action: str, params: Dict[str, Any], success: bool) -> None:
        """
        Track skill usage in Smart Memory (background thread).
        
        Args:
            action: Function name
            params: Parameters used
            success: Whether it succeeded
        """
        if not self.context_manager:
            return
        
        try:
            import threading
            
            def track():
                try:
                    sm = getattr(self.context_manager, 'smart_memory', None)
                    if sm and hasattr(sm, 'track_skill'):
                        sm.track_skill(action, params, success)
                        logger.debug(f"🎯 Tracked skill: {action} (success={success})")
                        # Notify Memory Panel for live refresh
                        eb = getattr(self.context_manager, '_event_bus', None)
                        if eb:
                            try:
                                eb.publish("memory.updated", source="skill")
                            except Exception:
                                pass
                except Exception as e:
                    logger.debug(f"Skill tracking failed (non-critical): {e}")
            
            threading.Thread(target=track, daemon=True).start()
            
        except Exception as e:
            logger.debug(f"Skill tracking setup failed: {e}")
    
    def get_catalog(self, format_type: str = "detailed") -> str:
        """
        Get function catalog for AI prompt.
        
        Args:
            format_type: 'detailed' or 'compact'
            
        Returns:
            Formatted string of available functions
        """
        if format_type == "compact":
            # Short version for faster prompts
            return ", ".join(self.functions.keys())
        
        # Detailed version with descriptions
        catalog = []
        for name, info in self.functions.items():
            if info["parameters"]:
                params_list = [f"{k}: {v}" for k, v in info["parameters"].items()]
                params_str = ", ".join(params_list)
                catalog.append(f"- {name}({params_str}) - {info['description']}")
            else:
                catalog.append(f"- {name}() - {info['description']}")
        
        return "\n".join(catalog)
    
    def list_functions(self) -> list:
        """Get list of all registered function names."""
        return list(self.functions.keys())
    
    def _list_functions(self) -> str:
        """
        Return a user-friendly summary of NEXA's capabilities.
        This is the registered function for LLM to call.
        """
        capabilities = {
            "🖥️ System Control": [
                "Open/close applications",
                "Adjust volume and brightness",
                "Window management (minimize, maximize, close)",
                "Screenshot capture",
                "System info (battery, CPU, RAM, GPU)"
            ],
            "🎵 Music & Media": [
                "Play/pause/skip music",
                "Search music library",
                "Volume control"
            ],
            "🌐 Online Features": [
                "Web search",
                "Weather information",
                "PDF creation and sharing"
            ],
            "🎮 Gaming": [
                "List installed games (Steam, Epic, GOG)",
                "Launch games by name"
            ],
            "🧠 Memory & Learning": [
                "Remember things you tell me",
                "Recall your preferences",
                "Learn from our conversations"
            ],
            "📝 Text & Content": [
                "Refine and improve text",
                "Generate PDFs",
                "Content mode for focused writing"
            ],
            "🔌 Connectivity": [
                "WiFi status and management",
                "Network information"
            ]
        }
        
        lines = [f"I can help you with {len(self.functions)} different functions! Here are my main capabilities:\n"]
        for category, features in capabilities.items():
            lines.append(f"\n{category}:")
            for feature in features:
                lines.append(f"  • {feature}")
        
        lines.append(f"\n\nJust ask naturally - I understand conversational commands!")
        return "\n".join(lines)
    
    def _switch_tts_engine(self, engine: str) -> str:
        """
        Switch TTS engine between Kokoro and Coqui.
        
        Args:
            engine: 'kokoro' or 'coqui'
            
        Returns:
            Success/failure message
        """
        engine = engine.lower().strip()
        
        if engine not in ('kokoro', 'coqui'):
            return f"Unknown TTS engine '{engine}'. Use 'kokoro' (fast, default) or 'coqui' (cloned voice with emotions)."
        
        try:
            # Access brain through executor
            if hasattr(self.executor, 'brain') and self.executor.brain:
                success = self.executor.brain.switch_tts_engine(engine)
                if success:
                    if engine == 'coqui':
                        return "Switched to Coqui XTTS with the cloned voice. This voice has better emotional range but uses more GPU memory."
                    else:
                        return "Switched to Kokoro TTS. This is the fast, lightweight engine with the af_heart voice."
                else:
                    return f"Failed to switch to {engine} engine. It may not be available."
            else:
                return "Cannot switch engine - brain not accessible."
        except Exception as e:
            logger.error(f"Error switching TTS engine: {e}")
            return f"Error switching TTS engine: {str(e)}"
    
    def _get_tts_engine(self) -> str:
        """Get the current TTS engine name."""
        try:
            if hasattr(self.executor, 'brain') and self.executor.brain:
                engine_name = self.executor.brain.get_tts_engine_name()
                if 'Coqui' in engine_name:
                    return "I'm currently using the Coqui XTTS engine with the cloned voice for better emotional expressions."
                else:
                    return "I'm currently using the Kokoro TTS engine with the af_heart voice. It's fast and lightweight."
            return "TTS engine info not available."
        except Exception as e:
            return f"Error getting TTS engine info: {str(e)}"
    
    def has_function(self, function_name: str) -> bool:
        """Check if function is registered."""
        return function_name in self.functions
    
    def get_function_description(self, function_name: str) -> Optional[str]:
        """
        Return the human-readable description for a registered function.

        Args:
            function_name: Name of the registered function

        Returns:
            Description string if found, otherwise None
        """
        info = self.functions.get(function_name)
        if not info:
            logger.debug(f"get_function_description: function not found: {function_name}")
            return None
        return info.get("description")

    def get_function_info(self, function_name: str) -> Optional[Dict[str, Any]]:
        """
        Return the full info dict for a registered function (function callable, description, parameters).

        Args:
            function_name: Name of the registered function

        Returns:
            Dict with keys 'function', 'description', 'parameters' or None if not found
        """
        return self.functions.get(function_name)
    
    # =========================================================================
    # MUSIC COMMAND IMPLEMENTATIONS
    # =========================================================================
    
    def _play_music_with_prompt(self, song_name: str = None) -> str:
        """
        Play music with user prompt if no song specified.
        
        If song_name is provided, play that song.
        If not, ask the user what they want to play (random, specific song, shuffle, etc.)
        """
        # Check for keywords that indicate random/shuffle
        if song_name:
            song_lower = song_name.lower().strip()
            if song_lower in ['random', 'shuffle', 'anything', 'surprise me', 'whatever']:
                return self.executor.music_manager.play_random()
            elif song_lower:
                # User specified a song - play it
                return self.executor.music_manager.play_song(song_name=song_name)
        
        # No song specified - ask what they want
        # Set up follow-up state to wait for user response
        try:
            # Use self.context_manager (passed to FunctionRegistry) for reliability
            context = self.context_manager
            if not context:
                # Fallback to executor.brain.context_manager
                context = getattr(getattr(self.executor, 'brain', None), 'context_manager', None)
            
            if not context:
                logger.error("🎵 No context_manager available!")
                return "What song would you like me to play?"
                
            logger.info(f"🎵 Setting pending intent for play_music")
            logger.info(f"🎵 IntentState available: {hasattr(context, 'intent_state') and context.intent_state is not None}")
            
            if hasattr(context, 'set_pending_intent'):
                context.set_pending_intent(
                    intent='play_music',
                    data_needed='song_name',
                    collected_data={}
                )
                logger.info("🎵 Pending intent SET successfully")
                
                # Verify it was set
                if hasattr(context, 'has_pending_follow_up'):
                    logger.info(f"🎵 Verification - has_pending_follow_up: {context.has_pending_follow_up()}")
            else:
                logger.warning("🎵 set_pending_intent method not found on context_manager!")
                
            return "What would you like to play? Say a song name, 'random' for a surprise, or 'list songs' to see options."
        except Exception as e:
            logger.error(f"Error setting pending intent: {e}", exc_info=True)
            return "What song would you like me to play?"
    
    # =========================================================================
    # SMART MEMORY COMMAND IMPLEMENTATIONS (Phase 19)
    # =========================================================================
    
    def _remember_this(self, fact: str) -> str:
        """Store a fact about the user in Smart Memory."""
        try:
            context = self.executor.brain.context_manager
            if not hasattr(context, 'learn_user_fact') or not context.smart_memory:
                return "Smart Memory is not available"
            
            memory_id = context.learn_user_fact(fact, source='user_stated')
            if memory_id:
                return f"Got it! I'll remember: '{fact}'"
            else:
                return "I couldn't save that right now"
        except Exception as e:
            logger.error(f"Error in remember_this: {e}")
            return "Something went wrong saving that"
    
    def _forget_about(self, topic: str) -> str:
        """Forget memories matching a topic."""
        try:
            context = self.executor.brain.context_manager
            if not hasattr(context, 'forget_memories') or not context.smart_memory:
                return "Smart Memory is not available"
            
            count = context.forget_memories(topic, limit=10)
            if count > 0:
                return f"Done! I forgot {count} memories about '{topic}'"
            else:
                return f"I don't have any memories about '{topic}'"
        except Exception as e:
            logger.error(f"Error in forget_about: {e}")
            return "Something went wrong"
    
    def _what_do_you_know(self, topic: str) -> str:
        """
        Recall knowledge about a topic and provide a NATURAL answer.
        
        Prioritizes knowledge facts (explicitly remembered) over conversations.
        Formats responses naturally like a human would answer.
        """
        try:
            context = self.executor.brain.context_manager
            if not hasattr(context, 'recall_knowledge_answer') or not context.smart_memory:
                return "Smart Memory is not available"
            
            # Use the new intelligent recall (prioritizes knowledge)
            result = context.recall_knowledge_answer(topic, limit=3)
            
            if not result.get('found'):
                return f"I don't remember anything about '{topic}'. You can tell me and I'll remember it!"
            
            # Get the best matching fact
            best_fact = result.get('best_match', '')
            all_facts = result.get('facts', [])
            
            # Format response naturally based on the question type
            response = self._format_knowledge_response(topic, best_fact, all_facts)
            return response
            
        except Exception as e:
            logger.error(f"Error in what_do_you_know: {e}")
            return "Something went wrong"
    
    def _format_knowledge_response(self, topic: str, best_fact: str, all_facts: list) -> str:
        """
        Format knowledge into a natural response.
        
        Adds date awareness for temporal questions (birthday, anniversary, etc.)
        """
        from datetime import datetime
        
        topic_lower = topic.lower()
        
        # Handle birthday questions specially
        if 'birthday' in topic_lower or 'born' in topic_lower:
            return self._format_birthday_response(best_fact)
        
        # Handle anniversary/date-based questions
        if any(word in topic_lower for word in ['anniversary', 'date', 'when']):
            return self._format_date_response(best_fact)
        
        # For preference questions (favorite X)
        if 'favorite' in topic_lower or 'prefer' in topic_lower:
            return self._format_preference_response(topic, best_fact, all_facts)
        
        # Generic response - just return the fact naturally
        if len(all_facts) == 1:
            return best_fact
        elif len(all_facts) > 1:
            # Multiple related facts
            return f"{best_fact}"  # Return just the most relevant one
        
        return best_fact
    
    def _format_birthday_response(self, fact: str) -> str:
        """Format birthday response with date awareness."""
        from datetime import datetime
        import re
        
        today = datetime.now()
        
        # Try to extract date from fact
        # Common patterns: "December 9", "9th of December", "Dec 9", "12/9"
        month_names = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
            'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
        
        fact_lower = fact.lower()
        bday_month = None
        bday_day = None
        
        # Pattern: "December 9" or "Dec 9"
        for month_name, month_num in month_names.items():
            pattern = rf'{month_name}\s+(\d{{1,2}})'
            match = re.search(pattern, fact_lower)
            if match:
                bday_month = month_num
                bday_day = int(match.group(1))
                break
            # Pattern: "9th of December" or "9 December"
            pattern = rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?{month_name}'
            match = re.search(pattern, fact_lower)
            if match:
                bday_month = month_num
                bday_day = int(match.group(1))
                break
        
        if bday_month and bday_day:
            # Calculate how close the birthday is
            try:
                this_year_bday = datetime(today.year, bday_month, bday_day)
                next_year_bday = datetime(today.year + 1, bday_month, bday_day)
                
                days_since = (today - this_year_bday).days
                days_until = (this_year_bday - today).days if this_year_bday > today else (next_year_bday - today).days
                
                if days_since == 0:
                    return f"Your birthday is TODAY! 🎂 Happy Birthday!"
                elif 0 < days_since <= 7:
                    return f"Your birthday was {days_since} day{'s' if days_since > 1 else ''} ago on {this_year_bday.strftime('%B %d')}! Hope you had a great one! 🎉"
                elif 0 < days_since <= 30:
                    return f"Your birthday was recently on {this_year_bday.strftime('%B %d')} - just {days_since} days ago!"
                elif 0 < days_until <= 7:
                    return f"Your birthday is coming up in {days_until} day{'s' if days_until > 1 else ''}! It's on {this_year_bday.strftime('%B %d')}. 🎂"
                elif 0 < days_until <= 30:
                    return f"Your birthday is on {this_year_bday.strftime('%B %d')} - that's in {days_until} days!"
                else:
                    return f"Your birthday is on {this_year_bday.strftime('%B %d')}."
            except ValueError:
                pass
        
        # Couldn't parse date, return the fact as-is
        return fact
    
    def _format_date_response(self, fact: str) -> str:
        """Format date-based response."""
        # For now, return the fact as-is
        # Could be enhanced to calculate days until/since
        return fact
    
    def _format_preference_response(self, topic: str, best_fact: str, all_facts: list) -> str:
        """Format preference response naturally."""
        # Just return the fact - it should already be natural
        # e.g., "Your favorite color is black"
        return best_fact

    def _get_memory_stats(self) -> str:
        """Get memory statistics."""
        try:
            context = self.executor.brain.context_manager
            if not hasattr(context, 'get_memory_stats'):
                return "Smart Memory is not available"
            
            stats = context.get_memory_stats()
            if stats.get('status') != 'available':
                return "Smart Memory is not available"
            
            return (
                f"📊 Memory Stats:\n"
                f"• Conversations: {stats.get('conversations', 0)}\n"
                f"• Knowledge facts: {stats.get('knowledge', 0)}\n"
                f"• Skills tracked: {stats.get('skills', 0)}"
            )
        except Exception as e:
            logger.error(f"Error in get_memory_stats: {e}")
            return "Something went wrong"
    
    def _show_memory_panel(self) -> str:
        """Open the Memory Management panel (via main thread signal)."""
        try:
            brain = self.executor.brain
            if not brain:
                return "Brain not available"
            
            # Get the main window and emit signal to create panel in main thread
            # This follows the same pattern as Content Mode window creation
            if hasattr(brain, 'window') and brain.window:
                if hasattr(brain.window, 'memory_panel_requested'):
                    brain.window.memory_panel_requested.emit()
                    return "Opening Memory Panel..."
                else:
                    return "Memory Panel signal not available - try clicking the 🧠 button"
            else:
                return "Window not available - try clicking the 🧠 button"
                
        except Exception as e:
            logger.error(f"Error opening memory panel: {e}")
            return f"Couldn't open memory panel: {str(e)}"
    
    def _clear_old_memory(self) -> str:
        """Clear memories older than 30 days."""
        try:
            context = self.executor.brain.context_manager
            if not hasattr(context, 'smart_memory') or not context.smart_memory:
                return "Smart Memory is not available"
            
            deleted = context.smart_memory.prune_old_memories(days=30, keep_important=True)
            
            if deleted > 0:
                return f"Done! I cleared {deleted} old memories (older than 30 days). Important memories were kept."
            else:
                return "No old memories to clear. Your memory is already clean!"
                
        except Exception as e:
            logger.error(f"Error in clear_old_memory: {e}")
            return "Something went wrong while clearing old memories"
    
    def _clear_all_memory(self) -> str:
        """Clear ALL memories (requires confirmation in conversation)."""
        try:
            context = self.executor.brain.context_manager
            if not hasattr(context, 'smart_memory') or not context.smart_memory:
                return "Smart Memory is not available"
            
            result = context.smart_memory.clear_all_memory(include_knowledge=True)
            total = sum(result.values())
            
            if total > 0:
                return f"Done! I've cleared all my memories. Deleted {result['conversations']} conversations, {result['knowledge']} knowledge facts, and {result['skills']} skill patterns. Starting fresh!"
            else:
                return "Memory was already empty. Nothing to clear!"
                
        except Exception as e:
            logger.error(f"Error in clear_all_memory: {e}")
            return "Something went wrong while clearing memory"

    # ========================================
    # PHASE 29: PROACTIVE ENGAGEMENT HANDLERS
    # ========================================
    
    def _accept_proactive_suggestion(self) -> str:
        """Handle user accepting a proactive suggestion."""
        return self.executor.accept_proactive_suggestion()
    
    def _decline_proactive_suggestion(self) -> str:
        """Handle user declining a proactive suggestion."""
        return self.executor.decline_proactive_suggestion()
    
    # =========================================================================
    # Phase 30: Emotional Intelligence Functions
    # =========================================================================
    
    def _journal_thought(self, thought: str = "") -> str:
        """Store a user's thought/reflection in emotional memory."""
        if not thought:
            return "What thought would you like me to journal?"
        try:
            from core.companion import get_emotional_memory, get_mood_tracker
            emotional_memory = get_emotional_memory()
            if not emotional_memory:
                return "Emotional memory is not available right now."
            
            # Get current mood for context
            current_mood = "neutral"
            mood_tracker = get_mood_tracker()
            if mood_tracker:
                current_mood = mood_tracker.get_current_mood().current_mood
            
            entry_id = emotional_memory.journal_thought(thought, emotion=current_mood)
            return f"I've journaled that thought for you. I'll remember this."
        except Exception as e:
            logger.error(f"Journal thought failed: {e}")
            return "I couldn't save that thought right now. Please try again."
    
    def _track_goal(self, goal_name: str = "", description: str = "") -> str:
        """Start tracking a new goal."""
        if not goal_name:
            return "What goal would you like me to track?"
        try:
            from core.companion import get_emotional_memory
            emotional_memory = get_emotional_memory()
            if not emotional_memory:
                return "Emotional memory is not available right now."
            
            goal_id = emotional_memory.track_goal(
                name=goal_name,
                description=description or goal_name
            )
            return f"I'm now tracking your goal: '{goal_name}'. I'll check in with you periodically to see how it's going!"
        except Exception as e:
            logger.error(f"Track goal failed: {e}")
            return "I couldn't set up that goal right now. Please try again."
    
    def _update_goal(self, goal_name: str = "", status: str = "", progress_note: str = "") -> str:
        """Update a tracked goal."""
        if not goal_name:
            return "Which goal would you like to update?"
        try:
            from core.companion import get_emotional_memory
            emotional_memory = get_emotional_memory()
            if not emotional_memory:
                return "Emotional memory is not available right now."
            
            # Try to find the goal by name
            active_goals = emotional_memory.get_active_goals()
            found_goal = None
            goal_name_lower = goal_name.lower()
            for g in active_goals:
                if goal_name_lower in g.name.lower() or g.name.lower() in goal_name_lower:
                    found_goal = g
                    break
            
            # Also check all goals (not just active)
            if not found_goal:
                for g in emotional_memory._goals.values():
                    if goal_name_lower in g.name.lower() or g.name.lower() in goal_name_lower:
                        found_goal = g
                        break
            
            if not found_goal:
                return f"I don't have a goal called '{goal_name}'. Would you like me to start tracking it?"
            
            success = emotional_memory.update_goal(
                goal_id=found_goal.id,
                status=status or None,
                progress_note=progress_note or None
            )
            
            if success:
                if status == "completed":
                    emotional_memory.celebrate_milestone('first_goal_completed')
                    return f"Congratulations! You've completed your goal: '{found_goal.name}'! That's amazing!"
                elif status:
                    return f"Updated goal '{found_goal.name}' to status: {status}."
                elif progress_note:
                    return f"Added progress note to '{found_goal.name}'. Keep it up!"
                else:
                    return f"Goal '{found_goal.name}' has been updated."
            return f"Could not update goal '{goal_name}'."
        except Exception as e:
            logger.error(f"Update goal failed: {e}")
            return "I couldn't update that goal right now. Please try again."
    
    def _get_my_goals(self) -> str:
        """List user's active goals."""
        try:
            from core.companion import get_emotional_memory
            emotional_memory = get_emotional_memory()
            if not emotional_memory:
                return "Emotional memory is not available right now."
            
            active_goals = emotional_memory.get_active_goals()
            if not active_goals:
                return "You don't have any active goals right now. Would you like to set one?"
            
            lines = [f"You have {len(active_goals)} active goal(s):"]
            for i, g in enumerate(active_goals, 1):
                days_active = int((time.time() - g.created_at) / 86400)
                notes_count = len(g.progress_notes)
                lines.append(f"  {i}. {g.name} (tracking for {days_active} days, {notes_count} progress notes)")
            
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Get goals failed: {e}")
            return "I couldn't retrieve your goals right now."
    
    def _get_my_mood(self) -> str:
        """Get user's mood summary."""
        try:
            from core.companion import get_mood_tracker
            mood_tracker = get_mood_tracker()
            if not mood_tracker:
                return "Mood tracking is not available right now."
            
            summary = mood_tracker.get_mood_summary(hours=24)
            
            if summary['readings_count'] == 0:
                return "I haven't detected enough emotional cues yet to give you a mood summary. Keep talking to me and I'll learn your patterns!"
            
            mood = summary['dominant_mood']
            count = summary['readings_count']
            valence = summary['average_valence']
            trend = summary['trend']
            
            # Build natural response
            valence_desc = "positive" if valence > 0.2 else "negative" if valence < -0.2 else "neutral"
            trend_desc = ""
            if trend == "improving":
                trend_desc = " Your mood seems to be improving, which is great!"
            elif trend == "declining":
                trend_desc = " I've noticed your mood has been dipping. I'm here for you if you need anything."
            
            return (f"Based on our {count} recent interactions, your dominant mood has been "
                    f"'{mood}' with an overall {valence_desc} tone.{trend_desc}")
        except Exception as e:
            logger.error(f"Get mood failed: {e}")
            return "I couldn't analyze your mood right now."