"""
Screen Reader - Vision Integration DISABLED (Phase 24: 100% API-Free)
Vision features disabled until Phase 23 (PaddleOCR-VL implementation).
This module is currently non-functional.
"""

import logging
from typing import Optional, Dict, Tuple
from PIL import ImageGrab, Image

logger = logging.getLogger(__name__)


class ScreenReader:
    """
    Vision features are DISABLED until Phase 23.
    Phase 23 will add PaddleOCR-VL for offline vision capabilities.
    """
    
    def __init__(self, config):
        """
        Initialize screen reader (DISABLED).
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.vision_model = None
        self.llm_manager = None
        logger.info("Screen Reader initialized (DISABLED - vision features unavailable until Phase 23)")
    
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Image.Image]:
        """
        Capture screenshot of screen or specific region.
        Basic screenshot still works - vision analysis disabled.
        
        Args:
            region: Optional (x, y, width, height) tuple for specific region
            
        Returns:
            PIL Image object or None if failed
        """
        try:
            if region:
                x, y, width, height = region
                screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            else:
                screenshot = ImageGrab.grab()
            
            logger.info(f"Screenshot captured: {screenshot.size}")
            return screenshot
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    def capture_active_window(self) -> Optional[Image.Image]:
        """
        Capture screenshot of active window only.
        
        Returns:
            PIL Image object or None if failed
        """
        try:
            import pygetwindow as gw
            active_window = gw.getActiveWindow()
            
            if active_window:
                x, y = active_window.left, active_window.top
                width, height = active_window.width, active_window.height
                screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
                logger.info(f"Active window captured: {screenshot.size}")
                return screenshot
            else:
                logger.warning("No active window found, capturing full screen")
                return self.capture_screen()
                
        except Exception as e:
            logger.error(f"Failed to capture active window: {e}")
            return self.capture_screen()
    
    def find_text_on_screen(self, query: str, active_window_only: bool = True) -> Optional[Dict]:
        """
        DISABLED - Vision features unavailable until Phase 23.
        
        Args:
            query: Natural language query
            active_window_only: If True, only scan active window
            
        Returns:
            None (vision disabled)
        """
        logger.warning("⚠️ Vision features disabled - Phase 23 will add PaddleOCR-VL")
        return None
    
    def read_screen_text(self, active_window_only: bool = True) -> Optional[str]:
        """
        DISABLED - Vision features unavailable until Phase 23.
        
        Args:
            active_window_only: If True, only scan active window
            
        Returns:
            None (vision disabled)
        """
        logger.warning("⚠️ Vision features disabled - Phase 23 will add PaddleOCR-VL")
        return None
    
    def describe_screen(self, active_window_only: bool = True) -> Optional[str]:
        """
        DISABLED - Vision features unavailable until Phase 23.
        
        Args:
            active_window_only: If True, only scan active window
            
        Returns:
            None (vision disabled)
        """
        logger.warning("⚠️ Vision features disabled - Phase 23 will add PaddleOCR-VL")
        return None
    
    def analyze_screen(self, query: str = "", active_window_only: bool = True) -> Optional[Dict]:
        """
        DISABLED - Vision features unavailable until Phase 23.
        
        Args:
            query: Optional specific question about screen
            active_window_only: If True, only scan active window
            
        Returns:
            None (vision disabled)
        """
        logger.warning("⚠️ Vision features disabled - Phase 23 will add PaddleOCR-VL")
        return None

    
    def capture_active_window(self) -> Optional[Image.Image]:
        """
        Capture screenshot of active window only.
        
        Returns:
            PIL Image object or None if failed
        """
        try:
            import pygetwindow as gw
            
            # Get active window
            active_window = gw.getActiveWindow()
            
            if active_window:
                # Get window position and size
                x, y = active_window.left, active_window.top
                width, height = active_window.width, active_window.height
                
                # Capture window region
                screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
                logger.info(f"Active window captured: {screenshot.size}")
                return screenshot
            else:
                logger.warning("No active window found, capturing full screen")
                return self.capture_screen()
                
        except Exception as e:
            logger.error(f"Failed to capture active window: {e}")
            # Fallback to full screen
            return self.capture_screen()
    
    def find_text_on_screen(self, query: str, active_window_only: bool = True) -> Optional[Dict]:
        """
        Find text on screen using Gemini Vision API.
        
        Args:
            query: Natural language query (e.g., "find the email address", "locate word hello")
            active_window_only: If True, only scan active window (faster)
            
        Returns:
            Dict with: {
                'text': str,           # The text found
                'x': int,              # X coordinate (center)
                'y': int,              # Y coordinate (center)
                'width': int,          # Text width
                'height': int,         # Text height
                'confidence': float    # 0.0 to 1.0
            } or None if not found
        """
        try:
            if not self.vision_model:
                logger.error("Gemini Vision not initialized")
                return None
            
            # Capture screenshot
            logger.info(f"🔍 Searching for: {query}")
            screenshot = self.capture_active_window() if active_window_only else self.capture_screen()
            
            if not screenshot:
                return None
            
            # Prepare prompt for Gemini Vision
            prompt = f"""You are analyzing a screenshot to find specific text.

USER QUERY: {query}

TASK: Find the text described in the query and return its location.

