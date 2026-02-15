"""
Phrase Pools for Natural Variety
=================================

Contains varied phrase pools for all companion features.
Using pools ensures NEXA doesn't sound repetitive.

All phrases are designed to be:
- Brief (1-3 words for acknowledgments)
- Natural and conversational
- Personality-appropriate (professional but friendly)
"""

import random
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class PhraseCategory:
    """A category of phrases with weights for variety."""
    phrases: List[str]
    weights: Optional[List[float]] = None
    last_used: List[int] = field(default_factory=list)
    avoid_repeat_count: int = 3  # Don't repeat same phrase within N selections
    
    def get_random(self) -> str:
        """Get a random phrase, avoiding recent repeats."""
        available_indices = [
            i for i in range(len(self.phrases))
            if i not in self.last_used[-self.avoid_repeat_count:]
        ]
        
        if not available_indices:
            # All phrases recently used, reset
            available_indices = list(range(len(self.phrases)))
            self.last_used.clear()
        
        if self.weights:
            # Filter weights for available indices
            available_weights = [self.weights[i] for i in available_indices]
            total = sum(available_weights)
            normalized = [w / total for w in available_weights]
            idx = random.choices(available_indices, weights=normalized, k=1)[0]
        else:
            idx = random.choice(available_indices)
        
        self.last_used.append(idx)
        return self.phrases[idx]


