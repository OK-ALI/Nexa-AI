"""
Nexa UI Module
Contains PySide6 user interface components.
"""

from .nexa_modern_window import NexaModernWindow
from .widgets.nexa_orb_ui import NexaOrbWidget
from .content_box_window import ContentBoxWindow
from .music_indicator import MusicIndicatorWidget
from .pet.sprite_pet_widget import SpritePetWidget
from .pet.pet_speech_bubble import PetSpeechBubble
from .widgets.typing_animator import TypingAnimator
# Note: MemoryPanel is imported lazily in nexa_modern_window._toggle_memory_panel
# to avoid QWidget creation before QApplication

__all__ = [
    'NexaModernWindow',
    'NexaOrbWidget', 
    'ContentBoxWindow',
    'MusicIndicatorWidget',
    'SpritePetWidget',
    'PetSpeechBubble',
    'TypingAnimator',
]

