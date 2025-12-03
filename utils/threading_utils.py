"""
Threading Utilities
Helper classes and functions for thread management.
"""

import logging
import threading
from typing import Callable, Any
from queue import Queue

logger = logging.getLogger(__name__)


class SafeThread(threading.Thread):
    """
    Thread subclass with exception handling and logging.
    """
    
    def __init__(self, target: Callable, name: str = None, daemon: bool = True):
        """
        Initialize safe thread.
        
        Args:
            target: Target function to run
            name: Thread name
            daemon: Whether thread is daemon
        """
        super().__init__(target=self._wrapped_target, name=name, daemon=daemon)
        self._target = target
        self.exception = None
    
    def _wrapped_target(self):
        """Wrapped target with exception handling."""
        try:
            self._target()
        except Exception as e:
            self.exception = e
            logger.error(f"Exception in thread {self.name}: {e}", exc_info=True)
    
    def join(self, timeout=None):
        """Join thread and re-raise exceptions."""
        super().join(timeout)
        if self.exception:
            raise self.exception


class ThreadPool:
    """
    Simple thread pool for managing worker threads.
    """
    
    def __init__(self, num_workers: int = 4):
        """
        Initialize thread pool.
        
        Args:
            num_workers: Number of worker threads
        """
        self.num_workers = num_workers
        self.task_queue = Queue()
        self.workers = []
        self.running = False
    
    def start(self):
        """Start worker threads."""
        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker,
                name=f"ThreadPoolWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Thread pool started with {self.num_workers} workers")
    
    def _worker(self):
        """Worker thread main loop."""
        while self.running:
            try:
                task = self.task_queue.get(timeout=0.5)
                if task:
                    func, args, kwargs = task
                    func(*args, **kwargs)
                self.task_queue.task_done()
            except Exception as e:
                if self.running:
                    logger.error(f"Error in worker thread: {e}")
    
    def submit(self, func: Callable, *args, **kwargs):
        """
        Submit task to thread pool.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        self.task_queue.put((func, args, kwargs))
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown thread pool.
        
        Args:
            wait: Whether to wait for tasks to complete
        """
        self.running = False
        
        if wait:
            self.task_queue.join()
        
        for worker in self.workers:
            worker.join(timeout=1.0)
        
        logger.info("Thread pool shutdown complete")