class PhrasePools:
    """
    Central repository for all phrase pools used by companion features.
    
    Design Philosophy:
    - Short acknowledgments (under 1 second to speak)
    - Natural variety to avoid repetition
    - Context-appropriate phrases
    """
    
    def __init__(self):
        self._init_acknowledgment_pools()
        self._init_progress_pools()
        self._init_completion_pools()
        self._init_error_pools()
    
    def _init_acknowledgment_pools(self):
        """Quick acknowledgment phrases (spoken immediately)."""
        
        # General acknowledgments - more conversational
        self.ack_general = PhraseCategory(
            phrases=[
                "Let me take care of that for you!",
                "I'm on it, give me just a moment!",
                "Sure thing, I'll handle that right away!",
                "Absolutely, working on it now!",
                "I'll get that done for you, one moment!",
                "Of course! Let me work on that!",
                "Great, I'm processing your request now!",
                "I'm looking into that for you!",
                "Let me see what I can do here!",
                "Understood! I'm working on it now!",
                "I've got this, just a second!",
                "I'll take care of that right now!",
            ]
        )
        
        # For search/lookup tasks
        self.ack_search = PhraseCategory(
            phrases=[
                "Let me search for that information for you!",
                "I'm looking that up right now!",
                "Give me a moment to find what you need!",
                "Searching through my knowledge base now!",
                "Let me dig into that for you!",
                "I'm on the hunt for that information!",
                "Let me see what I can find about that!",
            ]
        )
        
        # For app/system operations
        self.ack_system = PhraseCategory(
            phrases=[
                "I'm opening that up for you now!",
                "Let me take care of that system task!",
                "Starting that up right away!",
                "I'll handle that operation for you!",
                "Give me just a moment to set that up!",
                "I'm making that happen right now!",
            ]
        )
        
        # For complex/long tasks
        self.ack_complex = PhraseCategory(
            phrases=[
                "This might take me a little bit, but I'm on it!",
                "Let me work through this step by step for you!",
                "I'm analyzing that request now, give me a moment!",
                "This one requires some thought, let me work on it!",
                "I need to think about this one, hang tight!",
                "Let me carefully work through this for you!",
                "I'm processing all the details now!",
            ]
        )
        
        # For creative tasks (writing, generating)
        self.ack_creative = PhraseCategory(
            phrases=[
                "Let me put some thought into crafting that for you!",
                "I'm working on creating something nice for you!",
                "Give me a moment to compose that thoughtfully!",
                "Let me put my creative hat on for this one!",
                "I'm thinking about the best way to approach this!",
                "Let me craft something special for you!",
                "I'm brainstorming the best response for you!",
            ]
        )
    
    def _init_progress_pools(self):
        """Progress update phrases (for long-running tasks)."""
        
        # General progress
        self.progress_general = PhraseCategory(
            phrases=[
                "I'm still working on that for you...",
                "Almost there, just finishing up...",
                "Making good progress on your request...",
                "Just a little bit more and I'll have it!",
                "I'm getting close now...",
                "Still processing, thanks for your patience!",
            ]
        )
        
        # For search tasks
        self.progress_search = PhraseCategory(
            phrases=[
                "Still searching through the information...",
                "I'm going through the results now...",
                "Found some relevant stuff, organizing it for you...",
                "Almost have what you're looking for...",
                "Digging deeper into the data...",
            ]
        )
        
        # For complex operations
        self.progress_complex = PhraseCategory(
            phrases=[
                "This is a bit more complex, still working on it...",
                "I'm making my way through this step by step...",
                "Getting closer to the solution...",
                "Processing...",
            ]
        )
    
    def _init_completion_pools(self):
        """Task completion phrases."""
        
        self.complete_success = PhraseCategory(
            phrases=[
                "Done!",
                "All set!",
                "There you go!",
                "Here you go!",
                "Got it!",
            ]
        )
        
        self.complete_with_result = PhraseCategory(
            phrases=[
                "Here's what I found!",
                "Here you go!",
                "I found it!",
                "Take a look!",
            ]
        )
    
    def _init_error_pools(self):
        """Error/failure phrases (empathetic)."""
        
        self.error_general = PhraseCategory(
            phrases=[
                "Hmm, that didn't work.",
                "Oops, something went wrong.",
                "I ran into a problem.",
                "That didn't go as planned.",
            ]
        )
        
        self.error_not_found = PhraseCategory(
            phrases=[
                "I couldn't find that.",
                "Hmm, no luck finding it.",
                "I looked but couldn't find it.",
            ]
        )
        
        self.error_cant_do = PhraseCategory(
            phrases=[
                "I can't do that right now.",
                "That's not something I can help with.",
                "I'm not able to do that.",
            ]
        )
    
    # === Public API ===
    
    def get_acknowledgment(self, task_type: str = "general") -> str:
        """
        Get an appropriate acknowledgment phrase.
        
        Args:
            task_type: One of "general", "search", "system", "complex", "creative"
        
        Returns:
            A brief acknowledgment phrase
        """
        pools = {
            "general": self.ack_general,
            "search": self.ack_search,
            "system": self.ack_system,
            "complex": self.ack_complex,
            "creative": self.ack_creative,
        }
        pool = pools.get(task_type, self.ack_general)
        return pool.get_random()
    
    def get_progress(self, task_type: str = "general") -> str:
        """
        Get a progress update phrase.
        
        Args:
            task_type: One of "general", "search", "complex"
        
        Returns:
            A progress phrase
        """
        pools = {
            "general": self.progress_general,
            "search": self.progress_search,
            "complex": self.progress_complex,
        }
        pool = pools.get(task_type, self.progress_general)
        return pool.get_random()
    
    def get_completion(self, has_result: bool = False) -> str:
        """
        Get a completion phrase.
        
        Args:
            has_result: Whether there's a specific result to show
        
        Returns:
            A completion phrase
        """
        if has_result:
            return self.complete_with_result.get_random()
        return self.complete_success.get_random()
    
    def get_error(self, error_type: str = "general") -> str:
        """
        Get an error phrase.
        
        Args:
            error_type: One of "general", "not_found", "cant_do"
        
        Returns:
            An empathetic error phrase
        """
        pools = {
            "general": self.error_general,
            "not_found": self.error_not_found,
            "cant_do": self.error_cant_do,
        }
        pool = pools.get(error_type, self.error_general)
        return pool.get_random()


# Singleton instance for easy access
_phrase_pools: Optional[PhrasePools] = None


def get_phrase_pools() -> PhrasePools:
    """Get the singleton PhrasePools instance."""
    global _phrase_pools
    if _phrase_pools is None:
        _phrase_pools = PhrasePools()
    return _phrase_pools
