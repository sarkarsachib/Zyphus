"""
Unlimited Context Integration System
Comprehensive integration of unlimited context management with overload handling

Author: Sachib
Version: 1.0.0
Date: January 10, 2025

This system integrates all components of the unlimited context management system
with sophisticated overload handling, creating a seamless and intelligent
context management solution for DEVmind.
"""

import asyncio
import json
import time
import logging
import threading
import weakref
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict, deque

# Import our custom components
from .unlimited_context_manager import UnlimitedContextManager, ContextEntry, ContextType, MemoryPriority
from .type_entropy_limiter import TypeEntropyLimiter, ResourceType, OverloadLevel, ThoughtGraphMetrics
from .context_prioritization_engine import ContextPrioritizationEngine, ContextCategory, PriorityLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemState(Enum):
    """Overall system state"""
    OPTIMAL = "optimal"                    # System running optimally
    STABLE = "stable"                     # System stable but monitoring
    STRESSED = "stressed"                 # System under stress, active management
    OVERLOADED = "overloaded"            # System overloaded, aggressive intervention
    CRITICAL = "critical"                # Critical state, emergency protocols
    RECOVERY = "recovery"                # Recovering from critical state

class IntegrationMode(Enum):
    """Integration operation modes"""
    PASSIVE = "passive"                   # Passive monitoring only
    ACTIVE = "active"                    # Active management and optimization
    AGGRESSIVE = "aggressive"            # Aggressive optimization and intervention
    EMERGENCY = "emergency"              # Emergency mode with maximum intervention

@dataclass
class SystemMetrics:
    """Comprehensive system metrics"""
    timestamp: datetime
    memory_usage_percent: float
    cpu_usage_percent: float
    context_count: int
    working_memory_count: int
    compressed_memory_count: int
    archived_memory_count: int
    average_priority_score: float
    system_state: SystemState
    integration_mode: IntegrationMode
    overload_events_1h: int
    pruning_events_1h: int
    offloading_events_1h: int

@dataclass
class PerformanceTarget:
    """Performance targets for the system"""
    max_memory_usage: float = 0.85        # Maximum memory usage (85%)
    max_cpu_usage: float = 0.90          # Maximum CPU usage (90%)
    max_working_memory: int = 1000       # Maximum working memory items
    target_response_time: float = 0.1    # Target response time (100ms)
    min_priority_threshold: float = 0.3  # Minimum priority for retention