RULES:
1. If query says "find [word/phrase]", look for that exact text
2. If query says "find the email", look for email addresses (user@domain.com)
3. If query says "find the price", look for currency amounts ($XX.XX, €XX.XX)
4. If query says "find the time", look for time formats (3:00 PM, 15:00)
5. If query says "find the URL", look for web addresses (https://...)
6. Be smart about context - understand what user wants

RESPONSE FORMAT (JSON only, no explanation):
{{
    "found": true/false,
    "text": "the actual text found",
    "x": pixel_x_position_center,
    "y": pixel_y_position_center,
    "width": text_width_pixels,
    "height": text_height_pixels,
    "confidence": 0.0_to_1.0
}}

If text NOT found, return: {{"found": false, "reason": "explanation"}}

IMPORTANT: Return ONLY valid JSON, no markdown, no code blocks."""

            # Send to Gemini Vision
            response = self.vision_model.generate_content([prompt, screenshot])
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1])
            
            logger.info(f"🤖 Gemini Vision response: {response_text[:200]}")
            
            # Parse JSON response
            import json
            result = json.loads(response_text)
            
            if result.get('found'):
                logger.info(f"✅ Text found: '{result.get('text')}' at ({result.get('x')}, {result.get('y')})")
                return {
                    'text': result.get('text', ''),
                    'x': result.get('x', 0),
                    'y': result.get('y', 0),
                    'width': result.get('width', 50),
                    'height': result.get('height', 20),
                    'confidence': result.get('confidence', 0.5)
                }
            else:
                logger.warning(f"❌ Text not found: {result.get('reason', 'Unknown reason')}")
                return None
                
        except Exception as e:
            logger.error(f"Error finding text on screen: {e}", exc_info=True)
            return None
    
    def read_screen_content(self, active_window_only: bool = True) -> Optional[str]:
        """
        Read all text content visible on screen.
        Uses Gemini (online) or Gemma3 (offline).
        
        Args:
            active_window_only: If True, only read active window
            
        Returns:
            String of all visible text or None if failed
        """
        try:
            # Capture screenshot
            screenshot = self.capture_active_window() if active_window_only else self.capture_screen()
            
            if not screenshot:
                return None
            
            # Prepare prompt
            prompt = """Read and extract ALL text visible in this screenshot.

TASK: Return all text you see, organized naturally.

RULES:
1. Preserve formatting (headings, paragraphs, lists)
2. Include everything readable (buttons, labels, content)
3. Organize top-to-bottom, left-to-right
4. Separate sections with blank lines
5. Be comprehensive - don't summarize

Return ONLY the text, no explanations."""

            # Use offline or online vision
            if self._is_offline_mode():
                # Offline vision not available - Llama 3.1 has no vision
                logger.warning("📄 Offline vision not available - Llama 3.1 8B is text-only")
                return "Vision features require online mode (Gemini Vision API)"
            else:
                # Use Gemini Vision (online)
                if not self.vision_model:
                    logger.error("Gemini Vision not initialized")
                    return None
                logger.info("📄 Reading screen with Gemini (online)")
                response = self.vision_model.generate_content([prompt, screenshot])
                text_content = response.text.strip()
            
            logger.info(f"📄 Screen content read: {len(text_content)} characters")
            return text_content
            
        except Exception as e:
            logger.error(f"Error reading screen content: {e}", exc_info=True)
            return None
    
    def describe_screen(self, active_window_only: bool = True) -> Optional[str]:
        """
        Get AI description of what's on screen.
        Uses Gemini Vision (online only - no offline vision available).
        
        Args:
            active_window_only: If True, only describe active window
            
        Returns:
            Natural language description of screen content
        """
        try:
            # Capture screenshot
            screenshot = self.capture_active_window() if active_window_only else self.capture_screen()
            
            if not screenshot:
                return None
            
            # Prepare prompt
            prompt = """Describe what you see on this screen in natural language.

TASK: Provide a brief, useful description for a voice assistant user.

INCLUDE:
- What application or window is shown
- Main content or purpose
- Key elements (text, images, buttons)
- Any notable information

KEEP IT:
- Concise (2-3 sentences)
- Natural and conversational
- Helpful for understanding context"""

            # Use offline or online vision
            if self._is_offline_mode():
                # Offline vision not available - Llama 3.1 has no vision
                logger.warning("🖼️ Offline vision not available - Llama 3.1 8B is text-only")
                return "Vision features require online mode (Gemini Vision API)"
            else:
                # Use Gemini Vision (online)
                if not self.vision_model:
                    logger.error("Gemini Vision not initialized")
                    return None
                logger.info("🖼️ Describing screen with Gemini (online)")
                response = self.vision_model.generate_content([prompt, screenshot])
                description = response.text.strip()
            
            logger.info(f"🖼️ Screen description: {description[:100]}...")
            return description
            
        except Exception as e:
            logger.error(f"Error describing screen: {e}", exc_info=True)
            return None


# Convenience functions for quick access
def capture_screenshot(region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Image.Image]:
    """Quick screenshot capture."""
    return ImageGrab.grab(bbox=region) if region else ImageGrab.grab()


def save_screenshot(filepath: str, region: Optional[Tuple[int, int, int, int]] = None) -> bool:
    """Save screenshot to file."""
    try:
        screenshot = capture_screenshot(region)
        screenshot.save(filepath)
        logger.info(f"Screenshot saved: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to save screenshot: {e}")
        return False
