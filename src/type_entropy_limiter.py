"""
TypeEntropyLimiter - Dynamic Overload Handler and Resource Monitoring
Advanced overload detection and intelligent response system for DEVmind

Author: Sachib
Version: 1.0.0
Date: January 10, 2025

This system implements sophisticated overload detection and response mechanisms
that prevent system instability while maintaining optimal performance through
intelligent resource management and entropy control.
"""

import asyncio
import json
import time
import logging
import threading
import psutil
import gc
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict, deque
import weakref
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OverloadLevel(Enum):
    """Overload severity levels"""
    NORMAL = 0          # System operating normally
    SOFT_WARNING = 1    # Approaching limits, preventive measures
    MODERATE = 2        # Moderate overload, active management needed
    SEVERE = 3          # Severe overload, aggressive intervention
    CRITICAL = 4        # Critical overload, emergency protocols

class ResourceType(Enum):
    """Types of resources being monitored"""
    MEMORY = "memory"
    CPU = "cpu"
    THOUGHT_DEPTH = "thought_depth"
    RECURSION_DEPTH = "recursion_depth"
    EMOTION_VOLATILITY = "emotion_volatility"
    CONTEXT_SIZE = "context_size"
    NETWORK_IO = "network_io"
    DISK_IO = "disk_io"

class InterventionType(Enum):
    """Types of interventions available"""
    THROTTLE = "throttle"                    # Slow down processing
    COMPRESS = "compress"                    # Compress memory/context
    PRUNE = "prune"                         # Remove low-priority items
    ARCHIVE = "archive"                     # Move to cold storage
    REDIRECT = "redirect"                   # Redirect processing
    EMERGENCY_STOP = "emergency_stop"       # Stop dangerous operations
    CREATOR_ALERT = "creator_alert"         # Alert the creator
    SYSTEM_RESTART = "system_restart"       # Restart components

@dataclass
class ResourceMetrics:
    """Resource usage metrics"""
    resource_type: ResourceType
    current_value: float
    threshold_soft: float
    threshold_hard: float
    threshold_critical: float
    trend: float  # Rate of change
    timestamp: datetime
    
    def get_overload_level(self) -> OverloadLevel:
        """Determine overload level based on current value"""
        if self.current_value >= self.threshold_critical:
            return OverloadLevel.CRITICAL
        elif self.current_value >= self.threshold_hard:
            return OverloadLevel.SEVERE
        elif self.current_value >= self.threshold_soft:
            return OverloadLevel.MODERATE
        elif self.current_value >= self.threshold_soft * 0.8:
            return OverloadLevel.SOFT_WARNING
        else:
            return OverloadLevel.NORMAL

@dataclass
class OverloadEvent:
    """Record of an overload event and response"""
    timestamp: datetime
    resource_type: ResourceType
    overload_level: OverloadLevel
    trigger_value: float
    intervention_type: InterventionType
    intervention_success: bool
    recovery_time: Optional[float]
    metadata: Dict[str, Any]

@dataclass
class ThoughtGraphMetrics:
    """Metrics for thought graph complexity"""
    node_count: int
    edge_count: int
    max_depth: int
    recursion_loops: int
    complexity_score: float
    entropy_level: float
    
    def calculate_overload_risk(self) -> float:
        """Calculate risk of thought graph overload"""
        # Normalize metrics
        node_factor = min(1.0, self.node_count / 1000.0)
        depth_factor = min(1.0, self.max_depth / 20.0)
        recursion_factor = min(1.0, self.recursion_loops / 5.0)
        complexity_factor = min(1.0, self.complexity_score / 100.0)
        entropy_factor = min(1.0, self.entropy_level / 1.0)
        
        # Weighted risk calculation
        risk = (
            node_factor * 0.2 +
            depth_factor * 0.3 +
            recursion_factor * 0.3 +
            complexity_factor * 0.1 +
            entropy_factor * 0.1
        )
        
        return min(1.0, risk)

