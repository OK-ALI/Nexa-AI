"""
Context Manager - Local Memory and Conversation History
Manages conversation context, user preferences, and persistent storage.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from threading import RLock

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages Nexa's memory, conversation history, and user preferences.
    All data is stored locally in JSON format for privacy and transparency.
    """
    
    def __init__(self, config):
        """
        Initialize context manager with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.memory_file = config.memory_file
        self.prefs_file = config.prefs_file
        
        # Thread-safe access to memory (using RLock to allow reentrant calls)
        self._lock = RLock()
        
        # In-memory storage
        self.conversation_history: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Any] = {}
        
        # Pending action for confirmation follow-ups
        self.pending_action: Dict[str, Any] = {}
        
        # LEGACY: Single action storage (kept for backwards compatibility)
        self.last_action: str = ""
        self.last_action_data: Dict[str, Any] = {}
        
        # NEW: Action stack for multi-step context (stores last 5 actions)
        self.action_stack: List[Dict[str, Any]] = []
        
        # Load existing data
        self._load_memory()
        self._load_preferences()
        
        logger.info("Context Manager initialized")
    
    def _load_memory(self):
        """Load conversation history from disk."""
        try:
            if self.memory_file.exists():
                with open(self.memory_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
                    data = json.load(f)
                    self.conversation_history = data.get('history', [])
                logger.info(f"Loaded {len(self.conversation_history)} conversation entries")
            else:
                logger.info("No existing memory file, starting fresh")
                self._save_memory()
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            self.conversation_history = []
    
    def _load_preferences(self):
        """Load user preferences from disk."""
        try:
            if self.prefs_file.exists():
                with open(self.prefs_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
                    self.user_preferences = json.load(f)
                logger.info("User preferences loaded")
            else:
                # Create default preferences
                self.user_preferences = self._get_default_preferences()
                self._save_preferences()
                logger.info("Created default preferences")
        except Exception as e:
            logger.error(f"Error loading preferences: {e}")
            self.user_preferences = self._get_default_preferences()
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences."""
        return {
            'voice': {
                'speed': 1.0,
                'pitch': 1.0,
                'volume': 0.8
            },
            'ui': {
                'theme': 'dark',
                'show_waveform': True,
                'minimize_to_tray': True
            },
            'privacy': {
                'save_conversations': True,
                'max_history_days': 30
            },
            'behavior': {
                'wake_word_enabled': False,
                'wake_word': 'nexa',
                'auto_listen_after_response': False
            },
            # NEW: Learned user preferences (auto-detected patterns)
            'learned': {
                'volume_levels': {},  # Tracks most common volume settings
                'brightness_levels': {},  # Tracks most common brightness settings
                'frequently_opened_apps': {},  # Tracks app open frequency
                'preferred_game_platform': None,  # Steam, Epic, GOG, etc.
                'common_commands': {},  # Tracks command frequency
            }
        }
    
    def _save_memory(self):
        """Save conversation history to disk. Must be called from within locked context."""
        try:
            data = {
                'history': self.conversation_history,
                'last_updated': self._get_timestamp()
            }
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
    
    def _save_preferences(self):
        """Save user preferences to disk."""
        try:
            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")
    
    def add_interaction(self, user_message: str, nexa_response: str):
        """
        Add a new conversation interaction.
        
        Args:
            user_message: User's input
            nexa_response: Nexa's response (can be empty initially)
        """
        with self._lock:
            # Skip storing useless/duplicate conversations
            if self._should_skip_interaction(user_message, nexa_response):
                logger.debug(f"Skipping low-value interaction: '{user_message[:30]}'")
                return
            
            interaction = {
                'timestamp': self._get_timestamp(),
                'user': user_message,
                'nexa': nexa_response
            }
            self.conversation_history.append(interaction)
            
            # Limit history size (keep last 100 interactions)
            if len(self.conversation_history) > 100:
                self.conversation_history = self.conversation_history[-100:]
                logger.info("Trimmed conversation history to last 100 interactions")
            
            # Periodically save to disk (every 5 interactions)
            if len(self.conversation_history) % 5 == 0:
                self._save_memory()
    
    def _should_skip_interaction(self, user_message: str, nexa_response: str) -> bool:
        """
        Determine if an interaction should be skipped from memory.
        Skips short, repetitive, or low-value conversations.
        
        Args:
            user_message: User's input
            nexa_response: Nexa's response
            
        Returns:
            True if should skip, False if should store
        """
        user_lower = user_message.lower().strip()
        
        # Skip very short messages (less than 3 characters)
        if len(user_message.strip()) < 3:
            return True
        
        # Skip repetitive words (e.g., "and and and and")
        words = user_lower.split()
        if len(words) > 3 and len(set(words)) == 1:
            return True
        
        # Skip single repeated words
        if len(words) > 5:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:  # More than 70% repetition
                return True
        
        # Skip if just thanks/okay with no meaningful content
        simple_responses = ['thank you', 'thanks', 'okay', 'ok', 'sure', 'yes', 'no', 'yeah']
        if user_lower in simple_responses and not nexa_response:
            return True
        
        # Skip if duplicate of last interaction
        if self.conversation_history:
            last = self.conversation_history[-1]
            if last['user'].lower().strip() == user_lower:
                return True
        
        return False
    
    def update_last_response(self, nexa_response: str):
        """
        Update the last interaction with Nexa's response.
        
        Args:
            nexa_response: Nexa's response text
        """
        with self._lock:
            if self.conversation_history:
                self.conversation_history[-1]['nexa'] = nexa_response
                self._save_memory()
    
    def get_recent_context(self, max_interactions: int = 10, summarize_old: bool = True) -> List[Dict[str, Any]]:
        """
        Get recent conversation history, with optional summarization of older conversations.
        
        Args:
            max_interactions: Maximum number of interactions to return
            summarize_old: If True and history > max, prepend a summary of older conversations
            
        Returns:
            List of recent interactions (may include summary as first item)
        """
        with self._lock:
            recent = self.conversation_history[-max_interactions:]
            
            # If we have more history than requested, optionally add summary
            if summarize_old and len(self.conversation_history) > max_interactions:
                older_count = len(self.conversation_history) - max_interactions
                summary_entry = {
                    'timestamp': 'summary',
                    'user': '[CONVERSATION SUMMARY]',
                    'nexa': f'Previous {older_count} interactions covered: system commands, app management, and general queries.'
                }
                return [summary_entry] + recent
            
            return recent
    
    def clear_history(self):
        """Clear all conversation history."""
        with self._lock:
            self.conversation_history = []
            self._save_memory()
        logger.info("Conversation history cleared")
    
    def clear_old_history(self, days: int = 7):
        """
        Clear conversation history older than specified days.
        
        Args:
            days: Number of days to keep (default: 7)
        """
        with self._lock:
            if not self.conversation_history:
                return
            
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            original_count = len(self.conversation_history)
            self.conversation_history = [
                interaction for interaction in self.conversation_history
                if datetime.fromisoformat(interaction['timestamp']) > cutoff_date
            ]
            
            removed_count = original_count - len(self.conversation_history)
            if removed_count > 0:
                self._save_memory()
                logger.info(f"Cleared {removed_count} old interactions (older than {days} days)")

    
    def get_preference(self, category: str, key: str, default=None):
        """
        Get a user preference value.
        
        Args:
            category: Preference category (e.g., 'voice', 'ui')
            key: Preference key
            default: Default value if not found
            
        Returns:
            Preference value or default
        """
        return self.user_preferences.get(category, {}).get(key, default)
    
    def set_preference(self, category: str, key: str, value: Any):
        """
        Set a user preference value.
        
        Args:
            category: Preference category
            key: Preference key
            value: Value to set
        """
        if category not in self.user_preferences:
            self.user_preferences[category] = {}
        
        self.user_preferences[category][key] = value
        self._save_preferences()
        logger.info(f"Preference updated: {category}.{key} = {value}")
    
    def set_pending_action(self, action_type: str, action_data: Dict[str, Any]):
        """
        Store a pending action that needs user confirmation.
        
        Args:
            action_type: Type of action (e.g., 'open_app', 'close_app', 'command')
            action_data: Action details (e.g., {'app_name': 'chrome', 'command': 'OPEN_APP:chrome'})
        """
        with self._lock:
            self.pending_action = {
                'type': action_type,
                'data': action_data,
                'timestamp': self._get_timestamp()
            }
            logger.info(f"Pending action set: {action_type} - {action_data}")
    
    def get_pending_action(self) -> Dict[str, Any]:
        """
        Get and clear pending action.
        
        Returns:
            Pending action dict or empty dict if none
        """
        with self._lock:
            action = self.pending_action.copy()
            self.pending_action = {}
            return action
    
    def has_pending_action(self) -> bool:
        """
        Check if there's a pending action.
        
        Returns:
            True if pending action exists
        """
        return bool(self.pending_action)
    
    def clear_pending_action(self):
        """Clear any pending action."""
        with self._lock:
            self.pending_action = {}
            logger.info("Pending action cleared")
    
    def set_last_action(self, action: str, data: Dict[str, Any] = None):
        """
        Store the last action performed for smart follow-ups.
        
        Args:
            action: Action identifier (e.g., 'list_games', 'list_apps')
            data: Action-specific data (e.g., games list, count)
        """
        with self._lock:
            self.last_action = action
            self.last_action_data = data or {}
            logger.info(f"📌 Stored last action: {action}")
    
    def get_last_action(self) -> tuple[str, Dict[str, Any]]:
        """
        Get the last action and its data.
        
        Returns:
            Tuple of (action, data) for backwards compatibility,
            or dict if action stack has data
        """
        # NEW: If action stack has data, return most recent as dict
        if self.action_stack:
            return self.action_stack[-1]
        
        # LEGACY: Return tuple format for old code
        return self.last_action, self.last_action_data
    
    def clear_last_action(self):
        """Clear the last action context."""
        with self._lock:
            self.last_action = ""
            self.last_action_data = {}
    
    # ============================================================================
    # NEW: Action Stack Methods (Enhanced Multi-Step Context)
    # ============================================================================
    
    def push_action(self, action: str, data: Dict[str, Any] = None, result: Any = None):
        """
        Push a new action onto the action stack (stores last 5 actions).
        This enables multi-step context like "the previous one", "the first one".
        
        Args:
            action: Action identifier (e.g., 'list_games', 'open_application')
            data: Action parameters (e.g., {'platform': 'steam'})
            result: Action result (e.g., "Found 5 games")
        """
        with self._lock:
            action_entry = {
                'action': action,
                'data': data or {},
                'result': result,
                'timestamp': self._get_timestamp()
            }
            
            self.action_stack.append(action_entry)
            
            # Keep only last 5 actions (FIFO - First In, First Out)
            if len(self.action_stack) > 5:
                removed = self.action_stack.pop(0)
                logger.debug(f"🗑️ Removed oldest action from stack: {removed['action']}")
            
            logger.info(f"📚 Action stack: {len(self.action_stack)} actions (added: {action})")
            
            # ALSO update legacy single-action storage for backwards compatibility
            self.last_action = action
            self.last_action_data = {'result': result, 'data': data}
    
    def get_action_history(self, count: int = 3) -> List[Dict[str, Any]]:
        """
        Get recent action history from the stack.
        
        Args:
            count: Number of recent actions to retrieve (default: 3, max: 5)
            
        Returns:
            List of action entries (most recent last)
        """
        count = min(count, 5)  # Cap at 5
        return self.action_stack[-count:] if self.action_stack else []
    
    def get_action_by_index(self, index: int) -> Dict[str, Any]:
        """
        Get a specific action from the stack by index.
        Index 0 = oldest, -1 = most recent.
        
        Args:
            index: Stack index (negative for counting from end)
            
        Returns:
            Action entry or empty dict if index out of range
        """
        try:
            return self.action_stack[index]
        except IndexError:
            return {}
    
    def get_last_n_actions(self, action_type: str, n: int = 2) -> List[Dict[str, Any]]:
        """
        Get the last N actions of a specific type.
        Useful for "show me both game lists" (Steam + Epic).
        
        Args:
            action_type: Action identifier to filter by (supports substring matching)
            n: Number of matching actions to retrieve
            
        Returns:
            List of matching action entries
        """
        # Support both exact match and substring match
        matching = [a for a in self.action_stack 
                   if action_type.lower() in a['action'].lower()]
        return matching[-n:] if matching else []
    
    def clear_action_stack(self):
        """Clear the entire action stack."""
        with self._lock:
            self.action_stack = []
            logger.info("🗑️ Action stack cleared")
    
    def get_action_stack_summary(self) -> str:
        """
        Get a human-readable summary of the action stack.
        Useful for debugging or showing user their recent actions.
        
        Returns:
            Formatted string summarizing recent actions
        """
        if not self.action_stack:
            return "No recent actions"
        
        summary = f"Recent {len(self.action_stack)} actions:\n"
        for i, action in enumerate(self.action_stack, 1):
            summary += f"{i}. {action['action']}"
            if action.get('result'):
                result_preview = str(action['result'])[:50]
                summary += f" → {result_preview}"
            summary += "\n"
        
        return summary.strip()
    
    # ============================================================================
    # NEW: Pronoun Resolution System (Track targets for "it", "that", "them", etc.)
    # ============================================================================
    
    def get_last_target(self, preferred_type: str = None) -> str:
        """
        Get the most recent target from action stack (what was acted upon).
        Used to resolve pronouns like "it", "that", "this".
        
        Returns:
            Target string (e.g., 'chrome', 'screenshots', 'steam') or empty string
        """
        # If a preferred_type is requested (e.g., 'application', 'game', 'folder', 'network'),
        # search the action_stack for the most recent matching action of that type.
        if preferred_type:
            # Map requested type to action name keywords
            type_map = {
                'application': ['open_application', 'close_window', 'minimize_window', 'maximize_window', 'close_application', 'is_application_running'],
                'app': ['open_application', 'close_window', 'minimize_window', 'maximize_window', 'close_application', 'is_application_running'],
                'window': ['open_application', 'close_window', 'minimize_window', 'maximize_window', 'restore_window'],
                'game': ['launch_game', 'list_games'],
                'folder': ['find_folder', 'open_folder', 'take_screenshot'],
                'network': ['list_wifi_networks', 'connect_wifi', 'get_wifi_status'],
            }

            candidates = type_map.get(preferred_type, [])
            for action in reversed(self.action_stack):
                if action.get('action') in candidates:
                    action_data = action.get('data', {})
                    # reuse existing extraction logic by temporarily setting action_name
                    action_name = action.get('action', '')
                    break
            else:
                # If nothing in stack, only use legacy last_action if it matches the requested type
                if self.last_action in candidates:
                    action_name = self.last_action
                    action_data = self.last_action_data if isinstance(self.last_action_data, dict) else {}
                else:
                    # No suitable context found
                    action_name = ''
                    action_data = {}
        else:
            # If there is no action stack, fall back to legacy last_action/last_action_data
            if not self.action_stack:
                action_name = self.last_action or ''
                # Ensure dict for last_action_data
                action_data = self.last_action_data if isinstance(self.last_action_data, dict) else {}
            else:
                # Check most recent action for a target
                last_action = self.action_stack[-1]
                action_name = last_action.get('action', '')
                action_data = last_action.get('data', {})
        
        # Extract target based on action type
        target = None

        # App/window actions → target is app_name
        if action_name in ['open_application', 'close_window', 'minimize_window', 
                          'maximize_window', 'restore_window', 'is_application_running', 'close_application']:
            target = action_data.get('app_name')

        # Game actions → target is game_name or 'games' (plural)
        elif action_name in ['launch_game', 'list_games']:
            # Prefer explicit game_name, otherwise use generic 'games' as target
            if action_data.get('game_name'):
                target = action_data.get('game_name')
            else:
                target = 'games'

        # File/folder actions → target is folder_name or path
        elif action_name in ['find_folder', 'open_folder']:
            target = action_data.get('folder_name') or action_data.get('path')

        # Screenshot actions → target is 'screenshots' or folder
        elif action_name == 'take_screenshot':
            target = 'screenshots'

        # Network actions → target is 'wifi' or network name
        elif action_name in ['list_wifi_networks', 'connect_wifi', 'get_wifi_status']:
            target = action_data.get('network_name') or 'wifi'

        # Running apps → target is 'running applications'
        elif action_name == 'get_running_applications':
            target = 'running applications'

        # Screen analysis → target is 'screen'
        elif action_name in ['analyze_screen', 'read_screen_text', 'describe_screen']:
            target = 'screen'

        # Query-type informational actions → map to simple targets
        elif action_name in ['get_battery_status', 'check_battery', 'get_battery_percentage']:
            target = 'battery'
        elif action_name in ['get_current_time', 'get_time']:
            target = 'time'
        elif action_name in ['get_current_volume', 'get_volume', 'get_volume_level']:
            target = 'volume'
        elif action_name in ['get_current_brightness', 'get_brightness']:
            target = 'brightness'

        # If no specific target, do NOT fabricate one from the action name.
        # Returning an empty string allows callers to attempt safer fallbacks
        # (for example, resolving the active window title) instead of producing
        # unnatural phrases like 'minimize open application'.
        if not target:
            logger.debug(f"🎯 No explicit target found for action '{action_name}'")
            return ""

        logger.debug(f"🎯 Last target extracted: '{target}' from action '{action_name}'")
        return target
    
    def get_last_list(self) -> List[str]:
        """
        Get the last list of items returned (for resolving "the first one", "the second", etc.).
        
        Returns:
            List of items (e.g., game names, app names) or empty list
        """
        # If action_stack empty, fall back to legacy last_action_data saved by set_last_action
        if not self.action_stack:
            # Legacy storage may contain a 'games' list or similar in last_action_data
            if isinstance(self.last_action_data, dict):
                if 'games' in self.last_action_data:
                    return list(self.last_action_data.get('games', []))
                if 'items' in self.last_action_data:
                    return list(self.last_action_data.get('items', []))
            return []

        # Check recent actions for list results
        for action in reversed(self.action_stack):
            action_name = action.get('action', '')
            action_data = action.get('data', {})
            result = action.get('result', '')
            
            # List-type actions that return multiple items
            if action_name == 'list_games':
                # Parse game names from result (format: "Found N games: Game1, Game2...")
                if isinstance(result, str) and 'Found' in result:
                    # Extract games after the colon
                    import re
                    match = re.search(r': (.+)', result)
                    if match:
                        games_str = match.group(1).strip()
                        # Split by comma and clean
                        games = [g.strip() for g in games_str.split(',') if g.strip()]
                        logger.debug(f"📋 Extracted game list: {len(games)} games")
                        return games
            
            elif action_name == 'get_running_applications':
                # Parse running apps from result
                if isinstance(result, str):
                    import re
                    # Format: "Running: App1, App2, App3"
                    match = re.search(r'Running:?\s*(.+)', result, re.IGNORECASE)
                    if match:
                        apps_str = match.group(1).strip()
                        apps = [a.strip() for a in apps_str.split(',') if a.strip()]
                        logger.debug(f"📋 Extracted app list: {len(apps)} apps")
                        return apps
            
            elif action_name == 'list_wifi_networks':
                # Parse WiFi networks from result
                if isinstance(result, str):
                    import re
                    # Format: "Available networks: Net1, Net2..."
                    match = re.search(r'(?:Available|Found)[^:]*:\s*(.+)', result, re.IGNORECASE)
                    if match:
                        networks_str = match.group(1).strip()
                        networks = [n.strip() for n in networks_str.split(',') if n.strip()]
                        logger.debug(f"📋 Extracted network list: {len(networks)} networks")
                        return networks
        
        logger.debug("📋 No list found in recent actions")
        return []
    
    def resolve_ordinal_reference(self, reference: str) -> str:
        """
        Resolve ordinal references like "the first one", "second", "last" to actual item.
        
        Args:
            reference: Text containing ordinal reference (e.g., "launch the first one")
            
        Returns:
            Resolved item name or empty string if can't resolve
        """
        last_list = self.get_last_list()
        if not last_list:
            logger.debug("⚠️ Cannot resolve ordinal: no list in context")
            return ""
        
        ref_lower = reference.lower()
        
        # Ordinal mapping
        ordinals = {
            'first': 0,
            'second': 1,
            'third': 2,
            'fourth': 3,
            'fifth': 4,
            'last': -1,
            'previous': -1,
        }
        
        # Find which ordinal was mentioned
        for ordinal, index in ordinals.items():
            if ordinal in ref_lower:
                try:
                    resolved_item = last_list[index]
                    logger.info(f"✅ Resolved ordinal '{ordinal}' → '{resolved_item}' from list of {len(last_list)}")
                    return resolved_item
                except IndexError:
                    logger.warning(f"⚠️ Ordinal '{ordinal}' (index {index}) out of range for list of {len(last_list)}")
                    return ""
        
        logger.debug(f"⚠️ No ordinal found in reference: '{reference}'")
        return ""
    
    # ============================================================================
    
    def store_screen_analysis(self, analysis_type: str, result: str):
        """
        Store the most recent screen analysis result for follow-up questions.
        
        Args:
            analysis_type: Type of analysis ('ocr', 'vision', 'combined')
            result: Analysis result text
        """
        with self._lock:
            self.user_preferences['last_screen_analysis'] = {
                'type': analysis_type,
                'result': result,
                'timestamp': self._get_timestamp()
            }
            logger.info(f"📝 Stored screen analysis: {analysis_type}, {len(result)} chars")
    
    def get_last_screen_analysis(self) -> Dict[str, Any]:
        """
        Get the most recent screen analysis result.
        
        Returns:
            Dictionary with 'type', 'result', and 'timestamp', or empty dict
        """
        return self.user_preferences.get('last_screen_analysis', {})
    
    def has_screen_analysis_context(self) -> bool:
        """
        Check if there's a recent screen analysis available for context.
        
        Returns:
            True if screen analysis context exists
        """
        analysis = self.get_last_screen_analysis()
        if not analysis:
            return False
        
        # Check if analysis is recent (within last 5 minutes)
        try:
            from datetime import datetime, timedelta
            timestamp = datetime.fromisoformat(analysis.get('timestamp', ''))
            age = datetime.now() - timestamp
            return age < timedelta(minutes=5)
        except:
            return False
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    # ============================================================================
    # NEW: User Preference Learning System (Auto-detect patterns)
    # ============================================================================
    
    def learn_preference(self, category: str, key: str, value: Any):
        """
        Track user behavior and learn preferences over time.
        When a pattern is used 5+ times, it becomes a "learned preference".
        
        Args:
            category: Preference category ('volume', 'brightness', 'apps', etc.)
            key: Specific preference key (e.g., 'level', 'app_name')
            value: The value used (e.g., 50, 'chrome')
            
        Example:
            User sets volume to 50 five times → Learn that 50 is preferred volume
        """
        with self._lock:
            # Ensure learned preferences structure exists
            if 'learned' not in self.user_preferences:
                self.user_preferences['learned'] = {}
            
            learned = self.user_preferences['learned']
            
            # Initialize category tracking if needed
            if category not in learned:
                learned[category] = {}
            
            # Initialize key tracking if needed
            if key not in learned[category]:
                learned[category][key] = {}
            
            # Increment usage count for this value
            value_str = str(value)  # Convert to string for dict key
            learned[category][key][value_str] = learned[category][key].get(value_str, 0) + 1
            
            count = learned[category][key][value_str]
            
            # If used 5+ times, mark as strong preference
            if count >= 5:
                logger.info(f"📚 Learned preference: {category}.{key} = {value} (used {count} times)")
            else:
                logger.debug(f"📊 Tracking preference: {category}.{key} = {value} (count: {count})")
            
            # Periodically save (every 5 learns)
            total_learns = sum(
                sum(sum(counts.values()) for counts in cat_data.values())
                for cat_data in learned.values()
            )
            if total_learns % 5 == 0:
                self._save_preferences()
    
    def get_learned_preference(self, category: str, key: str) -> Any:
        """
        Get the most frequently used value for a preference.
        Returns None if no strong preference detected.
        
        Args:
            category: Preference category
            key: Preference key
            
        Returns:
            Most common value or None
        """
        learned = self.user_preferences.get('learned', {})
        if category not in learned or key not in learned[category]:
            return None
        
        value_counts = learned[category][key]
        if not value_counts:
            return None
        
        # Find most common value
        most_common = max(value_counts.items(), key=lambda x: x[1])
        value, count = most_common
        
        # Only return if used 3+ times (threshold for "preference")
        if count >= 3:
            # Convert value back to int if it looks like a number
            try:
                value = int(value)
            except (ValueError, TypeError):
                pass
            
            return {'value': value, 'count': count}
        return None
    
    def get_preference_suggestion(self, category: str, key: str) -> str:
        """
        Get a natural language suggestion based on learned preferences.
        
        Args:
            category: Preference category
            key: Preference key
            
        Returns:
            Human-readable suggestion or empty string
        """
        pref = self.get_learned_preference(category, key)
        if not pref:
            return ""
        
        learned = self.user_preferences.get('learned', {})
        count = learned.get(category, {}).get(key, {}).get(str(pref), 0)
        
        suggestions = {
            'volume_levels': f"You usually set volume to {pref}",
            'brightness_levels': f"You typically prefer brightness at {pref}",
            'frequently_opened_apps': f"You often open {pref}",
        }
        
        base_suggestion = suggestions.get(category, f"You often use {pref}")
        return f"{base_suggestion} (used {count} times)"
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about learned user preferences.
        Useful for debugging or showing user their patterns.
        
        Returns:
            Dictionary with usage statistics
        """
        learned = self.user_preferences.get('learned', {})
        stats = {
            'total_categories': len(learned),
            'categories': {}
        }
        
        for category, keys in learned.items():
            # keys is a dict like {'level': {'50': 3, '60': 2}}
            stats['categories'][category] = keys  # Return the actual data structure
        
        return stats
    
    def reset_learned_preferences(self, category: str = None):
        """
        Reset learned preferences (either specific category or all).
        
        Args:
            category: Category to reset (None = reset all)
        """
        with self._lock:
            learned = self.user_preferences.get('learned', {})
            
            if category:
                if category in learned:
                    learned[category] = {}
                    logger.info(f"🗑️ Reset learned preferences for: {category}")
            else:
                self.user_preferences['learned'] = {}
                logger.info(f"🗑️ Reset ALL learned preferences")
            
            self._save_preferences()
    
    # ============================================================================
    # NEW: Conversation Summarization (Token-efficient context)
    # ============================================================================
    
    def create_conversation_summary(self, interactions: List[Dict[str, Any]]) -> str:
        """
        Create a concise summary of multiple conversation interactions.
        Used to compress old conversations and save token budget.
        
        Args:
            interactions: List of conversation interactions to summarize
            
        Returns:
            Concise summary text (~50-100 tokens instead of 300-500)
        """
        if not interactions:
            return ""
        
        # Extract key actions and topics
        actions = []
        topics = set()
        
        for interaction in interactions:
            user_msg = interaction.get('user', '').lower()
            
            # Detect action types
            if any(word in user_msg for word in ['open', 'launch', 'start']):
                actions.append('opened apps')
            elif any(word in user_msg for word in ['volume', 'sound']):
                actions.append('adjusted volume')
            elif any(word in user_msg for word in ['brightness', 'screen']):
                actions.append('changed brightness')
            elif any(word in user_msg for word in ['game', 'play']):
                actions.append('checked games')
            elif any(word in user_msg for word in ['time', 'date']):
                actions.append('asked time/date')
            elif any(word in user_msg for word in ['battery', 'power']):
                actions.append('checked battery')
        
        # Create concise summary
        if actions:
            unique_actions = list(dict.fromkeys(actions))  # Remove duplicates, preserve order
            action_summary = ', '.join(unique_actions[:5])  # Max 5 actions
            return f"Earlier: {action_summary}"
        else:
            return f"Earlier: {len(interactions)} general queries"
