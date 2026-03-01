"""
Live2D Cubism Engine - Using live2d-py Library
Professional Live2D model rendering for Nexa's animated pet.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Global SDK path
_SDK_PATH: Optional[Path] = None
_INITIALIZED = False


class PetExpression(Enum):
    """Pet expressions mapped to Live2D parameters."""
    IDLE = "idle"
    HAPPY = "happy"
    THINKING = "thinking"
    LISTENING = "listening"
    SPEAKING = "speaking"
    SURPRISED = "surprised"
    SLEEPING = "sleeping"
    ERROR = "error"  # For error states / confusion


def set_sdk_path(path: str):
    """
    Set the Live2D SDK path.
    Note: With live2d-py, we mainly use this for finding models.
    """
    global _SDK_PATH
    _SDK_PATH = Path(path)
    logger.info(f"✅ Live2D SDK path set to: {_SDK_PATH}")


def get_sdk_path() -> Optional[Path]:
    """Get the current SDK path."""
    return _SDK_PATH


class Live2DModel:
    """
    Wrapper around live2d-py's LAppModel for easy control.
    Handles model loading, expressions, motions, and parameters.
    """
    
    def __init__(self, model_path: str):
        """
        Initialize Live2D model.
        
        Args:
            model_path: Path to .model3.json file
        """
        self.model_path = Path(model_path)
        self.model_dir = self.model_path.parent
        self.model = None
        self.is_loaded = False
        
        # Model info
        self.name = self.model_path.stem
        self.motion_groups: Dict[str, int] = {}
        self.expressions: List[str] = []
        self.parameters: Dict[str, Tuple[float, float, float]] = {}  # min, default, max
        
        # Current state
        self.current_expression = PetExpression.IDLE
        
        # Texture paths for reference
        self.textures: List[Path] = []
        
        # Import live2d here to ensure it's only loaded when needed
        try:
            import live2d.v3 as live2d
            self.live2d = live2d
            logger.info(f"✅ live2d-py loaded (version {live2d.LIVE2D_VERSION})")
        except ImportError as e:
            logger.error(f"❌ Failed to import live2d-py: {e}")
            raise
    
    def load(self) -> bool:
        """
        Load the Live2D model.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.model_path.exists():
                logger.error(f"❌ Model file not found: {self.model_path}")
                return False
            
            # Create the model instance
            self.model = self.live2d.LAppModel()
            
            # Load the model from the .model3.json path
            logger.info(f"📦 Loading model: {self.model_path}")
            self.model.LoadModelJson(str(self.model_path))
            
            # Get model information
            self._discover_motions()
            self._discover_expressions()
            self._discover_parameters()
            self._discover_textures()
            
            self.is_loaded = True
            logger.info(f"✅ Model '{self.name}' loaded successfully!")
            logger.info(f"   Motions: {sum(self.motion_groups.values())} in {len(self.motion_groups)} groups")
            logger.info(f"   Expressions: {len(self.expressions)}")
            logger.info(f"   Parameters: {len(self.parameters)}")
            logger.info(f"   Textures: {len(self.textures)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _discover_textures(self):
        """Discover texture files from model JSON."""
        import json
        try:
            with open(self.model_path, 'r', encoding='utf-8') as f:
                model_json = json.load(f)
            
            textures = model_json.get('FileReferences', {}).get('Textures', [])
            for tex in textures:
                tex_path = self.model_dir / tex
                if tex_path.exists():
                    self.textures.append(tex_path)
        except Exception:
            pass
    
    def _discover_motions(self):
        """Discover available motion groups."""
        try:
            # Use GetMotionGroups() which returns a dict directly
            self.motion_groups = self.model.GetMotionGroups()
            logger.info(f"   Found {len(self.motion_groups)} motion groups: {list(self.motion_groups.keys())}")
        except Exception as e:
            logger.warning(f"   Failed to discover motions with GetMotionGroups: {e}")
            # Fallback to standard groups
            standard_groups = ['Idle', 'TapBody', 'TapHead', 'Flick', 'FlickUp', 
                              'FlickDown', 'FlickLeft', 'FlickRight', 'Shake',
                              'Pinch', 'PinchIn', 'PinchOut']
            
            for group in standard_groups:
                try:
                    count = self.model.GetMotionCount(group)
                    if count > 0:
                        self.motion_groups[group] = count
                        logger.debug(f"   Motion group '{group}': {count} motions")
                except Exception:
                    pass
    
    def _discover_expressions(self):
        """Discover available expressions."""
        try:
            # Use GetExpressionIds() which returns the list directly
            self.expressions = self.model.GetExpressionIds()
            logger.info(f"   Found {len(self.expressions)} expressions: {self.expressions}")
        except Exception as e:
            logger.warning(f"   Failed to discover expressions: {e}")
            # Fallback: try the old method
            try:
                count = self.model.GetExpressionCount()
                for i in range(count):
                    try:
                        name = self.model.GetExpressionName(i)
                        self.expressions.append(name)
                    except Exception:
                        pass
                logger.info(f"   Found {len(self.expressions)} expressions (fallback)")
            except Exception:
                pass
    
    def _discover_parameters(self):
        """Discover model parameters."""
        try:
            # Use GetParamIds() which returns the list directly
            param_ids = self.model.GetParamIds()
            for i, param_id in enumerate(param_ids):
                try:
                    min_val = self.model.GetParameterMinimumValue(i)
                    max_val = self.model.GetParameterMaximumValue(i)
                    default_val = self.model.GetParameterDefaultValue(i)
                    self.parameters[param_id] = (min_val, default_val, max_val)
                except Exception:
                    pass
            logger.info(f"   Found {len(self.parameters)} parameters")
        except Exception as e:
            logger.warning(f"   Failed to discover parameters with GetParamIds: {e}")
            # Fallback to count-based method
            try:
                count = self.model.GetParameterCount()
                for i in range(count):
                    try:
                        param_id = self.model.GetParameterId(i)
                        min_val = self.model.GetParameterMinimumValue(i)
                        max_val = self.model.GetParameterMaximumValue(i)
                        default_val = self.model.GetParameterDefaultValue(i)
                        self.parameters[param_id] = (min_val, default_val, max_val)
                    except Exception:
                        pass
                logger.info(f"   Found {len(self.parameters)} parameters (fallback)")
            except Exception:
                pass
    
    def resize(self, width: int, height: int):
        """
        Resize the model's viewport.
        
        Args:
            width: New width in pixels
            height: New height in pixels
        """
        if self.model and self.is_loaded:
            try:
                self.model.Resize(width, height)
            except Exception as e:
                logger.warning(f"⚠️ Resize failed: {e}")
    
    def update(self):
        """
        Update the model (call every frame).
        Handles physics, motions, and expressions.
        """
        if self.model and self.is_loaded:
            try:
                self.model.Update()
            except Exception as e:
                logger.warning(f"⚠️ Update failed: {e}")
    
    def draw(self):
        """
        Draw the model (call after update).
        Renders the model to the current OpenGL context.
        """
        if self.model and self.is_loaded:
            try:
                self.model.Draw()
            except Exception as e:
                logger.warning(f"⚠️ Draw failed: {e}")
    
    def start_motion(self, group: str, index: int = 0, priority: int = 2):
        """
        Start a motion animation.
        
        Args:
            group: Motion group name (e.g., 'Idle', 'TapBody')
            index: Motion index within the group
            priority: Motion priority (1=Idle, 2=Normal, 3=Force)
        """
        if self.model and self.is_loaded:
            try:
                self.model.StartMotion(group, index, priority)
                logger.debug(f"🎬 Started motion: {group}[{index}]")
            except Exception as e:
                logger.warning(f"⚠️ Failed to start motion {group}[{index}]: {e}")
    
    def start_random_motion(self, group: str, priority: int = 2):
        """
        Start a random motion from a group.
        
        Args:
            group: Motion group name
            priority: Motion priority
        """
        if self.model and self.is_loaded:
            try:
                self.model.StartRandomMotion(group, priority)
                logger.debug(f"🎬 Started random motion from: {group}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to start random motion from {group}: {e}")
    
    def set_expression(self, expression_name: str):
        """
        Set a facial expression.
        
        Args:
            expression_name: Name of the expression
        """
        if self.model and self.is_loaded:
            try:
                # Check if expression exists
                if expression_name not in self.expressions:
                    logger.warning(f"⚠️ Expression '{expression_name}' not found! Available: {self.expressions}")
                    return
                
                self.model.SetExpression(expression_name)
                logger.info(f"😊 Set expression: {expression_name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to set expression {expression_name}: {e}")
    
    def set_random_expression(self):
        """Set a random expression."""
        if self.model and self.is_loaded:
            try:
                self.model.SetRandomExpression()
                logger.debug("😊 Set random expression")
            except Exception as e:
                logger.warning(f"⚠️ Failed to set random expression: {e}")
    
    def set_parameter(self, param_id: str, value: float):
        """
        Set a model parameter value.
        
        Args:
            param_id: Parameter ID (e.g., 'ParamAngleX', 'ParamEyeLOpen')
            value: Value to set
        """
        if self.model and self.is_loaded:
            try:
                self.model.SetParameterValue(param_id, value, 1.0)
            except Exception as e:
                logger.warning(f"⚠️ Failed to set parameter {param_id}: {e}")
    
    def set_look_at(self, x: float, y: float):
        """
        Make the model look at a position.
        
        Args:
            x: X position (-1 to 1, where 0 is center)
            y: Y position (-1 to 1, where 0 is center)
        """
        if self.model and self.is_loaded:
            try:
                # Use eye/face angle parameters for look-at
                self.set_parameter('ParamAngleX', x * 30)  # -30 to 30 degrees
                self.set_parameter('ParamAngleY', y * 30)
                self.set_parameter('ParamEyeBallX', x)
                self.set_parameter('ParamEyeBallY', y)
            except Exception:
                pass
    
    def touch(self, x: float, y: float):
        """
        Handle touch/click on the model.
        
        Args:
            x: X position in model space (-1 to 1)
            y: Y position in model space (-1 to 1)
        """
        if self.model and self.is_loaded:
            try:
                # Check hit areas and trigger appropriate motions
                hit_areas = ['Head', 'Body']
                for area in hit_areas:
                    if self.model.HitTest(area, x, y):
                        if area == 'Head':
                            self.start_random_motion('TapHead', 2)
                        elif area == 'Body':
                            self.start_random_motion('TapBody', 2)
                        logger.debug(f"👆 Touched: {area}")
                        return area
            except Exception:
                pass
        return None
    
    def set_pet_expression(self, expression: PetExpression):
        """
        Set the pet's expression using Nexa's expression system.
        Maps PetExpression enum to custom Nexa expressions.
        
        Custom Nexa expressions (for Hiyori model):
        - nexa_idle: Gentle smile, relaxed (default state)
        - nexa_listening: Alert, wide eyes, raised brows (listening to user)
        - nexa_thinking: Looking up/away (processing/thinking)
        - nexa_speaking: Animated, engaged (responding to user)
        - nexa_happy: Big smile, eyes closed (task completed/positive)
        - nexa_sleeping: Eyes closed, peaceful (standby/inactive)
        - nexa_error: Worried, confused (error state)
        
        Args:
            expression: PetExpression enum value
        """
        self.current_expression = expression
        
        if not self.model or not self.is_loaded:
            return
        
        try:
            logger.info(f"🎭 Setting pet expression: {expression.value}")
            
            if expression == PetExpression.IDLE:
                # Gentle smile, relaxed idle
                self.set_expression('nexa_idle')
                self.start_random_motion('Idle', 1)
                
            elif expression == PetExpression.HAPPY:
                # Big smile, eyes closed in joy
                self.set_expression('nexa_happy')
                self.start_random_motion('TapBody', 2)
                
            elif expression == PetExpression.THINKING:
                # Looking up/away while processing
                self.set_expression('nexa_thinking')
                self.start_motion('Idle', 1, 2)
                
            elif expression == PetExpression.LISTENING:
                # Alert, attentive, wide eyes
                self.set_expression('nexa_listening')
                
            elif expression == PetExpression.SPEAKING:
                # Animated, engaged while responding
                self.set_expression('nexa_speaking')
                self.start_random_motion('TapBody', 2)
                
            elif expression == PetExpression.SURPRISED:
                # Use listening expression for alert/surprised
                self.set_expression('nexa_listening')
                
            elif expression == PetExpression.SLEEPING:
                # Peaceful closed eyes
                self.set_expression('nexa_sleeping')
                
            elif expression == PetExpression.ERROR:
                # Worried/confused look for errors
                self.set_expression('nexa_error')
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to set pet expression {expression}: {e}")
    
    def set_error_expression(self):
        """
        Set error expression (worried/confused).
        Call this when Nexa encounters an error or can't understand.
        """
        if self.model and self.is_loaded:
            try:
                self.set_expression('nexa_error')
                logger.debug("😟 Set error expression")
            except Exception as e:
                logger.warning(f"⚠️ Failed to set error expression: {e}")


def init_live2d():
    """Initialize the Live2D system (call once at startup)."""
    global _INITIALIZED
    
    if _INITIALIZED:
        return True
    
    try:
        import live2d.v3 as live2d
        live2d.init()
        _INITIALIZED = True
        logger.info("✅ Live2D system initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Live2D: {e}")
        return False


def gl_init_live2d():
    """Initialize Live2D's OpenGL renderer (call from OpenGL context)."""
    try:
        import live2d.v3 as live2d
        live2d.glInit()
        logger.info("✅ Live2D OpenGL initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Live2D OpenGL: {e}")
        return False


def cleanup_live2d():
    """Clean up Live2D resources."""
    global _INITIALIZED
    
    try:
        import live2d.v3 as live2d
        live2d.glRelease()
        live2d.dispose()
        _INITIALIZED = False
        logger.info("✅ Live2D cleaned up")
    except Exception as e:
        logger.warning(f"⚠️ Live2D cleanup warning: {e}")


def clear_buffer():
    """Clear the Live2D render buffer."""
    try:
        import live2d.v3 as live2d
        live2d.clearBuffer()
    except Exception:
        pass


# For backward compatibility
Live2DCubismCore = None  # Not needed with live2d-py


def get_sample_model_path() -> Optional[Path]:
    """Get path to the default Nexa pet model (Hiyori with custom expressions)."""
    if not _SDK_PATH:
        return None
    
    # Prefer Hiyori model (customized with Nexa expressions)
    sample_paths = [
        _SDK_PATH / "Samples" / "Resources" / "Hiyori" / "Hiyori.model3.json",  # Primary - custom expressions
        _SDK_PATH / "Samples" / "Resources" / "Haru" / "Haru.model3.json",      # Fallback
        _SDK_PATH / "Samples" / "Resources" / "Mark" / "Mark.model3.json",      # Alternative
    ]
    
    for path in sample_paths:
        if path.exists():
            return path
    
    return None

