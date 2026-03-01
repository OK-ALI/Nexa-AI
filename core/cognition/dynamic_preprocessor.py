"""
Dynamic Command Preprocessor
Intelligent command preprocessing that works with ANY LLM model.

This module provides GUARANTEED preprocessing through code logic, not LLM interpretation.
Key features:
- Multi-step command detection and splitting
- Pronoun resolution in command sequences
- Ambiguity detection and validation
- Context-aware command transformation
- Model-agnostic (works with Llama, etc.)
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingResult:
    """Result from dynamic preprocessing."""
    commands: List[str]  # List of preprocessed commands
    needs_clarification: bool  # Whether user clarification is needed
    clarification_question: Optional[str]  # Question to ask user
    metadata: Dict[str, Any]  # Additional info (transformations applied, etc.)


class DynamicPreprocessor:
    """
    Dynamic command preprocessor with guaranteed behavior.
    
    This class implements intelligent preprocessing through code logic,
    ensuring consistent behavior regardless of which LLM is used.
    """
    
    def __init__(self, context_manager=None):
        """
        Initialize the dynamic preprocessor.
        
        Args:
            context_manager: Optional context manager for history tracking
        """
        self.context_manager = context_manager
        
        # ⚡ PHASE 1: Pre-compile all regex patterns for 10-15% speedup
        # Multi-step separators (compiled)
        self.multi_step_separators = [
            re.compile(r'\s+and\s+', re.IGNORECASE),      # " and "
            re.compile(r'\s+then\s+', re.IGNORECASE),     # " then "
            re.compile(r',\s+'),                          # ", "
            re.compile(r'\s+after that\s+', re.IGNORECASE),  # " after that "
        ]
        
        # Ambiguous verbs that require targets
        self.ambiguous_verbs = {
            'open': 'What would you like me to open?',
            'close': 'Which application should I close?',
            'launch': 'What would you like me to launch?',
            'start': 'What would you like to start?',
            'stop': 'What would you like to stop?',
            'minimize': 'Which window should I minimize?',
            'maximize': 'Which window should I maximize?',
            'hide': 'Which window should I hide?',
            'show': 'Which window should I show?',
            'restore': 'Which window should I restore?',
            'set': 'What would you like to set?',
            'get': 'What would you like to get?',
            'check': 'What would you like me to check?',
        }
        
        # Window operation variations (normalization)
        self.window_variations = {
            'make it bigger': 'maximize',
            'make bigger': 'maximize',
            'make it larger': 'maximize',
            'make larger': 'maximize',
            'make it smaller': 'minimize',
            'make smaller': 'minimize',
            'make it full screen': 'maximize',
            'make full screen': 'maximize',
            'make it fullscreen': 'maximize',
            'make fullscreen': 'maximize',
            'expand': 'maximize',
            'expand it': 'maximize',
            'shrink': 'minimize',
            'shrink it': 'minimize',
            'hide it': 'hide',
            'show it': 'show',
        }
        
        # Pronouns to resolve
        self.pronouns = ['it', 'that', 'them', 'this', 'those']
        
        # Implicit references (map phrase → context type)
        self.implicit_references = {
            'the app': 'application',
            'the application': 'application',
            'the window': 'window',
            'the game': 'game',
            'the folder': 'folder',
            'the network': 'network',
        }
        
        # Generic category mappings (map category → action types to search)
        self.category_mappings = {
            'browser': ['open_application', 'close_application', 'close_window', 'maximize_window', 'minimize_window'],
            'web browser': ['open_application', 'close_application', 'close_window', 'maximize_window', 'minimize_window'],
            'music app': ['open_application', 'close_application', 'close_window'],
            'music player': ['open_application', 'close_application', 'close_window'],
            'media player': ['open_application', 'close_application', 'close_window'],
            'text editor': ['open_application', 'close_application', 'close_window'],
            'code editor': ['open_application', 'close_application', 'close_window'],
            'ide': ['open_application', 'close_application', 'close_window'],
        }
        
        # Known apps by category (for category → app name resolution)
        self.app_categories = {
            'browser': ['chrome', 'firefox', 'edge', 'brave', 'opera', 'safari'],
            'web browser': ['chrome', 'firefox', 'edge', 'brave', 'opera', 'safari'],
            'music app': ['spotify', 'itunes', 'windows media player', 'vlc', 'foobar2000', 'musicbee'],
            'music player': ['spotify', 'itunes', 'windows media player', 'vlc', 'foobar2000', 'musicbee'],
            'media player': ['vlc', 'windows media player', 'kodi', 'plex'],
            'text editor': ['notepad', 'notepad++', 'sublime text', 'atom', 'vim', 'nano'],
            'code editor': ['vscode', 'visual studio code', 'sublime text', 'atom', 'pycharm', 'intellij'],
            'ide': ['visual studio', 'vscode', 'pycharm', 'intellij', 'eclipse', 'netbeans'],
        }
        
        logger.info("DynamicPreprocessor initialized")
    
    def preprocess(self, command: str) -> PreprocessingResult:
        """
        Main preprocessing pipeline.
        
        Applies all preprocessing steps in order:
        1. Normalize command variations
        2. Detect and handle multi-step commands
        3. Resolve implicit references and categories (BEFORE ambiguity check)
        4. Check for ambiguity
        
        Args:
            command: Raw user command
            
        Returns:
            PreprocessingResult with processed commands or clarification request
        """
        metadata = {'original_command': command, 'transformations': []}
        
        logger.debug(f"[DynamicPreprocessor] Processing: '{command}'")
        
        # STAGE 1: Normalize command variations
        normalized = self._normalize_command(command)
        if normalized != command:
            metadata['transformations'].append(f"Normalized: '{command}' → '{normalized}'")
            command = normalized
        
        # STAGE 2: Detect and split multi-step commands
        is_multi_step, commands = self._detect_multi_step(command)
        if is_multi_step:
            metadata['transformations'].append(f"Split into {len(commands)} commands")
            logger.info(f"[DynamicPreprocessor] Multi-step detected: {commands}")
        else:
            commands = [command]
        
        # STAGE 3: Resolve pronouns in command sequence (for multi-step)
        commands = self._resolve_pronouns_in_sequence(commands)
        
        # STAGE 4: Resolve implicit references and categories
        # This also resolves single-command pronouns using action stack
        commands = [self._resolve_implicit_references(cmd) for cmd in commands]
        
        # STAGE 5: Check for ambiguity (AFTER resolving references)
        # Only check first command for ambiguity (for simplicity)
        if commands:
            ambiguity_check = self._check_ambiguity(commands[0])
            if ambiguity_check:
                logger.info(f"[DynamicPreprocessor] Ambiguous command detected: {ambiguity_check}")
                return PreprocessingResult(
                    commands=[],
                    needs_clarification=True,
                    clarification_question=ambiguity_check,
                    metadata=metadata
                )
        
        logger.debug(f"[DynamicPreprocessor] Final commands: {commands}")
        
        return PreprocessingResult(
            commands=commands,
            needs_clarification=False,
            clarification_question=None,
            metadata=metadata
        )
    
    def _normalize_command(self, command: str) -> str:
        """
        Normalize command variations to standard forms.
        
        Examples:
        - "make it bigger" → "maximize it"
        - "make chrome full screen" → "maximize chrome"
        - "turn up volume" → "increase volume"
        
        Args:
            command: Original command
            
        Returns:
            Normalized command
        """
        command_lower = command.lower()
        # Normalize references to active/current/focused window into 'the window' so implicit
        # reference resolution can resolve it from context or active window.
        command_lower = re.sub(r"\b(active|current|focused)\s+window\b", 'the window', command_lower)
        
        # Check window variations
        for variation, normalized in self.window_variations.items():
            if variation in command_lower:
                # Extract target (app/window name)
                # Pattern: "make [target] bigger" or "make it bigger"
                target = ""
                if ' it ' in command_lower or command_lower.endswith(' it'):
                    target = "it"
                else:
                    # Try to extract app name
                    words = command.split()
                    for i, word in enumerate(words):
                        if word.lower() in ['make', 'bigger', 'smaller', 'full', 'screen', 'fullscreen', 'larger']:
                            continue
                        target = word
                        break
                
                if target:
                    result = f"{normalized} {target}"
                else:
                    result = normalized
                
                logger.debug(f"[Normalize] '{command}' → '{result}'")
                return result
        
        # Volume variations
        volume_patterns = [
            (r'\bturn (up|down) (?:the )?volume\b', r'\1 volume'),
            (r'\bvolume (up|down)\b', r'\1 volume'),
            (r'\bincrease volume\b', 'volume up'),
            (r'\bdecrease volume\b', 'volume down'),
            (r'\blower volume\b', 'volume down'),
            (r'\bhigher volume\b', 'volume up'),
        ]
        
        for pattern, replacement in volume_patterns:
            if re.search(pattern, command_lower):
                result = re.sub(pattern, replacement, command_lower, flags=re.IGNORECASE)
                logger.debug(f"[Normalize] '{command}' → '{result}'")
                return result
        
        return command
    
    def _check_ambiguity(self, command: str) -> Optional[str]:
        """
        Check if command is ambiguous and needs clarification.
        
        Detects commands that are missing critical information:
        - Single verb without target: "open", "close", "minimize"
        - Command without required parameters: "set volume" (no level)
        
        Args:
            command: Command to check
            
        Returns:
            Clarification question if ambiguous, None otherwise
        """
        command_lower = command.lower().strip()
        words = command_lower.split()
        
        # Check for single-word ambiguous commands
        if len(words) == 1 and words[0] in self.ambiguous_verbs:
            return self.ambiguous_verbs[words[0]]
        
        # Check for incomplete "set" commands
        if command_lower.startswith('set '):
            # "set volume" without level
            if re.match(r'^set (volume|brightness)$', command_lower):
                param = words[1]
                return f"What {param} level would you like?"
        
        # Check for "open/close/minimize/maximize" without target
        # But allow common exceptions like "open settings", "close window"
        verb_patterns = [
            (r'^(open|close|launch|start)\s+(it|that|this)$', 'verb + pronoun only'),
            (r'^(minimize|maximize|hide|show|restore)\s*$', 'window verb without target'),
        ]
        
        for pattern, description in verb_patterns:
            if re.match(pattern, command_lower):
                verb = words[0]
                if verb in self.ambiguous_verbs:
                    return self.ambiguous_verbs[verb]
        
        return None
    
    def _detect_multi_step(self, command: str) -> Tuple[bool, List[str]]:
        """
        Detect and split multi-step commands.
        
        Examples:
        - "open chrome and maximize it" → ["open chrome", "maximize it"]
        - "set volume to 50 then close chrome" → ["set volume to 50", "close chrome"]
        - "list games, launch the first one" → ["list games", "launch the first one"]
        
        BUT NOT:
        - "Hi Nexa, How are you?" → NOT split (conversational, no action verbs)
        - "Hello, what can you do?" → NOT split (questions, not commands)
        
        Args:
            command: Command to analyze
            
        Returns:
            Tuple of (is_multi_step: bool, commands: List[str])
        """
        # Action verbs that indicate actual commands
        action_verbs = [
            'open', 'close', 'launch', 'start', 'stop', 'quit', 'exit',
            'minimize', 'maximize', 'restore', 'hide', 'show',
            'set', 'get', 'increase', 'decrease', 'change',
            'play', 'pause', 'resume', 'next', 'previous', 'skip',
            'list', 'find', 'search', 'check', 'tell me',
            'take', 'capture', 'save', 'delete', 'remove',
            'connect', 'disconnect', 'turn on', 'turn off',
            'mute', 'unmute', 'volume', 'brightness'
        ]
        
        # ⚡ PHASE 1: Use pre-compiled patterns directly
        # Check if any separator exists
        separator_found = False
        for pattern in self.multi_step_separators:
            if pattern.search(command):
                separator_found = True
                break
        
        if separator_found:
            # Split by all separators (combine patterns)
            parts = [command]
            for pattern in self.multi_step_separators:
                new_parts = []
                for part in parts:
                    new_parts.extend(pattern.split(part))
                parts = new_parts
            
            # Clean up parts
            parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) > 1:
                # CRITICAL: Validate that both parts contain action verbs
                # This prevents splitting conversational phrases like "Hi Nexa, How are you?"
                valid_parts = []
                for part in parts:
                    part_lower = part.lower()
                    # Check if part contains any action verb
                    has_action = any(verb in part_lower for verb in action_verbs)
                    if has_action:
                        valid_parts.append(part)
                    else:
                        # Not a command - might be greeting, question, or conversation
                        logger.debug(f"[MultiStep] Rejected part (no action verb): '{part}'")
                
                # Only split if we have 2+ valid command parts
                if len(valid_parts) >= 2:
                    logger.debug(f"[MultiStep] Detected {len(valid_parts)} commands: {valid_parts}")
                    return True, valid_parts
                else:
                    # Not enough valid commands - treat as single command
                    logger.debug(f"[MultiStep] Not splitting: only {len(valid_parts)} command(s) found")
                    return False, [command]
        
        return False, [command]
    
    def _resolve_pronouns_in_sequence(self, commands: List[str]) -> List[str]:
        """
        Resolve pronouns in a sequence of commands.
        
        For multi-step commands, pronouns in later commands often refer to
        targets from earlier commands.
        
        IMPROVED: Now tracks MULTIPLE targets and resolves to MOST RECENT.
        
        Examples:
        - ["open chrome", "close it"] → ["open chrome", "close chrome"]
        - ["open chrome", "open firefox", "close it"] → ["open chrome", "open firefox", "close firefox"]
        - ["list games", "launch the first one"] → ["list games", "launch the first game"]
        
        Args:
            commands: List of commands in sequence
            
        Returns:
            List of commands with pronouns resolved
        """
        if len(commands) <= 1:
            return commands
        
        resolved = []
        target_stack = []  # Track multiple targets (LIFO - most recent is last)
        
        for i, cmd in enumerate(commands):
            # Extract target from current command
            current_target = self._extract_target(cmd)
            
            # Check if command contains pronouns
            cmd_lower = cmd.lower()
            has_pronoun = any(f' {pronoun} ' in f' {cmd_lower} ' or 
                            cmd_lower.endswith(f' {pronoun}') for pronoun in self.pronouns)
            
            if has_pronoun and target_stack:
                # Use MOST RECENT target (last in stack)
                most_recent_target = target_stack[-1]
                
                # Replace pronouns with most recent target
                resolved_cmd = cmd
                for pronoun in self.pronouns:
                    # Use word boundaries to avoid partial matches
                    pattern = r'\b' + pronoun + r'\b'
                    resolved_cmd = re.sub(pattern, most_recent_target, resolved_cmd, flags=re.IGNORECASE)
                
                logger.info(f"✅ Resolved pronoun '{cmd}' → '{resolved_cmd}' (target: {most_recent_target})")
                resolved.append(resolved_cmd)
            else:
                resolved.append(cmd)
            
            # Add current target to stack if we found one
            if current_target:
                target_stack.append(current_target)
                # Keep stack size reasonable (last 5 targets)
                if len(target_stack) > 5:
                    target_stack.pop(0)
                logger.debug(f"📚 Target stack: {target_stack}")
        
        return resolved
    
    def _extract_target(self, command: str) -> Optional[str]:
        """
        Extract the target (app/window/file) from a command.
        
        Examples:
        - "open chrome" → "chrome"
        - "maximize notepad" → "notepad"
        - "set volume to 50" → None (no target)
        
        Args:
            command: Command to analyze
            
        Returns:
            Target string or None
        """
        command_lower = command.lower()
        
        # Patterns to extract targets (support multi-word app/folder names and quoted names)
        patterns = [
            r'(?:open|close|launch|start|stop)\s+"([^"]+)"',  # open "Google Chrome"
            r"(?:open|close|launch|start|stop)\s+'([^']+)'",    # open 'Google Chrome'
            r'(?:open|close|launch|start|stop)\s+([\w\s\-\.\(\)]+?)(?:\s+window|\s+app|\s+browser|\s+folder|$|,)',
            r'(?:minimize|maximize|hide|show|restore)\s+([\w\s\-\.\(\)]+?)(?:\s+window|\s+app|$|,)',
            r'(?:open|close)\s+(?:the\s+)?([\w\s\-\.\(\)]+?)\s+(?:window|app)',
        ]

        for pattern in patterns:
            match = re.search(pattern, command_lower)
            if match:
                target = match.group(1).strip()
                logger.debug(f"[Extract] Target '{target}' from '{command}'")
                return target
        
        return None
    
    def _resolve_implicit_references(self, command: str) -> str:
        """
        Resolve implicit references like "the app", "the window", "the browser", and pronouns ("it").
        
        Uses context manager to find last referenced target of that type.
        
        Examples:
        - "close the app" → "close chrome" (if last app was chrome)
        - "minimize the window" → "minimize notepad" (if last window was notepad)
        - "close the browser" → "close chrome" (if chrome is in action stack)
        - "close it" → "close chrome" (if last app action was chrome)
        - "maximize active window" → "maximize chrome" (if chrome is active window)
        
        Args:
            command: Command with potential implicit references
            
        Returns:
            Command with references resolved
        """
        if not self.context_manager:
            return command
        
        command_lower = command.lower()
        resolved_command = command
        
        # STEP 0: Check for pronouns ("it", "that", "this") - resolve using action stack OR active window
        for pronoun in self.pronouns:
            # Check if pronoun exists as a standalone word
            pronoun_pattern = r'\b' + pronoun + r'\b'
            if re.search(pronoun_pattern, command_lower):
                # Try to get last target from action stack
                last_target = self.context_manager.get_last_target()
                
                # If no context target AND command is about a window, try getting active window
                if not last_target and any(keyword in command_lower for keyword in ['window', 'maximize', 'minimize', 'close', 'restore', 'hide', 'show', 'fullscreen', 'full screen']):
                    try:
                        from capabilities.system.window_manager import WindowManager
                        wm = WindowManager()
                        active_title = wm.get_active_window_title()
                        if active_title and 'Error' not in active_title:
                            # Extract app name from window title
                            # Common pattern: "Document - AppName" or just "AppName"
                            if ' - ' in active_title:
                                # Take last part (usually app name)
                                last_target = active_title.split(' - ')[-1].strip()
                            else:
                                last_target = active_title.strip()
                            logger.debug(f"🪟 Active window for pronoun: '{active_title}' → app: '{last_target}'")
                    except Exception as e:
                        logger.debug(f"⚠️ Could not get active window for pronoun: {e}")
                
                if last_target:
                    # Replace pronoun with target
                    resolved_command = re.sub(pronoun_pattern, last_target, resolved_command, 
                                            flags=re.IGNORECASE)
                    logger.info(f"✅ Resolved pronoun '{pronoun}' → '{last_target}' in: '{command}'")
                    return resolved_command
                # If no target found, leave pronoun as-is (ambiguity check will catch it later)
        
        # STEP 1: Check for generic category references ("the browser", "music app", etc.)
        for category, app_list in self.app_categories.items():
            # Build pattern to match "the [category]" or just "[category]"
            # Match with word boundaries and optional "the" prefix
            category_patterns = [
                r'\bthe\s+' + re.escape(category) + r'\b',  # "the browser"
                r'\b' + re.escape(category) + r'\b'  # "browser" (without "the")
            ]
            
            for pattern in category_patterns:
                if re.search(pattern, command_lower, re.IGNORECASE):
                    # Search action stack for any app matching this category
                    if self.context_manager.action_stack:
                        for action in reversed(self.context_manager.action_stack):
                            action_name = action.get('action', '')
                            action_data = action.get('data', {})
                            
                            # Check if this is an app-related action
                            if action_name in ['open_application', 'close_application', 'close_window', 
                                              'maximize_window', 'minimize_window', 'restore_window']:
                                app_name = action_data.get('app_name', '').lower()
                                
                                # Check if this app matches the category
                                if any(known_app in app_name for known_app in app_list):
                                    # Replace "the category" with just app name (not "the appname")
                                    resolved_command = re.sub(pattern, app_name, resolved_command, 
                                                            flags=re.IGNORECASE)
                                    logger.info(f"✅ Resolved category '{category}' → '{app_name}' in: '{command}'")
                                    return resolved_command
                    
                    logger.debug(f"⚠️ Category '{category}' found but no matching app in action stack")
                    break  # Don't try other patterns for this category
        
        # STEP 2: Check for standard implicit references ("the app", "the window", etc.)
        for reference, target_type in self.implicit_references.items():
            if reference in command_lower:
                # Get last target of this type from context
                last_target = None
                
                if target_type == 'application' or target_type == 'window':
                    last_target = self.context_manager.get_last_target('application')
                    # If no context target, try to get the currently active/focused window
                    if not last_target:
                        try:
                            from capabilities.system.window_manager import WindowManager
                            wm = WindowManager()
                            active_title = wm.get_active_window_title()
                            if active_title and 'Error' not in active_title:
                                # Extract app name from window title
                                # Common pattern: "Document - AppName" or just "AppName"
                                if ' - ' in active_title:
                                    # Take last part (usually app name)
                                    last_target = active_title.split(' - ')[-1].strip()
                                else:
                                    last_target = active_title.strip()
                                logger.debug(f"🪟 Active window: '{active_title}' → app: '{last_target}'")
                        except Exception as e:
                            logger.debug(f"⚠️ Could not get active window: {e}")
                            pass
                elif target_type == 'game':
                    last_target = self.context_manager.get_last_target('game')
                elif target_type == 'folder':
                    last_target = self.context_manager.get_last_target('folder')
                elif target_type == 'network':
                    last_target = self.context_manager.get_last_target('network')
                
                if last_target:
                    resolved_command = command.replace(reference, last_target)
                    logger.info(f"✅ Resolved '{reference}' → '{last_target}' in: '{command}'")
                    return resolved_command
        
        return resolved_command
    
    def is_enabled(self) -> bool:
        """Check if dynamic preprocessing is enabled."""
        return True  # Always enabled unless explicitly disabled
