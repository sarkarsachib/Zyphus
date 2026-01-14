"""
DEVmind Interrupt Watchers
Reactive awareness system that responds to external and internal triggers

This module implements interrupt watchers that monitor various signals and
triggers, allowing DEVmind to react to changes in its environment, internal
state, and external stimuli. Like human reflexes and attention mechanisms,
this enables immediate responses to important events.

Author: Sachib
Version: 1.0.0
"""

import asyncio
import json
import logging
import time
import threading
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import hashlib
import psutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import queue
import signal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InterruptType(Enum):
    """Types of interrupts that can be watched"""
    FILE_CHANGE = "file_change"
    USER_LOGIN = "user_login"
    DATA_ARRIVAL = "data_arrival"
    TIME_ELAPSED = "time_elapsed"
    EMOTIONAL_SHIFT = "emotional_shift"
    SYSTEM_CHANGE = "system_change"
    NETWORK_EVENT = "network_event"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_SPIKE = "cpu_spike"
    ERROR_OCCURRED = "error_occurred"
    THRESHOLD_BREACH = "threshold_breach"
    PATTERN_DETECTED = "pattern_detected"
    EXTERNAL_SIGNAL = "external_signal"
    INTERNAL_TRIGGER = "internal_trigger"

class InterruptPriority(Enum):
    """Priority levels for interrupts"""
    CRITICAL = "critical"    # Immediate response required
    HIGH = "high"           # High priority response
    MEDIUM = "medium"       # Normal priority
    LOW = "low"            # Low priority
    BACKGROUND = "background"  # Background processing