class ResourceMonitor:
    """Advanced resource monitoring system"""
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.monitoring_interval = monitoring_interval
        self.metrics_history: Dict[ResourceType, deque] = defaultdict(lambda: deque(maxlen=100))
        self.current_metrics: Dict[ResourceType, ResourceMetrics] = {}
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.callbacks: Dict[ResourceType, List[Callable]] = defaultdict(list)
        
        # Resource thresholds (can be dynamically adjusted)
        self.thresholds = {
            ResourceType.MEMORY: (0.7, 0.85, 0.95),  # 70%, 85%, 95%
            ResourceType.CPU: (0.8, 0.9, 0.98),      # 80%, 90%, 98%
            ResourceType.THOUGHT_DEPTH: (15, 25, 40),  # Thought depth levels
            ResourceType.RECURSION_DEPTH: (50, 100, 200),  # Recursion levels
            ResourceType.EMOTION_VOLATILITY: (0.7, 0.85, 0.95),  # Emotion volatility
            ResourceType.CONTEXT_SIZE: (1000, 5000, 10000),  # Context entries
            ResourceType.NETWORK_IO: (100, 500, 1000),  # MB/s
            ResourceType.DISK_IO: (50, 200, 500)  # MB/s
        }
        
        logger.info("ResourceMonitor initialized")
    
    def start_monitoring(self):
        """Start continuous resource monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Resource monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                self._collect_metrics()
                self._analyze_trends()
                self._trigger_callbacks()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_metrics(self):
        """Collect current resource metrics"""
        timestamp = datetime.now()
        
        # Memory metrics
        memory_info = psutil.virtual_memory()
        memory_metric = ResourceMetrics(
            resource_type=ResourceType.MEMORY,
            current_value=memory_info.percent / 100.0,
            threshold_soft=self.thresholds[ResourceType.MEMORY][0],
            threshold_hard=self.thresholds[ResourceType.MEMORY][1],
            threshold_critical=self.thresholds[ResourceType.MEMORY][2],
            trend=self._calculate_trend(ResourceType.MEMORY, memory_info.percent / 100.0),
            timestamp=timestamp
        )
        self.current_metrics[ResourceType.MEMORY] = memory_metric
        self.metrics_history[ResourceType.MEMORY].append(memory_metric)
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_metric = ResourceMetrics(
            resource_type=ResourceType.CPU,
            current_value=cpu_percent / 100.0,
            threshold_soft=self.thresholds[ResourceType.CPU][0],
            threshold_hard=self.thresholds[ResourceType.CPU][1],
            threshold_critical=self.thresholds[ResourceType.CPU][2],
            trend=self._calculate_trend(ResourceType.CPU, cpu_percent / 100.0),
            timestamp=timestamp
        )
        self.current_metrics[ResourceType.CPU] = cpu_metric
        self.metrics_history[ResourceType.CPU].append(cpu_metric)
        
        # Network I/O metrics
        try:
            net_io = psutil.net_io_counters()
            if hasattr(self, '_last_net_io'):
                time_diff = (timestamp - self._last_net_timestamp).total_seconds()
                if time_diff > 0:
                    bytes_sent_rate = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_diff / 1024 / 1024  # MB/s
                    bytes_recv_rate = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_diff / 1024 / 1024  # MB/s
                    total_rate = bytes_sent_rate + bytes_recv_rate
                    
                    network_metric = ResourceMetrics(
                        resource_type=ResourceType.NETWORK_IO,
                        current_value=total_rate,
                        threshold_soft=self.thresholds[ResourceType.NETWORK_IO][0],
                        threshold_hard=self.thresholds[ResourceType.NETWORK_IO][1],
                        threshold_critical=self.thresholds[ResourceType.NETWORK_IO][2],
                        trend=self._calculate_trend(ResourceType.NETWORK_IO, total_rate),
                        timestamp=timestamp
                    )
                    self.current_metrics[ResourceType.NETWORK_IO] = network_metric
                    self.metrics_history[ResourceType.NETWORK_IO].append(network_metric)
            
            self._last_net_io = net_io
            self._last_net_timestamp = timestamp
        except Exception as e:
            logger.warning(f"Failed to collect network metrics: {e}")
        
        # Disk I/O metrics
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io and hasattr(self, '_last_disk_io'):
                time_diff = (timestamp - self._last_disk_timestamp).total_seconds()
                if time_diff > 0:
                    read_rate = (disk_io.read_bytes - self._last_disk_io.read_bytes) / time_diff / 1024 / 1024  # MB/s
                    write_rate = (disk_io.write_bytes - self._last_disk_io.write_bytes) / time_diff / 1024 / 1024  # MB/s
                    total_rate = read_rate + write_rate
                    
                    disk_metric = ResourceMetrics(
                        resource_type=ResourceType.DISK_IO,
                        current_value=total_rate,
                        threshold_soft=self.thresholds[ResourceType.DISK_IO][0],
                        threshold_hard=self.thresholds[ResourceType.DISK_IO][1],
                        threshold_critical=self.thresholds[ResourceType.DISK_IO][2],
                        trend=self._calculate_trend(ResourceType.DISK_IO, total_rate),
                        timestamp=timestamp
                    )
                    self.current_metrics[ResourceType.DISK_IO] = disk_metric
                    self.metrics_history[ResourceType.DISK_IO].append(disk_metric)
            
            if disk_io:
                self._last_disk_io = disk_io
                self._last_disk_timestamp = timestamp
        except Exception as e:
            logger.warning(f"Failed to collect disk metrics: {e}")
    
    def _calculate_trend(self, resource_type: ResourceType, current_value: float) -> float:
        """Calculate trend for a resource metric"""
        history = self.metrics_history[resource_type]
        if len(history) < 2:
            return 0.0
        
        # Calculate trend over last 10 measurements
        recent_values = [m.current_value for m in list(history)[-10:]]
        if len(recent_values) < 2:
            return 0.0
        
        # Simple linear trend calculation
        x = np.arange(len(recent_values))
        y = np.array(recent_values)
        
        try:
            trend = np.polyfit(x, y, 1)[0]  # Slope of linear fit
            return float(trend)
        except:
            return 0.0
    
    def _analyze_trends(self):
        """Analyze resource trends for predictive overload detection"""
        for resource_type, metric in self.current_metrics.items():
            if metric.trend > 0:  # Increasing trend
                # Predict when threshold will be reached
                time_to_threshold = self._predict_threshold_time(metric)
                if time_to_threshold and time_to_threshold < 60:  # Less than 60 seconds
                    logger.warning(f"Predicted {resource_type.value} overload in {time_to_threshold:.1f} seconds")
    
    def _predict_threshold_time(self, metric: ResourceMetrics) -> Optional[float]:
        """Predict time until threshold is reached"""
        if metric.trend <= 0:
            return None
        
        remaining = metric.threshold_soft - metric.current_value
        if remaining <= 0:
            return 0.0
        
        # Simple linear prediction
        time_to_threshold = remaining / metric.trend
        return time_to_threshold if time_to_threshold > 0 else None
    
    def _trigger_callbacks(self):
        """Trigger callbacks for overloaded resources"""
        for resource_type, metric in self.current_metrics.items():
            overload_level = metric.get_overload_level()
            if overload_level != OverloadLevel.NORMAL:
                for callback in self.callbacks[resource_type]:
                    try:
                        callback(metric, overload_level)
                    except Exception as e:
                        logger.error(f"Error in callback for {resource_type.value}: {e}")
    
    def register_callback(self, resource_type: ResourceType, callback: Callable):
        """Register a callback for resource overload events"""
        self.callbacks[resource_type].append(callback)
        logger.info(f"Registered callback for {resource_type.value}")
    
    def update_thresholds(self, resource_type: ResourceType, soft: float, hard: float, critical: float):
        """Update thresholds for a resource type"""
        self.thresholds[resource_type] = (soft, hard, critical)
        logger.info(f"Updated thresholds for {resource_type.value}: {soft}, {hard}, {critical}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        status = {
            "monitoring_active": self.monitoring_active,
            "resources": {}
        }
        
        for resource_type, metric in self.current_metrics.items():
            status["resources"][resource_type.value] = {
                "current_value": metric.current_value,
                "overload_level": metric.get_overload_level().name,
                "trend": metric.trend,
                "timestamp": metric.timestamp.isoformat()
            }
        
        return status

class TypeEntropyLimiter:
    """
    Advanced overload handler and entropy control system for DEVmind
    
    This system provides intelligent overload detection and response mechanisms
    that prevent system instability while maintaining optimal performance through
    sophisticated resource management and entropy control.
    """
    
    def __init__(self, 
                 context_manager=None,
                 emotion_system=None,
                 thought_system=None):
        """
        Initialize the TypeEntropyLimiter
        
        Args:
            context_manager: Reference to the context management system
            emotion_system: Reference to the emotion system
            thought_system: Reference to the thought processing system
        """
        self.context_manager = weakref.ref(context_manager) if context_manager else None
        self.emotion_system = weakref.ref(emotion_system) if emotion_system else None
        self.thought_system = weakref.ref(thought_system) if thought_system else None
        
        # Core components
        self.resource_monitor = ResourceMonitor()
        self.overload_events: List[OverloadEvent] = []
        self.intervention_strategies: Dict[OverloadLevel, List[InterventionType]] = {
            OverloadLevel.SOFT_WARNING: [InterventionType.THROTTLE],
            OverloadLevel.MODERATE: [InterventionType.THROTTLE, InterventionType.COMPRESS],
            OverloadLevel.SEVERE: [InterventionType.COMPRESS, InterventionType.PRUNE, InterventionType.ARCHIVE],
            OverloadLevel.CRITICAL: [InterventionType.EMERGENCY_STOP, InterventionType.CREATOR_ALERT, InterventionType.SYSTEM_RESTART]
        }
        
        # Thought graph monitoring
        self.thought_graph_metrics: Optional[ThoughtGraphMetrics] = None
        self.max_thought_depth = 25
        self.max_recursion_depth = 100
        self.max_emotion_volatility = 0.85
        
        # Performance tracking
        self.intervention_success_rates: Dict[InterventionType, float] = defaultdict(float)
        self.intervention_counts: Dict[InterventionType, int] = defaultdict(int)
        
        # Threading and async support
        self.lock = threading.Lock()
        self.active = False
        self.background_tasks: List[asyncio.Task] = []
        
        # Register callbacks with resource monitor
        self._register_resource_callbacks()
        
        logger.info("TypeEntropyLimiter initialized")
    
    def _register_resource_callbacks(self):
        """Register callbacks for resource overload events"""
        for resource_type in ResourceType:
            self.resource_monitor.register_callback(
                resource_type,
                lambda metric, level, rt=resource_type: self._handle_resource_overload(rt, metric, level)
            )
    
    def start(self):
        """Start the entropy limiter and resource monitoring"""
        if self.active:
            return
        
        self.active = True
        self.resource_monitor.start_monitoring()
        logger.info("TypeEntropyLimiter started")
    
    def stop(self):
        """Stop the entropy limiter and resource monitoring"""
        if not self.active:
            return
        
        self.active = False
        self.resource_monitor.stop_monitoring()
        logger.info("TypeEntropyLimiter stopped")
    
    def _handle_resource_overload(self, 
                                resource_type: ResourceType, 
                                metric: ResourceMetrics, 
                                overload_level: OverloadLevel):
        """Handle resource overload events"""
        with self.lock:
            logger.warning(f"Resource overload detected: {resource_type.value} at {overload_level.name}")
            
            # Select appropriate intervention strategies
            strategies = self.intervention_strategies.get(overload_level, [])
            
            for intervention_type in strategies:
                success = self._execute_intervention(resource_type, intervention_type, metric)
                
                # Record the event
                event = OverloadEvent(
                    timestamp=datetime.now(),
                    resource_type=resource_type,
                    overload_level=overload_level,
                    trigger_value=metric.current_value,
                    intervention_type=intervention_type,
                    intervention_success=success,
                    recovery_time=None,
                    metadata={"trend": metric.trend}
                )
                self.overload_events.append(event)
                
                # Update success rates
                self.intervention_counts[intervention_type] += 1
                if success:
                    current_rate = self.intervention_success_rates[intervention_type]
                    count = self.intervention_counts[intervention_type]
                    self.intervention_success_rates[intervention_type] = (current_rate * (count - 1) + 1.0) / count
                
                # If intervention was successful, we can stop here
                if success:
                    break
    
    def _execute_intervention(self, 
                            resource_type: ResourceType, 
                            intervention_type: InterventionType, 
                            metric: ResourceMetrics) -> bool:
        """Execute a specific intervention strategy"""
        try:
            if intervention_type == InterventionType.THROTTLE:
                return self._throttle_processing(resource_type, metric)
            elif intervention_type == InterventionType.COMPRESS:
                return self._compress_memory_cluster(resource_type, metric)
            elif intervention_type == InterventionType.PRUNE:
                return self._prune_unemotional_nodes(resource_type, metric)
            elif intervention_type == InterventionType.ARCHIVE:
                return self._archive_to_coldstore(resource_type, metric)
            elif intervention_type == InterventionType.REDIRECT:
                return self._redirect_processing(resource_type, metric)
            elif intervention_type == InterventionType.EMERGENCY_STOP:
                return self._emergency_stop(resource_type, metric)
            elif intervention_type == InterventionType.CREATOR_ALERT:
                return self._alert_creator(resource_type, metric)
            elif intervention_type == InterventionType.SYSTEM_RESTART:
                return self._restart_components(resource_type, metric)
            else:
                logger.warning(f"Unknown intervention type: {intervention_type}")
                return False
        except Exception as e:
            logger.error(f"Failed to execute intervention {intervention_type}: {e}")
            return False
    
    def _throttle_processing(self, resource_type: ResourceType, metric: ResourceMetrics) -> bool:
        """Throttle processing to reduce resource usage"""
        logger.info(f"Throttling processing for {resource_type.value}")
        
        if resource_type == ResourceType.CPU:
            # Reduce processing frequency
            if hasattr(self, '_original_intervals'):
                for component, interval in self._original_intervals.items():
                    # Increase intervals by 50%
                    new_interval = interval * 1.5
                    self._update_component_interval(component, new_interval)
            return True
        
        elif resource_type == ResourceType.MEMORY:
            # Trigger garbage collection
            gc.collect()
            return True
        
        elif resource_type == ResourceType.THOUGHT_DEPTH:
            # Limit thought depth
            if self.thought_system and self.thought_system():
                thought_sys = self.thought_system()
                if hasattr(thought_sys, 'set_max_depth'):
                    thought_sys.set_max_depth(self.max_thought_depth // 2)
                    return True
        
        return False
    
    def _compress_memory_cluster(self, resource_type: ResourceType, metric: ResourceMetrics) -> bool:
        """Compress memory clusters to reduce memory usage"""
        logger.info(f"Compressing memory clusters for {resource_type.value}")
        
        if self.context_manager and self.context_manager():
            context_mgr = self.context_manager()
            
            # Find clusters with low retention scores
            clusters_to_compress = []
            for cluster_id, cluster in context_mgr.memory_clusters.items():
                if cluster.get_average_retention_score() < 0.5:
                    clusters_to_compress.append(cluster_id)
            
            # Compress the clusters
            compressed_count = 0
            for cluster_id in clusters_to_compress[:5]:  # Limit to 5 clusters
                cluster = context_mgr.memory_clusters[cluster_id]
                for entry in cluster.entries:
                    if context_mgr._compress_context(entry):
                        compressed_count += 1
                        if entry.id in context_mgr.working_memory:
                            del context_mgr.working_memory[entry.id]
            
            logger.info(f"Compressed {compressed_count} context entries")
            return compressed_count > 0
        
        return False
    
    def _prune_unemotional_nodes(self, resource_type: ResourceType, metric: ResourceMetrics) -> bool:
        """Prune nodes with low emotional weight"""
        logger.info(f"Pruning unemotional nodes for {resource_type.value}")
        
        if self.context_manager and self.context_manager():
            context_mgr = self.context_manager()
            
            # Find entries with low emotional weight and low access count
            candidates_for_pruning = []
            for context_id, entry in context_mgr.working_memory.items():
                if (abs(entry.emotional_weight) < 0.1 and 
                    entry.access_count < 2 and 
                    entry.priority.value < 0.5):
                    candidates_for_pruning.append(context_id)
            
            # Prune the candidates
            pruned_count = 0
            for context_id in candidates_for_pruning[:10]:  # Limit to 10 entries
                if context_id in context_mgr.working_memory:
                    entry = context_mgr.working_memory[context_id]
                    # Archive before pruning if it has some value
                    if entry.calculate_retention_score() > 0.2:
                        context_mgr._compress_context(entry)
                    del context_mgr.working_memory[context_id]
                    pruned_count += 1
            
            logger.info(f"Pruned {pruned_count} low-value entries")
            return pruned_count > 0
        
        return False
    
    def _archive_to_coldstore(self, resource_type: ResourceType, metric: ResourceMetrics) -> bool:
        """Archive data to cold storage"""
        logger.info(f"Archiving to cold storage for {resource_type.value}")
        
        if self.context_manager and self.context_manager():
            context_mgr = self.context_manager()
            
            # Find old compressed entries for archival
            cutoff_time = datetime.now() - timedelta(hours=1)  # More aggressive archival
            candidates_for_archival = []
            
            for context_id, compressed_data in context_mgr.compressed_memory.items():
                if context_id in context_mgr.compression_stats:
                    compression_time = context_mgr.compression_stats[context_id]["compression_time"]
                    if compression_time < cutoff_time:
                        candidates_for_archival.append(context_id)
            
            # Archive the candidates
            archived_count = 0
            for context_id in candidates_for_archival[:20]:  # Limit to 20 entries
                file_path = f"{context_mgr.archive_dir}/{context_id}.gz"
                try:
                    with open(file_path, 'wb') as f:
                        f.write(context_mgr.compressed_memory[context_id])
                    
                    context_mgr.archived_memory[context_id] = file_path
                    del context_mgr.compressed_memory[context_id]
                    archived_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to archive {context_id}: {e}")
            
            logger.info(f"Archived {archived_count} entries to cold storage")
            return archived_count > 0
        
        return False
    
    def _redirect_processing(self, resource_type: ResourceType, metric: ResourceMetrics) -> bool:
        """Redirect processing to alternative pathways"""
        logger.info(f"Redirecting processing for {resource_type.value}")
        
        # This is a placeholder for more sophisticated redirection logic
        # In a full implementation, this would redirect processing to
        # alternative algorithms or processing pathways
        
        return True
    
    def _emergency_stop(self, resource_type: ResourceType, metric: ResourceMetrics) -> bool:
        """Emergency stop of dangerous operations"""
        logger.critical(f"Emergency stop triggered for {resource_type.value}")
        
        # Stop background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        
        # Stop recursive operations
        if self.thought_system and self.thought_system():
            thought_sys = self.thought_system()
            if hasattr(thought_sys, 'emergency_stop'):
                thought_sys.emergency_stop()
        
        # Force garbage collection
        gc.collect()
        
        return True
    
    def _alert_creator(self, resource_type: ResourceType, metric: ResourceMetrics) -> bool:
        """Alert the creator about critical overload"""
        alert_message = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": "CRITICAL_OVERLOAD",
            "resource_type": resource_type.value,
            "current_value": metric.current_value,
            "threshold_critical": metric.threshold_critical,
            "trend": metric.trend,
            "system_status": self.get_system_status()
        }
        
        logger.critical(f"CREATOR ALERT: {json.dumps(alert_message, indent=2)}")
        
        # In a full implementation, this would send notifications through
        # various channels (email, SMS, system notifications, etc.)
        
        return True
    
    def _restart_components(self, resource_type: ResourceType, metric: ResourceMetrics) -> bool:
        """Restart system components to recover from critical overload"""
        logger.critical(f"Restarting components for {resource_type.value}")
        
        try:
            # Restart context manager
            if self.context_manager and self.context_manager():
                context_mgr = self.context_manager()
                if hasattr(context_mgr, 'restart'):
                    context_mgr.restart()
            
            # Restart emotion system
            if self.emotion_system and self.emotion_system():
                emotion_sys = self.emotion_system()
                if hasattr(emotion_sys, 'restart'):
                    emotion_sys.restart()
            
            # Restart thought system
            if self.thought_system and self.thought_system():
                thought_sys = self.thought_system()
                if hasattr(thought_sys, 'restart'):
                    thought_sys.restart()
            
            return True
        except Exception as e:
            logger.error(f"Failed to restart components: {e}")
            return False
    
    def _update_component_interval(self, component: str, new_interval: float):
        """Update processing interval for a component"""
        # This is a placeholder for component-specific interval updates
        logger.info(f"Updated {component} interval to {new_interval}")
    
    def update_thought_graph_metrics(self, metrics: ThoughtGraphMetrics):
        """Update thought graph metrics for monitoring"""
        self.thought_graph_metrics = metrics
        
        # Check for thought graph overload
        risk = metrics.calculate_overload_risk()
        if risk > 0.8:
            logger.warning(f"High thought graph overload risk: {risk:.2f}")
            
            # Create synthetic metric for thought depth
            thought_metric = ResourceMetrics(
                resource_type=ResourceType.THOUGHT_DEPTH,
                current_value=metrics.max_depth,
                threshold_soft=self.max_thought_depth * 0.7,
                threshold_hard=self.max_thought_depth * 0.9,
                threshold_critical=self.max_thought_depth,
                trend=0.0,  # Would need historical data for trend
                timestamp=datetime.now()
            )
            
            overload_level = thought_metric.get_overload_level()
            if overload_level != OverloadLevel.NORMAL:
                self._handle_resource_overload(ResourceType.THOUGHT_DEPTH, thought_metric, overload_level)
    
    def inject_self_reflect(self, reflection_topic: str):
        """Inject a self-reflection event"""
        logger.info(f"Injecting self-reflection: {reflection_topic}")
        
        # This would trigger the AI to reflect on the current situation
        # and potentially adjust its behavior or processing patterns
        
        reflection_data = {
            "topic": reflection_topic,
            "timestamp": datetime.now().isoformat(),
            "system_status": self.get_system_status(),
            "recent_events": [asdict(event) for event in self.overload_events[-5:]]
        }
        
        # In a full implementation, this would be passed to the reflection system
        logger.info(f"Self-reflection data: {json.dumps(reflection_data, indent=2, default=str)}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "active": self.active,
            "resource_monitor": self.resource_monitor.get_current_status(),
            "recent_overload_events": len([e for e in self.overload_events if (datetime.now() - e.timestamp).total_seconds() < 3600]),
            "intervention_success_rates": dict(self.intervention_success_rates),
            "intervention_counts": dict(self.intervention_counts),
            "thought_graph_metrics": asdict(self.thought_graph_metrics) if self.thought_graph_metrics else None
        }
        
        return status
    
    def get_overload_history(self, hours: int = 24) -> List[OverloadEvent]:
        """Get overload event history for the specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [event for event in self.overload_events if event.timestamp > cutoff_time]
    
    def optimize_thresholds(self):
        """Optimize resource thresholds based on historical performance"""
        logger.info("Optimizing resource thresholds based on historical data")
        
        # Analyze recent overload events to adjust thresholds
        recent_events = self.get_overload_history(hours=24)
        
        for resource_type in ResourceType:
            events_for_resource = [e for e in recent_events if e.resource_type == resource_type]
            
            if len(events_for_resource) > 5:  # Enough data for optimization
                # If too many false positives, increase thresholds
                false_positives = sum(1 for e in events_for_resource if not e.intervention_success)
                if false_positives / len(events_for_resource) > 0.3:
                    current_thresholds = self.resource_monitor.thresholds[resource_type]
                    new_thresholds = tuple(t * 1.1 for t in current_thresholds)  # Increase by 10%
                    self.resource_monitor.update_thresholds(resource_type, *new_thresholds)
                    logger.info(f"Increased thresholds for {resource_type.value} due to false positives")
                
                # If too many critical events, decrease thresholds
                critical_events = sum(1 for e in events_for_resource if e.overload_level == OverloadLevel.CRITICAL)
                if critical_events / len(events_for_resource) > 0.2:
                    current_thresholds = self.resource_monitor.thresholds[resource_type]
                    new_thresholds = tuple(t * 0.9 for t in current_thresholds)  # Decrease by 10%
                    self.resource_monitor.update_thresholds(resource_type, *new_thresholds)
                    logger.info(f"Decreased thresholds for {resource_type.value} due to critical events")
    
    async def start_background_optimization(self):
        """Start background optimization tasks"""
        logger.info("Starting background optimization tasks")
        
        async def threshold_optimization_task():
            while self.active:
                await asyncio.sleep(3600)  # Run every hour
                self.optimize_thresholds()
        
        async def cleanup_task():
            while self.active:
                await asyncio.sleep(1800)  # Run every 30 minutes
                self._cleanup_old_events()
        
        # Start tasks
        self.background_tasks = [
            asyncio.create_task(threshold_optimization_task()),
            asyncio.create_task(cleanup_task())
        ]
    
    def _cleanup_old_events(self):
        """Clean up old overload events"""
        cutoff_time = datetime.now() - timedelta(days=7)
        original_count = len(self.overload_events)
        self.overload_events = [e for e in self.overload_events if e.timestamp > cutoff_time]
        cleaned_count = original_count - len(self.overload_events)
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old overload events")
    
    async def shutdown(self):
        """Gracefully shutdown the entropy limiter"""
        logger.info("Shutting down TypeEntropyLimiter")
        
        self.stop()
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("TypeEntropyLimiter shutdown complete")

# Example usage and testing
if __name__ == "__main__":
    async def test_type_entropy_limiter():
        """Test the TypeEntropyLimiter"""
        limiter = TypeEntropyLimiter()
        
        # Start the limiter
        limiter.start()
        
        # Start background optimization
        await limiter.start_background_optimization()
        
        # Simulate some thought graph metrics
        thought_metrics = ThoughtGraphMetrics(
            node_count=500,
            edge_count=1200,
            max_depth=15,
            recursion_loops=2,
            complexity_score=45.0,
            entropy_level=0.6
        )
        limiter.update_thought_graph_metrics(thought_metrics)
        
        # Wait for monitoring to collect some data
        await asyncio.sleep(5)
        
        # Get system status
        status = limiter.get_system_status()
        print(f"System status: {json.dumps(status, indent=2, default=str)}")
        
        # Inject a self-reflection
        limiter.inject_self_reflect("memory_overload_test")
        
        # Shutdown
        await limiter.shutdown()
    
    # Run the test
    asyncio.run(test_type_entropy_limiter())

