import threading
import queue
import time
import psutil
import uuid
import logging
from collections import defaultdict
from typing import Dict, List, Callable, Any, Optional, Union
from .utils import ThreadPriority, ThreadStatus, logger

class ThreadGroup:
    """Manages a group of related threads"""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.threads = []
        self.group_lock = threading.RLock()
        self.creation_time = time.time()
        self.group_id = str(uuid.uuid4())
        
    def add_thread(self, thread):
        """Add a thread to this group"""
        with self.group_lock:
            self.threads.append(thread)
            
    def remove_thread(self, thread):
        """Remove a thread from this group"""
        with self.group_lock:
            if thread in self.threads:
                self.threads.remove(thread)
                
    def terminate_all(self):
        """Terminate all threads in this group"""
        with self.group_lock:
            for thread in self.threads:
                thread.terminate()
                
    def get_stats(self):
        """Get statistics about this thread group"""
        with self.group_lock:
            total = len(self.threads)
            running = sum(1 for t in self.threads if t.status == ThreadStatus.RUNNING)
            waiting = sum(1 for t in self.threads if t.status == ThreadStatus.WAITING)
            completed = sum(1 for t in self.threads if t.status == ThreadStatus.COMPLETED)
            failed = sum(1 for t in self.threads if t.status == ThreadStatus.FAILED)
            terminated = sum(1 for t in self.threads if t.status == ThreadStatus.TERMINATED)
            
            return {
                "total": total,
                "running": running,
                "waiting": waiting,
                "completed": completed,
                "failed": failed,
                "terminated": terminated
            }
            
    def __str__(self):
        return f"ThreadGroup({self.name}, threads={len(self.threads)})"


class ManagedThread:
    """A managed thread with enhanced functionality"""
    def __init__(self, 
                target: Callable, 
                args=(), 
                kwargs=None, 
                name: str = None,
                priority: ThreadPriority = ThreadPriority.NORMAL,
                group: ThreadGroup = None):
        
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.name = name or f"Thread-{uuid.uuid4().hex[:8]}"
        self.priority = priority
        self.group = group
        self.thread_id = str(uuid.uuid4())
        
        # Thread state
        self.status = ThreadStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.exception = None
        self.result = None
        
        # Synchronization primitives
        self.exit_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # Not paused by default
        self.thread_lock = threading.RLock()
        
        # Create the actual thread
        self._thread = threading.Thread(target=self._thread_wrapper, name=self.name)
        self._thread.daemon = True
        
        # Add to group if specified
        if self.group:
            self.group.add_thread(self)
            
        logger.info(f"Thread created: {self.name} ({self.thread_id})")
        
    def _thread_wrapper(self):
        """Wrapper for the target function to handle thread management"""
        self.start_time = time.time()
        self.update_status(ThreadStatus.RUNNING)
        
        try:
            while not self.exit_event.is_set():
                # Wait if paused
                self.pause_event.wait()
                
                # Check for exit signal again after potential pause
                if self.exit_event.is_set():
                    break
                    
                # Execute the target function
                self.result = self.target(*self.args, **self.kwargs)
                self.update_status(ThreadStatus.COMPLETED)
                break
                
        except Exception as e:
            self.exception = e
            self.update_status(ThreadStatus.FAILED)
            logger.error(f"Thread {self.name} failed with exception: {str(e)}")
            
        finally:
            self.end_time = time.time()
            
    def start(self):
        """Start the thread"""
        with self.thread_lock:
            if self.status == ThreadStatus.PENDING:
                self._thread.start()
                logger.info(f"Thread started: {self.name}")
                return True
            return False
            
    def join(self, timeout=None):
        """Join the thread with optional timeout"""
        return self._thread.join(timeout)
    
    def terminate(self):
        """Signal the thread to exit"""
        with self.thread_lock:
            self.exit_event.set()
            self.pause_event.set()  # Unpause if paused
            self.update_status(ThreadStatus.TERMINATED)
            logger.info(f"Thread termination requested: {self.name}")
            
    def pause(self):
        """Pause the thread execution"""
        with self.thread_lock:
            if self.status == ThreadStatus.RUNNING:
                self.pause_event.clear()
                self.update_status(ThreadStatus.WAITING)
                logger.info(f"Thread paused: {self.name}")
                return True
            return False
            
    def resume(self):
        """Resume the thread execution"""
        with self.thread_lock:
            if self.status == ThreadStatus.WAITING:
                self.pause_event.set()
                self.update_status(ThreadStatus.RUNNING)
                logger.info(f"Thread resumed: {self.name}")
                return True
            return False
            
    def is_alive(self):
        """Check if the thread is alive"""
        return self._thread.is_alive()
        
    def update_status(self, status: ThreadStatus):
        """Update the thread status"""
        with self.thread_lock:
            self.status = status
            
    def get_runtime(self):
        """Get the thread's running time in seconds"""
        if self.start_time is None:
            return 0
            
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
        
    def to_dict(self):
        """Convert thread info to dictionary"""
        return {
            'id': self.thread_id,
            'name': self.name,
            'status': self.status.name,
            'priority': self.priority.name,
            'runtime': self.get_runtime(),
            'group': self.group.name if self.group else None,
            'start_time': self.start_time,
            'has_error': self.exception is not None
        }
        
    def __str__(self):
        return f"ManagedThread({self.name}, status={self.status.name})"


