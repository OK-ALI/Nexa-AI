"""
YouTube Service Module
======================

Provides YouTube video playback, search, and audio streaming
for NEXA AI assistant, using yt-dlp (no API key required).

All functions require ONLINE mode (internet connection).

Features:
- Play YouTube videos by name/URL in browser
- Search YouTube and return results
- Audio-only streaming (background music from YouTube)
- Video info/metadata extraction
- Queue management for continuous playback

Dependencies:
- yt-dlp: Video/audio extraction (pip install yt-dlp)
- No API keys required - 100% free

Author: Nexa AI Team
Phase: 18 - YouTube Integration
"""

import logging
import shutil
import subprocess
import threading
import webbrowser
import time
import json
import re
import os
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)

# Optional imports
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logger.warning("⚠️ yt-dlp not installed. YouTube features limited. Install: pip install yt-dlp")


class YouTubeService:
    """
    YouTube integration service for NEXA AI.
    
    Provides search, playback, audio streaming, video/audio downloading,
    and metadata extraction using yt-dlp (no API key needed).
    
    All methods are online-only and will be blocked in offline mode
    by the function registry's INTERNET_REQUIRED_FUNCTIONS check.
    """
    
    # Video quality presets — prefer pre-merged formats that work WITHOUT ffmpeg,
    # fall back to separate streams (requires ffmpeg for merge) only as last resort.
    QUALITY_PRESETS_FFMPEG = {
        '360p':  'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]',
        '480p':  'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]',
        '720p':  'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]',
        '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]',
        '1440p': 'bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440][ext=mp4]/best[height<=1440]',
        '4k':    'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160][ext=mp4]/best[height<=2160]',
        'best':  'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    }
    QUALITY_PRESETS_NO_FFMPEG = {
        '360p':  'best[height<=360][ext=mp4]/best[height<=360]',
        '480p':  'best[height<=480][ext=mp4]/best[height<=480]',
        '720p':  'best[height<=720][ext=mp4]/best[height<=720]',
        '1080p': 'best[height<=1080][ext=mp4]/best[height<=1080]',
        '1440p': 'best[height<=1440][ext=mp4]/best[height<=1440]',
        '4k':    'best[height<=2160][ext=mp4]/best[height<=2160]',
        'best':  'best[ext=mp4]/best',
    }

    @property
    def QUALITY_PRESETS(self):
        """Return the correct preset dict based on ffmpeg availability."""
        return self.QUALITY_PRESETS_FFMPEG if self._has_ffmpeg else self.QUALITY_PRESETS_NO_FFMPEG
    
    def __init__(self, config=None):
        """
        Initialize YouTube service.
        
        Args:
            config: NexaConfig instance for paths and settings
        """
        self.config = config
        self._audio_process: Optional[subprocess.Popen] = None
        self._current_video: Optional[Dict[str, Any]] = None
        self._queue: List[Dict[str, Any]] = []
        self._queue_index: int = -1
        self._is_playing: bool = False
        self._is_downloading: bool = False
        self._playback_lock = threading.Lock()
        self._has_ffmpeg: bool = shutil.which('ffmpeg') is not None
        
        # Download progress tracking
        self._download_progress: float = 0.0  # 0-100%
        self._download_complete: bool = False
        self._download_error: Optional[str] = None
        self._current_download: Optional[Dict[str, Any]] = None
        self._download_speed: str = ""
        self._download_eta: str = ""
        self._download_filesize: str = ""
        
        # Callback for UI progress updates (set by executor/window)
        self.on_download_progress = None  # callable(percent, speed, eta, title)
        self.on_download_complete = None  # callable(title, filepath)
        self.on_download_error = None     # callable(title, error_msg)
        
        # yt-dlp options for search (lightweight - metadata only)
        self._search_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download, just get metadata
            'skip_download': True,
        }
        
        # yt-dlp options for audio extraction
        self._audio_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'skip_download': True,  # We just need the URL
        }
        
        # yt-dlp options for video info
        self._info_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        
        # Callback for NVP launch (set by executor/window)
        # Signature: (file_path, title, channel, duration, video_url, video_id) -> None
        self.on_play_video = None  # callable — launches NVP on GUI thread
        
        logger.info(f"🎬 YouTube service initialized (yt-dlp: {YT_DLP_AVAILABLE}, ffmpeg: {self._has_ffmpeg})")
    
    def play_youtube(self, query: str) -> str:
        """
        Play a YouTube video via NEXA Vision Player (NVP).
        
        Downloads a streamable-quality video to temp, then launches NVP.
        Falls back to browser if NVP is not available.
        
        Args:
            query: Video search query or YouTube URL
            
        Returns:
            Result message with video title
        """
        try:
            # Resolve query to video info
            video_url = None
            video_id = None
            title = query
            channel = 'Unknown'
            duration_str = ''
            duration_sec = 0
            
            if self._is_youtube_url(query):
                video_url = query
                info = self._get_video_info(query)
                if info:
                    title = info.get('title', query)
                    channel = info.get('channel', info.get('uploader', 'Unknown'))
                    duration_sec = info.get('duration', 0)
                    duration_str = self._format_duration(duration_sec)
                    video_id = info.get('id', '')
            elif YT_DLP_AVAILABLE:
                # Use YouTube search URL (avoids broken ytsearch: extractor)
                search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                search_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': 'in_playlist',
                    'skip_download': True,
                    'playlist_items': '1',
                }
                
                with yt_dlp.YoutubeDL(search_opts) as ydl:
                    result = ydl.extract_info(search_url, download=False)
                
                entries = result.get('entries', []) if result else []
                if entries:
                    video = entries[0]
                    video_id = video.get('id', video.get('url', ''))
                    video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ''
                    title = video.get('title', query)
                    channel = video.get('channel', video.get('uploader', 'Unknown')) or 'Unknown'
                    duration_sec = video.get('duration', 0) or 0
                    duration_str = self._format_duration(duration_sec)
                    
                    # If extract_flat gave minimal info, get full info
                    if not title or title == query:
                        try:
                            full_info = self._get_video_info(video_url)
                            if full_info:
                                title = full_info.get('title', title)
                                channel = full_info.get('channel', full_info.get('uploader', channel))
                                duration_sec = full_info.get('duration', duration_sec)
                                duration_str = self._format_duration(duration_sec)
                        except Exception:
                            pass
            
            if not video_url:
                # No video found — fallback to browser search
                search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                webbrowser.open(search_url)
                return f"Couldn't find a specific video for '{query}', opened YouTube search instead"
            
            # Store current video info
            self._current_video = {
                'title': title,
                'channel': channel,
                'duration': duration_str,
                'url': video_url,
                'id': video_id,
            }
            self._queue.append(self._current_video)
            self._queue_index = len(self._queue) - 1
            
            # === TRY NVP (embedded player) ===
            if self.on_play_video and video_id:
                try:
                    # No download needed — NVP embeds YouTube iframe directly
                    # This avoids codec issues and provides instant playback
                    formats = self._get_download_formats(video_url, duration_sec) if YT_DLP_AVAILABLE else []
                    
                    # Launch NVP via callback (GUI thread)
                    self.on_play_video(
                        '', title, channel, duration_str,
                        video_url, video_id, formats
                    )
                    
                    return f"Playing '{title}' by {channel} ({duration_str}) on NEXA Vision Player"
                except Exception as e:
                    logger.warning(f"NVP launch failed: {e}, falling back to browser")
            
            # === FALLBACK: Open in browser ===
            browser_url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1" if video_id else video_url
            webbrowser.open(browser_url)
            return f"Playing '{title}' by {channel} ({duration_str})"
            
        except Exception as e:
            logger.error(f"Error playing YouTube video: {e}")
            try:
                search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                webbrowser.open(search_url)
                return f"Had trouble finding the exact video. Opened YouTube search for '{query}'"
            except Exception:
                return f"Sorry, I couldn't play that video. Error: {str(e)}"
    
    def _get_download_formats(self, video_url: str, duration_sec: int = 0) -> list:
        """
        Get available download formats with estimated file sizes.
        Used by NVP download panel.
        """
        # Estimate file sizes based on typical bitrates and duration
        if duration_sec <= 0:
            duration_sec = 240  # assume 4 min
        
        formats = [
            {'quality': '1080p', 'label': '1080p', 'format': 'MP4', 'audio_only': False,
             'size': self._estimate_size(duration_sec, 5000)},
            {'quality': '720p', 'label': '720p', 'format': 'MP4', 'audio_only': False,
             'size': self._estimate_size(duration_sec, 2500)},
            {'quality': '480p', 'label': '480p', 'format': 'MP4', 'audio_only': False,
             'size': self._estimate_size(duration_sec, 1200)},
            {'quality': '360p', 'label': '360p', 'format': 'MP4', 'audio_only': False,
             'size': self._estimate_size(duration_sec, 700)},
            {'quality': 'best', 'label': 'Audio', 'format': 'MP3', 'audio_only': True,
             'size': self._estimate_size(duration_sec, 192)},
        ]
        return formats
    
    def _estimate_size(self, duration_sec: int, kbps: int) -> str:
        """Estimate file size string from duration and bitrate."""
        size_bytes = (kbps * 1000 / 8) * duration_sec
        if size_bytes >= 1_073_741_824:
            return f"{size_bytes / 1_073_741_824:.1f} GB"
        elif size_bytes >= 1_048_576:
            return f"{size_bytes / 1_048_576:.0f} MB"
        else:
            return f"{size_bytes / 1024:.0f} KB"
    
    def search_youtube(self, query: str, count: int = 5) -> str:
        """
        Search YouTube and return results with titles and channels.
        
        Args:
            query: Search query
            count: Number of results (default 5, max 10)
            
        Returns:
            Formatted search results
        """
        try:
            count = min(max(count, 1), 10)
            
            if not YT_DLP_AVAILABLE:
                search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                webbrowser.open(search_url)
                return f"Opened YouTube search for '{query}' — install yt-dlp for inline results"
            
            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',
                'skip_download': True,
                'playlist_items': f'1-{count}',
            }
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                result = ydl.extract_info(search_url, download=False)
            
            if not result or 'entries' not in result:
                return f"No results found for '{query}'"
            
            entries = result['entries']
            if not entries:
                return f"No results found for '{query}'"
            
            # Store results for "play the first/second one" follow-ups
            self._last_search_results = entries
            
            # Format results
            lines = [f"YouTube results for '{query}':"]
            for i, entry in enumerate(entries, 1):
                title = entry.get('title', 'Unknown')
                channel = entry.get('channel', entry.get('uploader', 'Unknown'))
                duration = self._format_duration(entry.get('duration', 0))
                lines.append(f"{i}. {title} — {channel} ({duration})")
            
            lines.append(f"\nSay 'play the first one' or 'play number 3' to play a result.")
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
            return f"Sorry, YouTube search failed: {str(e)}"
    
    def play_youtube_result(self, number: int) -> str:
        """
        Play a video from the last search results by number.
        
        Args:
            number: Result number (1-based)
            
        Returns:
            Result message
        """
        try:
            if not hasattr(self, '_last_search_results') or not self._last_search_results:
                return "No recent search results. Try searching YouTube first!"
            
            if number < 1 or number > len(self._last_search_results):
                return f"Invalid number. Choose between 1 and {len(self._last_search_results)}"
            
            entry = self._last_search_results[number - 1]
            video_id = entry.get('id', '')
            title = entry.get('title', 'Unknown')
            
            if video_id:
                url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
                webbrowser.open(url)
                
                self._current_video = {
                    'title': title,
                    'channel': entry.get('channel', entry.get('uploader', 'Unknown')),
                    'duration': self._format_duration(entry.get('duration', 0)),
                    'url': url,
                    'id': video_id,
                }
                self._queue.append(self._current_video)
                self._queue_index = len(self._queue) - 1
                
                return f"Playing '{title}'"
            else:
                return "Couldn't get video URL. Try playing by name instead."
                
        except Exception as e:
            logger.error(f"Error playing YouTube result: {e}")
            return f"Error playing result: {str(e)}"
    
    def get_video_info(self, query: str = "") -> str:
        """
        Get information about the current video or a specific video.
        
        Args:
            query: Video URL or search query (empty = current video)
            
        Returns:
            Video information string
        """
        try:
            if not query and self._current_video:
                v = self._current_video
                return (
                    f"Currently playing: {v.get('title', 'Unknown')}\n"
                    f"Channel: {v.get('channel', 'Unknown')}\n"
                    f"Duration: {v.get('duration', 'Unknown')}\n"
                    f"URL: {v.get('url', 'N/A')}"
                )
            
            if not query:
                return "No video is currently playing. Play something first or provide a video name/URL."
            
            if not YT_DLP_AVAILABLE:
                return "yt-dlp is not installed. Install it with: pip install yt-dlp"
            
            # Search for the video
            if not self._is_youtube_url(query):
                query = f"ytsearch1:{query}"
            
            info = self._get_video_info(query)
            if not info:
                return f"Couldn't find information for '{query}'"
            
            title = info.get('title', 'Unknown')
            channel = info.get('channel', info.get('uploader', 'Unknown'))
            duration = self._format_duration(info.get('duration', 0))
            views = info.get('view_count', 0)
            likes = info.get('like_count', 0)
            upload_date = info.get('upload_date', 'Unknown')
            description = info.get('description', '')[:200]
            
            # Format views nicely
            if views >= 1_000_000:
                views_str = f"{views / 1_000_000:.1f}M views"
            elif views >= 1_000:
                views_str = f"{views / 1_000:.1f}K views"
            elif views > 0:
                views_str = f"{views} views"
            else:
                views_str = "Unknown views"
            
            # Format upload date
            if upload_date and upload_date != 'Unknown' and len(upload_date) == 8:
                upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            
            result = (
                f"Title: {title}\n"
                f"Channel: {channel}\n"
                f"Duration: {duration}\n"
                f"Views: {views_str}\n"
                f"Published: {upload_date}"
            )
            
            if description:
                result += f"\nDescription: {description}..."
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return f"Couldn't get video info: {str(e)}"
    
    def get_youtube_queue(self) -> str:
        """
        Get the current video queue.
        
        Returns:
            Formatted queue list
        """
        if not self._queue:
            return "Your YouTube queue is empty. Play something to start building a queue!"
        
        lines = ["YouTube Queue:"]
        for i, video in enumerate(self._queue):
            marker = " ▶" if i == self._queue_index else ""
            title = video.get('title', 'Unknown')
            duration = video.get('duration', '')
            lines.append(f"{i + 1}. {title} ({duration}){marker}")
        
        return "\n".join(lines)
    
    def clear_youtube_queue(self) -> str:
        """
        Clear the YouTube queue.
        
        Returns:
            Confirmation message
        """
        count = len(self._queue)
        self._queue.clear()
        self._queue_index = -1
        self._current_video = None
        return f"Cleared {count} videos from the YouTube queue"
    
    # ==================== DOWNLOAD FEATURES ====================
    
    def download_youtube(self, query: str, audio_only: bool = False, quality: str = "1080p") -> str:
        """
        Download a YouTube video (MP4) or audio (MP3/M4A) by query or URL.
        
        Downloads are saved to the user's Videos/Nexa Downloads folder.
        Runs in a background thread so NEXA remains responsive.
        Works without ffmpeg (pre-merged single-stream fallback).
        Supports quality selection: 360p, 480p, 720p, 1080p, 1440p, 4k, best.
        
        Args:
            query: Video search query or YouTube URL
            audio_only: If True, download audio only as MP3
            quality: Video quality preset (360p/480p/720p/1080p/1440p/4k/best)
            
        Returns:
            Status message with video title, quality, and estimated size
        """
        try:
            if not YT_DLP_AVAILABLE:
                return "yt-dlp is not installed. Install it with: pip install yt-dlp"
            
            # Prevent concurrent downloads
            if self._is_downloading:
                return "A download is already in progress. Please wait for it to finish."
            
            # Normalize quality
            quality = quality.lower().strip()
            if quality not in self.QUALITY_PRESETS:
                quality = "1080p"
            
            # Create download directory
            download_dir = self._get_download_dir()
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # Resolve query to a URL if needed
            if not self._is_youtube_url(query):
                # Use YouTube search URL (ytsearch: extractor is broken)
                search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                search_opts = {
                    'quiet': True, 'no_warnings': True,
                    'extract_flat': 'in_playlist',
                    'skip_download': True, 'playlist_items': '1',
                }
                try:
                    with yt_dlp.YoutubeDL(search_opts) as ydl:
                        search_result = ydl.extract_info(search_url, download=False)
                    entries = search_result.get('entries', []) if search_result else []
                    if entries and entries[0]:
                        vid_id = entries[0].get('id', '')
                        search_query = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else query
                    else:
                        return f"Couldn't find a video for '{query}'"
                except Exception:
                    return f"Couldn't search for '{query}'"
            else:
                search_query = query
            
            # Get video info first (for title, filesize estimation)
            info = self._get_video_info(search_query)
            if not info:
                return f"Couldn't find a video for '{query}'"
            
            title = info.get('title', 'Unknown')
            video_id = info.get('id', '')
            duration = self._format_duration(info.get('duration', 0))
            
            # Estimate file size
            filesize_str = self._estimate_filesize(info, quality, audio_only)
            
            if not video_id:
                return f"Couldn't get video ID for '{query}'"
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            if audio_only:
                mode_str = "audio (MP3)" if self._has_ffmpeg else "audio (M4A)"
            else:
                mode_str = f"video ({quality} MP4)"
            
            # Reset progress
            self._download_progress = 0.0
            self._download_complete = False
            self._download_error = None
            self._download_speed = ""
            self._download_eta = ""
            self._is_downloading = True
            
            # Start download in background thread
            thread = threading.Thread(
                target=self._download_worker,
                args=(video_url, download_dir, audio_only, title, quality),
                daemon=True
            )
            thread.start()
            
            # Store download info
            self._current_download = {
                'title': title,
                'mode': mode_str,
                'quality': quality,
                'directory': str(download_dir),
                'started': time.time(),
                'filesize': filesize_str,
            }
            
            return (
                f"Downloading {mode_str}: '{title}' ({duration})\n"
                f"Quality: {quality.upper()} | Estimated size: {filesize_str}\n"
                f"Saving to: {download_dir}\n"
                f"Download is running in the background."
            )
            
        except Exception as e:
            logger.error(f"Error starting YouTube download: {e}")
            return f"Failed to start download: {str(e)}"
    
    def download_youtube_audio(self, query: str) -> str:
        """
        Download audio only (MP3) from a YouTube video.
        
        Convenience wrapper around download_youtube with audio_only=True.
        
        Args:
            query: Video search query or YouTube URL
            
        Returns:
            Status message
        """
        return self.download_youtube(query, audio_only=True)
    
    def download_youtube_video(self, query: str, quality: str = "1080p") -> str:
        """
        Download a YouTube video at specified quality.
        
        Args:
            query: Video search query or YouTube URL
            quality: Video quality (360p/480p/720p/1080p/1440p/4k/best)
            
        Returns:
            Status message
        """
        return self.download_youtube(query, audio_only=False, quality=quality)
    
    def get_download_status(self) -> str:
        """
        Get the status of the current/last download.
        
        Returns:
            Download status message with progress percentage
        """
        if not self._current_download:
            return "No downloads in progress or recent."
        
        dl = self._current_download
        elapsed = time.time() - dl.get('started', time.time())
        
        if self._download_complete:
            return (
                f"Download complete: '{dl['title']}'\n"
                f"Quality: {dl.get('quality', 'best').upper()} | Size: {dl.get('filesize', 'Unknown')}\n"
                f"Saved to: {dl['directory']}"
            )
        elif self._download_error:
            return f"Download failed: '{dl['title']}' — {self._download_error}"
        else:
            progress_str = f"{self._download_progress:.1f}%" if self._download_progress > 0 else "Starting..."
            speed_str = f" | Speed: {self._download_speed}" if self._download_speed else ""
            eta_str = f" | ETA: {self._download_eta}" if self._download_eta else ""
            return (
                f"Downloading: '{dl['title']}' ({dl['mode']})\n"
                f"Progress: {progress_str}{speed_str}{eta_str}\n"
                f"Time elapsed: {int(elapsed)}s\n"
                f"Saving to: {dl['directory']}"
            )
    
    def _download_progress_hook(self, d):
        """
        yt-dlp progress hook — called during download.
        Updates internal state and notifies UI via callback.
        """
        if d['status'] == 'downloading':
            # Extract progress percentage
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            
            if total > 0:
                self._download_progress = (downloaded / total) * 100
            elif '_percent_str' in d:
                try:
                    self._download_progress = float(d['_percent_str'].strip().replace('%', ''))
                except (ValueError, AttributeError):
                    pass
            
            # Extract speed and ETA
            speed = d.get('_speed_str', '')
            eta = d.get('_eta_str', '')
            self._download_speed = speed.strip() if speed else ""
            self._download_eta = eta.strip() if eta else ""
            
            # Filesize
            if total > 0:
                self._download_filesize = self._format_bytes(total)
            
            # Notify UI callback
            if self.on_download_progress:
                try:
                    title = self._current_download.get('title', '') if self._current_download else ''
                    self.on_download_progress(self._download_progress, self._download_speed, self._download_eta, title)
                except Exception:
                    pass  # Don't let UI callback errors break download
        
        elif d['status'] == 'finished':
            self._download_progress = 100.0
            if self.on_download_progress:
                try:
                    title = self._current_download.get('title', '') if self._current_download else ''
                    self.on_download_progress(100.0, "", "Done", title)
                except Exception:
                    pass
    
    def _download_worker(self, url: str, download_dir: Path, audio_only: bool, title: str, quality: str = "1080p"):
        """
        Background worker for downloading YouTube videos/audio.
        
        Works WITHOUT ffmpeg by using pre-merged single-stream formats.
        When ffmpeg IS available, uses separate streams + merge for best quality.
        
        Args:
            url: YouTube video URL
            download_dir: Directory to save to
            audio_only: If True, extract audio (MP3 if ffmpeg, M4A otherwise)
            title: Video title (for logging)
            quality: Video quality preset
        """
        try:
            self._download_complete = False
            self._download_error = None
            self._download_progress = 0.0
            
            if audio_only:
                if self._has_ffmpeg:
                    # Download + convert to MP3 via ffmpeg
                    opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'quiet': True,
                        'no_warnings': True,
                        'progress_hooks': [self._download_progress_hook],
                    }
                else:
                    # Download best audio as-is (m4a/webm) — no ffmpeg needed
                    opts = {
                        'format': 'bestaudio[ext=m4a]/bestaudio/best',
                        'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'progress_hooks': [self._download_progress_hook],
                    }
                    logger.info("📥 Downloading audio without ffmpeg (saving as M4A/native format)")
            else:
                # Download video at specified quality
                format_str = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS['1080p'])
                opts = {
                    'format': format_str,
                    'outtmpl': str(download_dir / '%(title)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    'progress_hooks': [self._download_progress_hook],
                }
                # Only set merge_output_format when ffmpeg is available (merge needs ffmpeg)
                if self._has_ffmpeg:
                    opts['merge_output_format'] = 'mp4'
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            
            self._download_complete = True
            self._download_progress = 100.0
            self._is_downloading = False
            logger.info(f"✅ YouTube download complete: '{title}' ({quality}) → {download_dir}")
            
            # Notify UI
            if self.on_download_complete:
                try:
                    self.on_download_complete(title, str(download_dir))
                except Exception:
                    pass
            
        except Exception as e:
            self._download_error = str(e)
            self._download_progress = 0.0
            self._is_downloading = False
            logger.error(f"❌ YouTube download failed: '{title}' — {e}")
            
            # Notify UI of error
            if self.on_download_error:
                try:
                    self.on_download_error(title, str(e))
                except Exception:
                    pass
    
    def _estimate_filesize(self, info: Dict[str, Any], quality: str, audio_only: bool) -> str:
        """
        Estimate file size based on video duration and quality.
        
        Args:
            info: Video info dict from yt-dlp
            quality: Quality preset
            audio_only: Whether downloading audio only
            
        Returns:
            Estimated file size string
        """
        duration = info.get('duration', 0)
        if not duration:
            return "Unknown"
        
        # Rough bitrate estimates (bytes per second)
        if audio_only:
            bps = 24_000  # ~192kbps MP3
        else:
            quality_bps = {
                '360p':  50_000,    # ~400kbps
                '480p':  100_000,   # ~800kbps
                '720p':  200_000,   # ~1.6Mbps
                '1080p': 400_000,   # ~3.2Mbps
                '1440p': 800_000,   # ~6.4Mbps
                '4k':    1_600_000, # ~12.8Mbps
                'best':  500_000,   # ~4Mbps average
            }
            bps = quality_bps.get(quality, 400_000)
        
        estimated_bytes = duration * bps
        return self._format_bytes(estimated_bytes)
    
    def _get_download_dir(self) -> Path:
        """
        Get the download directory for YouTube videos.
        
        Uses Videos/Nexa Downloads on Windows, falls back to ~/Downloads/Nexa Downloads.
        
        Returns:
            Path to download directory
        """
        # Try Windows Videos folder
        videos_dir = Path(os.path.expanduser("~")) / "Videos" / "Nexa Downloads"
        if videos_dir.parent.exists():
            return videos_dir
        
        # Fallback to Downloads folder
        downloads_dir = Path(os.path.expanduser("~")) / "Downloads" / "Nexa Downloads"
        return downloads_dir
    
    @staticmethod
    def _format_bytes(num_bytes: int) -> str:
        """Format bytes into human-readable string."""
        if num_bytes <= 0:
            return "Unknown"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if num_bytes < 1024:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes:.1f} TB"
    
    # ==================== INTERNAL HELPERS ====================
    
    def _is_youtube_url(self, text: str) -> bool:
        """Check if text looks like a YouTube URL."""
        youtube_patterns = [
            r'(https?://)?(www\.)?youtube\.com/watch\?v=',
            r'(https?://)?(www\.)?youtu\.be/',
            r'(https?://)?(www\.)?youtube\.com/shorts/',
            r'(https?://)?(www\.)?youtube\.com/playlist\?list=',
        ]
        return any(re.search(pattern, text) for pattern in youtube_patterns)
    
    # ==================== TRANSCRIPT / CAPTIONS ====================

    def get_video_transcript(self, query: str) -> str:
        """
        Extract the auto-generated English captions/transcript for a YouTube video.

        Args:
            query: YouTube URL or search query

        Returns:
            Plain-text transcript (up to ~2 000 chars) or an error message
        """
        if not YT_DLP_AVAILABLE:
            return "yt-dlp is not installed. Install it with: pip install yt-dlp"

        try:
            if not self._is_youtube_url(query):
                query = f"ytsearch1:{query}"

            # First, resolve to a real URL via info extraction
            info = self._get_video_info(query)
            if not info:
                return f"Could not find video for: {query}"

            video_url = info.get("webpage_url") or info.get("url", "")
            title = info.get("title", "this video")

            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                sub_opts = {
                    "skip_download": True,
                    "writeautomaticsub": True,
                    "writesubtitles": True,
                    "subtitlesformat": "json3",
                    "subtitleslangs": ["en", "en-US", "en-GB"],
                    "quiet": True,
                    "no_warnings": True,
                    "outtmpl": os.path.join(tmpdir, "%(id)s"),
                }
                with yt_dlp.YoutubeDL(sub_opts) as ydl:
                    ydl.download([video_url])

                # Find the written .json3 subtitle file
                json3_files = list(Path(tmpdir).glob("*.json3"))
                if not json3_files:
                    return f"No English captions found for '{title}'."

                data = json.loads(json3_files[0].read_text(encoding="utf-8"))
                segments = []
                for event in data.get("events", []):
                    for seg in event.get("segs", []):
                        text = seg.get("utf8", "").strip()
                        if text and text != "\n":
                            segments.append(text)

                transcript = " ".join(segments)
                # Collapse excessive whitespace / newlines
                transcript = re.sub(r"\s+", " ", transcript).strip()

                if not transcript:
                    return f"Captions exist but appear empty for '{title}'."

                # Cap at 2 000 chars to keep the LLM response concise
                if len(transcript) > 2000:
                    transcript = transcript[:2000] + "… [truncated]"

                return f"Transcript for '{title}':\n\n{transcript}"

        except Exception as e:
            logger.error(f"Error getting transcript: {e}")
            return f"Could not get transcript: {str(e)}"

    # ==================== TRENDING VIDEOS ====================

    def get_trending_videos(self, region: str = "US", count: int = 5) -> str:
        """
        Retrieve currently trending videos from YouTube for a given region.

        Args:
            region: Two-letter ISO country code (default: "US")
            count: Number of results to return (1-10)

        Returns:
            Numbered list of trending video titles with channel names
        """
        if not YT_DLP_AVAILABLE:
            return "yt-dlp is not installed. Install it with: pip install yt-dlp"

        count = max(1, min(count, 10))
        region = region.upper().strip() or "US"

        try:
            trending_url = f"https://www.youtube.com/feed/trending?gl={region}"
            opts = {
                "quiet": True,
                "no_warnings": True,
                "playliststart": 1,
                "playlistend": count,
                "extract_flat": True,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                result = ydl.extract_info(trending_url, download=False)

            if not result or "entries" not in result:
                return f"Could not retrieve trending videos for region '{region}'."

            entries = [e for e in result["entries"] if e] [:count]
            if not entries:
                return f"No trending videos found for region '{region}'."

            # Store results so play_youtube_result can use them
            self._last_search_results = entries

            lines = [f"🔥 Trending on YouTube ({region}):"]
            for i, entry in enumerate(entries, 1):
                title = entry.get("title", "Unknown")
                channel = entry.get("channel") or entry.get("uploader", "")
                duration = entry.get("duration")
                dur_str = f" ({self._format_duration(duration)})" if duration else ""
                ch_str = f" — {channel}" if channel else ""
                lines.append(f"{i}. {title}{ch_str}{dur_str}")

            lines.append(f"\nSay 'play result 1' (or any number) to watch one of these.")
            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error fetching trending videos: {e}")
            return f"Could not fetch trending videos: {str(e)}"

    # ==================== CHANNEL VIDEOS ====================

    def get_channel_videos(self, channel_name: str, count: int = 5) -> str:
        """
        List the most recent uploads from a YouTube channel.

        Args:
            channel_name: Channel name (handle like 'mkbhd') or full URL
            count: Number of recent videos to return (1-10)

        Returns:
            Numbered list of recent uploads with duration
        """
        if not YT_DLP_AVAILABLE:
            return "yt-dlp is not installed. Install it with: pip install yt-dlp"

        count = max(1, min(count, 10))
        channel_name = channel_name.strip().strip("@")

        # Build a channel URL from the handle
        if channel_name.startswith("http"):
            channel_url = channel_name
        else:
            channel_url = f"https://www.youtube.com/@{channel_name}/videos"

        try:
            opts = {
                "quiet": True,
                "no_warnings": True,
                "playliststart": 1,
                "playlistend": count,
                "extract_flat": True,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                result = ydl.extract_info(channel_url, download=False)

            if not result:
                return f"Could not find channel '{channel_name}'."

            entries = []
            if "entries" in result:
                entries = [e for e in result["entries"] if e][:count]
            elif result.get("title"):
                # Single video returned — treat as one entry
                entries = [result]

            if not entries:
                return f"No videos found for channel '{channel_name}'."

            display_name = result.get("channel") or result.get("uploader") or channel_name
            lines = [f"📺 Recent uploads from {display_name}:"]
            for i, entry in enumerate(entries, 1):
                title = entry.get("title", "Unknown")
                duration = entry.get("duration")
                dur_str = f" ({self._format_duration(duration)})" if duration else ""
                lines.append(f"{i}. {title}{dur_str}")

            lines.append(f"\nSay 'play result 1' (or any number) to watch one of these.")
            # Store entries so play_youtube_result can use them
            self._last_search_results = entries

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error fetching channel videos: {e}")
            return f"Could not fetch videos from '{channel_name}': {str(e)}"

    # ==================== PLAYLIST QUEUING ====================

    def play_youtube_playlist(self, url: str, max_videos: int = 10) -> str:
        """
        Load all videos from a YouTube playlist into the queue and play the first one.

        Args:
            url: Full YouTube playlist URL (e.g. https://www.youtube.com/playlist?list=...)
            max_videos: Maximum videos to add (capped at 20 to keep queue manageable)

        Returns:
            Status message with playlist title and number of videos queued
        """
        if not YT_DLP_AVAILABLE:
            return "yt-dlp is not installed. Install it with: pip install yt-dlp"

        max_videos = max(1, min(max_videos, 20))

        if not self._is_youtube_url(url):
            return "Please provide a full YouTube playlist URL (e.g. youtube.com/playlist?list=...)."

        try:
            opts = {
                "quiet": True,
                "no_warnings": True,
                "playliststart": 1,
                "playlistend": max_videos,
                "extract_flat": "in_playlist",
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                result = ydl.extract_info(url, download=False)

            if not result or "entries" not in result:
                return "Could not load that playlist. Make sure the URL is correct and the playlist is public."

            entries = [e for e in result["entries"] if e]
            if not entries:
                return "The playlist appears to be empty."

            playlist_title = result.get("title", "Unknown Playlist")

            # Build queue entries
            new_items = []
            for e in entries:
                vid_id = e.get("id", "")
                vid_url = (
                    e.get("webpage_url")
                    or e.get("url")
                    or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "")
                )
                new_items.append({
                    "title": e.get("title", "Unknown"),
                    "url": vid_url,
                    "duration": self._format_duration(e.get("duration", 0)),
                    "channel": e.get("channel") or e.get("uploader", ""),
                    "id": vid_id,
                })

            # Append to queue (beyond the currently playing item)
            self._queue.extend(new_items)

            # Play the first video using the standard play path
            first = new_items[0]
            play_result = self.play_youtube(first["url"])

            return (
                f"Loaded playlist '{playlist_title}' — {len(new_items)} videos queued.\n"
                f"{play_result}\n"
                f"Say 'next video' to skip to the next one."
            )

        except Exception as e:
            logger.error(f"Error loading playlist: {e}")
            return f"Could not load playlist: {str(e)}"

    # ==================== PRIVATE HELPERS ====================

    def _get_video_info(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get video metadata using yt-dlp.
        
        Args:
            query: YouTube URL or ytsearch query
            
        Returns:
            Video info dict or None
        """
        if not YT_DLP_AVAILABLE:
            return None
        
        try:
            with yt_dlp.YoutubeDL(self._info_opts) as ydl:
                result = ydl.extract_info(query, download=False)
            
            if result:
                # If search result, get first entry
                if 'entries' in result and result['entries']:
                    return result['entries'][0]
                return result
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get video info: {e}")
            return None
    
    def _format_duration(self, seconds) -> str:
        """Format duration in seconds to human-readable string."""
        if not seconds:
            return "Unknown"
        
        seconds = int(seconds)  # yt-dlp may return float
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
