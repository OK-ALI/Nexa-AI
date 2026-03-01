"""
Web Neural Brain Widget — HTML5 Canvas Memory Visualization

QWebEngineView-based neural graph with a particle-driven visualization.

Public API:
    - set_memories(memories)
    - clear_selection()
    - get_selected_memory()
    Signals: node_selected(str), node_hovered(str)

Communication uses the NEXA console.log bridge:
    JS → Python:  console.log('NEXA:' + JSON.stringify({event, ...}))
    Python → JS:  page.runJavaScript(script)
"""

import json
import logging
import os
import sys
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QUrl, QTimer, Slot, Signal, QPoint

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False

from PySide6.QtGui import QColor

logger = logging.getLogger(__name__)


def _get_neural_html_path() -> str:
    """Get the path to the neural memory HTML asset (handles frozen/dev)."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", "neural_memory", "index.html")


class _NeuralPage(QWebEnginePage):
    """
    Custom page that intercepts console.log messages
    starting with 'NEXA:' and forwards them to Python.
    """

    def __init__(self, callback, parent=None):
        super().__init__(parent)
        self._callback = callback

    def javaScriptConsoleMessage(self, level, message, line, source):
        if message.startswith('NEXA:'):
            try:
                payload = json.loads(message[5:])
                self._callback(payload)
            except json.JSONDecodeError:
                pass
        else:
            # Forward non-NEXA messages to normal logging
            if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
                logger.error(f"JS: {message}")


class WebNeuralBrainWidget(QWidget):
    """
    HTML5 Canvas neural brain visualization.

    Uses QWebEngineView with assets/neural_memory/index.html for
    a particle-based, force-directed memory node graph.
    """

    # Signals
    node_selected = Signal(str)   # memory_id
    node_hovered = Signal(str)    # memory_id

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(400, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Internal state
        self._page_ready = False
        self._pending_memories: Optional[str] = None
        self._selected_id: Optional[str] = None
        self._memories_lookup: Dict[str, Dict[str, Any]] = {}

        # Node lookup for panel integration
        self.nodes: Dict[str, Any] = {}
        self.center_offset = QPoint(0, 0)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if not WEBENGINE_AVAILABLE:
            logger.error("❌ QWebEngineView not available — WebNeuralBrainWidget disabled")
            return

        # Web view
        self._web_view = QWebEngineView(self)
        self._web_view.setStyleSheet("background: transparent;")

        # Custom page with NEXA bridge
        self._page = _NeuralPage(self._on_js_message, self._web_view)
        self._web_view.setPage(self._page)

        # Settings
        settings = self._page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)

        # Transparent background
        self._page.setBackgroundColor(QColor(0, 0, 0, 0))

        layout.addWidget(self._web_view)

        # Load HTML
        html_path = _get_neural_html_path()
        if os.path.exists(html_path):
            self._web_view.setUrl(QUrl.fromLocalFile(html_path))
            logger.info(f"✅ WebNeuralBrainWidget loading: {html_path}")
        else:
            logger.error(f"❌ Neural memory assets not found: {html_path}")
            return

        self._web_view.loadFinished.connect(self._on_page_loaded)

        logger.info("🧠 WebNeuralBrainWidget initialized")

    # ====================================================================
    # Page lifecycle
    # ====================================================================

    @Slot(bool)
    def _on_page_loaded(self, ok: bool):
        if not ok:
            logger.error("❌ Neural memory page failed to load")
            return
        QTimer.singleShot(200, self._apply_initial_state)

    def _apply_initial_state(self):
        self._page_ready = True
        logger.info("✅ Neural memory page ready")

        # Flush any pending data
        if self._pending_memories is not None:
            self._run_js(f"setMemories('{self._escape(self._pending_memories)}')")
            self._pending_memories = None

    # ====================================================================
    # JS bridge
    # ====================================================================

    def _run_js(self, script: str):
        try:
            self._page.runJavaScript(script)
        except Exception as e:
            logger.debug(f"JS exec error: {e}")

    @staticmethod
    def _escape(s: str) -> str:
        """Escape a JSON string for embedding in a JS single-quoted string literal."""
        return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")

    def _on_js_message(self, payload: dict):
        """Handle messages from JS."""
        event = payload.get('event')

        if event == 'nodeSelected':
            mid = payload.get('id', '')
            self._selected_id = mid
            self.node_selected.emit(mid)

        elif event == 'nodeHovered':
            mid = payload.get('id', '')
            self.node_hovered.emit(mid)

        elif event == 'nodeDeselected':
            self._selected_id = None

        elif event == 'statsUpdate':
            logger.debug(f"Neural stats: {payload.get('total')} total, {payload.get('visible')} visible")

    # ====================================================================
    # Public API
    # ====================================================================

    def set_memories(self, memories: List[Dict[str, Any]]):
        """
        Load memories as neural nodes.

        Args:
            memories: list of dicts with 'id', 'memory_type', 'content', 'importance', etc.
        """
        # Build lookup for detail card
        self._memories_lookup.clear()
        self.nodes.clear()
        for mem in memories:
            mid = mem.get('id', '')
            self._memories_lookup[mid] = mem
            # Lightweight shim so panel can do `neural_brain.nodes.get(id)`
            self.nodes[mid] = _NodeShim(mid, mem, self)

        json_str = json.dumps(memories, default=str)

        if self._page_ready:
            self._run_js(f"setMemories('{self._escape(json_str)}')")
        else:
            self._pending_memories = json_str

    def clear_selection(self):
        self._selected_id = None
        if self._page_ready:
            self._run_js("clearSelection()")

    def get_selected_memory(self) -> Optional[Dict[str, Any]]:
        if self._selected_id:
            return self._memories_lookup.get(self._selected_id)
        return None

    def filter_by_type(self, memory_type: Optional[str]):
        if self._page_ready:
            if memory_type:
                self._run_js(f"filterByType('{memory_type}')")
            else:
                self._run_js("filterByType(null)")

    def filter_nodes(self, query: str):
        if self._page_ready:
            safe = self._escape(query)
            self._run_js(f"filterNodes('{safe}')")

    def set_theme(self, theme: str):
        if self._page_ready:
            self._run_js(f"setTheme('{theme}')")

    def delete_node(self, node_id: str):
        if self._page_ready:
            safe = self._escape(node_id)
            self._run_js(f"deleteNode('{safe}')")

    # ====================================================================
    # Cleanup
    # ====================================================================

    def cleanup(self):
        try:
            if hasattr(self, '_web_view'):
                self._web_view.setUrl(QUrl("about:blank"))
        except Exception:
            pass

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)


class _NodeShim:
    """
    Thin compatibility shim so existing panel code like
        node = self.neural_brain.nodes.get(memory_id)
        node.memory_data
        node.get_display_position(offset)
    keeps working.
    """

    def __init__(self, node_id: str, data: Dict[str, Any], widget: 'WebNeuralBrainWidget'):
        self.id = node_id
        self.memory_data = data
        self.memory_type = data.get('memory_type', 'conversation')
        self._widget = widget

    def get_display_position(self, _offset=None):
        """Return center of the widget as approximate position for the detail card."""
        from PySide6.QtCore import QPointF
        w = self._widget
        return QPointF(w.width() / 2, w.height() / 2)