class ThreadPoolExecutor:
    """Thread pool for efficient thread management"""
    
    def __init__(self, max_workers=None, name="DefaultPool"):
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.name = name
        self.pool_id = str(uuid.uuid4())
        
        # Worker management
        self.workers = []
        self.task_queue = queue.Queue()
        self.pool_lock = threading.RLock()
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.total_tasks = 0
        self.creation_time = time.time()
        
        logger.info(f"Thread pool created: {self.name} with {self.max_workers} workers")
        
    def _worker_thread(self):
        """Worker thread that processes tasks from the queue"""
        while not self.shutdown_event.is_set():
            try:
                # Get a task from the queue with timeout
                task = self.task_queue.get(timeout=0.5)
                
                # Process the task
                managed_thread, future = task
                managed_thread.start()
                managed_thread.join()
                
                # Update result or exception in the future
                if managed_thread.exception:
                    future.set_exception(managed_thread.exception)
                    with self.pool_lock:
                        self.failed_tasks += 1
                else:
                    future.set_result(managed_thread.result)
                    with self.pool_lock:
                        self.completed_tasks += 1
                        
                self.task_queue.task_done()
                
            except queue.Empty:
                # No tasks available, continue waiting
                continue
                
            except Exception as e:
                logger.error(f"Worker thread error: {str(e)}")
                
    def start(self):
        """Start the thread pool"""
        with self.pool_lock:
            # Create worker threads
            for i in range(self.max_workers):
                worker = threading.Thread(
                    target=self._worker_thread,
                    name=f"{self.name}-Worker-{i}",
                    daemon=True
                )
                worker.start()
                self.workers.append(worker)
                
            logger.info(f"Thread pool started: {self.name}")
            
    def submit(self, target, args=(), kwargs=None, priority=ThreadPriority.NORMAL, name=None):
        """Submit a task to the thread pool"""
        with self.pool_lock:
            if self.shutdown_event.is_set():
                raise RuntimeError("Cannot submit tasks to a shutdown thread pool")
                
            # Create future for result
            future = ThreadFuture()
            
            # Create managed thread
            thread = ManagedThread(
                target=target,
                args=args,
                kwargs=kwargs,
                priority=priority,
                name=name
            )
            
            # Add to queue
            self.task_queue.put((thread, future))
            self.total_tasks += 1
            
            return future
            
    def shutdown(self, wait=True):
        """Shutdown the thread pool"""
        with self.pool_lock:
            self.shutdown_event.set()
            
            if wait:
                # Wait for all tasks to complete
                self.task_queue.join()
                
                # Wait for all workers to terminate
                for worker in self.workers:
                    worker.join()
                    
            logger.info(f"Thread pool shutdown: {self.name}")
            
    def get_stats(self):
        """Get statistics about this thread pool"""
        with self.pool_lock:
            return {
                "name": self.name,
                "max_workers": self.max_workers,
                "active_workers": len(self.workers),
                "queue_size": self.task_queue.qsize(),
                "completed_tasks": self.completed_tasks,
                "failed_tasks": self.failed_tasks,
                "total_tasks": self.total_tasks,
                "uptime": time.time() - self.creation_time
            }


