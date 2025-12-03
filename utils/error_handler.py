"""
Enhanced Error Handling and Logging System for Nexa
Provides structured error handling, recovery strategies, and user-friendly error messages.
"""

import logging
import traceback
from enum import Enum
from typing import Optional, Dict, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"  # Minor issues, can continue
    MEDIUM = "medium"  # Noticeable issues, degraded functionality
    HIGH = "high"  # Major issues, feature unavailable
    CRITICAL = "critical"  # System-breaking, cannot continue


class ErrorCategory(Enum):
    """Error categories for better classification."""
    NETWORK = "network"  # API, internet connection issues
    AUDIO = "audio"  # Microphone, speaker, TTS issues
    LLM = "llm"  # AI model, generation issues
    SYSTEM = "system"  # OS commands, permissions issues
    USER_INPUT = "user_input"  # Invalid user commands
    CONFIGURATION = "configuration"  # Config file, settings issues
    HARDWARE = "hardware"  # GPU, memory, device issues
    UNKNOWN = "unknown"  # Unclassified errors


class NexaError(Exception):
    """Base exception class for Nexa with enhanced error information."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        recovery_suggestion: Optional[str] = None,
        technical_details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Nexa error with rich context.
        
        Args:
            message: Technical error message (for logs)
            category: Error category
            severity: Error severity level
            user_message: User-friendly message (what user hears)
            recovery_suggestion: How to fix or recover
            technical_details: Additional context for debugging
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.user_message = user_message or self._generate_user_message()
        self.recovery_suggestion = recovery_suggestion
        self.technical_details = technical_details or {}
        self.timestamp = datetime.now()
    
    def _generate_user_message(self) -> str:
        """Generate user-friendly message based on category."""
        category_messages = {
            ErrorCategory.NETWORK: "I'm having trouble connecting to the internet",
            ErrorCategory.AUDIO: "I'm having trouble with audio",
            ErrorCategory.LLM: "I'm having trouble processing that request",
            ErrorCategory.SYSTEM: "I couldn't execute that system command",
            ErrorCategory.USER_INPUT: "I didn't understand that command",
            ErrorCategory.CONFIGURATION: "There's a configuration issue",
            ErrorCategory.HARDWARE: "There's a hardware issue",
            ErrorCategory.UNKNOWN: "Something went wrong"
        }
        return category_messages.get(self.category, "An error occurred")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "user_message": self.user_message,
            "recovery_suggestion": self.recovery_suggestion,
            "technical_details": self.technical_details
        }


class ErrorHandler:
    """
    Centralized error handling system with recovery strategies.
    """
    
    def __init__(self):
        """Initialize error handler."""
        self.error_counts: Dict[str, int] = {}  # Track error frequency
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {}
        self._setup_recovery_strategies()
    
    def _setup_recovery_strategies(self):
        """Setup automatic recovery strategies for common errors."""
        self.recovery_strategies = {
            ErrorCategory.NETWORK: self._recover_network_error,
            ErrorCategory.LLM: self._recover_llm_error,
            ErrorCategory.AUDIO: self._recover_audio_error,
        }
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[str] = None,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        recovery_suggestion: Optional[str] = None,
        auto_recover: bool = True
    ) -> tuple[str, bool]:
        """
        Handle an error with structured logging and recovery.
        
        Args:
            error: The exception that occurred
            context: Where the error occurred (function/component name)
            category: Error category
            severity: Error severity
            user_message: Custom user-friendly message
            recovery_suggestion: How to fix
            auto_recover: Attempt automatic recovery
            
        Returns:
            Tuple of (user_message, recovered_successfully)
        """
        # Convert to NexaError if needed
        if not isinstance(error, NexaError):
            nexa_error = NexaError(
                message=str(error),
                category=category,
                severity=severity,
                user_message=user_message,
                recovery_suggestion=recovery_suggestion,
                technical_details={
                    "original_exception": type(error).__name__,
                    "context": context,
                    "traceback": traceback.format_exc()
                }
            )
        else:
            nexa_error = error
        
        # Track error frequency
        error_key = f"{category.value}_{type(error).__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log error with structured format
        self._log_structured_error(nexa_error, context)
        
        # Attempt recovery if enabled
        recovered = False
        if auto_recover and category in self.recovery_strategies:
            try:
                recovered = self.recovery_strategies[category](nexa_error)
                if recovered:
                    logger.info(f"✅ Recovered from {category.value} error")
            except Exception as recovery_error:
                logger.error(f"❌ Recovery failed: {recovery_error}")
        
        return nexa_error.user_message, recovered
    
    def _log_structured_error(self, error: NexaError, context: Optional[str]):
        """Log error in structured, readable format."""
        severity_emoji = {
            ErrorSeverity.LOW: "ℹ️",
            ErrorSeverity.MEDIUM: "⚠️",
            ErrorSeverity.HIGH: "🔴",
            ErrorSeverity.CRITICAL: "💥"
        }
        
        emoji = severity_emoji.get(error.severity, "❌")
        
        # Main error log
        log_message = f"""
{'='*80}
{emoji} NEXA ERROR - {error.category.value.upper()} ({error.severity.value.upper()})
{'='*80}
📍 Timestamp: {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
🔧 Context: {error.technical_details.get('context', 'Unknown')}
💬 User Message: "{error.user_message}"
🐛 Technical: {error.message}
"""
        
        if error.recovery_suggestion:
            log_message += f"💡 Recovery: {error.recovery_suggestion}\n"
        
        if error.technical_details:
            log_message += "\n📊 Technical Details:\n"
            for key, value in error.technical_details.items():
                # Include traceback in main log for CRITICAL errors
                if key == "traceback" and error.severity != ErrorSeverity.CRITICAL:
                    continue
                log_message += f"   - {key}: {value}\n"
        
        log_message += "="*80
        
        # Log at appropriate level
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Log full traceback at debug level
        if "traceback" in error.technical_details:
            logger.debug(f"Full Traceback:\n{error.technical_details['traceback']}")
    
    def _recover_network_error(self, error: NexaError) -> bool:
        """Attempt to recover from network errors."""
        # Placeholder for network recovery (e.g., switch to offline mode)
        logger.info("🔄 Attempting network error recovery...")
        # Could implement: retry logic, switch to offline mode, etc.
        return False
    
    def _recover_llm_error(self, error: NexaError) -> bool:
        """Attempt to recover from LLM errors."""
        logger.info("🔄 Attempting LLM error recovery...")
        # Could implement: retry with different model, fallback to simpler prompt, etc.
        return False
    
    def _recover_audio_error(self, error: NexaError) -> bool:
        """Attempt to recover from audio errors."""
        logger.info("🔄 Attempting audio error recovery...")
        # Could implement: reinitialize audio devices, switch devices, etc.
        return False
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        # Separate errors by category and severity
        by_category = {}
        by_severity = {}
        
        for key, count in self.error_counts.items():
            # Parse key format: "CATEGORY:SEVERITY"
            if ':' in key:
                cat, sev = key.split(':', 1)
                by_category[cat] = by_category.get(cat, 0) + count
                by_severity[sev] = by_severity.get(sev, 0) + count
        
        # Find most common
        most_common_cat = max(by_category.items(), key=lambda x: x[1])[0] if by_category else "None"
        most_common_sev = max(by_severity.items(), key=lambda x: x[1])[0] if by_severity else "None"
        
        return {
            "total_errors": sum(self.error_counts.values()),
            "by_category": by_category,
            "by_severity": by_severity,
            "most_common_category": most_common_cat,
            "most_common_severity": most_common_sev,
            "raw_breakdown": dict(self.error_counts)
        }


# Global error handler instance
_error_handler = ErrorHandler()


def handle_error(
    error: Exception,
    context: str,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    user_message: Optional[str] = None,
    recovery_suggestion: Optional[str] = None
) -> tuple[str, bool]:
    """
    Convenience function for error handling.
    
    Args:
        error: The exception
        context: Where it occurred
        category: Error category
        severity: Error severity
        user_message: User-friendly message
        recovery_suggestion: How to fix
        
    Returns:
        Tuple of (user_message, recovered)
    """
    return _error_handler.handle_error(
        error=error,
        context=context,
        category=category,
        severity=severity,
        user_message=user_message,
        recovery_suggestion=recovery_suggestion
    )


def get_error_stats() -> Dict[str, Any]:
    """Get error statistics."""
    return _error_handler.get_error_stats()
