"""
Text Processing Utilities for Nexa Brain
Extracted from brain.py for better modularity and maintainability.

Contains:
- Compound command detection
- Pronoun resolution helpers  
- Implicit reference detection
- Markdown cleaning
- Text normalization utilities
"""

import logging
import re
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class TextProcessor:
    """
    Text processing utilities for NexaBrain.
    Handles compound commands, pronoun resolution, and text normalization.
    """
    
    def __init__(self):
        """Initialize TextProcessor."""
        # Action indicators for compound command detection
        self.action_indicators = [
            'set ', 'open ', 'close ', 'list ', 'show ', 'take ',
            'increase ', 'decrease ', 'turn ', 'switch ', 'launch ',
            'connect ', 'disconnect ', 'find ', 'copy ', 'paste ',
            'minimize ', 'maximize ', 'volume ', 'brightness '
        ]
        
        # Conjunctions for splitting compound commands
        self.conjunctions = [
            ' and then ',
            ' then ',
            ' and also ',
            ' also ',
            ' and ',
            ', and ',
            '; '
        ]
        
        # Ordinal patterns
        self.ordinal_patterns = ['first', 'second', 'third', 'fourth', 'fifth', 'last', 'previous']
        
        # Pronouns to resolve
        self.pronouns = ['it', 'that', 'this', 'them', 'those']
    
    def detect_compound_commands(self, user_text: str) -> List[str]:
        """
        Detect if user input contains multiple commands to be executed sequentially.
        Handles 3+ command sequences and sequential information queries.
        
        Args:
            user_text: User's input
            
        Returns:
            List of individual commands (single item if not compound)
        """
        user_lower = user_text.lower()
        
        # ENHANCEMENT 1: Detect sequential information queries first
        info_query_patterns = [
            r'what(?:\'s| is) .+ and what(?:\'s| is) .+',
            r'tell me .+ and .+',
            r'show me .+ and .+',
            r'check .+ and .+',
            r'get .+ and .+'
        ]
        
        for pattern in info_query_patterns:
            if re.search(pattern, user_lower):
                info_parts = self._split_info_queries(user_text, user_lower)
                if len(info_parts) >= 2:
                    logger.info(f"🔍 Detected sequential information queries: {len(info_parts)} queries")
                    return info_parts
        
        # ENHANCEMENT 2: Better comma-separated list detection for 3+ commands
        comma_and_pattern = r'.+,.+(?:,|\s+and\s+).+'
        if re.search(comma_and_pattern, user_lower):
            comma_parts = self._split_comma_commands(user_text)
            if len(comma_parts) >= 2:
                logger.info(f"🔗 Detected comma-separated commands: {len(comma_parts)} commands")
                return comma_parts
        
        # Check if input contains action words
        has_action = any(indicator in user_lower for indicator in self.action_indicators)
        
        if not has_action:
            return [user_text]
        
        # Check for conjunctions
        found_conjunction = None
        for conj in self.conjunctions:
            if conj in user_lower:
                found_conjunction = conj
                break
        
        if not found_conjunction:
            return [user_text]
        
        # Split by conjunction
        parts = self._split_by_conjunctions(user_text, found_conjunction)
        
        # Filter out very short parts
        filtered_parts = [p for p in parts if len(p) > 3]
        
        if len(filtered_parts) > 1:
            logger.info(f"🔗 Compound commands detected: {filtered_parts}")
            return filtered_parts
        else:
            return [user_text]
    
    def _split_info_queries(self, user_text: str, user_lower: str) -> List[str]:
        """Split sequential information queries."""
        info_parts = []
        
        if ' and what' in user_lower:
            parts_raw = re.split(r'\s+and\s+what', user_text, flags=re.IGNORECASE)
            info_parts.append(parts_raw[0].strip())
            for i in range(1, len(parts_raw)):
                info_parts.append('what' + parts_raw[i].strip())
        elif ' and tell' in user_lower:
            parts_raw = re.split(r'\s+and\s+tell', user_text, flags=re.IGNORECASE)
            info_parts.append(parts_raw[0].strip())
            for i in range(1, len(parts_raw)):
                info_parts.append('tell' + parts_raw[i].strip())
        else:
            info_keywords = ['battery', 'time', 'wifi', 'volume', 'brightness', 'status']
            if any(kw in user_lower for kw in info_keywords):
                parts_raw = re.split(r'\s+and\s+', user_text, maxsplit=1, flags=re.IGNORECASE)
                if len(parts_raw) == 2:
                    info_parts = [p.strip() for p in parts_raw]
        
        return info_parts
    
    def _split_comma_commands(self, user_text: str) -> List[str]:
        """Split comma-separated commands."""
        comma_parts = [p.strip() for p in user_text.split(',')]
        
        # Handle the last part which might have "and"
        if len(comma_parts) > 0:
            last_part = comma_parts[-1]
            if ' and ' in last_part.lower():
                and_parts = re.split(r'\s+and\s+', last_part, flags=re.IGNORECASE)
                comma_parts = comma_parts[:-1] + [p.strip() for p in and_parts]
        
        # Filter out empty parts
        return [p for p in comma_parts if len(p) > 3]
    
    def _split_by_conjunctions(self, user_text: str, found_conjunction: str) -> List[str]:
        """Split text by conjunctions."""
        parts = []
        remaining = user_text
        
        while found_conjunction:
            lower_remaining = remaining.lower()
            pos = lower_remaining.find(found_conjunction)
            
            if pos == -1:
                break
            
            part = remaining[:pos].strip()
            if part:
                parts.append(part)
            
            remaining = remaining[pos + len(found_conjunction):].strip()
            
            # Check for more conjunctions
            found_conjunction = None
            for conj in self.conjunctions:
                if conj in remaining.lower():
                    found_conjunction = conj
                    break
        
        if remaining.strip():
            parts.append(remaining.strip())
        
        return parts
    
    def detect_implicit_references(self, user_text: str) -> Dict[str, str]:
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
    
    def has_ordinal_reference(self, user_text: str) -> bool:
        """Check if text contains ordinal references."""
        text_lower = user_text.lower()
        return any(ordinal in text_lower for ordinal in self.ordinal_patterns)
    
    def has_pronoun(self, user_text: str) -> bool:
        """Check if text contains pronouns that need resolution."""
        text_lower = user_text.lower()
        return any(
            f' {pronoun} ' in f' {text_lower} ' or 
            f' {pronoun},' in f' {text_lower},' or
            text_lower.endswith(f' {pronoun}') 
            for pronoun in self.pronouns
        )
    
    def replace_ordinal(self, user_text: str, resolved_item: str) -> str:
        """Replace ordinal reference with resolved item."""
        pattern = r'\b(the\s+)?(first|second|third|fourth|fifth|last|previous)(\s+one)?\b'
        return re.sub(pattern, resolved_item, user_text, flags=re.IGNORECASE)
    
    def replace_pronouns(self, user_text: str, target: str) -> str:
        """Replace pronouns with target."""
        resolved_text = user_text
        
        for pronoun in self.pronouns:
            pattern = r'\b' + pronoun + r'\b'
            if re.search(pattern, user_text.lower()):
                resolved_text = re.sub(pattern, target, resolved_text, flags=re.IGNORECASE)
                logger.info(f"✅ Resolved pronoun '{pronoun}' → '{target}'")
                return resolved_text
        
        return resolved_text
    
    def clean_markdown(self, text: str) -> str:
        """
        Remove Markdown formatting from text for cleaner TTS.
        
        Args:
            text: Text potentially containing markdown
            
        Returns:
            Clean text without markdown formatting
        """
        if not text:
            return text
        
        # Remove bold markers (**text** or __text__)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        
        # Remove italic markers (*text* or _text_)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        
        # Remove inline code markers (`text`)
        text = re.sub(r'`(.+?)`', r'\1', text)
        
        # Remove headers (# Header)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Remove list markers (- item or * item)
        text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
        
        # Remove numbered list markers (1. item)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Remove links but keep text [text](url) → text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove blockquotes (> text)
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        
        return text
    
    def normalize_window_variations(self, user_text: str) -> str:
        """
        Normalize common variations of window-related commands.
        
        Args:
            user_text: User input text
            
        Returns:
            Normalized text
        """
        text_lower = user_text.lower()
        
        # "Close this" / "Close that" when referring to active window
        if re.search(r'\b(close|minimize|maximize)\s+(this|that)\b', text_lower):
            # If no specific target, assume active window
            if not any(app in text_lower for app in ['window', 'app', 'application']):
                return re.sub(
                    r'\b(close|minimize|maximize)\s+(this|that)\b',
                    r'\1 active window',
                    user_text,
                    flags=re.IGNORECASE
                )
        
        # "This window" → "active window"
        user_text = re.sub(r'\bthis window\b', 'active window', user_text, flags=re.IGNORECASE)
        
        # "Current window" → "active window"
        user_text = re.sub(r'\bcurrent window\b', 'active window', user_text, flags=re.IGNORECASE)
        
        return user_text
    
    def extract_action_verb(self, user_text: str) -> str:
        """
        Extract the primary action verb from user text.
        
        Args:
            user_text: User input
            
        Returns:
            Action verb or empty string
        """
        text_lower = user_text.lower().strip()
        
        # Common action verbs in order of specificity
        action_verbs = [
            'launch', 'open', 'close', 'exit', 'quit', 'terminate',
            'start', 'stop', 'pause', 'resume', 'play', 'skip',
            'increase', 'decrease', 'raise', 'lower', 'turn up', 'turn down',
            'set', 'change', 'switch', 'toggle',
            'minimize', 'maximize', 'restore', 'resize',
            'connect', 'disconnect', 'pair', 'unpair',
            'take', 'capture', 'save', 'copy', 'paste', 'cut', 'delete',
            'search', 'find', 'look up', 'google',
            'list', 'show', 'display', 'tell', 'what', 'check', 'get'
        ]
        
        for verb in action_verbs:
            if text_lower.startswith(verb) or f' {verb} ' in f' {text_lower} ':
                return verb
        
        return ''
    
    def is_counting_question(self, user_text: str) -> bool:
        """Check if user is asking a counting question."""
        text_lower = user_text.lower()
        
        counting_patterns = [
            r'\bhow many\b',
            r'\bhow much\b',
            r'\bcount\b',
            r'\bnumber of\b',
            r'\btotal\b',
            r'\bhow long\b'
        ]
        
        return any(re.search(pattern, text_lower) for pattern in counting_patterns)
    
    def is_listing_question(self, user_text: str) -> bool:
        """Check if user is asking for a list."""
        text_lower = user_text.lower()
        
        listing_patterns = [
            r'\blist\b',
            r'\bshow me\b',
            r'\bwhat are\b',
            r'\bwhich\b',
            r'\ball (my|the)\b',
            r'\bdisplay\b'
        ]
        
        return any(re.search(pattern, text_lower) for pattern in listing_patterns)


# Singleton instance for convenience
_text_processor = None

def get_text_processor() -> TextProcessor:
    """Get or create singleton TextProcessor instance."""
    global _text_processor
    if _text_processor is None:
        _text_processor = TextProcessor()
    return _text_processor