class ThreadFuture:
    """Future object for asynchronous results"""
    
    def __init__(self):
        self._result = None
        self._exception = None
        self._done_event = threading.Event()
        self._callbacks = []
        self._lock = threading.Lock()
        
    def set_result(self, result):
        """Set the result of the future"""
        with self._lock:
            self._result = result
            self._done_event.set()
            self._invoke_callbacks()
            
    def set_exception(self, exception):
        """Set an exception for the future"""
        with self._lock:
            self._exception = exception
            self._done_event.set()
            self._invoke_callbacks()
            
    def _invoke_callbacks(self):
        """Invoke all registered callbacks"""
        for callback in self._callbacks:
            try:
                callback(self)
            except Exception as e:
                logger.error(f"Error in future callback: {str(e)}")
                
    def add_done_callback(self, callback):
        """Add a callback to be invoked when the future is done"""
        with self._lock:
            if self._done_event.is_set():
                # Already done, invoke immediately
                try:
                    callback(self)
                except Exception as e:
                    logger.error(f"Error in future callback: {str(e)}")
            else:
                self._callbacks.append(callback)
                
    def result(self, timeout=None):
        """Get the result of the future, waiting if necessary"""
        if not self._done_event.wait(timeout):
            raise TimeoutError("Future operation timed out")
            
        if self._exception:
            raise self._exception
            
        return self._result
        
    def exception(self, timeout=None):
        """Get the exception of the future, waiting if necessary"""
        if not self._done_event.wait(timeout):
            raise TimeoutError("Future operation timed out")
            
        return self._exception
        
    def done(self):
        """Check if the future is done"""
        return self._done_event.is_set()
        
    def cancel(self):
        """Cancel the future (if possible)"""
        # This is a simplified implementation that doesn't actually cancel the task
        return False


class Barrier:
    """A reusable barrier for thread synchronization"""
    
    def __init__(self, parties, action=None, timeout=None):
        self.parties = parties
        self.action = action
        self.timeout = timeout
        self.barrier_lock = threading.RLock()
        self.count = 0
        self.generation = 0
        self.event = threading.Event()
        
    def wait(self, timeout=None):
        """Wait for the barrier"""
        with self.barrier_lock:
            generation = self.generation
            count = self.count
            self.count += 1
            
            if self.count == self.parties:
                # Last thread to arrive
                self.count = 0
                self.generation += 1
                self.event.set()
                
                if self.action:
                    self.action()
                    
                return 0
                
        # Wait for barrier
        timeout = timeout if timeout is not None else self.timeout
        if not self.event.wait(timeout):
            with self.barrier_lock:
                if generation == self.generation:
                    # Timeout occurred
                    self.count -= 1
                    if self.count == 0:
                        self.event.clear()
                    raise TimeoutError("Barrier wait timed out")
                    
        # Check if generation changed while waiting
        if generation != self.generation:
            # Barrier was already broken
            return 0
            
        # Reset event for next generation if all threads have passed
        with self.barrier_lock:
            if generation == self.generation - 1:
                self.event.clear()
                
        return 0


