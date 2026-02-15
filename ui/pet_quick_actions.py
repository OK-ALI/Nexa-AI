"""
Pet Quick Actions - Action handlers for the radial menu.

Connects radial menu actions to brain/executor functionality.

Part of P5: Quick Actions & Context Menu
"""

import logging
from typing import Optional, TYPE_CHECKING

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from core.brain import NexaBrain
    from ui.nexa_modern_window import NexaModernWindow

logger = logging.getLogger(__name__)


class PetQuickActions(QObject):
    """
    Handler for radial menu quick actions.
    
    Provides implementations for the 8 quick actions that connect
    to the NexaBrain and CommandExecutor.
    """
    
    # Signals for UI feedback
    action_completed = Signal(str, bool)  # (action_name, success)
    
    def __init__(self, brain: 'NexaBrain', window: Optional['NexaModernWindow'] = None):
        super().__init__()
        self.brain = brain
        self.window = window
        self.settings_panel = None  # P6 settings panel
        
        logger.info("⚡ Quick actions handler initialized")
    
    def set_window(self, window: 'NexaModernWindow'):
        """Set the main window reference."""
        self.window = window
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Quick Actions (8 total)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def take_screenshot(self):
        """
        📸 Screenshot - Take a screenshot of the desktop.
        """
        try:
            logger.info("📸 Quick action: Screenshot")
            
            # Use executor's screenshot function
            if hasattr(self.brain, 'executor') and self.brain.executor:
                result = self.brain.executor.function_registry.call('take_screenshot', {})
                logger.info(f"📸 Screenshot result: {result}")
                self.action_completed.emit("Screenshot", True)
            else:
                logger.warning("Executor not available for screenshot")
                self.action_completed.emit("Screenshot", False)
                
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            self.action_completed.emit("Screenshot", False)
    
    def toggle_music(self):
        """
        🎵 Music - Start playing random song or stop music.
        If music is playing, stop it. If stopped, play a random song.
        """
        try:
            logger.info("🎵 Quick action: Toggle music")
            
            if hasattr(self.brain, 'executor') and self.brain.executor:
                music_mgr = self.brain.executor.music_manager
                if music_mgr:
                    if music_mgr.is_playing:
                        # Stop music
                        music_mgr.stop()
                        logger.info("🎵 Music stopped")
                    else:
                        # Play random song from library
                        if hasattr(music_mgr, 'play_random') and callable(getattr(music_mgr, 'play_random', None)):
                            music_mgr.play_random()
                            logger.info("🎵 Playing random song")
                        elif hasattr(music_mgr, 'shuffle_play') and callable(getattr(music_mgr, 'shuffle_play', None)):
                            music_mgr.shuffle_play()
                            logger.info("🎵 Playing random song (shuffle)")
                        elif hasattr(music_mgr, 'play') and callable(getattr(music_mgr, 'play', None)):
                            # Try to play something
                            music_mgr.play()
                            logger.info("🎵 Started music playback")
                        else:
                            logger.warning("🎵 No play method available on music manager")
                    self.action_completed.emit("Music", True)
                else:
                    logger.warning("Music manager not available")
                    self.action_completed.emit("Music", False)
            else:
                self.action_completed.emit("Music", False)
                
        except Exception as e:
            logger.error(f"Music toggle error: {e}")
            self.action_completed.emit("Music", False)
    
    def show_volume_control(self):
        """
        🔊 Volume - Toggle mute/unmute.
        Uses executor's native volume methods.
        """
        try:
            logger.info("🔊 Quick action: Volume control")
            
            if hasattr(self.brain, 'executor') and self.brain.executor:
                executor = self.brain.executor
                
                # Get current volume using executor's internal method
                current = executor._get_volume_value()
                logger.info(f"🔊 Current volume: {current}%")
                
                # Handle error case
                if current == -1:
                    # Fallback: just set to 50%
                    logger.warning("🔊 Couldn't get current volume, setting to 50%")
                    executor.set_volume(50)
                    self.action_completed.emit("Volume", True)
                    return
                
                # Toggle logic: if muted (0), set to 50; otherwise mute
                if current == 0:
                    new_volume = 50
                    logger.info("🔊 Unmuting - setting to 50%")
                else:
                    new_volume = 0
                    logger.info("🔊 Muting")
                
                executor.set_volume(new_volume)
                logger.info(f"🔊 Volume set to: {new_volume}%")
                self.action_completed.emit("Volume", True)
            else:
                logger.warning("Executor not available for volume")
                self.action_completed.emit("Volume", False)
                
        except Exception as e:
            logger.error(f"Volume control error: {e}")
            self.action_completed.emit("Volume", False)
    
    def copy_last_response(self):
        """
        📱 Share - Copy the last Nexa response to clipboard.
        """
        try:
            logger.info("📱 Quick action: Share/Copy")
            
            # Get last response from context
            if hasattr(self.brain, 'context_manager') and self.brain.context_manager:
                history = self.brain.context_manager.get_recent_history(1)
                if history and len(history) > 0:
                    last_response = history[-1].get('nexa_response', '')
                    if last_response:
                        clipboard = QApplication.clipboard()
                        clipboard.setText(last_response)
                        logger.info(f"📱 Copied to clipboard: {last_response[:50]}...")
                        self.action_completed.emit("Share", True)
                        return
            
            logger.warning("No recent response to copy")
            self.action_completed.emit("Share", False)
            
        except Exception as e:
            logger.error(f"Share/copy error: {e}")
            self.action_completed.emit("Share", False)
    
    def toggle_mode(self):
        """
        🌐 Mode - Toggle between Online and Offline mode.
        """
        try:
            logger.info("🌐 Quick action: Toggle mode")
            
            if hasattr(self.brain, 'llm_manager') and self.brain.llm_manager:
                from core.llm_manager import LLMMode
                
                current_mode = self.brain.llm_manager.current_mode
                
                if current_mode == LLMMode.ONLINE:
                    self.brain.llm_manager.set_mode(LLMMode.OFFLINE)
                    logger.info("🌐 Switched to OFFLINE mode")
                else:
                    self.brain.llm_manager.set_mode(LLMMode.ONLINE)
                    logger.info("🌐 Switched to ONLINE mode")
                
                self.action_completed.emit("Mode", True)
            else:
                self.action_completed.emit("Mode", False)
                
        except Exception as e:
            logger.error(f"Mode toggle error: {e}")
            self.action_completed.emit("Mode", False)
    
    def show_settings(self):
        """
        ⚙️ Settings - Open the P6 settings panel.
        """
        try:
            logger.info("⚙️ Quick action: Settings")
            
            # Create settings panel if not exists
            if not self.settings_panel:
                from ui.pet_settings_panel import PetSettingsPanel
                
                # Get config from window's pet_config
                config = None
                if self.window and hasattr(self.window, 'pet_config'):
                    config = self.window.pet_config
                
                self.settings_panel = PetSettingsPanel(config=config)
                
                # Connect signals to pet widget for real-time updates
                self._connect_settings_signals()
            
            # Show panel near pet
            if self.window and hasattr(self.window, 'pet_widget') and self.window.pet_widget:
                self.settings_panel.show_near_pet(self.window.pet_widget.frameGeometry())
            else:
                from PySide6.QtCore import QPoint
                self.settings_panel.show_at(QPoint(100, 100))
            
            self.action_completed.emit("Settings", True)
            
        except Exception as e:
            logger.error(f"Settings error: {e}")
            self.action_completed.emit("Settings", False)
    
    def _connect_settings_signals(self):
        """Connect settings panel signals to pet widget."""
        if not self.settings_panel:
            return
        
        # Store pet reference for callbacks
        self._settings_pet = None
        if self.window and hasattr(self.window, 'pet_widget'):
            self._settings_pet = self.window.pet_widget
        
        if self._settings_pet:
            pet = self._settings_pet  # Local reference
            
            # ═══════════════════════════════════════════════════════════
            # Appearance Section
            # ═══════════════════════════════════════════════════════════
            self.settings_panel.size_changed.connect(self._on_size_setting_changed)
            self.settings_panel.opacity_changed.connect(self._on_opacity_setting_changed)
            
            # ═══════════════════════════════════════════════════════════
            # Effects Section
            # ═══════════════════════════════════════════════════════════
            self.settings_panel.glow_toggled.connect(self._on_glow_setting_changed)
            self.settings_panel.glow_intensity_changed.connect(self._on_glow_intensity_setting_changed)
            self.settings_panel.animations_toggled.connect(self._on_animations_setting_changed)
            
            # ═══════════════════════════════════════════════════════════
            # Behavior Section
            # ═══════════════════════════════════════════════════════════
            self.settings_panel.speech_bubble_toggled.connect(self._on_speech_bubble_setting_changed)
            self.settings_panel.snap_to_edges_toggled.connect(self._on_snap_setting_changed)
            self.settings_panel.expression_speed_changed.connect(self._on_expression_speed_setting_changed)
            
            # ═══════════════════════════════════════════════════════════
            # Personality Section
            # ═══════════════════════════════════════════════════════════
            self.settings_panel.personality_toggled.connect(self._on_personality_setting_changed)
            self.settings_panel.time_aware_toggled.connect(self._on_time_aware_setting_changed)
            self.settings_panel.idle_timeout_changed.connect(self._on_idle_timeout_setting_changed)
            
            logger.debug("⚙️ All settings signals connected")
    
    def _get_pet(self):
        """Get current pet widget reference."""
        if self._settings_pet:
            return self._settings_pet
        # Try to get fresh reference
        if self.window and hasattr(self.window, 'pet_widget'):
            self._settings_pet = self.window.pet_widget
            return self._settings_pet
        return None
    
    def _on_size_setting_changed(self, val):
        pet = self._get_pet()
        if pet:
            self._apply_pet_scale(pet, val)
            logger.info(f"📐 Size: {val}%")
    
    def _on_opacity_setting_changed(self, val):
        pet = self._get_pet()
        if pet:
            self._apply_pet_opacity(pet, val)
            logger.info(f"👁 Opacity: {val}%")
    
    def _on_glow_setting_changed(self, val):
        pet = self._get_pet()
        if pet:
            pet.update()
            logger.info(f"✨ Glow toggled: {val}")
    
    def _on_glow_intensity_setting_changed(self, val):
        pet = self._get_pet()
        if pet:
            pet.update()
            logger.info(f"✨ Glow intensity: {val}")
    
    def _on_animations_setting_changed(self, val):
        pet = self._get_pet()
        if pet:
            self._toggle_animations(pet, val)
            logger.info(f"🎬 Animations: {val}")
    
    def _on_speech_bubble_setting_changed(self, val):
        pet = self._get_pet()
        if pet:
            self._toggle_speech_bubble(pet, val)
            logger.info(f"💬 Speech bubble: {val}")
    
    def _on_snap_setting_changed(self, val):
        pet = self._get_pet()
        if pet:
            self._toggle_snap(pet, val)
            logger.info(f"📍 Snap to edges: {val}")
    
    def _on_expression_speed_setting_changed(self, val):
        pet = self._get_pet()
        if pet:
            self._set_expression_speed(pet, val)
            logger.info(f"⚡ Expression speed: {val}")
    
    def _on_personality_setting_changed(self, val):
        pet = self._get_pet()
        if pet and hasattr(pet, 'personality') and pet.personality:
            pet.personality.set_enabled(val)
            logger.info(f"🎭 Personality: {val}")
    
    def _on_time_aware_setting_changed(self, val):
        pet = self._get_pet()
        if pet and hasattr(pet, 'personality') and pet.personality:
            pet.personality.set_time_aware(val)
            logger.info(f"⏰ Time-aware: {val}")
    
    def _on_idle_timeout_setting_changed(self, val):
        pet = self._get_pet()
        if pet and hasattr(pet, 'personality') and pet.personality:
            if hasattr(pet.personality, 'idle_manager'):
                pet.personality.idle_manager.set_idle_timeout(val)
            logger.info(f"😴 Idle timeout: {val} min")
    
    def _apply_pet_scale(self, pet, scale_percent: int):
        """Apply scale to pet widget."""
        try:
            if hasattr(pet, 'set_scale'):
                pet.set_scale(scale_percent)
            else:
                # Fallback: resize based on base size
                base_w, base_h = 500, 700  # Medium size base
                new_w = int(base_w * scale_percent / 100)
                new_h = int(base_h * scale_percent / 100)
                pet.resize(new_w, new_h)
                logger.debug(f"⚙️ Pet resized to {new_w}x{new_h}")
        except Exception as e:
            logger.error(f"Error applying scale: {e}")
    
    def _apply_pet_opacity(self, pet, opacity: float):
        """Apply opacity to pet widget."""
        try:
            if hasattr(pet, 'set_opacity'):
                pet.set_opacity(opacity)
            else:
                # Fallback: use window opacity
                pet.setWindowOpacity(opacity)
                logger.debug(f"⚙️ Pet opacity set to {opacity}")
        except Exception as e:
            logger.error(f"Error applying opacity: {e}")
    
    def _toggle_animations(self, pet, enabled: bool):
        """Toggle pet animations on/off."""
        try:
            if hasattr(pet, 'set_animations_enabled'):
                pet.set_animations_enabled(enabled)
                logger.debug(f"⚙️ Animations {'enabled' if enabled else 'disabled'}")
            else:
                logger.warning("Pet widget missing set_animations_enabled method")
        except Exception as e:
            logger.error(f"Error toggling animations: {e}")
    
    def _toggle_speech_bubble(self, pet, enabled: bool):
        """Toggle speech bubble visibility."""
        try:
            # If disabling, hide any current bubble
            if not enabled and hasattr(pet, 'speech_bubble') and pet.speech_bubble:
                pet.speech_bubble.hide()
            logger.debug(f"⚙️ Speech bubble {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            logger.error(f"Error toggling speech bubble: {e}")
    
    def _toggle_snap(self, pet, enabled: bool):
        """Toggle snap to screen edges."""
        try:
            if hasattr(pet, 'snap_enabled'):
                pet.snap_enabled = enabled
            logger.debug(f"⚙️ Snap to edges {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            logger.error(f"Error toggling snap: {e}")
    
    def _set_expression_speed(self, pet, speed: float):
        """Set expression/reaction speed multiplier."""
        try:
            if hasattr(pet, 'set_expression_speed'):
                pet.set_expression_speed(speed)
            elif hasattr(pet, 'personality') and pet.personality:
                # Update personality idle manager speed
                if hasattr(pet.personality, 'idle_manager'):
                    pet.personality.idle_manager.speed_multiplier = 1.0 / speed
            logger.debug(f"⚙️ Expression speed set to {speed}")
        except Exception as e:
            logger.error(f"Error setting expression speed: {e}")
    
    def toggle_sleep_wake(self):
        """
        💤 Sleep/Wake - Toggle pet between sleep and wake states.
        If pet is awake, put to sleep (hide). If sleeping, wake up (show).
        """
        try:
            logger.info("💤 Quick action: Sleep/Wake toggle")
            
            # Check current pet visibility
            if self.window and hasattr(self.window, 'pet_widget') and self.window.pet_widget:
                pet = self.window.pet_widget
                
                if pet.isVisible():
                    # Pet is awake - put to sleep (hide)
                    pet.hide()
                    logger.info("💤 Pet is now sleeping (hidden)")
                    
                    # Update pet state
                    if hasattr(pet, 'set_state'):
                        pet.set_state('sleeping')
                else:
                    # Pet is sleeping - wake up (show)
                    pet.show()
                    pet.raise_()
                    logger.info("☀️ Pet is now awake (visible)")
                    
                    # Update pet state
                    if hasattr(pet, 'set_state'):
                        pet.set_state('idle')
                
                self.action_completed.emit("Sleep", True)
            else:
                logger.warning("Pet widget not available")
                self.action_completed.emit("Sleep", False)
            
        except Exception as e:
            logger.error(f"Sleep/Wake toggle error: {e}")
            self.action_completed.emit("Sleep", False)
    
    def toggle_content_mode(self):
        """
        📝 Content Mode - Toggle content writing/editing mode.
        Opens content mode window or exits if already in content mode.
        """
        try:
            logger.info("📝 Quick action: Toggle Content Mode")
            
            if hasattr(self.brain, 'executor') and self.brain.executor:
                executor = self.brain.executor
                
                # Check if already in content mode by checking brain state
                from core.brain import NexaState
                is_in_content_mode = (
                    hasattr(self.brain, 'state') and 
                    self.brain.state == NexaState.CONTENT_MODE
                )
                
                if is_in_content_mode:
                    # Exit content mode
                    result = executor.exit_content_mode()
                    logger.info("📝 Exited content mode")
                else:
                    # Enter content mode
                    result = executor.enter_content_mode()
                    logger.info("📝 Entered content mode")
                
                self.action_completed.emit("Content", True)
            else:
                logger.warning("Executor not available for content mode")
                self.action_completed.emit("Content", False)
                
        except Exception as e:
            logger.error(f"Content mode toggle error: {e}")
            self.action_completed.emit("Content", False)
    
    def toggle_mic(self):
        """
        🎤 Mic Toggle - Toggle microphone/listening state.
        Starts or stops listening for voice commands.
        """
        try:
            logger.info("🎤 Quick action: Toggle Mic")
            
            # Access listener via brain.listener (same as system tray)
            if hasattr(self.brain, 'listener') and self.brain.listener:
                listener = self.brain.listener
                
                # Check if currently listening
                if hasattr(listener, 'is_listening') and listener.is_listening:
                    # Stop listening
                    listener.stop_listening()
                    logger.info("🎤 Microphone stopped - not listening")
                else:
                    # Start listening
                    listener.start_listening()
                    logger.info("🎤 Microphone started - listening")
                
                self.action_completed.emit("Mic", True)
            else:
                logger.warning("Listener not available for mic toggle")
                self.action_completed.emit("Mic", False)
                
        except Exception as e:
            logger.error(f"Mic toggle error: {e}")
            self.action_completed.emit("Mic", False)
    
    def exit_nexa(self):
        """
        ❌ Exit - Close the Nexa application.
        """
        try:
            logger.info("❌ Quick action: Exit Nexa")
            
            # Close the main window which triggers shutdown
            if self.window:
                self.window.close()
            else:
                # Fallback: quit application directly
                QApplication.quit()
            
            self.action_completed.emit("Exit", True)
            
        except Exception as e:
            logger.error(f"Exit error: {e}")
            self.action_completed.emit("Exit", False)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Action List for Radial Menu
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_menu_items(self):
        """
        Get the list of RadialMenuItem objects with connected actions.
        
        Returns:
            List of RadialMenuItem for the radial menu (10 items)
        """
        from ui.pet_radial_menu import RadialMenuItem
        
        return [
            RadialMenuItem("🔊", "Volume", self.show_volume_control, "V"),
            RadialMenuItem("📸", "Screenshot", self.take_screenshot, "S"),
            RadialMenuItem("🎵", "Music", self.toggle_music, "M"),
            RadialMenuItem("📱", "Share", self.copy_last_response, "H"),
            RadialMenuItem("🌐", "Mode", self.toggle_mode, "O"),
            RadialMenuItem("⚙️", "Settings", self.show_settings, ","),
            RadialMenuItem("💤", "Sleep/Wake", self.toggle_sleep_wake, "Z"),
            RadialMenuItem("📝", "Content", self.toggle_content_mode, "C"),
            RadialMenuItem("🎤", "Mic", self.toggle_mic, "N"),
            RadialMenuItem("❌", "Exit", self.exit_nexa, "Esc"),
        ]