class UnlimitedContextIntegration:
    """
    Comprehensive integration system for unlimited context management
    
    This system orchestrates all components of the unlimited context management
    system, providing intelligent coordination between context storage, overload
    handling, and prioritization to achieve truly unlimited context capabilities
    while maintaining optimal performance.
    """
    
    def __init__(self, 
                 emotion_system=None,
                 thought_system=None,
                 performance_targets: Optional[PerformanceTarget] = None):
        """
        Initialize the unlimited context integration system
        
        Args:
            emotion_system: Reference to the emotion system
            thought_system: Reference to the thought processing system
            performance_targets: Performance targets for the system
        """
        self.emotion_system = weakref.ref(emotion_system) if emotion_system else None
        self.thought_system = weakref.ref(thought_system) if thought_system else None
        self.performance_targets = performance_targets or PerformanceTarget()
        
        # Core components
        self.context_manager = UnlimitedContextManager()
        self.entropy_limiter = TypeEntropyLimiter(
            context_manager=self.context_manager,
            emotion_system=emotion_system,
            thought_system=thought_system
        )
        self.prioritization_engine = ContextPrioritizationEngine(
            context_manager=self.context_manager,
            emotion_system=emotion_system,
            max_working_memory=self.performance_targets.max_working_memory,
            target_memory_usage=self.performance_targets.max_memory_usage
        )
        
        # System state management
        self.current_state = SystemState.OPTIMAL
        self.integration_mode = IntegrationMode.ACTIVE
        self.state_history: List[Tuple[datetime, SystemState]] = []
        self.mode_history: List[Tuple[datetime, IntegrationMode]] = []
        
        # Performance tracking
        self.metrics_history: deque = deque(maxlen=1000)  # Keep last 1000 metrics
        self.performance_stats: Dict[str, Any] = {
            "total_contexts_processed": 0,
            "total_optimizations": 0,
            "total_state_changes": 0,
            "average_response_time": 0.0,
            "uptime_start": datetime.now()
        }
        
        # Event handling
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
        # Threading and async
        self.lock = threading.Lock()
        self.active = False
        self.background_tasks: List[asyncio.Task] = []
        
        # Integration callbacks
        self._setup_integration_callbacks()
        
        logger.info("UnlimitedContextIntegration initialized")
    
    def _setup_integration_callbacks(self):
        """Setup callbacks between components for seamless integration"""
        # Context manager callbacks
        self.context_manager.register_callback(
            "context_added", 
            self._on_context_added
        )
        self.context_manager.register_callback(
            "context_accessed", 
            self._on_context_accessed
        )
        self.context_manager.register_callback(
            "memory_pressure", 
            self._on_memory_pressure
        )
        
        # Entropy limiter callbacks
        self.entropy_limiter.resource_monitor.register_callback(
            ResourceType.MEMORY,
            self._on_memory_overload
        )
        self.entropy_limiter.resource_monitor.register_callback(
            ResourceType.CPU,
            self._on_cpu_overload
        )
        
        logger.info("Integration callbacks setup complete")
    
    async def start(self):
        """Start the unlimited context integration system"""
        if self.active:
            return
        
        self.active = True
        
        # Start core components
        await self.context_manager.start()
        self.entropy_limiter.start()
        self.prioritization_engine.start()
        
        # Start background tasks
        await self._start_background_tasks()
        
        # Start event processing
        asyncio.create_task(self._process_events())
        
        logger.info("UnlimitedContextIntegration started")
    
    async def stop(self):
        """Stop the unlimited context integration system"""
        if not self.active:
            return
        
        self.active = False
        
        # Stop background tasks
        for task in self.background_tasks:
            task.cancel()
        
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Stop core components
        await self.context_manager.stop()
        self.entropy_limiter.stop()
        self.prioritization_engine.stop()
        
        logger.info("UnlimitedContextIntegration stopped")
    
    async def _start_background_tasks(self):
        """Start background monitoring and optimization tasks"""
        async def system_monitoring_task():
            """Monitor system state and performance"""
            while self.active:
                try:
                    await self._update_system_metrics()
                    await self._evaluate_system_state()
                    await asyncio.sleep(5)  # Monitor every 5 seconds
                except Exception as e:
                    logger.error(f"Error in system monitoring: {e}")
                    await asyncio.sleep(5)
        
        async def optimization_task():
            """Perform periodic optimization"""
            while self.active:
                try:
                    await self._perform_optimization()
                    await asyncio.sleep(60)  # Optimize every minute
                except Exception as e:
                    logger.error(f"Error in optimization: {e}")
                    await asyncio.sleep(60)
        
        async def health_check_task():
            """Perform health checks and recovery"""
            while self.active:
                try:
                    await self._perform_health_check()
                    await asyncio.sleep(30)  # Health check every 30 seconds
                except Exception as e:
                    logger.error(f"Error in health check: {e}")
                    await asyncio.sleep(30)
        
        async def metrics_cleanup_task():
            """Clean up old metrics and logs"""
            while self.active:
                try:
                    await self._cleanup_old_metrics()
                    await asyncio.sleep(3600)  # Cleanup every hour
                except Exception as e:
                    logger.error(f"Error in metrics cleanup: {e}")
                    await asyncio.sleep(3600)
        
        # Start all background tasks
        self.background_tasks = [
            asyncio.create_task(system_monitoring_task()),
            asyncio.create_task(optimization_task()),
            asyncio.create_task(health_check_task()),
            asyncio.create_task(metrics_cleanup_task())
        ]
        
        # Start component background tasks
        await self.context_manager.start_background_optimization()
        await self.entropy_limiter.start_background_optimization()
        await self.prioritization_engine.start_background_optimization()
        
        logger.info("Background tasks started")
    
    async def _update_system_metrics(self):
        """Update comprehensive system metrics"""
        # Get metrics from all components
        context_stats = self.context_manager.get_system_stats()
        entropy_stats = self.entropy_limiter.get_system_status()
        priority_stats = self.prioritization_engine.get_prioritization_stats()
        
        # Calculate derived metrics
        total_contexts = (
            context_stats["working_memory"]["entries"] +
            context_stats["compressed_memory"]["entries"] +
            context_stats["archived_memory"]["entries"]
        )
        
        # Get resource usage
        memory_usage = 0.0
        cpu_usage = 0.0
        if entropy_stats["resource_monitor"]["monitoring_active"]:
            resources = entropy_stats["resource_monitor"]["resources"]
            memory_usage = resources.get("memory", {}).get("current_value", 0.0)
            cpu_usage = resources.get("cpu", {}).get("current_value", 0.0)
        
        # Create metrics object
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            memory_usage_percent=memory_usage * 100,
            cpu_usage_percent=cpu_usage * 100,
            context_count=total_contexts,
            working_memory_count=context_stats["working_memory"]["entries"],
            compressed_memory_count=context_stats["compressed_memory"]["entries"],
            archived_memory_count=context_stats["archived_memory"]["entries"],
            average_priority_score=priority_stats.get("average_priority_score", 0.0),
            system_state=self.current_state,
            integration_mode=self.integration_mode,
            overload_events_1h=entropy_stats.get("recent_overload_events", 0),
            pruning_events_1h=priority_stats.get("recent_prunings_1h", 0),
            offloading_events_1h=priority_stats.get("recent_offloads_1h", 0)
        )
        
        # Store metrics
        self.metrics_history.append(metrics)
        
        # Update performance stats
        self.performance_stats["total_contexts_processed"] = total_contexts
    
    async def _evaluate_system_state(self):
        """Evaluate and update system state based on current metrics"""
        if not self.metrics_history:
            return
        
        current_metrics = self.metrics_history[-1]
        previous_state = self.current_state
        
        # Determine new state based on metrics
        new_state = self._calculate_system_state(current_metrics)
        
        if new_state != self.current_state:
            logger.info(f"System state change: {self.current_state.value} -> {new_state.value}")
            self.current_state = new_state
            self.state_history.append((datetime.now(), new_state))
            self.performance_stats["total_state_changes"] += 1
            
            # Adjust integration mode based on state
            await self._adjust_integration_mode(new_state, previous_state)
            
            # Emit state change event
            await self._emit_event("state_changed", {
                "previous_state": previous_state.value,
                "new_state": new_state.value,
                "metrics": asdict(current_metrics)
            })
    
    def _calculate_system_state(self, metrics: SystemMetrics) -> SystemState:
        """Calculate system state based on metrics"""
        # Critical conditions
        if (metrics.memory_usage_percent > 95 or 
            metrics.cpu_usage_percent > 98 or
            metrics.overload_events_1h > 10):
            return SystemState.CRITICAL
        
        # Overloaded conditions
        if (metrics.memory_usage_percent > 90 or 
            metrics.cpu_usage_percent > 95 or
            metrics.overload_events_1h > 5):
            return SystemState.OVERLOADED
        
        # Stressed conditions
        if (metrics.memory_usage_percent > 85 or 
            metrics.cpu_usage_percent > 90 or
            metrics.working_memory_count > self.performance_targets.max_working_memory * 0.9):
            return SystemState.STRESSED
        
        # Recovery conditions (coming down from higher states)
        if (self.current_state in [SystemState.CRITICAL, SystemState.OVERLOADED] and
            metrics.memory_usage_percent < 80 and
            metrics.cpu_usage_percent < 85):
            return SystemState.RECOVERY
        
        # Stable conditions
        if (metrics.memory_usage_percent > 70 or 
            metrics.cpu_usage_percent > 80):
            return SystemState.STABLE
        
        # Optimal conditions
        return SystemState.OPTIMAL
    
    async def _adjust_integration_mode(self, new_state: SystemState, previous_state: SystemState):
        """Adjust integration mode based on system state"""
        previous_mode = self.integration_mode
        
        # Determine new mode based on state
        if new_state == SystemState.CRITICAL:
            new_mode = IntegrationMode.EMERGENCY
        elif new_state == SystemState.OVERLOADED:
            new_mode = IntegrationMode.AGGRESSIVE
        elif new_state in [SystemState.STRESSED, SystemState.RECOVERY]:
            new_mode = IntegrationMode.ACTIVE
        else:
            new_mode = IntegrationMode.ACTIVE  # Default to active
        
        if new_mode != self.integration_mode:
            logger.info(f"Integration mode change: {self.integration_mode.value} -> {new_mode.value}")
            self.integration_mode = new_mode
            self.mode_history.append((datetime.now(), new_mode))
            
            # Apply mode-specific configurations
            await self._apply_integration_mode(new_mode)
            
            # Emit mode change event
            await self._emit_event("mode_changed", {
                "previous_mode": previous_mode.value,
                "new_mode": new_mode.value,
                "state": new_state.value
            })
    
    async def _apply_integration_mode(self, mode: IntegrationMode):
        """Apply configuration changes for the integration mode"""
        if mode == IntegrationMode.EMERGENCY:
            # Emergency mode: maximum intervention
            self.context_manager.set_compression_threshold(0.3)  # Aggressive compression
            self.prioritization_engine.target_memory_usage = 0.6  # Reduce target usage
            
            # Update entropy limiter thresholds
            self.entropy_limiter.resource_monitor.update_thresholds(
                ResourceType.MEMORY, 0.6, 0.75, 0.85
            )
            
        elif mode == IntegrationMode.AGGRESSIVE:
            # Aggressive mode: active intervention
            self.context_manager.set_compression_threshold(0.5)
            self.prioritization_engine.target_memory_usage = 0.7
            
            self.entropy_limiter.resource_monitor.update_thresholds(
                ResourceType.MEMORY, 0.7, 0.85, 0.95
            )
            
        elif mode == IntegrationMode.ACTIVE:
            # Active mode: normal operation
            self.context_manager.set_compression_threshold(0.7)
            self.prioritization_engine.target_memory_usage = 0.8
            
            # Reset to default thresholds
            self.entropy_limiter.resource_monitor.update_thresholds(
                ResourceType.MEMORY, 0.7, 0.85, 0.95
            )
            
        elif mode == IntegrationMode.PASSIVE:
            # Passive mode: minimal intervention
            self.context_manager.set_compression_threshold(0.9)
            self.prioritization_engine.target_memory_usage = 0.9
        
        logger.info(f"Applied configuration for {mode.value} mode")
    
    async def _perform_optimization(self):
        """Perform system optimization based on current state and mode"""
        if not self.active:
            return
        
        optimization_start = time.time()
        
        try:
            # Get current metrics
            if not self.metrics_history:
                return
            
            current_metrics = self.metrics_history[-1]
            
            # Determine optimization strategy based on state and mode
            if self.current_state in [SystemState.CRITICAL, SystemState.OVERLOADED]:
                await self._perform_emergency_optimization(current_metrics)
            elif self.current_state == SystemState.STRESSED:
                await self._perform_aggressive_optimization(current_metrics)
            elif self.current_state in [SystemState.STABLE, SystemState.RECOVERY]:
                await self._perform_standard_optimization(current_metrics)
            else:
                await self._perform_maintenance_optimization(current_metrics)
            
            # Update performance stats
            optimization_time = time.time() - optimization_start
            self.performance_stats["total_optimizations"] += 1
            
            # Update average response time
            current_avg = self.performance_stats["average_response_time"]
            total_opts = self.performance_stats["total_optimizations"]
            self.performance_stats["average_response_time"] = (
                (current_avg * (total_opts - 1) + optimization_time) / total_opts
            )
            
            logger.debug(f"Optimization completed in {optimization_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Error during optimization: {e}")
    
    async def _perform_emergency_optimization(self, metrics: SystemMetrics):
        """Perform emergency optimization for critical states"""
        logger.warning("Performing emergency optimization")
        
        # Immediate memory relief
        if metrics.memory_usage_percent > 90:
            # Aggressive pruning
            target_items = int(metrics.working_memory_count * 0.3)  # Remove 30%
            pruning_candidates = self.prioritization_engine.identify_pruning_candidates(target_items)
            await asyncio.to_thread(self.prioritization_engine.execute_pruning, pruning_candidates)
            
            # Aggressive offloading
            target_size = int(metrics.working_memory_count * 0.4 * 1024)  # Estimate size
            offload_candidates = self.prioritization_engine.identify_offload_candidates(target_size)
            await asyncio.to_thread(self.prioritization_engine.execute_offloading, offload_candidates)
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Emergency context compression
        await self.context_manager.emergency_compress()
        
        # Inject self-reflection
        self.entropy_limiter.inject_self_reflect("emergency_optimization_triggered")
    
    async def _perform_aggressive_optimization(self, metrics: SystemMetrics):
        """Perform aggressive optimization for overloaded states"""
        logger.info("Performing aggressive optimization")
        
        # Targeted memory optimization
        optimization_result = await asyncio.to_thread(
            self.prioritization_engine.optimize_memory_usage, 
            0.7  # Target 70% usage
        )
        
        # Compress old contexts
        await self.context_manager.compress_old_contexts(hours=1)
        
        # Archive inactive contexts
        await self.context_manager.archive_inactive_contexts(hours=6)
    
    async def _perform_standard_optimization(self, metrics: SystemMetrics):
        """Perform standard optimization for normal operation"""
        logger.debug("Performing standard optimization")
        
        # Regular memory optimization
        if metrics.working_memory_count > self.performance_targets.max_working_memory * 0.8:
            await asyncio.to_thread(self.prioritization_engine.optimize_memory_usage)
        
        # Regular compression and archival
        await self.context_manager.compress_old_contexts(hours=6)
        await self.context_manager.archive_inactive_contexts(hours=24)
    
    async def _perform_maintenance_optimization(self, metrics: SystemMetrics):
        """Perform maintenance optimization for optimal states"""
        logger.debug("Performing maintenance optimization")
        
        # Light maintenance
        await self.context_manager.compress_old_contexts(hours=12)
        await self.context_manager.archive_inactive_contexts(hours=48)
        
        # Optimize thresholds
        await asyncio.to_thread(self.entropy_limiter.optimize_thresholds)
    
    async def _perform_health_check(self):
        """Perform comprehensive health check"""
        health_issues = []
        
        try:
            # Check component health
            if not self.context_manager.active:
                health_issues.append("Context manager not active")
            
            if not self.entropy_limiter.active:
                health_issues.append("Entropy limiter not active")
            
            if not self.prioritization_engine.active:
                health_issues.append("Prioritization engine not active")
            
            # Check metrics freshness
            if self.metrics_history:
                last_metrics = self.metrics_history[-1]
                age = (datetime.now() - last_metrics.timestamp).total_seconds()
                if age > 60:  # Metrics older than 1 minute
                    health_issues.append(f"Metrics stale ({age:.1f}s old)")
            
            # Check for stuck states
            if len(self.state_history) > 1:
                current_state_duration = (datetime.now() - self.state_history[-1][0]).total_seconds()
                if (self.current_state in [SystemState.CRITICAL, SystemState.OVERLOADED] and 
                    current_state_duration > 300):  # 5 minutes
                    health_issues.append(f"Stuck in {self.current_state.value} state for {current_state_duration:.1f}s")
            
            # Check background task health
            dead_tasks = [task for task in self.background_tasks if task.done()]
            if dead_tasks:
                health_issues.append(f"{len(dead_tasks)} background tasks have died")
            
            # Log health status
            if health_issues:
                logger.warning(f"Health check found issues: {health_issues}")
                await self._emit_event("health_issues", {"issues": health_issues})
            else:
                logger.debug("Health check passed")
            
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            health_issues.append(f"Health check error: {e}")
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics and logs"""
        try:
            # Clean up state history (keep last 100 entries)
            if len(self.state_history) > 100:
                self.state_history = self.state_history[-100:]
            
            # Clean up mode history (keep last 100 entries)
            if len(self.mode_history) > 100:
                self.mode_history = self.mode_history[-100:]
            
            # Metrics history is already limited by deque maxlen
            
            logger.debug("Metrics cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during metrics cleanup: {e}")
    
    async def _process_events(self):
        """Process events from the event queue"""
        while self.active:
            try:
                # Wait for events with timeout
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                event_type = event.get("type")
                event_data = event.get("data", {})
                
                # Process the event
                handlers = self.event_handlers.get(event_type, [])
                for handler in handlers:
                    try:
                        await handler(event_data)
                    except Exception as e:
                        logger.error(f"Error in event handler for {event_type}: {e}")
                
                # Mark event as done
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                # No events to process, continue
                continue
            except Exception as e:
                logger.error(f"Error processing events: {e}")
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to the event queue"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await self.event_queue.put(event)
        except Exception as e:
            logger.error(f"Failed to emit event {event_type}: {e}")
    
    # Callback methods for component integration
    def _on_context_added(self, context_id: str, context_entry: ContextEntry):
        """Handle context added event"""
        # Register with prioritization engine
        self.prioritization_engine.register_context_access(context_id)
        
        # Categorize the context
        category = self._determine_context_category(context_entry)
        self.prioritization_engine.categorize_context(context_id, category)
        
        # Add to context graph
        self.prioritization_engine.context_graph.add_node(context_id, {
            "type": context_entry.context_type.value,
            "priority": context_entry.priority.value,
            "timestamp": context_entry.timestamp.isoformat()
        })
        
        logger.debug(f"Integrated new context: {context_id}")
    
    def _on_context_accessed(self, context_id: str):
        """Handle context accessed event"""
        # Register access with prioritization engine
        self.prioritization_engine.register_context_access(context_id)
        
        # Update thought graph metrics if this is a thought-related context
        if self.thought_system and self.thought_system():
            thought_sys = self.thought_system()
            if hasattr(thought_sys, 'get_thought_metrics'):
                metrics = thought_sys.get_thought_metrics()
                if metrics:
                    self.entropy_limiter.update_thought_graph_metrics(metrics)
    
    def _on_memory_pressure(self, pressure_level: float):
        """Handle memory pressure event"""
        logger.info(f"Memory pressure detected: {pressure_level:.2f}")
        
        # Trigger optimization based on pressure level
        if pressure_level > 0.8:
            asyncio.create_task(self._perform_aggressive_optimization(self.metrics_history[-1] if self.metrics_history else None))
        elif pressure_level > 0.6:
            asyncio.create_task(self._perform_standard_optimization(self.metrics_history[-1] if self.metrics_history else None))
    
    def _on_memory_overload(self, metric, overload_level: OverloadLevel):
        """Handle memory overload event"""
        logger.warning(f"Memory overload: {overload_level.name}")
        
        # Trigger immediate optimization
        if overload_level in [OverloadLevel.SEVERE, OverloadLevel.CRITICAL]:
            asyncio.create_task(self._perform_emergency_optimization(self.metrics_history[-1] if self.metrics_history else None))
    
    def _on_cpu_overload(self, metric, overload_level: OverloadLevel):
        """Handle CPU overload event"""
        logger.warning(f"CPU overload: {overload_level.name}")
        
        # Reduce processing intensity
        if overload_level in [OverloadLevel.SEVERE, OverloadLevel.CRITICAL]:
            # Throttle background tasks
            for task in self.background_tasks:
                if hasattr(task, '_throttle'):
                    task._throttle = True
    
    def _determine_context_category(self, context_entry: ContextEntry) -> ContextCategory:
        """Determine the category for a context entry"""
        # Simple categorization logic based on context type and content
        if context_entry.context_type == ContextType.LONG_TERM_MEMORY:
            return ContextCategory.CORE_MEMORY
        elif context_entry.context_type == ContextType.ACTIVE_TASK_CONTEXT:
            return ContextCategory.ACTIVE_TASK
        elif abs(context_entry.emotional_weight) > 0.7:
            return ContextCategory.EMOTIONAL_SIGNIFICANT
        elif context_entry.context_type == ContextType.INTERNAL_THOUGHT_LOGS:
            return ContextCategory.LEARNING_PATTERN
        elif context_entry.context_type == ContextType.EXTERNAL_INTERACTION_LOGS:
            return ContextCategory.RELATIONSHIP
        elif context_entry.context_type == ContextType.SKILL_KNOWLEDGE:
            return ContextCategory.SKILL_KNOWLEDGE
        elif context_entry.context_type == ContextType.REFERENCE_INFORMATION:
            return ContextCategory.REFERENCE_DATA
        else:
            return ContextCategory.TEMPORARY_WORKING
    
    # Public API methods
    async def add_context(self, 
                         content: Any, 
                         context_type: ContextType,
                         priority: MemoryPriority = MemoryPriority.MEDIUM,
                         emotional_weight: float = 0.0,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a new context to the system"""
        context_id = await self.context_manager.add_context(
            content, context_type, priority, emotional_weight, metadata
        )
        
        # The _on_context_added callback will handle integration
        
        return context_id
    
    async def get_context(self, context_id: str) -> Optional[ContextEntry]:
        """Get a context by ID"""
        context = await self.context_manager.get_context(context_id)
        
        if context:
            # The _on_context_accessed callback will handle access tracking
            pass
        
        return context
    
    async def search_contexts(self, 
                            query: str, 
                            limit: int = 10,
                            context_types: Optional[List[ContextType]] = None,
                            min_priority: Optional[MemoryPriority] = None) -> List[ContextEntry]:
        """Search for contexts"""
        return await self.context_manager.search_contexts(query, limit, context_types, min_priority)
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler"""
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered event handler for {event_type}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "active": self.active,
            "current_state": self.current_state.value,
            "integration_mode": self.integration_mode.value,
            "performance_stats": dict(self.performance_stats),
            "component_status": {
                "context_manager": self.context_manager.get_system_stats(),
                "entropy_limiter": self.entropy_limiter.get_system_status(),
                "prioritization_engine": self.prioritization_engine.get_prioritization_stats()
            }
        }
        
        # Add recent metrics
        if self.metrics_history:
            status["latest_metrics"] = asdict(self.metrics_history[-1])
        
        # Add uptime
        uptime = datetime.now() - self.performance_stats["uptime_start"]
        status["uptime_seconds"] = uptime.total_seconds()
        
        return status
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance report for the specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter metrics for the time period
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {"error": "No metrics available for the specified period"}
        
        # Calculate statistics
        memory_usage = [m.memory_usage_percent for m in recent_metrics]
        cpu_usage = [m.cpu_usage_percent for m in recent_metrics]
        context_counts = [m.context_count for m in recent_metrics]
        
        report = {
            "time_period_hours": hours,
            "total_metrics": len(recent_metrics),
            "memory_usage": {
                "average": np.mean(memory_usage),
                "max": np.max(memory_usage),
                "min": np.min(memory_usage),
                "std": np.std(memory_usage)
            },
            "cpu_usage": {
                "average": np.mean(cpu_usage),
                "max": np.max(cpu_usage),
                "min": np.min(cpu_usage),
                "std": np.std(cpu_usage)
            },
            "context_growth": {
                "start_count": recent_metrics[0].context_count,
                "end_count": recent_metrics[-1].context_count,
                "growth": recent_metrics[-1].context_count - recent_metrics[0].context_count,
                "average_count": np.mean(context_counts)
            },
            "state_changes": len([s for s in self.state_history if s[0] > cutoff_time]),
            "mode_changes": len([m for m in self.mode_history if m[0] > cutoff_time])
        }
        
        return report

# Example usage and testing
if __name__ == "__main__":
    async def test_unlimited_context_integration():
        """Test the unlimited context integration system"""
        integration = UnlimitedContextIntegration()
        
        # Start the system
        await integration.start()
        
        # Add some test contexts
        context_ids = []
        for i in range(10):
            context_id = await integration.add_context(
                content=f"Test context {i}",
                context_type=ContextType.TEMPORARY_WORKING,
                priority=Priority.MEDIUM,
                emotional_weight=0.1 * i
            )
            context_ids.append(context_id)
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Get system status
        status = integration.get_system_status()
        print(f"System status: {json.dumps(status, indent=2, default=str)}")
        
        # Get performance report
        report = integration.get_performance_report(hours=1)
        print(f"Performance report: {json.dumps(report, indent=2, default=str)}")
        
        # Search for contexts
        results = await integration.search_contexts("Test context")
        print(f"Search results: {len(results)} contexts found")
        
        # Shutdown
        await integration.stop()
    
    # Run the test
    asyncio.run(test_unlimited_context_integration())

