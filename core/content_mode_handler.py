"""
Content Mode Handler - Text Editing and PDF Generation
Handles Content Mode operations: enter/exit mode, refine text, create PDF.
Extracted from executor.py for better modularity.
"""

import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ContentModeHandler:
    """
    Manages Content Mode for text editing and PDF generation.
    Provides AI-powered text refinement and PDF export capabilities.
    """
    
    def __init__(self, config, executor_ref):
        """
        Initialize Content Mode handler.
        
        Args:
            config: Configuration object
            executor_ref: Reference to CommandExecutor for accessing shared resources
        """
        self.config = config
        self.executor = executor_ref
        
        # Content Mode tracking
        self._content_mode_exiting = False
        
        # Components initialized on demand
        self._text_refiner = None
        self._pdf_generator = None
        
        logger.debug("ContentModeHandler initialized")
    
    @property
    def text_refiner(self):
        """Lazy-load text refiner."""
        if self._text_refiner is None:
            from core.text_refiner import TextRefiner
            if hasattr(self.executor, 'brain') and self.executor.brain:
                self._text_refiner = TextRefiner(self.executor.brain.llm_manager)
        return self._text_refiner
    
    @property
    def pdf_generator(self):
        """Lazy-load PDF generator."""
        if self._pdf_generator is None:
            from core.pdf_generator import PDFGenerator
            self._pdf_generator = PDFGenerator()
        return self._pdf_generator
    
    @property
    def content_window(self):
        """Access content window from executor."""
        return getattr(self.executor, 'content_window', None)
    
    @content_window.setter
    def content_window(self, value):
        """Set content window on executor."""
        self.executor.content_window = value
    
    def is_exiting(self) -> bool:
        """Check if Content Mode is in the process of exiting."""
        return self._content_mode_exiting
    
    def enter_content_mode(self) -> str:
        """
        Enter Content Mode - Opens Content Box window for text editing and PDF generation.
        
        Returns:
            str: Status message
        """
        try:
            from core.brain import NexaState
            
            # Check if already in content mode
            if self.content_window is not None:
                if self.content_window.isVisible():
                    self.content_window.raise_()
                    self.content_window.activateWindow()
                    return "Content Mode is already active."
            
            # Verify LLM manager is available
            if not hasattr(self.executor, 'brain') or not self.executor.brain:
                return "Cannot enter Content Mode: LLM Manager not available"
            
            # Reset exit flag when entering Content Mode
            self._content_mode_exiting = False
            
            # Request window creation from main UI thread via signal
            window = getattr(self.executor, 'window', None)
            if window and hasattr(window, 'content_mode_requested'):
                # Emit signal to create window in main thread
                window.content_mode_requested.emit(self.executor)
                logger.info("📝 Content window creation requested via signal")
            else:
                logger.warning("⚠️ Cannot create content window: UI window not available or signal not connected")
                return "Cannot open Content Mode window: UI not properly initialized"
            
            # Update brain state if brain is available
            if hasattr(self.executor, 'brain') and self.executor.brain:
                self.executor.brain._change_state(NexaState.CONTENT_MODE)
            
            logger.info("📝 Entered Content Mode")
            return "Content Mode activated. You can now edit text, refine content, and create PDFs."
            
        except ImportError as e:
            error_msg = f"Content Mode components not available: {str(e)}"
            logger.error(error_msg)
            return f"Cannot enter Content Mode: Missing dependencies. {str(e)}"
        except Exception as e:
            error_msg = f"Error entering Content Mode: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def exit_content_mode(self) -> str:
        """
        Exit Content Mode - Closes Content Box window and returns to normal operation.
        Uses Signal/Slot mechanism for thread-safe GUI operations.
        
        Returns:
            str: Status message
        """
        try:
            from core.brain import NexaState
            
            # Set exit flag FIRST (so Content Mode check returns False immediately)
            self._content_mode_exiting = True
            
            # Update brain state back to IDLE
            if hasattr(self.executor, 'brain') and self.executor.brain:
                self.executor.brain._change_state(NexaState.IDLE)
            
            # Close content window if it exists
            if self.content_window is not None:
                logger.info(f"🚪 Emitting close_content_window_requested signal (window visible: {self.content_window.isVisible()})")
                
                # Emit signal - will be handled in main thread by connected slot
                self.executor.close_content_window_requested.emit()
                logger.info("✅ Signal emitted, window will close in main thread")
            else:
                self._content_mode_exiting = False
                logger.warning("⚠️ No content window to close")
            
            logger.info("🚪 Content Mode exit initiated")
            return "Content Mode closed. Returning to normal operation."
            
        except Exception as e:
            error_msg = f"Error exiting Content Mode: {str(e)}"
            logger.error(error_msg)
            self._content_mode_exiting = False
            return error_msg
    
    def refine_text(self, mode: str, text: Optional[str] = None) -> str:
        """
        Refine text content using AI.
        
        Args:
            mode: Refinement mode (formal, shorter, grammar_only, improve, summarize, casual)
            text: Optional text to refine (if None, uses content from Content Box window)
            
        Returns:
            str: Refined text or error message
        """
        try:
            # CRITICAL FIX: Get text from Content Box if not provided OR if empty string
            if not text or not text.strip():
                if self.content_window is not None:
                    # Check content status before processing
                    content_status = self.content_window.get_content_status()
                    word_count = self.content_window.get_word_count()
                    
                    if content_status == "empty":
                        return "The content editor is empty. Please paste or type your content first."
                    elif content_status == "not_ready":
                        min_words = self.content_window.MIN_WORDS
                        return f"Content is too short. Please add more text (minimum {min_words} words, you have {word_count})."
                    elif content_status == "exceeds_limit":
                        max_words = self.content_window.MAX_WORDS
                        return f"Content is too long ({word_count} words). Please shorten it to under {max_words} words before refining."
                    
                    text = self.content_window.get_text()
                else:
                    return "No text to refine. Please provide text or use Content Mode."
            
            # Final check after retrieval
            if not text or not text.strip():
                return "Cannot refine empty text."
            
            # Ensure text refiner is available
            if self.text_refiner is None:
                return "Text refiner not available"
            
            # Refine the text
            logger.info(f"✨ Refining text with mode: {mode}")
            refined_text, llm_mode = self.text_refiner.refine_text(text, mode)
            
            # Update Content Box window if it exists (skip validation for Nexa's output)
            if self.content_window is not None:
                self.content_window.set_text(refined_text, skip_validation=True)
                self.content_window.set_status(f"✓ Text refined using {llm_mode} model", 3000)
            
            logger.info(f"✅ Text refined successfully ({len(refined_text)} chars)")
            return refined_text
            
        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"⚠️ Invalid refinement request: {error_msg}")
            if self.content_window is not None:
                self.content_window.set_status(error_msg, 5000, error=True)
            return error_msg
        except Exception as e:
            error_msg = f"Error refining text: {str(e)}"
            logger.error(error_msg)
            if self.content_window is not None:
                self.content_window.set_status(error_msg, 5000, error=True)
            return error_msg
    
    def create_pdf(self, pdf_format: str = "simple_text", filename: Optional[str] = None, 
                   text: Optional[str] = None, title: Optional[str] = None) -> str:
        """
        Create a PDF document from text content.
        
        Args:
            pdf_format: PDF format (simple_text, with_bullets, formatted_paragraphs)
            filename: Optional filename (auto-generated if None)
            text: Optional text content (if None, uses content from Content Box window)
            title: Optional document title
            
        Returns:
            str: Success message with file path or error message
        """
        try:
            # CRITICAL FIX: Get text from Content Box if not provided OR if empty string
            if not text or not text.strip():
                if self.content_window is not None:
                    # Check content status before processing
                    content_status = self.content_window.get_content_status()
                    word_count = self.content_window.get_word_count()
                    
                    if content_status == "empty":
                        return "The content editor is empty. Please paste or type your content first."
                    elif content_status == "not_ready":
                        min_words = self.content_window.MIN_WORDS
                        return f"Content is too short to create a PDF. Please add more text (minimum {min_words} words, you have {word_count})."
                    elif content_status == "exceeds_limit":
                        max_words = self.content_window.MAX_WORDS
                        return f"Content is too long ({word_count} words). Please shorten it to under {max_words} words before creating PDF."
                    
                    # Get HTML content to preserve formatting
                    text = self.content_window.get_html()
                else:
                    return "No text to export. Please provide text or use Content Mode."
            
            # Final check after retrieval
            if not text or not text.strip():
                return "Cannot create PDF from empty text."
            
            # Prepare metadata for PDF header
            metadata = {
                'name': self.config.user_name if hasattr(self.config, 'user_name') else 'Student',
                'id': getattr(self.config, 'student_id', None),
                'course': getattr(self.config, 'course_name', None),
                'date': None  # Auto-generate current date
            }
            
            # CRITICAL FIX: Convert empty string filename to None
            if filename is not None and not filename.strip():
                filename = None
                logger.debug("📝 Empty filename provided, will auto-generate")
            
            # Create the PDF
            logger.info(f"📄 Creating PDF - Format: {pdf_format}, Filename: {filename or 'auto'}")
            pdf_path, success = self.pdf_generator.create_pdf(
                text=text,
                filename=filename,
                pdf_format=pdf_format,
                title=title,
                metadata=metadata
            )
            
            if success:
                # Track this PDF for smart sharing
                self.executor.last_created_pdf = pdf_path
                self.executor.last_used_file = pdf_path
                logger.debug(f"📌 Tracked last created PDF: {pdf_path.name}")
                
                # Update Content Box window status
                if self.content_window is not None:
                    self.content_window.set_status(f"✓ PDF created: {pdf_path.name}", 5000)
                
                # Open PDF folder
                import subprocess
                import platform
                if platform.system() == "Windows":
                    subprocess.Popen(f'explorer /select,"{pdf_path}"')
                
                logger.info(f"✅ PDF created successfully: {pdf_path}")
                return f"PDF created successfully: {pdf_path.name}. Saved in {pdf_path.parent}"
            else:
                return "PDF creation failed."
                
        except ImportError as e:
            error_msg = f"PDF generation not available: {str(e)}. Install with: pip install reportlab"
            logger.error(error_msg)
            if self.content_window is not None:
                self.content_window.set_status("ReportLab not installed", 5000, error=True)
            return error_msg
        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"⚠️ Invalid PDF request: {error_msg}")
            if self.content_window is not None:
                self.content_window.set_status(error_msg, 5000, error=True)
            return error_msg
        except Exception as e:
            error_msg = f"Error creating PDF: {str(e)}"
            logger.error(error_msg)
            if self.content_window is not None:
                self.content_window.set_status(error_msg, 5000, error=True)
            return error_msg
    
    def on_content_window_closed(self):
        """Handle Content Box window close event."""
        logger.info("🚪 Content Box window closed by user")
        self.exit_content_mode()
    
    def on_refine_requested(self, mode: str, text: str):
        """
        Handle refine request from Content Box window.
        
        Args:
            mode: Refinement mode
            text: Text to refine
        """
        try:
            self.refine_text(mode, text)
        except Exception as e:
            logger.error(f"Error handling refine request: {e}")
            if self.content_window is not None:
                self.content_window.set_status(f"Refinement failed: {str(e)}", 5000, error=True)
    
    def on_pdf_requested(self, pdf_format: str, filename: str, text: str):
        """
        Handle PDF creation request from Content Box window.
        
        Args:
            pdf_format: PDF format
            filename: Filename
            text: Text content
        """
        try:
            self.create_pdf(pdf_format, filename, text)
        except Exception as e:
            logger.error(f"Error handling PDF request: {e}")
            if self.content_window is not None:
                self.content_window.set_status(f"PDF creation failed: {str(e)}", 5000, error=True)
    
    def on_content_ready(self, text: str):
        """
        Handle content ready signal from Content Box window.
        User has clicked "Ready" button or said voice command.
        
        Args:
            text: The content that's ready for processing
        """
        logger.info(f"✓ Content marked as ready by user ({len(text)} chars)")
        
        # Store that content is ready for next voice command
        if self.content_window is not None:
            self.content_window.set_status("✓ Ready - Now you can say refinement commands", 3000)
        
        # Optionally: Speak confirmation (non-blocking to avoid freezing UI)
        if hasattr(self.executor, 'brain') and self.executor.brain:
            try:
                self.executor.brain.tts.speak(
                    "Content received. What would you like me to do with it?",
                    blocking=False, ducking=True
                )
            except Exception as e:
                logger.debug(f"Could not speak confirmation: {e}")
    
    def mark_content_ready(self) -> str:
        """
        Voice command handler: Mark content as ready for processing.
        User can say "I'm ready", "Done pasting", "Content ready", etc.
        
        Returns:
            str: Confirmation message
        """
        try:
            if self.content_window is not None:
                text = self.content_window.get_text()
                if text and text.strip():
                    self.on_content_ready(text)
                    return "Got it! Content is ready. You can now tell me what to do with it."
                else:
                    return "There's no content in the editor yet. Please paste or type your content first."
            else:
                return "Content Mode is not active. Please open Content Mode first."
        except Exception as e:
            error_msg = f"Error marking content ready: {str(e)}"
            logger.error(error_msg)
            return error_msg