class InterruptStatus(Enum):
    """Status of interrupt watchers"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class InterruptEvent:
    """Represents an interrupt event"""
    id: str
    interrupt_type: InterruptType
    priority: InterruptPriority
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    processed: bool
    response_time: Optional[float]
    handler_result: Optional[Any]

@dataclass
class InterruptWatcher:
    """Represents an interrupt watcher"""
    id: str
    name: str
    interrupt_type: InterruptType
    priority: InterruptPriority
    status: InterruptStatus
    created_at: datetime
    last_triggered: Optional[datetime]
    trigger_count: int
    configuration: Dict[str, Any]
    handler: Optional[Callable]
    conditions: Dict[str, Any]
    cooldown_seconds: float
    max_triggers_per_hour: int
    enabled: bool

@dataclass
class WatcherMetrics:
    """Metrics for interrupt watchers"""
    total_watchers: int = 0
    active_watchers: int = 0
    total_interrupts: int = 0
    interrupts_per_hour: float = 0.0
    average_response_time: float = 0.0
    critical_interrupts: int = 0
    failed_responses: int = 0
    success_rate: float = 1.0

class FileSystemWatcher(FileSystemEventHandler):
    """File system event handler for file change interrupts"""
    
    def __init__(self, interrupt_manager):
        super().__init__()
        self.interrupt_manager = interrupt_manager
    
    def on_modified(self, event):
        if not event.is_directory:
            self._trigger_file_interrupt('modified', event.src_path)
    
    def on_created(self, event):
        if not event.is_directory:
            self._trigger_file_interrupt('created', event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory:
            self._trigger_file_interrupt('deleted', event.src_path)
    
    def on_moved(self, event):
        if not event.is_directory:
            self._trigger_file_interrupt('moved', event.src_path, event.dest_path)
    
    def _trigger_file_interrupt(self, action: str, src_path: str, dest_path: str = None):
        """Trigger a file change interrupt"""
        asyncio.create_task(self.interrupt_manager.trigger_interrupt(
            interrupt_type=InterruptType.FILE_CHANGE,
            source=f"filesystem:{action}",
            data={
                'action': action,
                'src_path': src_path,
                'dest_path': dest_path,
                'file_size': os.path.getsize(src_path) if os.path.exists(src_path) else 0,
                'timestamp': datetime.now().isoformat()
            },
            priority=InterruptPriority.MEDIUM
        ))

class SystemMonitor:
    """Monitors system resources and triggers interrupts"""
    
    def __init__(self, interrupt_manager):
        self.interrupt_manager = interrupt_manager
        self.is_running = False
        self.monitor_task = None
        self.last_cpu_check = 0
        self.last_memory_check = 0
        self.cpu_threshold = 80.0  # CPU usage threshold
        self.memory_threshold = 80.0  # Memory usage threshold
    
    async def start(self):
        """Start system monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("System monitor started")
    
    async def stop(self):
        """Stop system monitoring"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("System monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Check CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                if cpu_percent > self.cpu_threshold:
                    await self._trigger_cpu_spike(cpu_percent)
                
                # Check memory usage
                memory = psutil.virtual_memory()
                if memory.percent > self.memory_threshold:
                    await self._trigger_memory_pressure(memory.percent)
                
                # Check for new processes
                await self._check_process_changes()
                
                # Check network activity
                await self._check_network_activity()
                
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in system monitor: {str(e)}")
                await asyncio.sleep(10.0)
    
    async def _trigger_cpu_spike(self, cpu_percent: float):
        """Trigger CPU spike interrupt"""
        current_time = time.time()
        if current_time - self.last_cpu_check > 30:  # Cooldown of 30 seconds
            self.last_cpu_check = current_time
            
            await self.interrupt_manager.trigger_interrupt(
                interrupt_type=InterruptType.CPU_SPIKE,
                source="system_monitor",
                data={
                    'cpu_percent': cpu_percent,
                    'threshold': self.cpu_threshold,
                    'timestamp': datetime.now().isoformat()
                },
                priority=InterruptPriority.HIGH
            )
    
    async def _trigger_memory_pressure(self, memory_percent: float):
        """Trigger memory pressure interrupt"""
        current_time = time.time()
        if current_time - self.last_memory_check > 60:  # Cooldown of 60 seconds
            self.last_memory_check = current_time
            
            await self.interrupt_manager.trigger_interrupt(
                interrupt_type=InterruptType.MEMORY_PRESSURE,
                source="system_monitor",
                data={
                    'memory_percent': memory_percent,
                    'threshold': self.memory_threshold,
                    'available_mb': psutil.virtual_memory().available / 1024 / 1024,
                    'timestamp': datetime.now().isoformat()
                },
                priority=InterruptPriority.HIGH
            )
    
    async def _check_process_changes(self):
        """Check for new or terminated processes"""
        # Placeholder for process monitoring
        pass
    
    async def _check_network_activity(self):
        """Check for significant network activity"""
        # Placeholder for network monitoring
        pass

class EmotionalStateWatcher:
    """Watches for emotional state changes and triggers interrupts"""
    
    def __init__(self, interrupt_manager):
        self.interrupt_manager = interrupt_manager
        self.last_emotional_state = None
        self.emotional_history = []
        self.instability_threshold = 3  # Number of changes indicating instability
        self.time_window = 300  # 5 minutes
    
    async def check_emotional_state(self, current_state: str, intensity: float):
        """Check emotional state and trigger interrupts if needed"""
        current_time = datetime.now()
        
        # Record emotional state
        self.emotional_history.append({
            'state': current_state,
            'intensity': intensity,
            'timestamp': current_time
        })
        
        # Clean old history
        cutoff_time = current_time - timedelta(seconds=self.time_window)
        self.emotional_history = [
            h for h in self.emotional_history 
            if h['timestamp'] > cutoff_time
        ]
        
        # Check for emotional shift
        if self.last_emotional_state and self.last_emotional_state != current_state:
            await self._trigger_emotional_shift(current_state, intensity)
        
        # Check for emotional instability
        if len(self.emotional_history) >= self.instability_threshold:
            unique_states = set(h['state'] for h in self.emotional_history)
            if len(unique_states) >= self.instability_threshold:
                await self._trigger_emotional_instability(unique_states)
        
        self.last_emotional_state = current_state
    
    async def _trigger_emotional_shift(self, new_state: str, intensity: float):
        """Trigger emotional shift interrupt"""
        await self.interrupt_manager.trigger_interrupt(
            interrupt_type=InterruptType.EMOTIONAL_SHIFT,
            source="emotional_monitor",
            data={
                'old_state': self.last_emotional_state,
                'new_state': new_state,
                'intensity': intensity,
                'timestamp': datetime.now().isoformat()
            },
            priority=InterruptPriority.MEDIUM
        )
    
    async def _trigger_emotional_instability(self, states: Set[str]):
        """Trigger emotional instability interrupt"""
        await self.interrupt_manager.trigger_interrupt(
            interrupt_type=InterruptType.EMOTIONAL_SHIFT,
            source="emotional_monitor",
            data={
                'type': 'instability',
                'states': list(states),
                'frequency': len(self.emotional_history),
                'time_window': self.time_window,
                'timestamp': datetime.now().isoformat()
            },
            priority=InterruptPriority.HIGH
        )

class TimeBasedWatcher:
    """Watches for time-based triggers"""
    
    def __init__(self, interrupt_manager):
        self.interrupt_manager = interrupt_manager
        self.timers = {}
        self.is_running = False
        self.timer_task = None
    
    async def start(self):
        """Start time-based watching"""
        if self.is_running:
            return
        
        self.is_running = True
        self.timer_task = asyncio.create_task(self._timer_loop())
        logger.info("Time-based watcher started")
    
    async def stop(self):
        """Stop time-based watching"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.timer_task:
            self.timer_task.cancel()
            try:
                await self.timer_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Time-based watcher stopped")
    
    def add_timer(self, name: str, duration_seconds: float, 
                  priority: InterruptPriority = InterruptPriority.MEDIUM,
                  metadata: Dict[str, Any] = None):
        """Add a timer that will trigger an interrupt"""
        trigger_time = datetime.now() + timedelta(seconds=duration_seconds)
        
        self.timers[name] = {
            'trigger_time': trigger_time,
            'duration': duration_seconds,
            'priority': priority,
            'metadata': metadata or {},
            'triggered': False
        }
        
        logger.info(f"Added timer: {name} (triggers in {duration_seconds}s)")
    
    def remove_timer(self, name: str):
        """Remove a timer"""
        if name in self.timers:
            del self.timers[name]
            logger.info(f"Removed timer: {name}")
    
    async def _timer_loop(self):
        """Main timer loop"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Check all timers
                for name, timer_info in list(self.timers.items()):
                    if not timer_info['triggered'] and current_time >= timer_info['trigger_time']:
                        await self._trigger_timer(name, timer_info)
                        timer_info['triggered'] = True
                
                # Clean up triggered timers
                self.timers = {
                    name: info for name, info in self.timers.items()
                    if not info['triggered']
                }
                
                await asyncio.sleep(1.0)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in timer loop: {str(e)}")
                await asyncio.sleep(5.0)
    
    async def _trigger_timer(self, name: str, timer_info: Dict[str, Any]):
        """Trigger a timer interrupt"""
        await self.interrupt_manager.trigger_interrupt(
            interrupt_type=InterruptType.TIME_ELAPSED,
            source=f"timer:{name}",
            data={
                'timer_name': name,
                'duration': timer_info['duration'],
                'metadata': timer_info['metadata'],
                'timestamp': datetime.now().isoformat()
            },
            priority=timer_info['priority']
        )

class PatternDetector:
    """Detects patterns in data and triggers interrupts"""
    
    def __init__(self, interrupt_manager):
        self.interrupt_manager = interrupt_manager
        self.data_streams = {}
        self.patterns = {}
        self.detection_window = 100  # Number of data points to analyze
    
    def add_data_stream(self, stream_name: str, data_point: Any):
        """Add a data point to a stream"""
        if stream_name not in self.data_streams:
            self.data_streams[stream_name] = []
        
        self.data_streams[stream_name].append({
            'value': data_point,
            'timestamp': datetime.now()
        })
        
        # Limit stream size
        if len(self.data_streams[stream_name]) > self.detection_window:
            self.data_streams[stream_name] = self.data_streams[stream_name][-self.detection_window:]
        
        # Check for patterns
        asyncio.create_task(self._check_patterns(stream_name))
    
    def register_pattern(self, pattern_name: str, stream_name: str, 
                        detector_func: Callable, priority: InterruptPriority = InterruptPriority.MEDIUM):
        """Register a pattern detector"""
        self.patterns[pattern_name] = {
            'stream_name': stream_name,
            'detector_func': detector_func,
            'priority': priority,
            'last_detected': None
        }
    
    async def _check_patterns(self, stream_name: str):
        """Check for patterns in a data stream"""
        for pattern_name, pattern_info in self.patterns.items():
            if pattern_info['stream_name'] == stream_name:
                try:
                    data_points = self.data_streams[stream_name]
                    if len(data_points) >= 5:  # Minimum data points for pattern detection
                        
                        # Extract values for pattern detection
                        values = [dp['value'] for dp in data_points]
                        
                        # Run pattern detector
                        pattern_detected = pattern_info['detector_func'](values)
                        
                        if pattern_detected:
                            await self._trigger_pattern_detection(pattern_name, pattern_info, data_points)
                
                except Exception as e:
                    logger.error(f"Error in pattern detection for {pattern_name}: {str(e)}")
    
    async def _trigger_pattern_detection(self, pattern_name: str, pattern_info: Dict[str, Any], 
                                       data_points: List[Dict[str, Any]]):
        """Trigger pattern detection interrupt"""
        current_time = datetime.now()
        
        # Check cooldown
        if (pattern_info['last_detected'] and 
            (current_time - pattern_info['last_detected']).total_seconds() < 60):
            return
        
        pattern_info['last_detected'] = current_time
        
        await self.interrupt_manager.trigger_interrupt(
            interrupt_type=InterruptType.PATTERN_DETECTED,
            source=f"pattern_detector:{pattern_name}",
            data={
                'pattern_name': pattern_name,
                'stream_name': pattern_info['stream_name'],
                'data_points_count': len(data_points),
                'latest_values': [dp['value'] for dp in data_points[-5:]],
                'timestamp': current_time.isoformat()
            },
            priority=pattern_info['priority']
        )

class InterruptManager:
    """
    The Interrupt Manager - Reactive awareness system
    
    This manager coordinates all interrupt watchers and handles interrupt
    events, providing reactive awareness that allows DEVmind to respond
    immediately to important changes and events.
    """
    
    def __init__(self, manager_id: str = None):
        self.manager_id = manager_id or f"im_{uuid.uuid4().hex[:8]}"
        self.is_running = False
        self.metrics = WatcherMetrics()
        
        # Interrupt storage
        self.watchers: Dict[str, InterruptWatcher] = {}
        self.recent_interrupts: List[InterruptEvent] = []
        self.interrupt_queue = asyncio.Queue()
        
        # Processing
        self.processor_task = None
        self.max_queue_size = 1000
        self.processing_timeout = 30.0
        
        # Built-in watchers
        self.file_system_watcher = FileSystemWatcher(self)
        self.system_monitor = SystemMonitor(self)
        self.emotional_watcher = EmotionalStateWatcher(self)
        self.time_watcher = TimeBasedWatcher(self)
        self.pattern_detector = PatternDetector(self)
        
        # File system observer
        self.fs_observer = Observer()
        self.watched_paths = set()
        
        # Default handlers
        self.default_handlers = {}
        self._register_default_handlers()
        
        # Persistence
        self.persistence_path = Path(f"/tmp/devmind_interrupts_{self.manager_id}")
        self.persistence_path.mkdir(exist_ok=True)
        
        logger.info(f"Interrupt Manager initialized: {self.manager_id}")
    
    async def start(self) -> Dict[str, Any]:
        """Start the interrupt manager"""
        if self.is_running:
            return {
                'success': False,
                'error': 'Interrupt manager is already running',
                'manager_id': self.manager_id
            }
        
        logger.info(f"Starting Interrupt Manager: {self.manager_id}")
        
        # Load persistent state
        await self._load_persistent_state()
        
        # Start processing
        self.is_running = True
        self.processor_task = asyncio.create_task(self._processor_loop())
        
        # Start built-in watchers
        await self.system_monitor.start()
        await self.time_watcher.start()
        
        # Start file system watching
        self.fs_observer.start()
        
        # Create default watchers
        await self._create_default_watchers()
        
        return {
            'success': True,
            'manager_id': self.manager_id,
            'watchers_created': len(self.watchers),
            'built_in_watchers': ['file_system', 'system_monitor', 'emotional', 'time_based', 'pattern_detector']
        }
    
    async def stop(self) -> Dict[str, Any]:
        """Stop the interrupt manager"""
        if not self.is_running:
            return {
                'success': False,
                'error': 'Interrupt manager is not running',
                'manager_id': self.manager_id
            }
        
        logger.info(f"Stopping Interrupt Manager: {self.manager_id}")
        
        # Stop processing
        self.is_running = False
        
        # Stop built-in watchers
        await self.system_monitor.stop()
        await self.time_watcher.stop()
        
        # Stop file system watching
        self.fs_observer.stop()
        self.fs_observer.join()
        
        # Cancel processor
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        # Save persistent state
        await self._save_persistent_state()
        
        return {
            'success': True,
            'manager_id': self.manager_id,
            'final_metrics': asdict(self.metrics),
            'total_interrupts_processed': self.metrics.total_interrupts
        }
    
    async def _processor_loop(self):
        """Main interrupt processing loop"""
        logger.info("Interrupt processor started")
        
        while self.is_running:
            try:
                # Get next interrupt from queue
                try:
                    interrupt_event = await asyncio.wait_for(
                        self.interrupt_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the interrupt
                await self._process_interrupt(interrupt_event)
                
                # Update metrics
                self.metrics.total_interrupts += 1
                
                # Mark queue task as done
                self.interrupt_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in interrupt processor: {str(e)}")
                await asyncio.sleep(1.0)
    
    async def _process_interrupt(self, interrupt_event: InterruptEvent):
        """Process a single interrupt event"""
        start_time = time.time()
        
        try:
            # Find appropriate handler
            handler = await self._find_handler(interrupt_event)
            
            if handler:
                # Execute handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(interrupt_event)
                else:
                    result = handler(interrupt_event)
                
                interrupt_event.handler_result = result
                interrupt_event.processed = True
                
                logger.info(f"Processed interrupt: {interrupt_event.interrupt_type.value} "
                           f"from {interrupt_event.source}")
            else:
                logger.warning(f"No handler found for interrupt: {interrupt_event.interrupt_type.value}")
        
        except Exception as e:
            logger.error(f"Error processing interrupt {interrupt_event.id}: {str(e)}")
            self.metrics.failed_responses += 1
        
        finally:
            # Record response time
            interrupt_event.response_time = time.time() - start_time
            
            # Store in recent interrupts
            self.recent_interrupts.append(interrupt_event)
            if len(self.recent_interrupts) > 1000:  # Keep last 1000
                self.recent_interrupts = self.recent_interrupts[-1000:]
    
    async def _find_handler(self, interrupt_event: InterruptEvent) -> Optional[Callable]:
        """Find the appropriate handler for an interrupt"""
        # Check for specific watcher handler
        for watcher in self.watchers.values():
            if (watcher.interrupt_type == interrupt_event.interrupt_type and 
                watcher.handler and watcher.enabled):
                return watcher.handler
        
        # Check default handlers
        if interrupt_event.interrupt_type in self.default_handlers:
            return self.default_handlers[interrupt_event.interrupt_type]
        
        return None
    
    async def trigger_interrupt(self, interrupt_type: InterruptType, source: str,
                              data: Dict[str, Any], priority: InterruptPriority = InterruptPriority.MEDIUM,
                              metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Trigger an interrupt event"""
        
        # Create interrupt event
        interrupt_event = InterruptEvent(
            id=uuid.uuid4().hex[:8],
            interrupt_type=interrupt_type,
            priority=priority,
            timestamp=datetime.now(),
            source=source,
            data=data,
            metadata=metadata or {},
            processed=False,
            response_time=None,
            handler_result=None
        )
        
        # Check if queue is full
        if self.interrupt_queue.qsize() >= self.max_queue_size:
            logger.warning("Interrupt queue is full, dropping oldest interrupt")
            try:
                self.interrupt_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        
        # Add to queue
        await self.interrupt_queue.put(interrupt_event)
        
        # Update watcher trigger count
        await self._update_watcher_triggers(interrupt_type)
        
        return {
            'success': True,
            'interrupt_id': interrupt_event.id,
            'interrupt_type': interrupt_type.value,
            'priority': priority.value,
            'queued_at': interrupt_event.timestamp.isoformat()
        }
    
    async def _update_watcher_triggers(self, interrupt_type: InterruptType):
        """Update trigger count for watchers"""
        current_time = datetime.now()
        
        for watcher in self.watchers.values():
            if watcher.interrupt_type == interrupt_type:
                watcher.trigger_count += 1
                watcher.last_triggered = current_time
                watcher.status = InterruptStatus.TRIGGERED
    
    async def create_watcher(self, name: str, interrupt_type: InterruptType,
                           priority: InterruptPriority = InterruptPriority.MEDIUM,
                           handler: Callable = None,
                           configuration: Dict[str, Any] = None,
                           conditions: Dict[str, Any] = None,
                           cooldown_seconds: float = 0.0,
                           max_triggers_per_hour: int = 3600) -> Dict[str, Any]:
        """Create a new interrupt watcher"""
        
        watcher = InterruptWatcher(
            id=uuid.uuid4().hex[:8],
            name=name,
            interrupt_type=interrupt_type,
            priority=priority,
            status=InterruptStatus.ACTIVE,
            created_at=datetime.now(),
            last_triggered=None,
            trigger_count=0,
            configuration=configuration or {},
            handler=handler,
            conditions=conditions or {},
            cooldown_seconds=cooldown_seconds,
            max_triggers_per_hour=max_triggers_per_hour,
            enabled=True
        )
        
        self.watchers[watcher.id] = watcher
        self.metrics.total_watchers += 1
        self.metrics.active_watchers += 1
        
        # Special setup for file watchers
        if interrupt_type == InterruptType.FILE_CHANGE:
            await self._setup_file_watcher(watcher)
        
        logger.info(f"Created watcher: {name} ({watcher.id})")
        
        return {
            'success': True,
            'watcher_id': watcher.id,
            'name': name,
            'interrupt_type': interrupt_type.value,
            'priority': priority.value
        }
    
    async def _setup_file_watcher(self, watcher: InterruptWatcher):
        """Setup file system watching for a file watcher"""
        watch_path = watcher.configuration.get('path', '/tmp')
        
        if watch_path not in self.watched_paths:
            self.fs_observer.schedule(
                self.file_system_watcher,
                watch_path,
                recursive=watcher.configuration.get('recursive', False)
            )
            self.watched_paths.add(watch_path)
            logger.info(f"Started watching path: {watch_path}")
    
    async def _create_default_watchers(self):
        """Create default watchers"""
        default_watchers = [
            {
                'name': 'System CPU Monitor',
                'interrupt_type': InterruptType.CPU_SPIKE,
                'priority': InterruptPriority.HIGH,
                'configuration': {'threshold': 80.0}
            },
            {
                'name': 'System Memory Monitor',
                'interrupt_type': InterruptType.MEMORY_PRESSURE,
                'priority': InterruptPriority.HIGH,
                'configuration': {'threshold': 80.0}
            },
            {
                'name': 'Emotional State Monitor',
                'interrupt_type': InterruptType.EMOTIONAL_SHIFT,
                'priority': InterruptPriority.MEDIUM,
                'configuration': {'sensitivity': 0.5}
            },
            {
                'name': 'Error Monitor',
                'interrupt_type': InterruptType.ERROR_OCCURRED,
                'priority': InterruptPriority.HIGH,
                'configuration': {'auto_response': True}
            }
        ]
        
        for watcher_config in default_watchers:
            await self.create_watcher(**watcher_config)
    
    def _register_default_handlers(self):
        """Register default interrupt handlers"""
        
        async def handle_file_change(interrupt_event: InterruptEvent):
            """Handle file change interrupts"""
            data = interrupt_event.data
            action = data.get('action', 'unknown')
            path = data.get('src_path', 'unknown')
            
            logger.info(f"File {action}: {path}")
            
            # Trigger exploration if it's a new file
            if action == 'created':
                # Could trigger exploration task
                pass
            
            return {'handled': True, 'action_taken': f'logged_{action}'}
        
        async def handle_cpu_spike(interrupt_event: InterruptEvent):
            """Handle CPU spike interrupts"""
            cpu_percent = interrupt_event.data.get('cpu_percent', 0)
            
            logger.warning(f"CPU spike detected: {cpu_percent}%")
            
            # Could trigger optimization tasks
            return {'handled': True, 'action_taken': 'optimization_triggered'}
        
        async def handle_memory_pressure(interrupt_event: InterruptEvent):
            """Handle memory pressure interrupts"""
            memory_percent = interrupt_event.data.get('memory_percent', 0)
            
            logger.warning(f"Memory pressure detected: {memory_percent}%")
            
            # Could trigger memory cleanup
            return {'handled': True, 'action_taken': 'cleanup_triggered'}
        
        async def handle_emotional_shift(interrupt_event: InterruptEvent):
            """Handle emotional state changes"""
            data = interrupt_event.data
            
            if data.get('type') == 'instability':
                logger.warning("Emotional instability detected")
                # Could trigger calming activities
                return {'handled': True, 'action_taken': 'stabilization_triggered'}
            else:
                old_state = data.get('old_state', 'unknown')
                new_state = data.get('new_state', 'unknown')
                logger.info(f"Emotional shift: {old_state} -> {new_state}")
                return {'handled': True, 'action_taken': 'state_logged'}
        
        async def handle_time_elapsed(interrupt_event: InterruptEvent):
            """Handle time-based interrupts"""
            timer_name = interrupt_event.data.get('timer_name', 'unknown')
            
            logger.info(f"Timer triggered: {timer_name}")
            
            # Could trigger scheduled tasks
            return {'handled': True, 'action_taken': 'timer_processed'}
        
        async def handle_pattern_detected(interrupt_event: InterruptEvent):
            """Handle pattern detection interrupts"""
            pattern_name = interrupt_event.data.get('pattern_name', 'unknown')
            
            logger.info(f"Pattern detected: {pattern_name}")
            
            # Could trigger analysis or prediction tasks
            return {'handled': True, 'action_taken': 'pattern_analyzed'}
        
        async def handle_error_occurred(interrupt_event: InterruptEvent):
            """Handle error interrupts"""
            error_info = interrupt_event.data
            
            logger.error(f"Error interrupt: {error_info}")
            
            # Could trigger healing tasks
            return {'handled': True, 'action_taken': 'error_logged'}
        
        # Register handlers
        self.default_handlers = {
            InterruptType.FILE_CHANGE: handle_file_change,
            InterruptType.CPU_SPIKE: handle_cpu_spike,
            InterruptType.MEMORY_PRESSURE: handle_memory_pressure,
            InterruptType.EMOTIONAL_SHIFT: handle_emotional_shift,
            InterruptType.TIME_ELAPSED: handle_time_elapsed,
            InterruptType.PATTERN_DETECTED: handle_pattern_detected,
            InterruptType.ERROR_OCCURRED: handle_error_occurred
        }
    
    # Public interface methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get interrupt manager status"""
        return {
            'manager_id': self.manager_id,
            'is_running': self.is_running,
            'metrics': asdict(self.metrics),
            'active_watchers': len([w for w in self.watchers.values() if w.enabled]),
            'total_watchers': len(self.watchers),
            'queue_size': self.interrupt_queue.qsize(),
            'recent_interrupts': len(self.recent_interrupts)
        }
    
    def get_watchers(self, interrupt_type: InterruptType = None) -> List[Dict[str, Any]]:
        """Get watchers, optionally filtered by type"""
        watchers = list(self.watchers.values())
        
        if interrupt_type:
            watchers = [w for w in watchers if w.interrupt_type == interrupt_type]
        
        return [asdict(w) for w in watchers]
    
    def get_recent_interrupts(self, limit: int = 50, 
                            interrupt_type: InterruptType = None) -> List[Dict[str, Any]]:
        """Get recent interrupts"""
        interrupts = self.recent_interrupts
        
        if interrupt_type:
            interrupts = [i for i in interrupts if i.interrupt_type == interrupt_type]
        
        # Sort by timestamp (newest first)
        interrupts.sort(key=lambda i: i.timestamp, reverse=True)
        
        return [asdict(i) for i in interrupts[:limit]]
    
    async def enable_watcher(self, watcher_id: str) -> Dict[str, Any]:
        """Enable a watcher"""
        if watcher_id not in self.watchers:
            return {'success': False, 'error': f'Watcher not found: {watcher_id}'}
        
        watcher = self.watchers[watcher_id]
        watcher.enabled = True
        watcher.status = InterruptStatus.ACTIVE
        
        return {'success': True, 'watcher_id': watcher_id, 'enabled': True}
    
    async def disable_watcher(self, watcher_id: str) -> Dict[str, Any]:
        """Disable a watcher"""
        if watcher_id not in self.watchers:
            return {'success': False, 'error': f'Watcher not found: {watcher_id}'}
        
        watcher = self.watchers[watcher_id]
        watcher.enabled = False
        watcher.status = InterruptStatus.DISABLED
        
        return {'success': True, 'watcher_id': watcher_id, 'enabled': False}
    
    async def add_file_watch(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """Add a file system watch"""
        return await self.create_watcher(
            name=f"File Watch: {path}",
            interrupt_type=InterruptType.FILE_CHANGE,
            priority=InterruptPriority.MEDIUM,
            configuration={'path': path, 'recursive': recursive}
        )
    
    def add_timer(self, name: str, duration_seconds: float, 
                  priority: InterruptPriority = InterruptPriority.MEDIUM,
                  metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a timer interrupt"""
        self.time_watcher.add_timer(name, duration_seconds, priority, metadata)
        return {
            'success': True,
            'timer_name': name,
            'duration_seconds': duration_seconds,
            'priority': priority.value
        }
    
    def add_pattern_detector(self, pattern_name: str, stream_name: str,
                           detector_func: Callable, 
                           priority: InterruptPriority = InterruptPriority.MEDIUM) -> Dict[str, Any]:
        """Add a pattern detector"""
        self.pattern_detector.register_pattern(pattern_name, stream_name, detector_func, priority)
        return {
            'success': True,
            'pattern_name': pattern_name,
            'stream_name': stream_name,
            'priority': priority.value
        }
    
    def add_data_point(self, stream_name: str, data_point: Any) -> Dict[str, Any]:
        """Add a data point to a stream for pattern detection"""
        self.pattern_detector.add_data_stream(stream_name, data_point)
        return {
            'success': True,
            'stream_name': stream_name,
            'data_point_added': True
        }
    
    async def check_emotional_state(self, state: str, intensity: float) -> Dict[str, Any]:
        """Check emotional state for changes"""
        await self.emotional_watcher.check_emotional_state(state, intensity)
        return {
            'success': True,
            'state': state,
            'intensity': intensity,
            'checked_at': datetime.now().isoformat()
        }
    
    # Persistence methods
    
    async def _save_persistent_state(self):
        """Save interrupt manager state to disk"""
        state_data = {
            'manager_id': self.manager_id,
            'metrics': asdict(self.metrics),
            'watchers': {k: asdict(v) for k, v in self.watchers.items()},
            'watched_paths': list(self.watched_paths),
            'saved_at': datetime.now().isoformat()
        }
        
        state_file = self.persistence_path / 'interrupt_state.json'
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2, default=str)
    
    async def _load_persistent_state(self):
        """Load interrupt manager state from disk"""
        state_file = self.persistence_path / 'interrupt_state.json'
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Restore metrics
                if 'metrics' in state_data:
                    self.metrics = WatcherMetrics(**state_data['metrics'])
                
                # Restore watchers
                if 'watchers' in state_data:
                    for watcher_id, watcher_data in state_data['watchers'].items():
                        # Convert datetime strings back to datetime objects
                        watcher_data['created_at'] = datetime.fromisoformat(watcher_data['created_at'])
                        if watcher_data['last_triggered']:
                            watcher_data['last_triggered'] = datetime.fromisoformat(watcher_data['last_triggered'])
                        
                        # Convert enums
                        watcher_data['interrupt_type'] = InterruptType(watcher_data['interrupt_type'])
                        watcher_data['priority'] = InterruptPriority(watcher_data['priority'])
                        watcher_data['status'] = InterruptStatus(watcher_data['status'])
                        
                        # Handler will be None (can't serialize functions)
                        watcher_data['handler'] = None
                        
                        self.watchers[watcher_id] = InterruptWatcher(**watcher_data)
                
                # Restore watched paths
                if 'watched_paths' in state_data:
                    self.watched_paths = set(state_data['watched_paths'])
                
                logger.info(f"Loaded persistent state for interrupt manager {self.manager_id}")
                
            except Exception as e:
                logger.error(f"Error loading persistent state: {str(e)}")

# Global interrupt manager instance
interrupt_manager = InterruptManager()

# Convenience functions
async def start_interrupt_watchers() -> Dict[str, Any]:
    """Start the interrupt manager"""
    return await interrupt_manager.start()

async def stop_interrupt_watchers() -> Dict[str, Any]:
    """Stop the interrupt manager"""
    return await interrupt_manager.stop()

def get_interrupt_status() -> Dict[str, Any]:
    """Get interrupt manager status"""
    return interrupt_manager.get_status()

async def trigger_interrupt(interrupt_type: InterruptType, source: str,
                          data: Dict[str, Any], priority: InterruptPriority = InterruptPriority.MEDIUM) -> Dict[str, Any]:
    """Trigger an interrupt"""
    return await interrupt_manager.trigger_interrupt(interrupt_type, source, data, priority)

async def create_interrupt_watcher(name: str, interrupt_type: InterruptType,
                                 priority: InterruptPriority = InterruptPriority.MEDIUM,
                                 **kwargs) -> Dict[str, Any]:
    """Create an interrupt watcher"""
    return await interrupt_manager.create_watcher(name, interrupt_type, priority, **kwargs)

async def add_file_watch(path: str, recursive: bool = False) -> Dict[str, Any]:
    """Add file system watching"""
    return await interrupt_manager.add_file_watch(path, recursive)

def add_timer_interrupt(name: str, duration_seconds: float, 
                       priority: InterruptPriority = InterruptPriority.MEDIUM) -> Dict[str, Any]:
    """Add a timer interrupt"""
    return interrupt_manager.add_timer(name, duration_seconds, priority)

async def check_emotional_state(state: str, intensity: float) -> Dict[str, Any]:
    """Check emotional state"""
    return await interrupt_manager.check_emotional_state(state, intensity)

def get_recent_interrupts(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent interrupts"""
    return interrupt_manager.get_recent_interrupts(limit)

