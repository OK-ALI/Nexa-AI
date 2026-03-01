"""
Reference Resolver for Nexa Brain
Extracted from brain.py for better modularity.

Handles:
- Pronoun resolution (it, that, this, them)
- Ordinal references (first, second, last)
- Standalone ordinal commands (auto-listing)
- Implicit references (the folder, the network)

Requires context_manager and executor for context-aware resolution.
"""

import logging
import re
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class ReferenceResolver:
    """
    Resolves pronouns, ordinals, and implicit references using context.
    Works with ContextManager and Executor for context-aware resolution.
    """
    
    def __init__(self, context_manager, executor):
        """
        Initialize ReferenceResolver with required dependencies.
        
        Args:
            context_manager: ContextManager instance for context access
            executor: Executor instance for auto-listing commands
        """
        self.context_manager = context_manager
        self.executor = executor
        
        # Ordinal patterns
        self.ordinal_patterns = ['first', 'second', 'third', 'fourth', 'fifth', 'last', 'previous']
        
        # Pronouns to resolve
        self.pronouns = ['it', 'that', 'this', 'them', 'those']
    
    def resolve_pronouns(self, user_text: str) -> str:
        """
        Resolve pronouns (it, that, this, them) to actual targets from context.
        This runs BEFORE AI processing to make commands explicit.
        
        Examples:
            "Open Chrome" → context stores target='chrome'
            "Close it" → resolves to "Close chrome"
            
            "List games" → context stores list=['Cyberpunk', 'Elden Ring', ...]
            "Launch the first one" → resolves to "Launch Cyberpunk"
        
        Args:
            user_text: Original user input with pronouns
            
        Returns:
            str: Text with pronouns resolved to actual targets
        """
        text_lower = user_text.lower()
        
        # Step 1: Check for ordinal references ("the first one", "second", "last")
        has_ordinal = any(ordinal in text_lower for ordinal in self.ordinal_patterns)
        
        if has_ordinal:
            resolved_item = self.context_manager.resolve_ordinal_reference(user_text)
            if resolved_item:
                # Replace ordinal reference with actual item
                pattern = r'\b(the\s+)?(first|second|third|fourth|fifth|last|previous)(\s+one)?\b'
                resolved_text = re.sub(pattern, resolved_item, user_text, flags=re.IGNORECASE)
                logger.info(f"✅ Resolved ordinal reference: '{user_text}' → '{resolved_text}'")
                return resolved_text
        
        # Step 2: Check for pronouns ("it", "that", "this", "them")
        has_pronoun = any(
            f' {pronoun} ' in f' {text_lower} ' or 
            f' {pronoun},' in f' {text_lower},' or
            text_lower.endswith(f' {pronoun}') 
            for pronoun in self.pronouns
        )
        
        if has_pronoun:
            last_target = self.context_manager.get_last_target()
            if last_target:
                # Replace pronouns with actual target
                resolved_text = user_text
                
                for pronoun in self.pronouns:
                    # Pattern: whole word match (not part of another word)
                    pattern = r'\b' + pronoun + r'\b'
                    if re.search(pattern, text_lower):
                        resolved_text = re.sub(pattern, last_target, resolved_text, flags=re.IGNORECASE)
                        logger.info(f"✅ Resolved pronoun '{pronoun}' → '{last_target}' in: '{user_text}'")
                        return resolved_text
            else:
                logger.debug(f"⚠️ Pronoun detected but no target in context: '{user_text}'")
        
        # Step 3: Check for implicit references ("the folder", "the network", "the game")
        implicit_references = self._detect_implicit_references(user_text)
        if implicit_references:
            resolved_text = self._resolve_implicit_references(user_text, implicit_references)
            if resolved_text != user_text:
                logger.info(f"✅ Resolved implicit reference: '{user_text}' → '{resolved_text}'")
                return resolved_text
        
        # No pronouns, ordinals, or implicit references to resolve
        return user_text
    
    def resolve_standalone_ordinal(self, user_text: str) -> str:
        """
        Resolve standalone ordinal commands by auto-executing implicit list commands.
        
        Handles cases like:
            "launch the first one" → auto-lists games → resolves to "launch TEKKEN 8"
            "open the second app" → auto-lists running apps → resolves to "open Chrome"
            "connect to the last network" → auto-lists WiFi → resolves to "connect to HomeWiFi"
        
        This ONLY runs if there's NO list in context (standalone ordinal command).
        
        Args:
            user_text: Original user input with ordinal reference
            
        Returns:
            str: Text with ordinal resolved to actual item (after auto-listing)
        """
        text_lower = user_text.lower()
        
        # Check if ordinal present
        ordinal_match = re.search(r'\b(first|second|third|fourth|fifth|last|previous)(\s+one)?\b', text_lower)
        if not ordinal_match:
            return user_text  # No ordinal found
        
        ordinal = ordinal_match.group(1)  # Extract ordinal word
        
        # Check if we already have a list in context
        existing_list = self.context_manager.get_last_list()
        if existing_list:
            # List exists, let normal pronoun resolution handle it
            return user_text
        
        # No list in context - need to infer what to list
        logger.info(f"🔍 Standalone ordinal detected: '{ordinal}' with no context")
        
        # Detect what type of list is needed based on command keywords
        list_type = None
        list_command = None
        
        # Music-related keywords (check first - "play" is ambiguous)
        if any(word in text_lower for word in ['song', 'music', 'track', 'album', 'artist']):
            list_type = 'songs'
            list_command = 'list_music'
            logger.info(f"📋 Inferred list type: songs (detected music-related command)")
        
        # Game-related keywords
        elif any(word in text_lower for word in ['launch', 'start game', 'open game', 'game']):
            list_type = 'games'
            list_command = 'list_games'
            logger.info(f"📋 Inferred list type: games (detected game-related command)")
        
        # App-related keywords
        elif any(word in text_lower for word in ['open app', 'close app', 'switch to', 'running', 'application']):
            list_type = 'apps'
            list_command = 'get_running_applications'
            logger.info(f"📋 Inferred list type: running apps (detected app-related command)")
        
        # Network-related keywords
        elif any(word in text_lower for word in ['connect', 'wifi', 'network', 'ssid']):
            list_type = 'networks'
            list_command = 'list_wifi_networks'
            logger.info(f"📋 Inferred list type: WiFi networks (detected network command)")
        
        # If can't infer, return unchanged
        if not list_command:
            logger.warning(f"⚠️ Could not infer list type for ordinal command: '{user_text}'")
            return user_text
        
        # Execute the list command to populate context
        try:
            logger.info(f"🔧 Auto-executing {list_command} to resolve ordinal...")
            result = self.executor.function_registry.call(list_command, {})
            
            # Store the result in context
            self.context_manager.push_action(
                action=list_command,
                data={},
                result=result
            )
            
            logger.info(f"✅ Auto-list result: {result[:100]}...")
            
            # Now resolve the ordinal with populated context
            resolved_item = self.context_manager.resolve_ordinal_reference(user_text)
            
            if resolved_item:
                # Replace ordinal reference with actual item
                pattern = r'\b(the\s+)?(first|second|third|fourth|fifth|last|previous)(\s+one)?\b'
                resolved_text = re.sub(pattern, resolved_item, user_text, flags=re.IGNORECASE)
                logger.info(f"✅ Resolved standalone ordinal: '{user_text}' → '{resolved_text}'")
                return resolved_text
            else:
                logger.warning(f"⚠️ Failed to resolve ordinal after auto-listing: '{user_text}'")
                return user_text
                
        except Exception as e:
            logger.error(f"❌ Auto-list execution failed for '{list_command}': {e}")
            return user_text
    
    def _detect_implicit_references(self, user_text: str) -> Dict[str, str]:
        """
        Detect implicit references in user text (e.g., "the folder", "the network").
        
        Args:
            user_text: User input text
            
        Returns:
            Dict mapping reference type to phrase found
        """
        text_lower = user_text.lower()
        detected = {}
        
        # Folder references
        if re.search(r'\b(the|that|this)\s+(folder|directory)\b', text_lower):
            detected['folder'] = 'folder'
        
        # Network references
        if re.search(r'\b(the|that|this)\s+(network|wifi|ssid)\b', text_lower):
            detected['network'] = 'network'
        
        # Game references
        if re.search(r'\b(the|that|this)\s+game\b', text_lower):
            detected['game'] = 'game'
        
        # App/Application references
        if re.search(r'\b(the|that|this)\s+(app|application)\b', text_lower):
            detected['app'] = 'app'
        
        # Screenshot references
        if re.search(r'(where|the)\s+(screenshot|screenshots)\s+(go|are|saved|folder)', text_lower):
            detected['screenshots_folder'] = 'screenshots folder'
        
        # Downloads folder references
        if re.search(r'(where|the)\s+(download|downloads)\s+(go|are|saved|folder)', text_lower):
            detected['downloads_folder'] = 'downloads folder'
        
        return detected
    
    def _resolve_implicit_references(self, user_text: str, references: Dict[str, str]) -> str:
        """
        Resolve implicit references to actual entities from context.
        
        Args:
            user_text: Original user input
            references: Dict of detected reference types
            
        Returns:
            str: Text with implicit references resolved
        """
        resolved_text = user_text
        
        # Get action stack for context
        if not self.context_manager.action_stack:
            logger.debug("⚠️ No context available for implicit reference resolution")
            return user_text
        
        # Resolve based on reference type
        for ref_type, ref_phrase in references.items():
            
            # Resolve "the folder" to last folder action
            if ref_type == 'folder':
                # Look for last folder-related action
                for action in reversed(self.context_manager.action_stack):
                    action_name = action.get('action', '')
                    action_data = action.get('data', {})
                    
                    if action_name in ['find_folder', 'open_folder', 'take_screenshot']:
                        # Extract folder name
                        if action_name == 'take_screenshot':
                            folder_name = 'screenshots folder'
                        else:
                            folder_name = action_data.get('folder_name') or action_data.get('path', '')
                        
                        if folder_name:
                            # Replace "the folder" with actual folder name
                            pattern = r'\b(the|that|this)\s+(folder|directory)\b'
                            resolved_text = re.sub(pattern, folder_name, resolved_text, flags=re.IGNORECASE)
                            logger.debug(f"📁 Resolved 'the folder' → '{folder_name}'")
                            break
            
            # Resolve "the network" to last network action
            elif ref_type == 'network':
                for action in reversed(self.context_manager.action_stack):
                    action_name = action.get('action', '')
                    action_data = action.get('data', {})
                    
                    if action_name in ['list_wifi_networks', 'connect_wifi', 'get_wifi_status']:
                        network_name = action_data.get('network_name', '')
                        if network_name:
                            pattern = r'\b(the|that|this)\s+(network|wifi|ssid)\b'
                            resolved_text = re.sub(pattern, network_name, resolved_text, flags=re.IGNORECASE)
                            logger.debug(f"📡 Resolved 'the network' → '{network_name}'")
                            break
            
            # Resolve "the game" to last game action
            elif ref_type == 'game':
                for action in reversed(self.context_manager.action_stack):
                    action_name = action.get('action', '')
                    action_data = action.get('data', {})
                    
                    if action_name in ['launch_game', 'list_games']:
                        game_name = action_data.get('game_name', '')
                        if game_name:
                            pattern = r'\b(the|that|this)\s+game\b'
                            resolved_text = re.sub(pattern, game_name, resolved_text, flags=re.IGNORECASE)
                            logger.debug(f"🎮 Resolved 'the game' → '{game_name}'")
                            break
            
            # Resolve "the app" to last app action
            elif ref_type == 'app':
                for action in reversed(self.context_manager.action_stack):
                    action_name = action.get('action', '')
                    action_data = action.get('data', {})
                    
                    if action_name in ['open_application', 'close_window', 'minimize_window', 'maximize_window']:
                        app_name = action_data.get('app_name', '')
                        if app_name:
                            pattern = r'\b(the|that|this)\s+(app|application)\b'
                            resolved_text = re.sub(pattern, app_name, resolved_text, flags=re.IGNORECASE)
                            logger.debug(f"💻 Resolved 'the app' → '{app_name}'")
                            break
            
            # Resolve "where screenshots go" to screenshots folder
            elif ref_type == 'screenshots_folder':
                # Replace with explicit folder reference
                pattern = r'(where|the)\s+(screenshot|screenshots)\s+(go|are|saved|folder)'
                resolved_text = re.sub(pattern, 'screenshots folder', resolved_text, flags=re.IGNORECASE)
                logger.debug(f"📸 Resolved 'where screenshots go' → 'screenshots folder'")
            
            # Resolve "where downloads go" to downloads folder
            elif ref_type == 'downloads_folder':
                pattern = r'(where|the)\s+(download|downloads)\s+(go|are|saved|folder)'
                resolved_text = re.sub(pattern, 'downloads folder', resolved_text, flags=re.IGNORECASE)
                logger.debug(f"📥 Resolved 'where downloads go' → 'downloads folder'")
        
        return resolved_text


# Singleton instance
_resolver_instance: Optional[ReferenceResolver] = None


def get_reference_resolver(context_manager=None, executor=None) -> ReferenceResolver:
    """
    Get or create the ReferenceResolver singleton.
    
    Args:
        context_manager: ContextManager instance (required on first call)
        executor: Executor instance (required on first call)
        
    Returns:
        ReferenceResolver singleton instance
    """
    global _resolver_instance
    
    if _resolver_instance is None:
        if context_manager is None or executor is None:
            raise ValueError("context_manager and executor required for first initialization")
        _resolver_instance = ReferenceResolver(context_manager, executor)
    
    return _resolver_instance
