"""
LLM Manager - Single Model Architecture
Uses Llama 3.1 8B for BOTH online and offline modes.
Online/Offline distinction is ONLY for internet-dependent features.
"""

import logging
import socket
import requests
import hashlib
import time
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from collections import OrderedDict

# ⚡ PHASE 1: Import torch for GPU cache management
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.info("⚠️ PyTorch not available - GPU cache clearing disabled")

# Import error handling
try:
    from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity
    ERROR_HANDLING_AVAILABLE = True
except ImportError:
    ERROR_HANDLING_AVAILABLE = False
    logging.warning("Error handler not available in llm_manager")

logger = logging.getLogger(__name__)


class LLMMode(Enum):
    """Operating mode - determines feature availability, NOT model selection."""
    ONLINE = "online"   # Internet available - web-dependent features enabled
    OFFLINE = "offline"  # No internet - only local features available
    ERROR = "error"      # LLM unavailable


class LLMManager:
    """
    Single-Model AI Manager.
    Uses Llama 3.1 8B for ALL text processing (both online and offline).
    Online/offline mode only affects internet-dependent feature availability.
    """
    
    def __init__(self, config, executor=None):
        """
        Initialize LLM Manager with single-model architecture.
        
        Args:
            config: Configuration object with settings
            executor: CommandExecutor instance for dynamic function catalog (optional)
        """
        self.config = config
        self.executor = executor  # Store executor reference for dynamic function catalog
        self.current_mode = LLMMode.OFFLINE  # Start offline until internet verified
        self.ollama_url = "http://127.0.0.1:11434"
        self.llama_model = "llama3.1:8b-instruct-q4_K_M"  # Llama 3.1 8B - Superior reasoning, lower hallucination, better NLP
        self.ollama_available = False  # Track if Ollama has been verified
        self.ollama_prewarmed = False  # Track if model has been pre-warmed
        
        # Manual mode override (for UI toggle - internet access control)
        self.force_offline = False  # User can manually disable internet features
        
        # Connection status cache (avoid checking too frequently)
        self._last_connectivity_check = 0
        self._connectivity_cache = False
        self._cache_duration = 30  # seconds
        
        # Response caching for common queries
        self._response_cache = OrderedDict()  # LRU cache
        self._cache_max_size = 20  # Maximum 20 cached responses
        self._cache_ttl = 300  # 5 minutes TTL (300 seconds)
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Mode change callbacks for UI updates
        self.mode_callbacks = []
        
        # PHASE 24: Setup only Ollama (100% local, no Gemini)
        self._verify_ollama()  # CRITICAL - required for all text processing
        
        logger.info(f"🎯 LLM Manager initialized - Single Model Architecture")
        logger.info(f"📦 Text Model: {self.llama_model} (both online/offline)")
        logger.info(f"👁️ Vision: Disabled (Phase 23 will add PaddleOCR-VL for offline vision)")
        logger.info(f"🔧 Mode: {self.current_mode.value} (determines feature availability)")
        logger.info(f"💾 Response cache: max_size={self._cache_max_size}, ttl={self._cache_ttl}s")
    
    
    def _verify_ollama(self):
        """Verify Ollama is running and offline model is available. Pre-warm the model ONCE."""
        import time
        start_verify = time.time()
        
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                if any(self.llama_model in name for name in model_names):
                    time_verify = time.time() - start_verify
                    logger.info(f"✅ Ollama verified - {self.llama_model} available ({time_verify:.3f}s)")
                    self.ollama_available = True
                    
                    # Pre-warm model ONLY ONCE (avoid re-warming on every mode check)
                    if not self.ollama_prewarmed:
                        logger.info(f"🔥 Pre-warming {self.llama_model} model (loading into memory)...")
                        logger.info(f"   └─ This happens ONCE during startup - subsequent calls will be instant!")
                        start_prewarm = time.time()
                        try:
                            # Use keep_alive to prevent Ollama from unloading the model
                            # -1 = keep loaded forever, "30m" = 30 minutes, etc.
                            warmup = requests.post(
                                f"{self.ollama_url}/api/generate",
                                json={
                                    "model": self.llama_model,
                                    "prompt": "You are Nexa, an AI assistant. Say hello.",
                                    "stream": False,
                                    "keep_alive": "60m"  # Keep model loaded for 60 minutes
                                },
                                timeout=90  # First load can take 30-60 seconds on slow systems
                            )
                            time_prewarm = time.time() - start_prewarm
                            if warmup.status_code == 200:
                                logger.info(f"✅ {self.llama_model} model pre-warmed and ready ({time_prewarm:.3f}s)")
                                logger.info(f"   └─ Model will stay loaded for 60 minutes. First command = INSTANT! 🚀")
                                self.ollama_prewarmed = True
                            else:
                                logger.warning(f"⚠️ Pre-warming returned status {warmup.status_code} ({time_prewarm:.3f}s)")
                        except requests.exceptions.Timeout:
                            logger.warning("⚠️ Pre-warming timeout - model may take longer on first use")
                        except Exception as e:
                            logger.warning(f"⚠️ Pre-warming failed: {e}")
                    
                    return True
                else:
                    logger.warning(f"⚠️ {self.llama_model} not found in Ollama. Available: {model_names}")
                    logger.warning(f"   Run: ollama pull {self.llama_model}")
                    self.ollama_available = False
                    return False
        except Exception as e:
            logger.warning(f"⚠️ Ollama not accessible: {e}")
            self.ollama_available = False
            return False
    
    def full_warmup(self):
        """
        Perform a FULL warm-up with the actual system prompt and function catalog.
        This ensures the first real voice command is instant.
        
        Called AFTER brain is fully initialized (so function catalog is ready).
        """
        if not self.ollama_available or not self.executor:
            logger.warning("⚠️ Cannot perform full warmup - Ollama or executor not available")
            return
        
        import time
        logger.info("🔥 Performing FULL LLM warm-up with system prompt...")
        logger.info("   └─ This simulates a real command to pre-cache the prompt processing")
        
        start_warmup = time.time()
        
        try:
            # Build the REAL system prompt with function catalog (same as actual commands)
            warmup_prompt = f"""You are Nexa, a friendly and helpful AI assistant. You control a Windows computer.

RESPONSE FORMAT: Always respond in JSON format.
For commands: {{"function_call": {{"name": "function_name", "parameters": {{}}}}, "response": "Friendly message"}}
For conversation: {{"response": "Your friendly response"}}

AVAILABLE FUNCTIONS:
{self._get_dynamic_function_catalog()}

User: what time is it

JSON Response:"""
            
            payload = {
                "model": self.llama_model,
                "prompt": warmup_prompt,
                "stream": False,
                "keep_alive": "60m",  # Keep model loaded for 60 minutes
                "options": {
                    "temperature": 0.3,
                    "num_predict": 100,  # Short response for warmup
                    "num_ctx": 4096,  # Same context as real commands
                    "num_batch": 128,
                    "num_gpu": 99,
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=120  # Allow time for full prompt processing
            )
            
            time_warmup = time.time() - start_warmup
            
            if response.status_code == 200:
                logger.info(f"✅ FULL warm-up complete! ({time_warmup:.2f}s)")
                logger.info(f"   └─ First voice command will now be INSTANT! 🚀")
            else:
                logger.warning(f"⚠️ Full warm-up returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning("⚠️ Full warm-up timeout - first command may be slower")
        except Exception as e:
            logger.warning(f"⚠️ Full warm-up failed: {e}")
    
    def check_internet_connectivity(self) -> bool:
        """
        Check if internet is available.
        Uses caching to avoid frequent checks.
        
        Returns:
            True if internet is available
        """
        import time
        
        # Check cache first
        current_time = time.time()
        if current_time - self._last_connectivity_check < self._cache_duration:
            return self._connectivity_cache
        
        # Perform actual check
        try:
            # Try to reach Google DNS (fast and reliable)
            socket.create_connection(("8.8.8.8", 53), timeout=1)  # Faster timeout
            self._connectivity_cache = True
            logger.debug("✅ Internet connectivity: Online")
        except OSError:
            self._connectivity_cache = False
            logger.debug("❌ Internet connectivity: Offline")
        
        self._last_connectivity_check = current_time
        return self._connectivity_cache
    
    def get_current_mode(self) -> LLMMode:
        """
        Determine current mode based on internet connectivity (Phase 24).
        Mode affects ONLY feature availability, NOT model selection.
        Llama 3.1 8B is used for text in both modes.
        
        Returns:
            ONLINE - Internet available, web-dependent features enabled
            OFFLINE - No internet, only local features available
            ERROR - Ollama not available
        """
        # Check manual override first (UI toggle - disables internet features)
        if self.force_offline:
            logger.debug("🔒 Manual offline mode - internet features disabled by user")
            if self.ollama_available:
                return LLMMode.OFFLINE
            else:
                # Verify Ollama if not already available
                if self._verify_ollama():
                    return LLMMode.OFFLINE
                return LLMMode.ERROR
        
        # Check if Ollama is available (required for all text processing)
        if not self.ollama_available:
            if not self._verify_ollama():
                return LLMMode.ERROR
        
        # Check internet connectivity (for feature gating only)
        if self.check_internet_connectivity():
            return LLMMode.ONLINE  # Internet available - web features enabled
        else:
            return LLMMode.OFFLINE  # No internet - only local features
    
    def set_mode(self, mode: LLMMode, clear_cache: bool = True):
        """
        Manually set the operating mode (Phase 24).
        Controls internet feature availability, NOT model selection.
        
        Args:
            mode: Desired mode (ONLINE or OFFLINE)
            clear_cache: Whether to clear connectivity cache (default True)
        """
        old_mode = self.current_mode
        
        if mode == LLMMode.OFFLINE:
            self.force_offline = True
            logger.info("🔒 Switched to OFFLINE mode - internet features disabled")
        elif mode == LLMMode.ONLINE:
            self.force_offline = False
            logger.info("🌐 Switched to ONLINE mode - internet features enabled (if available)")
        
        # Clear connectivity cache to force fresh check
        if clear_cache:
            self._connectivity_cache = False  # Force re-check
            self._last_connectivity_check = 0
            logger.debug("♻️ Connectivity cache cleared")
        
        # Update current mode
        self.current_mode = mode
        
        # Emit mode change callback if mode actually changed
        if old_mode != mode:
            self._emit_mode_change(mode)
    
    def register_mode_callback(self, callback):
        """Register a callback for mode changes."""
        if callback not in self.mode_callbacks:
            self.mode_callbacks.append(callback)
            logger.debug(f"Mode callback registered: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
    
    def _emit_mode_change(self, new_mode: LLMMode):
        """Emit mode change to all registered callbacks."""
        logger.info(f"📢 Emitting mode change: {new_mode.value}")
        for callback in self.mode_callbacks:
            try:
                callback(new_mode)
            except Exception as e:
                logger.error(f"Error in mode callback: {e}")
    
    def _generate_cache_key(self, prompt: str, **kwargs) -> str:
        """
        Generate a unique cache key for a prompt.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters that affect the response
            
        Returns:
            MD5 hash of the prompt and parameters
        """
        # Include relevant parameters in cache key
        cache_data = {
            'prompt': prompt,
            'temperature': kwargs.get('temperature', 0.3),
            'max_tokens': kwargs.get('max_output_tokens', 800),  # FIX: Increased from 200 to 800
        }
        
        # Create deterministic string representation
        cache_string = str(sorted(cache_data.items()))
        
        # Generate MD5 hash (fast and sufficient for cache keys)
        cache_key = hashlib.md5(cache_string.encode('utf-8')).hexdigest()
        
        return cache_key
    
    def _get_from_cache(self, cache_key: str) -> Optional[Tuple[str, LLMMode]]:
        """
        Retrieve response from cache if valid.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached (response, mode) tuple or None if not found/expired
        """
        if cache_key not in self._response_cache:
            self._cache_misses += 1
            return None
        
        cached_data = self._response_cache[cache_key]
        cached_response = cached_data['response']
        cached_mode = cached_data['mode']
        cached_time = cached_data['timestamp']
        
        # Check if cache entry is still valid
        current_time = time.time()
        if current_time - cached_time > self._cache_ttl:
            # Expired - remove from cache
            logger.debug(f"Cache entry expired (age: {current_time - cached_time:.1f}s)")
            del self._response_cache[cache_key]
            self._cache_misses += 1
            return None
        
        # Move to end (LRU - most recently used)
        self._response_cache.move_to_end(cache_key)
        
        self._cache_hits += 1
        cache_age = current_time - cached_time
        logger.info(f"✅ Cache HIT (age: {cache_age:.1f}s, hits: {self._cache_hits}, misses: {self._cache_misses})")
        
        return (cached_response, cached_mode)
    
    def _add_to_cache(self, cache_key: str, response: str, mode: LLMMode):
        """
        Add response to cache with LRU eviction.
        
        Args:
            cache_key: Cache key
            response: Response text to cache
            mode: Mode used to generate response
        """
        # Check if cache is full
        if len(self._response_cache) >= self._cache_max_size:
            # Remove oldest entry (FIFO from OrderedDict)
            oldest_key = next(iter(self._response_cache))
            del self._response_cache[oldest_key]
            logger.debug(f"Cache full - evicted oldest entry")
        
        # Add new entry
        self._response_cache[cache_key] = {
            'response': response,
            'mode': mode,
            'timestamp': time.time()
        }
        
        logger.debug(f"Added to cache (size: {len(self._response_cache)}/{self._cache_max_size})")
    
    def _should_skip_cache(self, prompt: str) -> bool:
        """
        Determine if a prompt should skip caching.
        
        Args:
            prompt: The input prompt
            
        Returns:
            True if should skip cache
        """
        # Skip cache for prompts that likely contain user-specific or time-sensitive data
        skip_keywords = [
            'user', 'ali', 'my name', 'i am', "i'm",  # User-specific
            'current', 'now', 'today', 'time', 'date',  # Time-sensitive
            'screen', 'analyze', 'what do you see',  # Screen analysis
            'screenshot', 'image', 'picture',  # Vision queries
        ]
        
        prompt_lower = prompt.lower()
        
        for keyword in skip_keywords:
            if keyword in prompt_lower:
                logger.debug(f"Skipping cache - prompt contains '{keyword}'")
                return True
        
        return False
    
    def clear_cache(self):
        """Clear all cached responses."""
        cache_size = len(self._response_cache)
        self._response_cache.clear()
        logger.info(f"🗑️ Cache cleared ({cache_size} entries removed)")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self._response_cache),
            'max_size': self._cache_max_size,
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 1),
            'ttl_seconds': self._cache_ttl
        }
    
    def generate_response(self, prompt: str, **kwargs) -> Tuple[str, LLMMode]:
        """
        Generate AI response using Llama 3.1 8B (Phase 24: Single Model Architecture).
        Uses caching for common queries to improve speed.
        Mode (online/offline) only affects feature availability, NOT model selection.
        
        Args:
            prompt: User prompt/system prompt
            **kwargs: Additional generation parameters
                - skip_cache (bool): Force skip cache lookup
                - use_raw_prompt (bool): Use prompt as-is without system wrapper (for text refinement)
            
        Returns:
            Tuple of (response_text, mode_used)
        """
        # Check if cache should be skipped
        skip_cache = kwargs.pop('skip_cache', False)
        
        # Try to get from cache first (unless explicitly skipped)
        if not skip_cache and not self._should_skip_cache(prompt):
            cache_key = self._generate_cache_key(prompt, **kwargs)
            cached_result = self._get_from_cache(cache_key)
            
            if cached_result is not None:
                response_text, cached_mode = cached_result
                self.current_mode = cached_mode
                return response_text, cached_mode
        else:
            cache_key = None
            logger.debug("Cache skipped for this prompt")
        
        # Determine mode based on connectivity (for feature gating only)
        mode = self.get_current_mode()
        
        # PHASE 24: Always use Llama 3.1 8B for text processing
        # Mode only determines if internet-dependent features are available
        try:
            logger.debug(f"Using {self.llama_model} (mode: {mode.value})")
            response_text = self._generate_with_llama(prompt, **kwargs)
            self.current_mode = mode
            logger.info(f"✅ {self.llama_model} response successful ({mode.value} mode)")
            
            # Cache the response (if cache key exists)
            if cache_key:
                self._add_to_cache(cache_key, response_text, mode)
            
            return response_text, mode
        except Exception as e:
            logger.error(f"❌ {self.llama_model} failed: {e}")
            if ERROR_HANDLING_AVAILABLE:
                user_msg, recovered = handle_error(
                    error=e,
                    context="llm_manager.generate_response",
                    category=ErrorCategory.LLM,
                    severity=ErrorSeverity.CRITICAL,
                    user_message="I'm sorry, the AI model is unavailable. Please check if Ollama is running.",
                    recovery_suggestion="Ensure Ollama is running and the model is downloaded: ollama pull llama3.1:8b-instruct-q4_K_M"
                )
                self.current_mode = LLMMode.ERROR
                return user_msg, LLMMode.ERROR
            else:
                self.current_mode = LLMMode.ERROR
                return "I'm sorry, the AI model is unavailable. Please ensure Ollama is running.", LLMMode.ERROR
    
    def _validate_and_fix_json(self, response_text: str) -> str:
        """
        Validate and attempt to fix common JSON errors in Llama responses.
        
        Args:
            response_text: Raw response from Llama
            
        Returns:
            Fixed response text
        """
        import json
        import re
        
        # If it doesn't look like JSON, return as-is
        if not response_text.strip().startswith('{'):
            return response_text
        
        try:
            # Try parsing as-is first
            json.loads(response_text)
            return response_text  # Valid JSON, no changes needed
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Invalid JSON from Llama: {e}")
            logger.debug(f"   Raw response: {response_text[:200]}")
            
            # Common fix 1: Remove trailing commas
            fixed = re.sub(r',(\s*[}\]])', r'\1', response_text)
            
            # Common fix 2: Fix single quotes to double quotes (but not in strings)
            # This is tricky - skip for now to avoid breaking strings
            
            # Common fix 3: Add missing closing braces
            open_braces = response_text.count('{')
            close_braces = response_text.count('}')
            if open_braces > close_braces:
                fixed = fixed + ('}' * (open_braces - close_braces))
                logger.debug(f"   Added {open_braces - close_braces} closing braces")
            
            # Common fix 4: Remove text before/after JSON
            match = re.search(r'\{.*\}', fixed, re.DOTALL)
            if match:
                fixed = match.group(0)
            
            # Try parsing fixed version
            try:
                json.loads(fixed)
                logger.info("✅ JSON auto-fixed successfully")
                return fixed
            except json.JSONDecodeError:
                logger.error("❌ Could not fix JSON - returning original")
                return response_text
    
    def _get_dynamic_function_catalog(self) -> str:
        """
        Get dynamic function catalog from executor's function registry.
        Falls back to static message if executor not available (backward compatibility).
        
        Returns:
            Formatted string of all available functions with descriptions
        """
        if self.executor and hasattr(self.executor, 'function_registry'):
            try:
                # Get catalog from registry (detailed format with descriptions)
                catalog = self.executor.function_registry.get_catalog(format_type="detailed")
                function_count = len(self.executor.function_registry.list_functions())
                logger.debug(f"📚 Dynamic function catalog loaded: {function_count} functions")
                return catalog
            except Exception as e:
                logger.warning(f"⚠️ Failed to get dynamic catalog: {e}, using fallback")
        
        # Fallback: If executor not available, return basic message
        logger.warning("⚠️ Executor not available - using static fallback catalog")
        return """⚠️ Function catalog unavailable - using basic function set.
Contact system administrator if you see this message."""
    
    def _generate_with_llama(self, prompt: str, **kwargs) -> str:
        """
        Generate response using Llama 3.1 8B via Ollama.
        This is the PRIMARY model for ALL text processing (online and offline).
        
        Args:
            prompt: System prompt
            **kwargs: Generation config parameters
                - use_raw_prompt (bool): Use prompt as-is without wrapper (for text refinement)
            
        Returns:
            Response text
        """
        import time
        
        # ⏱️ TIMING: Start overall measurement
        start_total = time.time()
        
        # ⚡ GPU SAFETY: Clear cache and check memory before inference
        if TORCH_AVAILABLE and torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                
                # Check available VRAM
                free_memory = torch.cuda.mem_get_info()[0] / (1024**3)  # GB
                if free_memory < 0.5:  # Less than 500MB free
                    logger.warning(f"⚠️ Low GPU memory: {free_memory:.2f}GB free - reducing context")
                    # Will use conservative settings below
                
                logger.debug(f"🔥 GPU cache cleared ({free_memory:.2f}GB free)")
            except Exception as e:
                logger.warning(f"⚠️ GPU cache clearing failed: {e}")
        
        # Check if we should use raw prompt (for text refinement)
        use_raw_prompt = kwargs.pop('use_raw_prompt', False)
        
        if use_raw_prompt:
            # Use prompt exactly as provided (for text refinement)
            llama_prompt = prompt
            logger.debug("Using raw prompt for specialized task (text refinement)")
        else:
            # CRITICAL OPTIMIZATION: Extract only the user request from massive prompt
            # Brain sends 5000+ token prompts, but Llama 3.1 only needs the essentials
            # Llama 3.1 can understand context better with less prompt engineering
            user_request = ""
            if "User request:" in prompt:
                # Extract just the user's actual question (last line)
                user_request = prompt.split("User request:")[-1].strip()
            elif "User:" in prompt:
                user_request = prompt.split("User:")[-1].strip()
            else:
                # Fallback: use last 200 chars (likely the actual request)
                user_request = prompt[-200:].strip()
            
            # FIX #1: Extract conversation history for context awareness
            # Extract last 3 interactions (max ~150 tokens) for follow-up questions
            history_context = ""
            if "RECENT CONVERSATION HISTORY" in prompt:
                # Extract history section from brain prompt
                history_section = prompt.split("RECENT CONVERSATION HISTORY")[1]
                if "Use this context" in history_section:
                    history_section = history_section.split("Use this context")[0]
                
                # Parse and limit to last 3 interactions (not 5) to save tokens
                lines = history_section.strip().split('\n')
                interaction_count = 0
                history_lines = []
                
                for line in lines:
                    if line.startswith("User:") or line.startswith("Nexa:"):
                        if interaction_count < 6:  # 3 interactions = 6 lines (User + Nexa)
                            history_lines.append(line)
                            if line.startswith("Nexa:"):
                                interaction_count += 1
                
                if history_lines:
                    history_context = "\n\nRecent conversation:\n" + "\n".join(history_lines[-6:])
            
            # Llama 3.1 8B OPTIMIZED prompt - Superior reasoning, native function calling, excellent NLP
            # Llama 3.1 is specifically trained for tool use and instruction following
            llama_prompt = f"""You are Nexa, a friendly AI assistant. Respond in JSON format ONLY.

RESPONSE FORMAT (choose ONE):

1. Function Call (for actions/queries):
{{"function_call": {{"name": "function_name", "parameters": {{"key": "value"}}}}, "response": "Friendly message"}}

2. Chat Only (for conversation):
{{"response": "Your friendly response here"}}

🚫 CRITICAL ANTI-HALLUCINATION RULES:
1. ONLY use functions from AVAILABLE FUNCTIONS below - NEVER invent names
2. For info queries (time, battery, WiFi), MUST call function - NEVER guess data
3. NEVER make up time, date, battery level, system info - ALWAYS call function
4. ALWAYS respond with VALID JSON - no extra text
5. Use exact function names from list (case-sensitive)
6. NEVER use: browse_web, google_search - use search_web instead
7. If function needs parameters, MUST provide them - never empty
8. For chat, use {{"response": "message"}} format
9. Be warm and friendly in "response" field

✅ WEB SEARCH: Use search_web function to search the internet!

EXAMPLES:

User: "open file explorer"
{{"function_call": {{"name": "open_application", "parameters": {{"app_name": "explorer"}}}}, "response": "Opening File Explorer!"}}

User: "what time is it"
{{"function_call": {{"name": "get_current_time", "parameters": {{}}}}, "response": "Let me check!"}}

User: "what's my battery"
{{"function_call": {{"name": "get_battery_status", "parameters": {{}}}}, "response": "Checking battery!"}}

User: "set volume 50"
{{"function_call": {{"name": "set_volume", "parameters": {{"level": 50}}}}, "response": "Setting volume to 50%!"}}

User: "hello"
{{"response": "Hey there! What can I help you with?"}}

User: "search for cats"
{{"function_call": {{"name": "search_web", "parameters": {{"query": "cats"}}}}, "response": "Searching the web for cats!"}}

User: "search the web for best laptops 2025"
{{"function_call": {{"name": "search_web", "parameters": {{"query": "best laptops 2025"}}}}, "response": "Let me search that for you!"}}

AVAILABLE FUNCTIONS:
{self._get_dynamic_function_catalog()}

🚫 DO NOT USE: browse_web, google_search (use search_web instead){history_context}

User: {user_request}

JSON Response:"""
        
        # ⏱️ TIMING: Prompt preparation complete
        time_prompt_prep = time.time() - start_total
        logger.debug(f"⏱️ Prompt preparation: {time_prompt_prep:.3f}s")
        logger.debug(f"⏱️ Optimized prompt size: {len(llama_prompt)} chars (vs {len(prompt)} original)")
        
        # PHASE 3 OPTIMIZATION: Dynamic num_predict based on query complexity
        # Faster token generation for simple queries
        num_predict = self._calculate_optimal_tokens(prompt, llama_prompt)
        logger.debug(f"⏱️ Optimal token count: {num_predict} (dynamic sizing)")
        
        # Prepare request with optimized settings for Llama 3.1 8B (BALANCED MODE - Safe for 8GB VRAM)
        payload = {
            "model": self.llama_model,
            "prompt": llama_prompt,
            "stream": False,
            "keep_alive": "30m",  # ⚡ OPTIMIZED: Keep model loaded for 30 minutes (60% faster on follow-ups!)
            "options": {
                "temperature": 0.3,  # OPTIMIZED: Lower for more focused responses (was 0.4)
                "top_p": 0.9,  # Better response variety
                "top_k": 40,  # More token options for natural speech
                "num_predict": 256,  # ⚡ SAFE: Balanced response length (not 512 - causes VRAM spikes)
                "num_ctx": 4096,  # ⚡ SAFE: 4K context (8K causes crashes on 8GB GPU)
                "num_batch": 128,  # ⚡ SAFE: Conservative batch size (512 too large for 8GB)
                "repeat_penalty": 1.15,  # Stronger repetition prevention
                "num_thread": 8,  # Use 8 threads for parallel processing
                "num_gpu": 99,  # ⚡ OPTIMIZED: Force ALL layers on GPU
            }
        }
        
        # ⏱️ TIMING: Start API call
        start_api_call = time.time()
        logger.info(f"⏱️ Calling {self.llama_model} API (timeout: 120s)...")
        
        # Call Ollama API with longer timeout (120s) for complex prompts
        # First inference after startup can take 30-60s to load model into VRAM
        # Subsequent calls are much faster (2-4s for Llama 3.1)
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json=payload,
            timeout=120  # CRITICAL: Increased from 30s to 120s to prevent timeout errors
        )
        
        # ⏱️ TIMING: API call complete
        time_api_call = time.time() - start_api_call
        time_total = time.time() - start_total
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '').strip()
            
            # POST-PROCESSING: Validate and clean JSON responses
            response_text = self._validate_and_fix_json(response_text)
            
            # ⏱️ TIMING: Log performance metrics
            logger.info(f"⏱️ {self.llama_model} generation complete:")
            logger.info(f"   ├─ Prompt prep: {time_prompt_prep:.3f}s")
            logger.info(f"   ├─ API call: {time_api_call:.3f}s")
            logger.info(f"   ├─ Total: {time_total:.3f}s")
            logger.info(f"   ├─ Response length: {len(response_text)} chars")
            logger.info(f"   └─ Speed: {len(response_text)/time_api_call:.1f} chars/sec")
            
            # Check if model stats are available
            if 'total_duration' in result:
                total_ns = result.get('total_duration', 0)
                load_ns = result.get('load_duration', 0)
                eval_ns = result.get('eval_duration', 0)
                
                logger.info(f"⏱️ Ollama internal metrics:")
                logger.info(f"   ├─ Total duration: {total_ns/1e9:.3f}s")
                logger.info(f"   ├─ Load duration: {load_ns/1e9:.3f}s")
                logger.info(f"   └─ Eval duration: {eval_ns/1e9:.3f}s")
            
            return response_text
        else:
            raise Exception(f"Ollama API returned status {response.status_code}")
    
    def _calculate_optimal_tokens(self, original_prompt: str, optimized_prompt: str) -> int:
        """
        PHASE 3 OPTIMIZATION: Calculate optimal num_predict based on query complexity.
        Reduces token generation for simple queries to save 2-3s.
        
        Args:
            original_prompt: Original full prompt from brain
            optimized_prompt: Optimized prompt sent to LLM
            
        Returns:
            Optimal number of tokens to predict
        """
        # Extract user request for analysis
        user_request = ""
        if "User:" in optimized_prompt:
            user_request = optimized_prompt.split("User:")[-1].strip().lower()
        else:
            user_request = optimized_prompt[-200:].lower()
        
        # AGGRESSIVE OPTIMIZATION: Most commands need <150 tokens (just function call JSON)
        # JSON format: {"function_call": {"name": "...", "parameters": {...}}, "response": "..."}
        # Average size: 80-120 tokens
        
        # Simple action commands (just need function call JSON, ~80-100 tokens)
        simple_patterns = [
            'volume', 'brightness', 'mute', 'unmute', 
            'minimize', 'maximize', 'restore', 'close', 'open',
            'screenshot', 'copy', 'paste', 'select all',
            'window', 'folder', 'file', 'app', 'application',
            'launch', 'start', 'stop', 'quit', 'exit',
            'increase', 'decrease', 'set', 'change',
            'wifi', 'connect', 'disconnect', 'turn on', 'turn off'
        ]
        
        # Information queries (need function call + brief response, ~100-130 tokens)
        info_patterns = [
            'time', 'battery', 'status', 'level', 'current',
            'what is', 'what\'s', 'how much', 'how many',
            'running', 'active', 'list', 'show', 'get',
            'where', 'when', 'which', 'check'
        ]
        
        # Conversation patterns (need longer responses, ~150-250 tokens)
        chat_patterns = [
            'how are you', 'thank', 'hello', 'hi ', 'hey',
            'tell me about', 'explain', 'why', 'how do',
            'what can you', 'help me', 'i need'
        ]
        
        # Multi-step or complex patterns (need full capacity, ~200-500 tokens)
        complex_patterns = [
            ' and ', ' then ', ' after ', 'first', 'second',
            'compound', 'multiple', 'sequence'
        ]
        
        # Check patterns (order matters - most specific first)
        is_complex = any(pattern in user_request for pattern in complex_patterns)
        is_chat = any(pattern in user_request for pattern in chat_patterns)
        is_simple = any(pattern in user_request for pattern in simple_patterns)
        is_info = any(pattern in user_request for pattern in info_patterns)
        
        # Assign token counts based on complexity (AGGRESSIVE REDUCTION)
        if is_complex:
            return 250  # Multi-step tasks (was 800, now 250)
        elif is_chat:
            return 200  # Conversational response (was 300, now 200)
        elif is_simple:
            return 100  # Just function call JSON (was 100, kept same)
        elif is_info:
            return 120  # Function call + brief response (was 150, now 120)
        else:
            # Unknown patterns - assume simple command (CRITICAL CHANGE)
            # Most voice commands are actions, not conversations
            return 120  # Default to simple (was 800, now 120 - 85% reduction!)
    
    def _generate_with_vision(self, prompt: str, image_data: str, **kwargs) -> str:
        """
        Generate response using vision model (NOT IMPLEMENTED - Llama 3.1 8B has no vision).
        This method exists for compatibility but will fail.
        Vision features require Gemini (online mode).
        
        Args:
            prompt: Query about the image
            image_data: Base64 encoded image data
            **kwargs: Generation config parameters
            
        Returns:
            Response text (or error message)
        """
        # Prepare request with vision support
        payload = {
            "model": self.llama_model,
            "prompt": prompt,
            "images": [image_data],  # Base64 image
            "stream": False,
            "keep_alive": "10m",  # CRITICAL: Keep model in VRAM for 10 minutes (prevents reload!)
            "options": {
                "temperature": 0.1,  # Slightly higher for vision tasks
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 200,  # Allow more tokens for descriptions
                "num_ctx": 2048,  # Larger context for image understanding
                "num_thread": 8,
                "num_gpu": 1,
            },
            "keep_alive": "30m"  # Keep model loaded for 30 minutes
        }
        
        # Call Ollama API with longer timeout for vision
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json=payload,
            timeout=60  # Vision tasks take longer
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            raise Exception(f"Ollama API returned status {response.status_code}")
    
    def get_mode_description(self) -> str:
        """
        Get user-friendly description of current mode (Phase 24).
        
        Returns:
            Mode description
        """
        if self.current_mode == LLMMode.ONLINE:
            return "Online - Internet features enabled (weather, web search, email)"
        elif self.current_mode == LLMMode.OFFLINE:
            return "Offline - Core features available (no internet required)"
        else:
            return "Error - AI model unavailable (check Ollama)"
    
    def get_offline_limitations(self) -> str:
        """
        Get description of offline mode limitations (Phase 24).
        
        Returns:
            Limitations description
        """
        return f"""Offline mode - Llama 3.1 8B:
- ✅ ALL system commands (apps, volume, brightness, windows, etc.)
- ✅ Conversation and chat (same quality as online)
- ✅ All local features work perfectly
- ❌ No web search (requires internet)
- ❌ No weather data (requires API)
- ❌ No email checking (requires internet)
- ℹ️ Vision: Requires online mode (temporary - Phase 23 will add offline vision)"""
    
    # ============================================================================
    # NEW: Smart Follow-up Detection (AI-powered, not pattern-based)
    # ============================================================================
    
    def is_follow_up_question(self, user_text: str, last_action: str, last_result: str = "", 
                              available_functions: list = None) -> bool:
        """
        Dynamically determine if user's question is a follow-up using intelligent analysis.
        Uses minimal hardcoding - analyzes query structure and context instead.
        
        Args:
            user_text: Current user input
            last_action: Last function executed (e.g., 'list_games')
            last_result: Result from last action (optional, for context)
            available_functions: List of available function names (dynamic check)
            
        Returns:
            True if this is a follow-up question, False otherwise
        """
        if not last_action:
            return False
        
        user_lower = user_text.lower()
        words = user_text.split()
        word_count = len(words)
        
        # ============================================================================
        # DYNAMIC ANALYSIS - Minimal Hardcoding
        # ============================================================================
        
        # 1. DYNAMIC: Check if query mentions any known function from registry
        if available_functions:
            # Extract function base words (e.g., "open_application" → "open", "application")
            function_words = set()
            for func_name in available_functions:
                # Split by underscore and extract meaningful words
                parts = func_name.replace('_', ' ').split()
                function_words.update([p.lower() for p in parts if len(p) > 3])
            
            # If user mentions ANY function-related word, it's likely a new command
            query_words = set([w.lower() for w in words if len(w) > 3])
            if query_words & function_words:  # Set intersection
                logger.debug(f"🔍 Dynamic skip: Query mentions known function words {query_words & function_words}")
                return False
        
        # 2. STRUCTURAL ANALYSIS: Imperative vs. Interrogative
        # Imperative sentences (commands) start with verbs: "Open chrome", "Set volume"
        # Interrogative (questions) use question words or pronouns: "What were they?"
        
        first_word = words[0].lower() if words else ""
        
        # Check if first word is a verb (action) - indicates NEW command
        # We can check if it's in the infinitive form (base verb)
        common_verb_patterns = ['open', 'close', 'start', 'stop', 'get', 'set', 
                               'take', 'make', 'show', 'list', 'find', 'search',
                               'play', 'pause', 'increase', 'decrease', 'change',
                               'minimize', 'maximize', 'launch', 'check', 'connect']
        
        if first_word in common_verb_patterns:
            logger.debug(f"🔍 Structural skip: Starts with imperative verb '{first_word}' → NEW command")
            return False
        
        # 3. PRONOUN ANALYSIS: Follow-ups often use pronouns
        pronouns = ['it', 'them', 'they', 'those', 'that', 'these', 'this']
        has_pronoun = any(word in user_lower for word in pronouns)
        
        # Question words indicate interrogative follow-ups
        question_words = ['what', 'which', 'who', 'where', 'when', 'how', 'why']
        starts_with_question = first_word in question_words
        
        # If it's a question with a pronoun, likely a follow-up
        if starts_with_question and has_pronoun:
            logger.debug(f"🔍 Structural analysis: Question + pronoun → Likely follow-up")
            # Proceed to LLM check
        
        # 4. REFERENCE ANALYSIS: Does query reference previous result?
        # Follow-ups often ask about quantity or specifics
        reference_phrases = ['what are', 'what were', 'how many', 'which one', 
                            'tell me', 'show me', 'list them', 'name them']
        has_reference = any(phrase in user_lower for phrase in reference_phrases)
        
        if has_reference:
            logger.debug(f"🔍 Reference detected: Query asks about previous result → Likely follow-up")
            # Proceed to LLM check
        
        # 5. LENGTH ANALYSIS: Very short queries with pronouns are usually follow-ups
        # "Open chrome" (2 words) = command
        # "What are they?" (3 words) = follow-up
        if word_count <= 5 and has_pronoun:
            logger.debug(f"🔍 Short query ({word_count} words) + pronoun → Likely follow-up")
            # Proceed to LLM check
        
        # 6. SPECIFICITY CHECK: Specific targets (app names, numbers) = NEW command
        has_number = any(char.isdigit() for char in user_text)
        
        # Common app/target names (this is the ONLY hardcoded list, but it's for exclusion)
        common_targets = ['chrome', 'firefox', 'explorer', 'notepad', 'vscode', 
                         'volume', 'brightness', 'wifi', 'screenshot', 'battery']
        has_specific_target = any(target in user_lower for target in common_targets)
        
        if has_number or has_specific_target:
            logger.debug(f"🔍 Specific target/number detected → NEW command")
            return False
        
        # 7. LONG QUERIES: Detailed commands are rarely follow-ups
        if word_count > 12:
            logger.debug(f"🔍 Long query ({word_count} words) → Likely NEW request")
            return False
        
        # ============================================================================
        # INTELLIGENT DECISION: Use LLM only for ambiguous cases
        # ============================================================================
        
        # Only use LLM if:
        # - Query has pronouns/references AND
        # - No clear action verb AND
        # - No specific targets
        use_llm = (has_pronoun or has_reference) and not (first_word in common_verb_patterns)
        
        if not use_llm:
            logger.debug(f"🔍 Clear non-follow-up: No ambiguity detected")
            return False
        
        logger.info(f"🤖 Ambiguous query - using LLM for follow-up detection...")
        
        # Prepare quick follow-up detection prompt (minimal tokens, fast response)
        detection_prompt = f"""Last action: {last_action}
Current query: "{user_text}"

Is this asking for MORE details about the last action?
- Follow-up examples: "What are they?", "How many?", "Tell me more"
- New command examples: "Open chrome", "Set volume 50"

Answer: YES or NO

Answer:"""
        
        try:
            # Ultra-fast LLM call (50 tokens, <0.5s response)
            payload = {
                "model": self.llama_model,
                "prompt": detection_prompt,
                "stream": False,
                "keep_alive": "30m",  # Keep model loaded for 30 minutes
                "options": {
                    "temperature": 0.0,  # Deterministic
                    "num_predict": 5,  # Only need "YES" or "NO"
                    "num_ctx": 512,  # Minimal context
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=10  # INCREASED: Follow-up detection timeout (was 3s, now 10s)
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('response', '').strip().upper()
                
                is_follow_up = 'YES' in answer
                logger.info(f"🤖 AI Follow-up Detection: {'YES' if is_follow_up else 'NO'} (confidence: {answer})")
                return is_follow_up
            else:
                logger.warning(f"⚠️ Follow-up detection failed, falling back to pattern matching")
                return False
                
        except Exception as e:
            logger.error(f"❌ Smart follow-up detection error: {e}")
            # Fallback: return False (use pattern matching instead)
            return False

    def cleanup(self):
        """
        Unload Ollama model from GPU memory.
        Called during Nexa shutdown to free VRAM for other applications (games, etc.)
        """
        if not self.ollama_available:
            logger.debug("Ollama not available, skipping cleanup")
            return
        
        try:
            logger.info(f"🧹 Unloading {self.llama_model} from Ollama (freeing ~5-6GB VRAM)...")
            
            # Send request with keep_alive=0 to unload the model
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.llama_model,
                    "prompt": "",  # Empty prompt
                    "keep_alive": 0  # 0 = unload immediately
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('done_reason') == 'unload' or result.get('done'):
                    logger.info(f"✅ {self.llama_model} unloaded from Ollama - VRAM freed!")
                    self.ollama_prewarmed = False  # Mark as no longer pre-warmed
                else:
                    logger.info(f"✅ Unload request sent to Ollama")
            else:
                logger.warning(f"⚠️ Ollama unload returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning("⚠️ Ollama unload timeout - model may still be loaded")
        except requests.exceptions.ConnectionError:
            logger.debug("Ollama not running, nothing to unload")
        except Exception as e:
            logger.debug(f"Error unloading Ollama model: {e}")