class ThreadSemaphore:
    """Enhanced semaphore with timeout and owner tracking"""
    
    def __init__(self, value=1, name=None):
        self.semaphore = threading.Semaphore(value)
        self.name = name or f"Semaphore-{uuid.uuid4().hex[:8]}"
        self.value = value
        self.owners = set()
        self.owner_lock = threading.Lock()
        
    def acquire(self, blocking=True, timeout=None, owner=None):
        """Acquire the semaphore"""
        result = self.semaphore.acquire(blocking, timeout)
        
        if result and owner:
            with self.owner_lock:
                self.owners.add(owner)
                
        return result
        
    def release(self, owner=None):
        """Release the semaphore"""
        if owner:
            with self.owner_lock:
                if owner in self.owners:
                    self.owners.remove(owner)
                    
        self.semaphore.release()
        
    def get_owners(self):
        """Get the current owners of the semaphore"""
        with self.owner_lock:
            return list(self.owners)
            
    def __enter__(self):
        self.acquire()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class EventBus:
    """Event bus for thread communication"""
    
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.lock = threading.RLock()
        
    def subscribe(self, event_type, callback):
        """Subscribe to an event type"""
        with self.lock:
            self.subscribers[event_type].append(callback)
            
    def unsubscribe(self, event_type, callback):
        """Unsubscribe from an event type"""
        with self.lock:
            if event_type in self.subscribers:
                try:
                    self.subscribers[event_type].remove(callback)
                except ValueError:
                    pass
                    
    def publish(self, event_type, data=None):
        """Publish an event"""
        callbacks = []
        with self.lock:
            if event_type in self.subscribers:
                callbacks = self.subscribers[event_type].copy()
                
        # Call callbacks outside the lock
        for callback in callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in event subscriber: {str(e)}")


