"""
Music Manager - Local Music Library & Playback Control
Manages user's local music collection with AI-powered features.
"""

import logging
import os
import random
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import threading
import time
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class MusicManager(QObject):
    """
    Manages local music library with playback control.
    Supports: MP3, WAV, FLAC, M4A, OGG formats.
    Features: Library scanning, playback, random play, search, recommendations.
    """
    
    # Qt Signals
    on_play_started = Signal(str)  # Emits song name when playback starts
    on_play_stopped = Signal()      # Emits when playback stops
    on_song_changed = Signal(str)   # Emits new song name on track change (user-requested)
    on_auto_advance = Signal(str)   # Emits new song name when auto-advancing (for TTS announcement)
    
    # Supported audio formats
    SUPPORTED_FORMATS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.wma'}
    
    def __init__(self, music_folder: Path = None):
        """
        Initialize Music Manager.
        
        Args:
            music_folder: Path to music library (default: user's Music folder)
        """
        super().__init__()  # Initialize QObject
        
        # Set music folder
        if music_folder is None:
            music_folder = Path.home() / "Music"
        
        self.music_folder = Path(music_folder)
        
        # Library state
        self.library: List[Dict[str, any]] = []
        self.indexed = False
        
        # Playback state
        self.current_track: Optional[Dict] = None
        self.current_index: int = -1
        self.playlist: List[Dict] = []
        self.is_playing = False
        self.is_paused = False
        
        # Playback modes
        self.shuffle_mode: bool = False
        self.repeat_mode: str = 'off'  # 'off', 'one', 'all'
        self.auto_advance: bool = True  # Auto-play next song when current ends
        self.shuffled_playlist: List[Dict] = []  # Shuffled order when shuffle enabled
        
        # Volume control - 4-state system for better VAD accuracy
        self.normal_volume: float = 0.85    # 85% - Normal music playback volume
        self.listening_volume: float = 0.70 # 70% - During wake word listening (good volume, ducking handles the rest)
        self.pre_duck_volume: float = 0.15  # 15% - When VAD shows ANY speech probability (pre-emptive ducking)
        self.duck_volume: float = 0.03      # 3% - During confirmed speech / TTS playback (near-mute for NEXA voice clarity)
        self.current_volume_state: str = 'normal'  # 'normal', 'listening', 'pre_duck', 'ducked'
        self.is_ducked: bool = False
        self.is_pre_ducked: bool = False
        self.wake_word_mode: bool = True    # When True, return to normal volume after ducking (not listening volume)
        
        # Pygame mixer (lazy initialization)
        self.mixer = None
        self.mixer_initialized = False
        
        # Playback thread
        self.playback_thread = None
        self.stop_playback_flag = False
        self._is_auto_advance = False  # Flag to track if current play is auto-advance
        self._mixer_lock = threading.Lock()  # Thread safety for mixer operations
        
        logger.info(f"Music Manager initialized (folder: {self.music_folder})")
    
    def _ensure_mixer(self):
        """Initialize pygame mixer if not already done."""
        if self.mixer_initialized:
            return True
        
        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.mixer = pygame.mixer.music
            self.mixer_initialized = True
            logger.info("✅ Pygame mixer initialized")
            return True
        except ImportError:
            logger.error("❌ pygame not installed. Run: pip install pygame")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize mixer: {e}")
            return False
    
    def scan_library(self) -> int:
        """
        Scan music folder and index all audio files.
        
        Returns:
            Number of songs found
        """
        logger.info(f"🔍 Scanning music library: {self.music_folder}")
        
        if not self.music_folder.exists():
            logger.warning(f"⚠️ Music folder not found: {self.music_folder}")
            return 0
        
        self.library = []
        
        # Recursively find all audio files
        for file_path in self.music_folder.rglob("*"):
            if file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                try:
                    song_info = self._get_song_info(file_path)
                    self.library.append(song_info)
                except Exception as e:
                    logger.debug(f"⚠️ Skipped {file_path.name}: {e}")
        
        self.indexed = True
        logger.info(f"✅ Library indexed: {len(self.library)} songs found")
        return len(self.library)
    
    def _get_song_info(self, file_path: Path) -> Dict:
        """
        Extract song information from file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with song metadata
        """
        # Basic info
        song_info = {
            'path': str(file_path),
            'filename': file_path.name,
            'title': file_path.stem,  # Filename without extension
            'artist': 'Unknown',
            'album': 'Unknown',
            'genre': 'Unknown',
            'duration': 0,
            'size': file_path.stat().st_size
        }
        
        # Try to read ID3 tags (optional - requires mutagen)
        try:
            from mutagen import File
            audio = File(file_path)
            
            if audio is not None:
                # Extract metadata if available
                if hasattr(audio, 'tags') and audio.tags:
                    # MP3/FLAC/OGG tags
                    song_info['title'] = str(audio.tags.get('title', [song_info['title']])[0]) if 'title' in audio.tags else song_info['title']
                    song_info['artist'] = str(audio.tags.get('artist', ['Unknown'])[0]) if 'artist' in audio.tags else 'Unknown'
                    song_info['album'] = str(audio.tags.get('album', ['Unknown'])[0]) if 'album' in audio.tags else 'Unknown'
                    song_info['genre'] = str(audio.tags.get('genre', ['Unknown'])[0]) if 'genre' in audio.tags else 'Unknown'
                
                # Duration
                if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                    song_info['duration'] = int(audio.info.length)
        
        except ImportError:
            # mutagen not installed - use filename only
            logger.debug("mutagen not available - using filenames for metadata")
        except Exception as e:
            logger.debug(f"Could not read metadata for {file_path.name}: {e}")
        
        return song_info
    
    def list_songs(self, limit: int = None, filter_artist: str = None, filter_genre: str = None) -> List[str]:
        """
        List all songs in library.
        
        Args:
            limit: Maximum number of songs to return
            filter_artist: Filter by artist name
            filter_genre: Filter by genre
            
        Returns:
            List of song titles
        """
        # Scan library if not done yet
        if not self.indexed:
            self.scan_library()
        
        # Filter songs
        songs = self.library
        
        if filter_artist:
            songs = [s for s in songs if filter_artist.lower() in s['artist'].lower()]
        
        if filter_genre:
            songs = [s for s in songs if filter_genre.lower() in s['genre'].lower()]
        
        # Format song list using clean formatting
        song_list = [self._format_song_name(s) for s in songs]
        
        # Apply limit
        if limit:
            song_list = song_list[:limit]
        
        return song_list
    
    def _format_song_name(self, song: Dict) -> str:
        """
        Format song name for natural speech output.
        
        Converts filenames like:
        - "Dua Lipa - Levitating (Lyrics)_256k" → "Levitating by Dua Lipa"
        - "Justin Bieber - Baby (Official Video)_160k" → "Baby by Justin Bieber"
        - "Attention - Charlie Puth" → "Attention by Charlie Puth"
        - "Song Title" → "Song Title"
        
        Args:
            song: Song dictionary with 'title' and optional 'artist'
            
        Returns:
            Formatted song name for speech
        """
        title = song.get('title', '')
        artist = song.get('artist', 'Unknown')
        
        # If we have proper metadata (not from filename), use it
        if artist != 'Unknown' and ' - ' not in title:
            return f"{title} by {artist}"
        
        # Parse filename format: "Artist - Title (extras)_quality"
        # Common patterns:
        # 1. "Artist - Title (Lyrics)_256k"
        # 2. "Title - Artist"
        # 3. "Title (feat. Artist)"
        
        # Remove quality markers: _256k, _160k, (MP3_160K), etc.
        clean_title = re.sub(r'_\d+k', '', title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\(mp3_\d+k\)', '', clean_title, flags=re.IGNORECASE)
        
        # Remove common extras: (Lyrics), (Official Video), (Audio), etc.
        clean_title = re.sub(r'\s*\((lyrics|official video|audio|music video|official audio|official music video|lyric video|visualizer)\)\s*', '', clean_title, flags=re.IGNORECASE)
        
        # Check for "Artist - Title" pattern
        if ' - ' in clean_title:
            parts = clean_title.split(' - ', 1)
            part1 = parts[0].strip()
            part2 = parts[1].strip()
            
            # Determine which is artist and which is title
            # Standard format: "Artist - Title" (most common)
            # Alternative format: "Title - Artist" (less common)
            
            # Heuristic 1: Check for common artist indicators
            common_artist_words = ['feat', 'ft', '&', 'and', 'x']
            part1_has_artist_words = any(word in part1.lower() for word in common_artist_words)
            part2_has_artist_words = any(word in part2.lower() for word in common_artist_words)
            
            # Heuristic 2: Check if part2 looks like a full artist name (has first+last name)
            # Common pattern: "Title - FirstName LastName" (2 words = likely artist)
            part2_words = len(part2.split())
            part1_words = len(part1.split())
            
            # Heuristic 3: Song titles are often shorter single words
            # If part1 is a single word and part2 is 2+ words, likely "Title - Artist"
            
            # Decision logic:
            # - If part1 has artist words (feat, &, etc.) → part1 is artist
            # - Else if part2 has artist words → part2 is artist  
            # - Else if part1 is 1 word and part2 is 2+ words → "Title - Artist" format
            # - Else assume standard format: "Artist - Title"
            
            if part1_has_artist_words and not part2_has_artist_words:
                # Part1 is artist (e.g., "Dua Lipa & Elton John - Title")
                return f"{part2} by {part1}"
            elif part2_has_artist_words and not part1_has_artist_words:
                # Part2 is artist (e.g., "Title - Artist feat. X")
                return f"{part1} by {part2}"
            elif part1_words == 1 and part2_words >= 2:
                # Likely "Title - FirstName LastName" format
                return f"{part1} by {part2}"
            else:
                # Default: Assume standard "Artist - Title" format
                # This covers most cases like "Dua Lipa - Levitating"
                return f"{part2} by {part1}"
        
        # No dash separator - check for (feat. Artist) pattern
        feat_match = re.search(r'(.+?)\s*\(feat\.?\s+(.+?)\)', clean_title, re.IGNORECASE)
        if feat_match:
            title_part = feat_match.group(1).strip()
            feat_artist = feat_match.group(2).strip()
            return f"{title_part} featuring {feat_artist}"
        
        # No recognizable pattern - just return cleaned title
        return clean_title.strip()
    
    def play_random(self) -> str:
        """
        Play a random song from library.
        
        Returns:
            Status message
        """
        # Ensure library is scanned
        if not self.indexed:
            self.scan_library()
        
        if not self.library:
            return "I couldn't find any music files in your Music folder. Would you like me to help you add some?"
        
        # Pick random song
        random_song = random.choice(self.library)
        
        result = self.play_song(random_song)
        # Return the play result - user requested this
        return result
    
    def play_song(self, song: Dict = None, song_name: str = None, enable_auto_advance: bool = False) -> str:
        """
        Play a specific song.
        
        Args:
            song: Song dictionary from library
            song_name: Song name to search for
            enable_auto_advance: If True, enable auto-advance to next song when finished
            
        Returns:
            Status message
        """
        # Set auto-advance mode (True for playlists, False for single songs)
        self.auto_advance = enable_auto_advance
        
        # Search by name if provided
        if song_name and not song:
            song = self.find_song(song_name)
            if not song:
                # Try to find similar songs for suggestions
                suggestions = self._find_similar_songs(song_name, limit=3)
                if suggestions:
                    suggestion_text = ", ".join([s['title'] for s in suggestions])
                    return f"I couldn't find '{song_name}'. Did you mean: {suggestion_text}?"
                else:
                    return f"I couldn't find '{song_name}' in your library. Try 'list my music' to see what's available."
        
        if not song:
            return "I'm not sure which song to play. Could you tell me the song name?"
        
        # Initialize mixer
        if not self._ensure_mixer():
            return "Oops, I'm having trouble with the audio system. Let me know if you need help fixing this."
        
        try:
            # Check if this is a track change (not initial play)
            was_playing = self.is_playing
            
            # Stop current playback
            if self.is_playing:
                self.mixer.stop()
            
            # Load and play
            logger.info(f"🎵 Playing: {song['title']} - {song['artist']}")
            self.mixer.load(song['path'])
            self.mixer.play()
            
            # Set initial volume
            self.mixer.set_volume(self.normal_volume)
            
            # Update state
            self.current_track = song
            self.is_playing = True
            self.is_paused = False
            self.is_ducked = False  # Reset ducking state
            
            # Format song name for UI/speech
            formatted_song = self._format_song_name(song)
            
            # Emit appropriate signal
            if was_playing:
                if self._is_auto_advance:
                    self.on_auto_advance.emit(formatted_song)  # Auto-advance - announce via TTS
                else:
                    self.on_song_changed.emit(formatted_song)  # User request - no TTS announcement
            else:
                self.on_play_started.emit(formatted_song)  # Initial playback
            
            # Reset auto-advance flag after emitting
            self._is_auto_advance = False
            
            # Start playback monitoring thread
            self._start_playback_monitor()
            
            # Natural response variations
            responses = [
                f"Playing {formatted_song}",
                f"Sure! Here's {formatted_song}",
                f"You got it! Playing {formatted_song}",
                f"Great choice! {formatted_song} coming right up",
                f"Alright, starting {formatted_song}",
            ]
            
            # Pick a random natural response
            return random.choice(responses)
        
        except Exception as e:
            logger.error(f"❌ Playback error: {e}")
            return f"Sorry, I had trouble playing that song. The file might be corrupted."
    
    def _start_playback_monitor(self):
        """Start background thread to monitor playback and handle song end"""
        # Stop existing monitor if running
        if self.playback_thread and self.playback_thread.is_alive():
            self.stop_playback_flag = True
            self.playback_thread.join(timeout=1.0)
        
        # Start new monitor thread
        self.stop_playback_flag = False
        self.playback_thread = threading.Thread(target=self._monitor_playback, daemon=True)
        self.playback_thread.start()
        logger.debug("🔄 Playback monitor started")
    
    def _monitor_playback(self):
        """
        Background thread that monitors when a song finishes playing.
        Handles auto-advance or stops indicator when playback ends.
        """
        try:
            import pygame
            
            # Wait a brief moment for the song to actually start
            time.sleep(0.2)
            
            while not self.stop_playback_flag and self.is_playing:
                # Check if music is still playing
                if not pygame.mixer.music.get_busy():
                    # Wait briefly to distinguish between song change and actual end
                    time.sleep(0.3)
                    
                    # Re-check - if still not busy, song really ended
                    if not pygame.mixer.music.get_busy():
                        # Check if we should auto-advance to next song
                        if self.auto_advance and self._should_play_next():
                            logger.info("⏭️ Auto-advancing to next song...")
                            self._is_auto_advance = True  # Mark this as auto-advance for TTS announcement
                            self.next_song()
                        else:
                            # No more songs or auto-advance disabled
                            logger.info("⏹️ Playback complete - stopping indicator")
                            self.is_playing = False
                            self.current_track = None
                            self.on_play_stopped.emit()
                        
                        break  # Exit monitor thread
                
                # Check every 500ms
                time.sleep(0.5)
        
        except Exception as e:
            logger.error(f"❌ Playback monitor error: {e}")
    
    def _should_play_next(self) -> bool:
        """
        Determine if we should auto-play the next song.
        Returns False if:
        - Only a single song was requested (not playlist mode)
        - We're at the end of playlist and repeat is off
        """
        # If repeat one is enabled, always continue
        if self.repeat_mode == 'one':
            return True
        
        # If we have a playlist/library and repeat all is on, continue
        if self.repeat_mode == 'all':
            return True
        
        # Check if there's a next song available
        playlist = self.shuffled_playlist if self.shuffle_mode else self.library
        if not playlist or not self.current_track:
            return False
        
        try:
            current_index = playlist.index(self.current_track)
            # If not at the end, continue
            if current_index < len(playlist) - 1:
                return True
        except ValueError:
            pass
        
        # At the end and no repeat - stop
        return False
    
    def find_song(self, song_name: str) -> Optional[Dict]:
        """
        Find song by name (advanced fuzzy matching).
        
        Handles:
        - Partial matches ("Attention" finds "Charlie Puth - Attention (Lyrics)_256k.mp3")
        - Ignores quality markers: (MP3_160K), _256k, (Lyrics), etc.
        - Multi-word search ("charlie attention" finds "Charlie Puth - Attention")
        - Case-insensitive matching
        
        Args:
            song_name: Song name or partial name
            
        Returns:
            Song dictionary or None
        """
        if not self.indexed:
            self.scan_library()
        
        if not self.library:
            return None
        
        song_name_lower = song_name.lower().strip()
        
        # Helper function to clean song title (remove quality markers)
        def clean_title(title: str) -> str:
            """Remove common quality/format markers from title."""
            cleaned = title.lower()
            # Remove quality markers
            cleaned = re.sub(r'\(mp3_\d+k\)', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'_\d+k', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\(lyrics\)', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\blyrics?\b', '', cleaned, flags=re.IGNORECASE)  # Remove standalone "lyrics"
            cleaned = re.sub(r'\(official.*?\)', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\(audio\)', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\(music video\)', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\[.*?\]', '', cleaned)  # Remove [brackets]
            cleaned = re.sub(r'[_-]+', ' ', cleaned)  # Convert underscores/dashes to spaces
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # Normalize spaces
            return cleaned
        
        # STRATEGY 1: Exact match (cleaned)
        for song in self.library:
            cleaned_title = clean_title(song['title'])
            cleaned_filename = clean_title(song['filename'])
            
            if song_name_lower == cleaned_title or song_name_lower == cleaned_filename:
                logger.debug(f"✅ Exact match: {song['title']}")
                return song
        
        # STRATEGY 2: Exact substring match in cleaned title
        for song in self.library:
            cleaned_title = clean_title(song['title'])
            cleaned_filename = clean_title(song['filename'])
            
            if song_name_lower in cleaned_title or song_name_lower in cleaned_filename:
                logger.debug(f"✅ Substring match: {song['title']}")
                return song
        
        # STRATEGY 3: Multi-word matching (all words must be present)
        search_words = song_name_lower.split()
        if len(search_words) > 1:
            for song in self.library:
                cleaned_title = clean_title(song['title'])
                cleaned_filename = clean_title(song['filename'])
                
                # Check if ALL search words are in title or filename
                title_match = all(word in cleaned_title for word in search_words)
                filename_match = all(word in cleaned_filename for word in search_words)
                
                if title_match or filename_match:
                    logger.debug(f"✅ Multi-word match: {song['title']}")
                    return song
        
        # STRATEGY 4: Partial word matching (any word matches)
        for song in self.library:
            cleaned_title = clean_title(song['title'])
            cleaned_filename = clean_title(song['filename'])
            
            # Split title into words and check if any search word matches any title word
            title_words = cleaned_title.split()
            filename_words = cleaned_filename.split()
            
            for search_word in search_words:
                # Check if search word is a substantial part of any title word (>= 4 chars)
                if len(search_word) >= 4:
                    for title_word in title_words:
                        if search_word in title_word or title_word in search_word:
                            logger.debug(f"✅ Partial word match: {song['title']}")
                            return song
                    for filename_word in filename_words:
                        if search_word in filename_word or filename_word in search_word:
                            logger.debug(f"✅ Partial filename match: {song['title']}")
                            return song
        
        # STRATEGY 5: Fuzzy scoring (Levenshtein distance - optional, basic implementation)
        # Score each song based on similarity
        best_match = None
        best_score = 0
        
        for song in self.library:
            cleaned_title = clean_title(song['title'])
            
            # Simple scoring: count matching characters in order
            score = 0
            search_idx = 0
            for char in cleaned_title:
                if search_idx < len(song_name_lower) and char == song_name_lower[search_idx]:
                    score += 1
                    search_idx += 1
            
            # Normalize score by search length
            normalized_score = score / len(song_name_lower) if len(song_name_lower) > 0 else 0
            
            if normalized_score > best_score and normalized_score >= 0.6:  # 60% match threshold
                best_score = normalized_score
                best_match = song
        
        if best_match:
            logger.debug(f"✅ Fuzzy match ({best_score:.0%}): {best_match['title']}")
            return best_match
        
        logger.debug(f"❌ No match found for: {song_name}")
        return None
    
    def pause(self) -> str:
        """
        Pause current playback.
        
        Returns:
            Status message
        """
        if not self.mixer_initialized:
            return "There's no music playing right now."
        
        # Check if actually playing using pygame's get_busy()
        try:
            import pygame
            if not pygame.mixer.music.get_busy() and not self.is_paused:
                return "There's no music playing right now."
        except:
            if not self.is_playing:
                return "There's no music playing right now."
        
        try:
            if not self.is_paused:
                self.mixer.pause()
                self.is_paused = True
                # Keep is_playing True so we can resume!
                logger.info("⏸️ Music paused")
                responses = [
                    "Paused!",
                    "Music paused",
                    "Alright, pausing the music",
                    "Paused it for you",
                ]
                return random.choice(responses)
            else:
                return "The music is already paused."
        except Exception as e:
            logger.error(f"❌ Pause error: {e}")
            return "Hmm, I had trouble pausing that."
    
    def resume(self) -> str:
        """
        Resume paused playback.
        
        Returns:
            Status message
        """
        if not self.mixer_initialized:
            return "There's no music paused right now."
        
        try:
            if self.is_paused:
                self.mixer.unpause()
                self.is_paused = False
                self.is_playing = True  # Ensure is_playing is True
                logger.info("▶️ Music resumed")
                responses = [
                    "Resuming!",
                    "Back to the music!",
                    "Here we go again!",
                    "Continuing where we left off",
                ]
                return random.choice(responses)
            elif self.is_playing:
                return "The music is already playing."
            else:
                return "There's no music paused right now."
        except Exception as e:
            logger.error(f"❌ Resume error: {e}")
            return "I had trouble resuming playback."
    
    def stop(self) -> str:
        """
        Stop playback completely.
        
        Returns:
            Status message
        """
        if not self.mixer_initialized:
            return "There's no music playing right now."
        
        try:
            # Stop monitor thread first
            self.stop_playback_flag = True
            
            # Wait for monitor thread to stop (with timeout)
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=0.5)
            
            # Thread-safe mixer stop
            with self._mixer_lock:
                try:
                    self.mixer.stop()
                except Exception:
                    pass  # Ignore mixer errors during stop
            
            self.is_playing = False
            self.is_paused = False
            self.current_track = None
            
            # Emit signal for UI update
            try:
                self.on_play_stopped.emit()
            except Exception:
                pass  # Ignore signal errors
            
            responses = [
                "Music stopped!",
                "Alright, stopped the music",
                "Done! Music is off",
                "Stopped",
            ]
            return random.choice(responses)
        except Exception as e:
            logger.error(f"❌ Stop error: {e}")
            return "I had trouble stopping the music."
    
    def next_song(self) -> str:
        """
        Play next song in library (respects shuffle and repeat modes).
        
        Returns:
            Status message
        """
        if not self.indexed:
            self.scan_library()
        
        if not self.library:
            return "I don't have any music files to play."
        
        # Check repeat one mode
        if self.repeat_mode == 'one' and self.current_track:
            return self.play_song(self.current_track, enable_auto_advance=True)
        
        # Determine which playlist to use
        playlist = self.shuffled_playlist if self.shuffle_mode else self.library
        
        if not playlist:
            playlist = self.library
        
        # Find current song index
        if self.current_track:
            try:
                current_index = playlist.index(self.current_track)
                next_index = current_index + 1
                
                # Check if we've reached the end
                if next_index >= len(playlist):
                    if self.repeat_mode == 'all':
                        next_index = 0  # Loop back to start
                    else:
                        return "That was the last song in your library."
            except ValueError:
                next_index = 0
        else:
            next_index = 0
        
        # Play next song with auto-advance enabled
        next_song = playlist[next_index]
        result = self.play_song(next_song, enable_auto_advance=True)
        # Return the play result - user requested this, so let play_song provide the response
        return result
    
    def previous_song(self) -> str:
        """
        Play previous song in library (respects shuffle and repeat modes).
        
        Returns:
            Status message
        """
        if not self.indexed:
            self.scan_library()
        
        if not self.library:
            return "I don't have any music files to play."
        
        # Check repeat one mode
        if self.repeat_mode == 'one' and self.current_track:
            return self.play_song(self.current_track, enable_auto_advance=True)
        
        # Determine which playlist to use
        playlist = self.shuffled_playlist if self.shuffle_mode else self.library
        
        if not playlist:
            playlist = self.library
        
        # Find current song index
        if self.current_track:
            try:
                current_index = playlist.index(self.current_track)
                prev_index = current_index - 1
                
                # Check if we've reached the beginning
                if prev_index < 0:
                    if self.repeat_mode == 'all':
                        prev_index = len(playlist) - 1  # Loop to end
                    else:
                        return "That was the first song in your library."
            except ValueError:
                prev_index = 0
        else:
            prev_index = 0
        
        # Play previous song with auto-advance enabled
        prev_song = playlist[prev_index]
        result = self.play_song(prev_song, enable_auto_advance=True)
        # Return the play result - user requested this, so let play_song provide the response
        return result
    
    def get_current_track(self) -> str:
        """
        Get currently playing track info.
        
        Returns:
            Track information
        """
        if not self.current_track:
            return "Nothing's playing right now."
        
        track = self.current_track
        
        # Format song name for natural speech
        formatted_song = self._format_song_name(track)
        
        if self.is_paused:
            return f"Currently paused on {formatted_song}"
        else:
            responses = [
                f"Right now I'm playing {formatted_song}",
                f"This is {formatted_song}",
                f"You're listening to {formatted_song}",
                f"Playing {formatted_song}",
            ]
            return random.choice(responses)
    
    def get_library_stats(self) -> str:
        """
        Get music library statistics.
        
        Returns:
            Library statistics
        """
        if not self.indexed:
            self.scan_library()
        
        if not self.library:
            return "Your music library is empty right now."
        
        # Calculate stats
        total_songs = len(self.library)
        total_duration = sum(s['duration'] for s in self.library)
        total_size_mb = sum(s['size'] for s in self.library) / (1024 * 1024)
        
        # Unique artists
        artists = set(s['artist'] for s in self.library if s['artist'] != 'Unknown')
        
        # Format duration
        hours = total_duration // 3600
        minutes = (total_duration % 3600) // 60
        
        # Natural response variations
        if total_songs == 1:
            stats = "You have 1 song in your library"
        else:
            stats = f"You've got {total_songs} songs in your library"
        
        if artists:
            stats += f" from {len(artists)} different artists"
        
        if hours > 0:
            stats += f". That's about {hours} hours and {minutes} minutes of music!"
        else:
            stats += f". That's about {minutes} minutes of music!"
        
        return stats
    
    def _find_similar_songs(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Find songs similar to the query for suggestions.
        
        Args:
            query: Search query
            limit: Maximum number of suggestions
            
        Returns:
            List of similar song dictionaries
        """
        if not self.indexed:
            self.scan_library()
        
        if not self.library:
            return []
        
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        # Helper function to clean song title
        def clean_title(title: str) -> str:
            cleaned = title.lower()
            cleaned = re.sub(r'\(mp3_\d+k\)', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'_\d+k', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\(lyrics\)', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\(official.*?\)', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\[.*?\]', '', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            return cleaned
        
        # Score each song
        scored_songs = []
        for song in self.library:
            cleaned_title = clean_title(song['title'])
            cleaned_filename = clean_title(song['filename'])
            
            score = 0
            
            # Score based on word overlap
            title_words = cleaned_title.split()
            for query_word in query_words:
                if len(query_word) >= 3:  # Only substantial words
                    for title_word in title_words:
                        # Exact word match
                        if query_word == title_word:
                            score += 10
                        # Partial word match
                        elif query_word in title_word or title_word in query_word:
                            score += 5
                        # Starting characters match (at least 3 chars)
                        elif len(query_word) >= 3 and title_word.startswith(query_word[:3]):
                            score += 3
            
            # Bonus for substring match
            if query_lower in cleaned_title:
                score += 15
            
            if score > 0:
                scored_songs.append((score, song))
        
        # Sort by score (highest first) and return top matches
        scored_songs.sort(key=lambda x: x[0], reverse=True)
        
        return [song for score, song in scored_songs[:limit]]
    
    def suggest_music(self, count: int = 5, based_on_current: bool = False) -> str:
        """
        Suggest random songs from library or based on currently playing track.
        
        Args:
            count: Number of suggestions (default: 5)
            based_on_current: If True, suggest similar to current track
            
        Returns:
            Formatted suggestion message
        """
        if not self.indexed:
            self.scan_library()
        
        if not self.library:
            return "Your music library is empty. Add some songs to your Music folder first!"
        
        # Limit suggestions to available songs
        count = min(count, len(self.library))
        
        if based_on_current and self.current_track:
            # Suggest based on current track (same artist or similar)
            current_artist = self.current_track.get('artist', 'Unknown')
            current_genre = self.current_track.get('genre', 'Unknown')
            
            # Find songs by same artist or genre
            suggestions = []
            
            # Priority 1: Same artist (excluding current song)
            if current_artist != 'Unknown':
                same_artist = [
                    s for s in self.library 
                    if s['artist'].lower() == current_artist.lower() 
                    and s['path'] != self.current_track['path']
                ]
                suggestions.extend(same_artist[:count])
            
            # Priority 2: Same genre (if we need more suggestions)
            if len(suggestions) < count and current_genre != 'Unknown':
                same_genre = [
                    s for s in self.library 
                    if s['genre'].lower() == current_genre.lower() 
                    and s not in suggestions
                    and s['path'] != self.current_track['path']
                ]
                suggestions.extend(same_genre[:count - len(suggestions)])
            
            # Priority 3: Random songs (if still need more)
            if len(suggestions) < count:
                remaining = [
                    s for s in self.library 
                    if s not in suggestions 
                    and s['path'] != self.current_track['path']
                ]
                random_picks = random.sample(remaining, min(count - len(suggestions), len(remaining)))
                suggestions.extend(random_picks)
            
            # Format response
            if not suggestions:
                return "I couldn't find similar songs. Want me to suggest some random ones?"
            
            suggestion_list = []
            for i, song in enumerate(suggestions[:count], 1):
                # Clean title for display
                clean_title = song['title'].replace('(MP3_160K)', '').replace('(MP3_128K)', '')
                clean_title = re.sub(r'_\d+k', '', clean_title).strip()
                
                artist_info = f" by {song['artist']}" if song['artist'] != 'Unknown' else ""
                suggestion_list.append(f"{i}. {clean_title}{artist_info}")
            
            intro = f"Since you're listening to {self.current_track['title']}, you might like:\n"
            return intro + "\n".join(suggestion_list)
        
        else:
            # Random suggestions
            suggestions = random.sample(self.library, count)
            
            suggestion_list = []
            for i, song in enumerate(suggestions, 1):
                # Clean title for display
                clean_title = song['title'].replace('(MP3_160K)', '').replace('(MP3_128K)', '')
                clean_title = re.sub(r'_\d+k', '', clean_title).strip()
                clean_title = re.sub(r'\(lyrics\)', '', clean_title, flags=re.IGNORECASE).strip()
                
                artist_info = f" by {song['artist']}" if song['artist'] != 'Unknown' else ""
                suggestion_list.append(f"{i}. {clean_title}{artist_info}")
            
            responses = [
                f"Here are {count} songs you might enjoy:\n",
                f"How about these {count} songs?\n",
                f"I picked {count} songs for you:\n",
                f"You might like these:\n",
            ]
            
            return random.choice(responses) + "\n".join(suggestion_list)
    
    # ===== VOLUME CONTROL & DUCKING =====
    
    def set_volume(self, volume: float) -> str:
        """
        Set music playback volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
            
        Returns:
            Confirmation message
        """
        if not self.mixer_initialized:
            return "Music system not initialized"
        
        try:
            # Clamp volume to valid range
            volume = max(0.0, min(1.0, volume))
            
            # Set pygame mixer volume (only affects music, not system)
            self.mixer.set_volume(volume)
            
            # Update normal volume if not currently ducked
            if not self.is_ducked:
                self.normal_volume = volume
            
            logger.info(f"🔊 Music volume set to {int(volume * 100)}%")
            return f"Music volume set to {int(volume * 100)}%"
            
        except Exception as e:
            logger.error(f"❌ Failed to set volume: {e}")
            return "Failed to set volume"
    
    def get_volume(self) -> float:
        """
        Get current music volume.
        
        Returns:
            Current volume (0.0 to 1.0)
        """
        if not self.mixer_initialized:
            return 0.0
        
        try:
            return self.mixer.get_volume()
        except:
            return self.normal_volume
    
    def set_listening_mode(self) -> None:
        """
        Set listening mode - lower volume to 5% for better VAD accuracy.
        Called when listener is actively waiting for user speech.
        """
        if not self.mixer_initialized or not self.is_playing:
            return
        
        try:
            self.mixer.set_volume(self.listening_volume)
            self.current_volume_state = 'listening'
            self.is_ducked = False
            self.is_pre_ducked = False
            
            logger.debug(f"🎧 Listening mode: Volume → {int(self.listening_volume * 100)}%")
            
        except Exception as e:
            logger.error(f"❌ Failed to set listening mode: {e}")
    
    def set_normal_mode(self) -> None:
        """
        Set normal mode - restore volume to 70% when user cannot speak.
        Called during TTS or when listener is paused.
        """
        if not self.mixer_initialized or not self.is_playing:
            return
        
        try:
            self.mixer.set_volume(self.normal_volume)
            self.current_volume_state = 'normal'
            self.is_ducked = False
            self.is_pre_ducked = False
            
            logger.debug(f"🔊 Normal mode: Volume → {int(self.normal_volume * 100)}%")
            
        except Exception as e:
            logger.error(f"❌ Failed to set normal mode: {e}")
    
    def enable_pre_ducking(self) -> None:
        """
        Enable pre-ducking - lower music to 2% when VAD shows any speech probability.
        This is called BEFORE confirmed speech to give VAD a clean signal.
        """
        # Check if mixer is available - also check pygame.mixer.music.get_busy() for real playing state
        if not self.mixer_initialized:
            return
        
        # Check actual playing state from pygame (more reliable than self.is_playing)
        try:
            import pygame
            actual_playing = pygame.mixer.music.get_busy()
        except:
            actual_playing = self.is_playing
        
        if not actual_playing:
            return
        
        # Don't pre-duck if already ducked or pre-ducked
        if self.is_ducked or self.is_pre_ducked:
            return
        
        try:
            prev_volume = self.get_volume()
            self.mixer.set_volume(self.pre_duck_volume)
            self.current_volume_state = 'pre_duck'
            self.is_pre_ducked = True
            
            logger.info(f"🔉 Pre-ducking: {int(prev_volume * 100)}% → {int(self.pre_duck_volume * 100)}%")
            
        except Exception as e:
            logger.error(f"❌ Failed to enable pre-ducking: {e}")
    
    def enable_ducking(self, duck_volume: float = None) -> None:
        """
        Enable full ducking - mute music (0%) during confirmed speech recording.
        Provides maximum clarity for speech recognition.
        
        Args:
            duck_volume: Volume to duck to (default: 0.0 = mute)
        """
        # Check if mixer is available
        if not self.mixer_initialized:
            return
        
        # Check actual playing state from pygame (more reliable than self.is_playing)
        try:
            import pygame
            actual_playing = pygame.mixer.music.get_busy()
        except:
            actual_playing = self.is_playing
        
        if not actual_playing:
            return
        
        try:
            # Set duck volume if provided
            if duck_volume is not None:
                self.duck_volume = max(0.0, min(1.0, duck_volume))
            
            # Apply full ducking (mute)
            prev_volume = self.get_volume()
            self.mixer.set_volume(self.duck_volume)
            self.current_volume_state = 'ducked'
            self.is_ducked = True
            self.is_pre_ducked = False
            
            logger.info(f"🔇 Full ducking (mute): {int(prev_volume * 100)}% → {int(self.duck_volume * 100)}%")
            
        except Exception as e:
            logger.error(f"❌ Failed to enable ducking: {e}")
    
    def disable_ducking(self) -> None:
        """
        Disable ducking - restore volume after speech recording.
        In wake word mode: returns to normal volume (85%)
        In direct mode: returns to listening volume (70%)
        """
        if not self.mixer_initialized or (not self.is_ducked and not self.is_pre_ducked):
            return
        
        try:
            # In wake word mode, return to normal volume (music plays normally between commands)
            # In direct mode, return to listening volume (always ready for speech)
            if self.wake_word_mode:
                self.mixer.set_volume(self.normal_volume)
                self.current_volume_state = 'normal'
                logger.debug(f"🔊 Ducking disabled → Normal mode ({int(self.normal_volume * 100)}%)")
            else:
                self.mixer.set_volume(self.listening_volume)
                self.current_volume_state = 'listening'
                logger.debug(f"🔊 Ducking disabled → Listening mode ({int(self.listening_volume * 100)}%)")
            
            self.is_ducked = False
            self.is_pre_ducked = False
            
        except Exception as e:
            logger.error(f"❌ Failed to disable ducking: {e}")
    
    def disable_pre_ducking(self) -> None:
        """
        Disable pre-ducking - restore volume if no speech was confirmed.
        In wake word mode: returns to normal volume (85%)
        In direct mode: returns to listening volume (70%)
        """
        if not self.mixer_initialized or not self.is_pre_ducked:
            return
        
        try:
            # In wake word mode, return to normal volume
            # In direct mode, return to listening volume
            if self.wake_word_mode:
                self.mixer.set_volume(self.normal_volume)
                self.current_volume_state = 'normal'
                logger.debug(f"🔊 Pre-ducking disabled → Normal mode ({int(self.normal_volume * 100)}%)")
            else:
                self.mixer.set_volume(self.listening_volume)
                self.current_volume_state = 'listening'
                logger.debug(f"🔊 Pre-ducking disabled → Listening mode ({int(self.listening_volume * 100)}%)")
            
            self.is_pre_ducked = False
            
        except Exception as e:
            logger.error(f"❌ Failed to disable pre-ducking: {e}")
    
    def set_wake_word_mode(self, enabled: bool) -> None:
        """
        Set wake word mode for ducking behavior.
        
        In wake word mode (enabled=True):
        - Music stays at normal volume during passive listening
        - Ducks only when speech is detected
        - Returns to normal volume after ducking
        
        In direct mode (enabled=False):
        - Music at listening volume (70%) during listening
        - Returns to listening volume after ducking
        
        Args:
            enabled: True for wake word mode, False for direct mode
        """
        self.wake_word_mode = enabled
        logger.debug(f"🎵 Wake word mode: {'enabled' if enabled else 'disabled'}")
    
    def is_ducking_active(self) -> bool:
        """
        Check if any ducking (pre or full) is currently active.
        
        Returns:
            True if music is ducked or pre-ducked, False otherwise
        """
        return self.is_ducked or self.is_pre_ducked
    
    # ===== SHUFFLE AND REPEAT CONTROLS =====
    
    def enable_shuffle(self) -> str:
        """
        Enable shuffle mode - play songs in random order.
        
        Returns:
            Status message
        """
        if not self.indexed:
            self.scan_library()
        
        if not self.library:
            return "I don't have any music to shuffle yet."
        
        self.shuffle_mode = True
        
        # Create shuffled playlist
        self.shuffled_playlist = self.library.copy()
        random.shuffle(self.shuffled_playlist)
        
        logger.info("🔀 Shuffle mode enabled")
        
        responses = [
            "Shuffle mode is now on! I'll play your music in random order.",
            "Got it! Shuffling your library now.",
            "Shuffle enabled! Time for some musical variety.",
            "Alright, I'll mix things up for you!",
        ]
        return random.choice(responses)
    
    def disable_shuffle(self) -> str:
        """
        Disable shuffle mode - return to sequential playback.
        
        Returns:
            Status message
        """
        self.shuffle_mode = False
        self.shuffled_playlist = []
        
        logger.info("➡️ Shuffle mode disabled")
        
        responses = [
            "Shuffle mode is now off. I'll play in order.",
            "Alright, back to sequential playback.",
            "Shuffle disabled! Playing in normal order.",
            "Got it, no more shuffling.",
        ]
        return random.choice(responses)
    
    def set_repeat_mode(self, mode: str) -> str:
        """
        Set repeat mode.
        
        Args:
            mode: 'off', 'one', or 'all'
                - 'off': No repeat
                - 'one': Repeat current song
                - 'all': Repeat entire library
        
        Returns:
            Status message
        """
        mode = mode.lower().strip()
        
        if mode not in ['off', 'one', 'all']:
            return f"Invalid repeat mode '{mode}'. Use 'off', 'one', or 'all'."
        
        self.repeat_mode = mode
        
        logger.info(f"🔁 Repeat mode set to: {mode}")
        
        if mode == 'off':
            return "Repeat mode is now off."
        elif mode == 'one':
            return "Repeat one is on. I'll keep playing this song."
        else:  # 'all'
            return "Repeat all is on. I'll loop through your entire library."
    
    def get_playback_mode(self) -> str:
        """
        Get current playback mode (shuffle and repeat status).
        
        Returns:
            Playback mode information
        """
        shuffle_status = "on" if self.shuffle_mode else "off"
        
        mode_info = f"Shuffle: {shuffle_status}, Repeat: {self.repeat_mode}"
        
        # Natural response
        parts = []
        if self.shuffle_mode:
            parts.append("Shuffle is on")
        else:
            parts.append("Shuffle is off")
        
        if self.repeat_mode == 'one':
            parts.append("repeating current song")
        elif self.repeat_mode == 'all':
            parts.append("repeating all songs")
        else:
            parts.append("no repeat")
        
        return f"{parts[0]} and {parts[1]}."
    
    def play_all_library(self, shuffle: bool = False) -> str:
        """
        Start playing entire library from beginning.
        
        Args:
            shuffle: If True, play in random order
        
        Returns:
            Status message
        """
        if not self.indexed:
            self.scan_library()
        
        if not self.library:
            return "I don't have any music files to play."
        
        # Set modes
        if shuffle:
            self.enable_shuffle()
        else:
            self.shuffle_mode = False
        
        # Start from first song with auto-advance enabled
        playlist = self.shuffled_playlist if self.shuffle_mode else self.library
        first_song = playlist[0]
        
        result = self.play_song(first_song, enable_auto_advance=True)
        
        total_songs = len(self.library)
        mode_text = "in shuffle mode" if shuffle else "in order"
        
        return f"{result} I'll play all {total_songs} songs {mode_text}."
