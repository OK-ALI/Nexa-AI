"""
Nexa Core Module
Contains all core logic components for the AI assistant.
"""

from .brain import NexaBrain
from config.settings import Config
from core.cognition.context_manager import ContextManager
from capabilities.executor import CommandExecutor
from core.interface.voice_listener import AudioListener
from core.interface.tts_engine import TTSEngine

__all__ = [
    'NexaBrain',
    'Config',
    'ContextManager',
    'CommandExecutor',
    'AudioListener',
    'TTSEngine'
]