class ThreadMaster:
    """Main thread management system"""
    
    def __init__(self):
        # Thread tracking
        self.threads = {}
        self.groups = {}
        self.pools = {}
        self.master_lock = threading.RLock()
        
        # Communication
        self.event_bus = EventBus()
        
        # CPU usage tracking
        self.cpu_history = []
        self.memory_history = []
        self.tracking_active = False
        self.tracking_interval = 1.0  # seconds
        self._tracking_thread = None
        
        # Synchronization tools
        self.barriers = {}
        self.semaphores = {}
        
        logger.info("ThreadMaster initialized")

    def save_session_log(self, filename="session_log.json"):
        """Save session statistics to a JSON file"""
        import json
        
        try:
            data = {
                "timestamp": time.time(),
                "duration": time.time() - self.cpu_history[0][0] if self.cpu_history else 0,
                "stats": self.get_thread_stats(),
                "system": self.get_system_stats(),
                "threads": {
                    tid: t.to_dict() for tid, t in self.threads.items()
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Session log saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session log: {str(e)}")
            return False
        
    def create_thread(self, target, args=(), kwargs=None, name=None, 
                     priority=ThreadPriority.NORMAL, group_name=None,
                     auto_start=False):
        """Create a managed thread"""
        with self.master_lock:
            # Get or create group if specified
            group = None
            if group_name:
                group = self.groups.get(group_name)
                if not group:
                    group = self.create_group(group_name)
                    
            # Create thread
            thread = ManagedThread(
                target=target,
                args=args,
                kwargs=kwargs,
                name=name,
                priority=priority,
                group=group
            )
            
            # Store thread
            self.threads[thread.thread_id] = thread
            
            # Auto-start if requested
            if auto_start:
                thread.start()
                
            return thread
            
    def create_group(self, name, description=""):
        """Create a thread group"""
        with self.master_lock:
            if name in self.groups:
                return self.groups[name]
                
            group = ThreadGroup(name, description)
            self.groups[name] = group
            return group
            
    def create_pool(self, max_workers=None, name=None):
        """Create a thread pool"""
        with self.master_lock:
            pool = ThreadPoolExecutor(max_workers, name)
            self.pools[pool.pool_id] = pool
            pool.start()
            return pool
            
    def create_barrier(self, name, parties, action=None, timeout=None):
        """Create a barrier"""
        with self.master_lock:
            barrier = Barrier(parties, action, timeout)
            self.barriers[name] = barrier
            return barrier
            
    def create_semaphore(self, name, value=1):
        """Create a semaphore"""
        with self.master_lock:
            semaphore = ThreadSemaphore(value, name)
            self.semaphores[name] = semaphore
            return semaphore
            
    def get_thread(self, thread_id):
        """Get a thread by ID"""
        with self.master_lock:
            return self.threads.get(thread_id)
            
    def get_group(self, name):
        """Get a group by name"""
        with self.master_lock:
            return self.groups.get(name)
            
    def get_threads_by_status(self, status):
        """Get all threads with the specified status"""
        with self.master_lock:
            return [t for t in self.threads.values() if t.status == status]
            
    def get_threads_by_group(self, group_name):
        """Get all threads in the specified group"""
        with self.master_lock:
            group = self.groups.get(group_name)
            return group.threads if group else []
            
    def terminate_all(self):
        """Terminate all managed threads"""
        with self.master_lock:
            for thread in self.threads.values():
                thread.terminate()
                
            for pool in self.pools.values():
                pool.shutdown(wait=False)
                
    def start_resource_tracking(self):
        """Start tracking system resources"""
        with self.master_lock:
            if self.tracking_active:
                return False
                
            self.tracking_active = True
            self._tracking_thread = threading.Thread(
                target=self._track_resources,
                daemon=True,
                name="ResourceTracker"
            )
            self._tracking_thread.start()
            logger.info("Resource tracking started")
            return True
            
    def stop_resource_tracking(self):
        """Stop tracking system resources"""
        with self.master_lock:
            self.tracking_active = False
            if self._tracking_thread:
                self._tracking_thread.join(timeout=2.0)
                logger.info("Resource tracking stopped")
                
    def _track_resources(self):
        """Track CPU and memory usage"""
        max_history = 60  # Keep last 60 samples
        
        while self.tracking_active:
            try:
                # Get CPU and memory usage
                cpu = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory().percent
                
                # Add to history
                timestamp = time.time()
                with self.master_lock:
                    self.cpu_history.append((timestamp, cpu))
                    self.memory_history.append((timestamp, memory))
                    
                    # Trim history if needed
                    if len(self.cpu_history) > max_history:
                        self.cpu_history = self.cpu_history[-max_history:]
                    if len(self.memory_history) > max_history:
                        self.memory_history = self.memory_history[-max_history:]
                        
                # Sleep until next sample
                time.sleep(self.tracking_interval)
                
            except Exception as e:
                logger.error(f"Error in resource tracking: {str(e)}")
                time.sleep(1.0)  # Sleep on error
                
    def get_system_stats(self):
        """Get system statistics"""
        with self.master_lock:
            cpu_usage = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            
            return {
                "cpu_usage": cpu_usage,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "memory_percent": memory.percent,
                "cpu_history": self.cpu_history,
                "memory_history": self.memory_history
            }
            
    def get_thread_stats(self):
        """Get thread statistics"""
        with self.master_lock:
            total = len(self.threads)
            running = len(self.get_threads_by_status(ThreadStatus.RUNNING))
            waiting = len(self.get_threads_by_status(ThreadStatus.WAITING))
            completed = len(self.get_threads_by_status(ThreadStatus.COMPLETED))
            failed = len(self.get_threads_by_status(ThreadStatus.FAILED))
            terminated = len(self.get_threads_by_status(ThreadStatus.TERMINATED))
            
            return {
                "total": total,
                "running": running,
                "waiting": waiting,
                "completed": completed,
                "failed": failed,
                "terminated": terminated,
                "groups": len(self.groups),
                "pools": len(self.pools)
            }
            
    def cleanup_completed(self):
        """Clean up completed and failed threads"""
        with self.master_lock:
            to_remove = []
            
            for thread_id, thread in self.threads.items():
                if thread.status in (ThreadStatus.COMPLETED, 
                                    ThreadStatus.FAILED,
                                    ThreadStatus.TERMINATED):
                    to_remove.append(thread_id)
                    
            # Remove threads
            for thread_id in to_remove:
                thread = self.threads.pop(thread_id)
                
                # Remove from group if needed
                if thread.group:
                    thread.group.remove_thread(thread)
                    
            return len(to_remove)

# Updated by Hasini

# Updated by Hasini
