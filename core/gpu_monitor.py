"""
GPU Memory Monitor for Nexa
Real-time VRAM tracking with automatic report generation on shutdown.
"""

import logging
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
from collections import deque

logger = logging.getLogger(__name__)


class GPUMonitor:
    """
    Monitor GPU memory usage in real-time and generate reports.
    Displays periodic updates in terminal and creates graph on shutdown.
    """
    
    def __init__(self, report_dir: Path = None, update_interval: int = 30, config=None):
        """
        Initialize GPU monitor.
        
        Args:
            report_dir: Directory to save reports (default: data/logs/gpu_reports)
            update_interval: Seconds between terminal updates (default: 30)
            config: Configuration object with data_dir path
        """
        if report_dir:
            self.report_dir = report_dir
        elif config and hasattr(config, 'logs_dir'):
            self.report_dir = config.logs_dir / "gpu_reports"
        else:
            self.report_dir = Path("data/logs/gpu_reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.update_interval = update_interval
        self.monitoring = False
        self.monitor_thread = None
        
        # Store history: [(timestamp, used_mb, total_mb, model_name)]
        self.history: deque = deque(maxlen=10000)  # Max 10k samples (~83 hours at 30s interval)
        
        # Track which models are loaded
        self.current_models = set()
        
        # Check if pynvml is available
        self.nvml_available = False
        try:
            import pynvml
            pynvml.nvmlInit()
            self.nvml_available = True
            logger.info("✅ GPU monitoring enabled (NVIDIA GPU detected)")
        except Exception as e:
            logger.warning(f"⚠️ GPU monitoring unavailable: {e}")
    
    def start_monitoring(self):
        """Start background monitoring thread."""
        if not self.nvml_available:
            logger.info("GPU monitoring disabled (no NVIDIA GPU)")
            return
        
        if self.monitoring:
            logger.warning("GPU monitoring already running")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"🔍 GPU monitoring started (updates every {self.update_interval}s)")
    
    def stop_monitoring(self):
        """Stop monitoring and generate final report."""
        if not self.monitoring:
            return
        
        logger.info("🛑 Stopping GPU monitoring...")
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        # Generate final report
        if len(self.history) > 0:
            self._generate_report()
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        import pynvml
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # First GPU
            
            while self.monitoring:
                try:
                    # Get memory info
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    used_mb = mem_info.used / 1024 / 1024
                    total_mb = mem_info.total / 1024 / 1024
                    free_mb = mem_info.free / 1024 / 1024
                    usage_percent = (used_mb / total_mb) * 100
                    
                    # Get GPU name
                    gpu_name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(gpu_name, bytes):
                        gpu_name = gpu_name.decode('utf-8')
                    
                    # Store in history
                    timestamp = time.time()
                    models_str = ", ".join(self.current_models) if self.current_models else "Idle"
                    self.history.append((timestamp, used_mb, total_mb, models_str))
                    
                    # Log to terminal
                    logger.info(f"📊 GPU: {used_mb:.0f}MB / {total_mb:.0f}MB ({usage_percent:.1f}%) | Free: {free_mb:.0f}MB | Models: {models_str}")
                    
                    # Sleep until next check
                    time.sleep(self.update_interval)
                    
                except Exception as e:
                    logger.error(f"Error reading GPU stats: {e}")
                    time.sleep(self.update_interval)
        
        except Exception as e:
            logger.error(f"GPU monitoring failed: {e}")
            self.monitoring = False
    
    def register_model_load(self, model_name: str):
        """
        Register that a model was loaded.
        
        Args:
            model_name: Name of the model (e.g., "Whisper", "Llama 3.1", "SpeechBrain")
        """
        self.current_models.add(model_name)
        logger.debug(f"📌 Model loaded: {model_name} | Active: {self.current_models}")
    
    def register_model_unload(self, model_name: str):
        """
        Register that a model was unloaded.
        
        Args:
            model_name: Name of the model
        """
        self.current_models.discard(model_name)
        logger.debug(f"📌 Model unloaded: {model_name} | Active: {self.current_models}")
    
    def _generate_report(self):
        """Generate markdown report with usage graph."""
        if not self.history:
            logger.warning("No GPU data to report")
            return
        
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.report_dir / f"gpu_report_{timestamp}.md"
            graph_file = self.report_dir / f"gpu_graph_{timestamp}.png"
            
            # Calculate statistics
            vram_usage = [used for _, used, _, _ in self.history]
            avg_usage = sum(vram_usage) / len(vram_usage)
            max_usage = max(vram_usage)
            min_usage = min(vram_usage)
            
            # Get total VRAM from first sample
            total_vram = self.history[0][2]
            
            # Get session duration
            start_time = self.history[0][0]
            end_time = self.history[-1][0]
            duration_seconds = end_time - start_time
            duration_minutes = duration_seconds / 60
            
            # Generate graph using matplotlib
            try:
                import matplotlib
                matplotlib.use('Agg')  # Non-interactive backend
                import matplotlib.pyplot as plt
                
                # Prepare data
                timestamps = [(t - start_time) / 60 for t, _, _, _ in self.history]  # Minutes since start
                usage_values = [used for _, used, _, _ in self.history]
                
                # Create figure
                plt.figure(figsize=(12, 6))
                plt.plot(timestamps, usage_values, linewidth=2, color='#1f77b4')
                plt.axhline(y=total_vram, color='red', linestyle='--', label=f'Total VRAM ({total_vram:.0f}MB)', alpha=0.7)
                plt.axhline(y=avg_usage, color='green', linestyle='--', label=f'Average ({avg_usage:.0f}MB)', alpha=0.7)
                
                plt.xlabel('Time (minutes)', fontsize=12)
                plt.ylabel('VRAM Usage (MB)', fontsize=12)
                plt.title(f'Nexa GPU Memory Usage - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', fontsize=14, fontweight='bold')
                plt.legend(loc='upper right')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                
                # Save graph
                plt.savefig(graph_file, dpi=150, bbox_inches='tight')
                plt.close()
                
                logger.info(f"📈 GPU usage graph saved: {graph_file}")
                graph_generated = True
                
            except Exception as e:
                logger.warning(f"⚠️ Could not generate graph: {e}")
                graph_generated = False
            
            # Generate markdown report
            report_content = f"""# Nexa GPU Memory Usage Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Duration**: {duration_minutes:.1f} minutes ({len(self.history)} samples)  
**Update Interval**: {self.update_interval} seconds

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| **Total VRAM** | {total_vram:.0f} MB |
| **Average Usage** | {avg_usage:.0f} MB ({(avg_usage/total_vram)*100:.1f}%) |
| **Peak Usage** | {max_usage:.0f} MB ({(max_usage/total_vram)*100:.1f}%) |
| **Minimum Usage** | {min_usage:.0f} MB ({(min_usage/total_vram)*100:.1f}%) |
| **Average Free** | {total_vram - avg_usage:.0f} MB |

---

## Usage Graph

"""
            
            if graph_generated:
                report_content += f"![GPU Usage Graph]({graph_file.name})\n\n"
            else:
                report_content += "*Graph generation failed - matplotlib not available*\n\n"
            
            report_content += """---

## Detailed Log

| Time (min) | VRAM Used | Free | Usage % | Models Active |
|-----------|-----------|------|---------|---------------|
"""
            
            # Add sample data points (every 5th sample to keep report readable)
            for i, (timestamp, used, total, models) in enumerate(self.history):
                if i % 5 == 0 or i == len(self.history) - 1:  # Every 5th sample + last sample
                    time_min = (timestamp - start_time) / 60
                    free = total - used
                    usage_pct = (used / total) * 100
                    report_content += f"| {time_min:.1f} | {used:.0f} MB | {free:.0f} MB | {usage_pct:.1f}% | {models} |\n"
            
            report_content += """
---

## Tips for Optimization

- **High VRAM usage (>90%)**: Consider reducing model sizes or disabling unused features
- **Frequent peaks**: May indicate memory fragmentation - restart Nexa periodically
- **Crashes at peaks**: Reduce `num_ctx` in llm_manager.py or use smaller Whisper model
- **Low usage (<50%)**: You have headroom - can use larger models for better quality

---

*Report generated by Nexa GPU Monitor*
"""
            
            # Write report
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"📄 GPU usage report saved: {report_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate GPU report: {e}")
    
    def get_current_usage(self) -> Optional[Tuple[float, float, float]]:
        """
        Get current GPU usage.
        
        Returns:
            Tuple of (used_mb, total_mb, usage_percent) or None if unavailable
        """
        if not self.nvml_available:
            return None
        
        try:
            import pynvml
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            used_mb = mem_info.used / 1024 / 1024
            total_mb = mem_info.total / 1024 / 1024
            usage_percent = (used_mb / total_mb) * 100
            
            return (used_mb, total_mb, usage_percent)
        
        except Exception as e:
            logger.debug(f"Could not get GPU usage: {e}")
            return None
