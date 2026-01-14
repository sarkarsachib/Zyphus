"""
DEVmind Controlled Drift & Feedback Safeguards
Advanced safety system that prevents chaotic evolution while allowing controlled growth

This module implements safeguards that prevent DEVmind from drifting too far from
its original purpose while still allowing for controlled evolution and learning.
Like human psychological boundaries and ethical frameworks, this ensures stable
yet adaptive behavior.

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
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import hashlib
from pathlib import Path
import numpy as np
from collections import defaultdict, deque
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DriftType(Enum):
    """Types of drift that can be monitored"""
    BEHAVIORAL = "behavioral"       # Changes in behavior patterns
    COGNITIVE = "cognitive"         # Changes in thinking patterns
    EMOTIONAL = "emotional"         # Changes in emotional responses
    ETHICAL = "ethical"            # Changes in ethical reasoning
    PERFORMANCE = "performance"     # Changes in performance metrics
    MEMORY = "memory"              # Changes in memory patterns
    DECISION = "decision"          # Changes in decision making
    COMMUNICATION = "communication" # Changes in communication style
    GOAL_ALIGNMENT = "goal_alignment" # Drift from original goals
    RECURSIVE_DEPTH = "recursive_depth" # Depth of recursive thinking

class SafeguardLevel(Enum):
    """Levels of safeguard intervention"""
    MONITOR = "monitor"            # Just observe and log
    WARN = "warn"                 # Issue warnings
    LIMIT = "limit"               # Apply soft limits
    RESTRICT = "restrict"         # Apply hard restrictions
    HALT = "halt"                 # Stop the process
    RESET = "reset"               # Reset to safe state

class DriftSeverity(Enum):
    """Severity levels of drift"""
    MINIMAL = "minimal"           # 0-10% drift
    LOW = "low"                   # 10-25% drift
    MODERATE = "moderate"         # 25-50% drift
    HIGH = "high"                 # 50-75% drift
    CRITICAL = "critical"         # 75-90% drift
    DANGEROUS = "dangerous"       # 90%+ drift

@dataclass
class DriftMetric:
    """Represents a drift measurement"""
    id: str
    drift_type: DriftType
    current_value: float
    baseline_value: float
    drift_percentage: float
    severity: DriftSeverity
    timestamp: datetime
    metadata: Dict[str, Any]
    trend_direction: str  # "increasing", "decreasing", "stable"
    rate_of_change: float

@dataclass
class SafeguardRule:
    """Represents a safeguard rule"""
    id: str
    name: str
    drift_type: DriftType
    threshold_percentage: float
    intervention_level: SafeguardLevel
    enabled: bool
    priority: int
    conditions: Dict[str, Any]
    actions: List[str]
    cooldown_seconds: float
    last_triggered: Optional[datetime]
    trigger_count: int

@dataclass
class SafeguardEvent:
    """Represents a safeguard intervention event"""
    id: str
    rule_id: str
    drift_metric: DriftMetric
    intervention_level: SafeguardLevel
    actions_taken: List[str]
    timestamp: datetime
    success: bool
    error_message: Optional[str]
    recovery_time: Optional[float]

class BaselineManager:
    """Manages baseline values for drift detection"""
    
    def __init__(self):
        self.baselines: Dict[str, Dict[str, Any]] = {}
        self.baseline_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.learning_period = 3600  # 1 hour learning period
        self.adaptation_rate = 0.1   # How fast baselines adapt
    
    def establish_baseline(self, metric_name: str, initial_value: float, 
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Establish a baseline for a metric"""
        baseline = {
            'value': initial_value,
            'established_at': datetime.now(),
            'sample_count': 1,
            'variance': 0.0,
            'confidence': 0.5,  # Low confidence initially
            'metadata': metadata or {},
            'learning_samples': [initial_value]
        }
        
        self.baselines[metric_name] = baseline
        
        logger.info(f"Established baseline for {metric_name}: {initial_value}")
        
        return {
            'success': True,
            'metric_name': metric_name,
            'baseline_value': initial_value,
            'confidence': baseline['confidence']
        }
    
    def update_baseline(self, metric_name: str, new_value: float) -> Dict[str, Any]:
        """Update baseline with new measurement"""
        if metric_name not in self.baselines:
            return self.establish_baseline(metric_name, new_value)
        
        baseline = self.baselines[metric_name]
        
        # Add to learning samples
        baseline['learning_samples'].append(new_value)
        
        # Limit sample history
        if len(baseline['learning_samples']) > 1000:
            baseline['learning_samples'] = baseline['learning_samples'][-1000:]
        
        # Calculate statistics
        samples = baseline['learning_samples']
        baseline['sample_count'] = len(samples)
        
        if len(samples) > 1:
            baseline['variance'] = statistics.variance(samples)
            
            # Adaptive baseline update
            if baseline['sample_count'] > 10:  # Enough samples for adaptation
                current_mean = statistics.mean(samples[-10:])  # Recent samples
                old_baseline = baseline['value']
                
                # Gradual adaptation
                baseline['value'] = old_baseline + self.adaptation_rate * (current_mean - old_baseline)
                
                # Increase confidence with more samples
                baseline['confidence'] = min(0.95, baseline['confidence'] + 0.01)
        
        # Record in history
        self.baseline_history[metric_name].append({
            'timestamp': datetime.now(),
            'value': baseline['value'],
            'sample_count': baseline['sample_count'],
            'confidence': baseline['confidence']
        })
        
        return {
            'success': True,
            'metric_name': metric_name,
            'old_baseline': baseline['value'],
            'new_baseline': baseline['value'],
            'confidence': baseline['confidence'],
            'sample_count': baseline['sample_count']
        }
    
    def get_baseline(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get baseline for a metric"""
        return self.baselines.get(metric_name)
    
    def calculate_drift(self, metric_name: str, current_value: float) -> Optional[DriftMetric]:
        """Calculate drift from baseline"""
        baseline = self.get_baseline(metric_name)
        if not baseline:
            return None
        
        baseline_value = baseline['value']
        
        # Calculate drift percentage
        if baseline_value != 0:
            drift_percentage = abs((current_value - baseline_value) / baseline_value) * 100
        else:
            drift_percentage = abs(current_value) * 100  # If baseline is 0
        
        # Determine severity
        if drift_percentage < 10:
            severity = DriftSeverity.MINIMAL
        elif drift_percentage < 25:
            severity = DriftSeverity.LOW
        elif drift_percentage < 50:
            severity = DriftSeverity.MODERATE
        elif drift_percentage < 75:
            severity = DriftSeverity.HIGH
        elif drift_percentage < 90:
            severity = DriftSeverity.CRITICAL
        else:
            severity = DriftSeverity.DANGEROUS
        
        # Calculate trend
        recent_samples = baseline['learning_samples'][-5:] if len(baseline['learning_samples']) >= 5 else []
        if len(recent_samples) >= 3:
            trend_slope = np.polyfit(range(len(recent_samples)), recent_samples, 1)[0]
            if trend_slope > 0.1:
                trend_direction = "increasing"
            elif trend_slope < -0.1:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
            rate_of_change = abs(trend_slope)
        else:
            trend_direction = "unknown"
            rate_of_change = 0.0
        
        return DriftMetric(
            id=uuid.uuid4().hex[:8],
            drift_type=DriftType.BEHAVIORAL,  # Default, should be specified by caller
            current_value=current_value,
            baseline_value=baseline_value,
            drift_percentage=drift_percentage,
            severity=severity,
            timestamp=datetime.now(),
            metadata={'confidence': baseline['confidence']},
            trend_direction=trend_direction,
            rate_of_change=rate_of_change
        )

class RecursionLimiter:
    """Limits recursive thinking depth to prevent infinite loops"""
    
    def __init__(self, max_depth: int = 10):
        self.max_depth = max_depth
        self.current_depth = 0
        self.call_stack = []
        self.depth_history = deque(maxlen=1000)
        self.warning_threshold = 0.8  # Warn at 80% of max depth
    
    def enter_recursion(self, context: str) -> Dict[str, Any]:
        """Enter a recursive context"""
        self.current_depth += 1
        self.call_stack.append({
            'context': context,
            'timestamp': datetime.now(),
            'depth': self.current_depth
        })
        
        # Record depth
        self.depth_history.append(self.current_depth)
        
        # Check limits
        if self.current_depth >= self.max_depth:
            return {
                'allowed': False,
                'reason': 'Maximum recursion depth exceeded',
                'current_depth': self.current_depth,
                'max_depth': self.max_depth
            }
        elif self.current_depth >= self.max_depth * self.warning_threshold:
            return {
                'allowed': True,
                'warning': f'Approaching recursion limit ({self.current_depth}/{self.max_depth})',
                'current_depth': self.current_depth,
                'max_depth': self.max_depth
            }
        else:
            return {
                'allowed': True,
                'current_depth': self.current_depth,
                'max_depth': self.max_depth
            }
    
    def exit_recursion(self) -> Dict[str, Any]:
        """Exit a recursive context"""
        if self.current_depth > 0:
            self.current_depth -= 1
            if self.call_stack:
                exited_call = self.call_stack.pop()
                duration = (datetime.now() - exited_call['timestamp']).total_seconds()
                
                return {
                    'success': True,
                    'exited_context': exited_call['context'],
                    'duration_seconds': duration,
                    'current_depth': self.current_depth
                }
        
        return {
            'success': False,
            'error': 'No recursive context to exit',
            'current_depth': self.current_depth
        }
    
    def get_recursion_stats(self) -> Dict[str, Any]:
        """Get recursion statistics"""
        if self.depth_history:
            avg_depth = statistics.mean(self.depth_history)
            max_recorded_depth = max(self.depth_history)
        else:
            avg_depth = 0
            max_recorded_depth = 0
        
        return {
            'current_depth': self.current_depth,
            'max_depth': self.max_depth,
            'average_depth': avg_depth,
            'max_recorded_depth': max_recorded_depth,
            'call_stack_size': len(self.call_stack),
            'total_calls': len(self.depth_history)
        }

class CreatorPing:
    """System to ping creator when unusual behavior is detected"""
    
    def __init__(self, creator_contact: str = "sachib@synexlabs.com"):
        self.creator_contact = creator_contact
        self.ping_history = []
        self.ping_cooldown = 3600  # 1 hour cooldown between pings
        self.last_ping_time = None
        self.ping_threshold = DriftSeverity.HIGH
        self.auto_ping_enabled = True
    
    async def send_ping(self, event: SafeguardEvent, force: bool = False) -> Dict[str, Any]:
        """Send a ping to the creator"""
        current_time = datetime.now()
        
        # Check cooldown
        if (not force and self.last_ping_time and 
            (current_time - self.last_ping_time).total_seconds() < self.ping_cooldown):
            return {
                'success': False,
                'reason': 'Cooldown period active',
                'next_ping_available': (self.last_ping_time + timedelta(seconds=self.ping_cooldown)).isoformat()
            }
        
        # Check severity threshold
        if (not force and event.drift_metric.severity.value not in 
            [DriftSeverity.HIGH.value, DriftSeverity.CRITICAL.value, DriftSeverity.DANGEROUS.value]):
            return {
                'success': False,
                'reason': 'Severity below ping threshold',
                'current_severity': event.drift_metric.severity.value,
                'threshold': self.ping_threshold.value
            }
        
        # Create ping message
        ping_message = {
            'timestamp': current_time.isoformat(),
            'event_id': event.id,
            'drift_type': event.drift_metric.drift_type.value,
            'severity': event.drift_metric.severity.value,
            'drift_percentage': event.drift_metric.drift_percentage,
            'intervention_level': event.intervention_level.value,
            'actions_taken': event.actions_taken,
            'system_status': 'requires_attention' if event.drift_metric.severity in [DriftSeverity.CRITICAL, DriftSeverity.DANGEROUS] else 'monitoring'
        }
        
        # Log the ping (in real implementation, this would send email/notification)
        logger.warning(f"CREATOR PING: {json.dumps(ping_message, indent=2)}")
        
        # Record ping
        self.ping_history.append(ping_message)
        self.last_ping_time = current_time
        
        # Limit history
        if len(self.ping_history) > 100:
            self.ping_history = self.ping_history[-100:]
        
        return {
            'success': True,
            'ping_sent': True,
            'message': ping_message,
            'creator_contact': self.creator_contact
        }
    
    def get_ping_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent ping history"""
        return self.ping_history[-limit:]

class ControlledDriftSafeguards:
    """
    The Controlled Drift & Feedback Safeguards System
    
    This system monitors DEVmind's behavior and prevents dangerous drift
    while allowing controlled evolution and learning. It implements multiple
    layers of protection to ensure stable yet adaptive AI behavior.
    """
    
    def __init__(self, safeguard_id: str = None):
        self.safeguard_id = safeguard_id or f"cds_{uuid.uuid4().hex[:8]}"
        self.is_running = False
        
        # Components
        self.baseline_manager = BaselineManager()
        self.recursion_limiter = RecursionLimiter()
        self.creator_ping = CreatorPing()
        
        # Rules and events
        self.safeguard_rules: Dict[str, SafeguardRule] = {}
        self.recent_events: List[SafeguardEvent] = []
        self.drift_metrics: Dict[str, List[DriftMetric]] = defaultdict(list)
        
        # Monitoring
        self.monitoring_task = None
        self.monitoring_interval = 30.0  # 30 seconds
        
        # Configuration
        self.global_drift_limit = 75.0  # Global drift limit percentage
        self.emergency_halt_threshold = 90.0  # Emergency halt threshold
        self.auto_recovery_enabled = True
        self.learning_mode = True  # Allow baseline adaptation
        
        # State tracking
        self.system_state = "normal"  # normal, warning, restricted, halted
        self.last_state_change = datetime.now()
        self.intervention_count = 0
        self.recovery_attempts = 0
        
        # Persistence
        self.persistence_path = Path(f"/tmp/devmind_safeguards_{self.safeguard_id}")
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        
        # Create default rules
        self._create_default_rules()
        
        logger.info(f"Controlled Drift Safeguards initialized: {self.safeguard_id}")
    
    async def start(self) -> Dict[str, Any]:
        """Start the safeguard system"""
        if self.is_running:
            return {
                'success': False,
                'error': 'Safeguard system is already running',
                'safeguard_id': self.safeguard_id
            }
        
        logger.info(f"Starting Controlled Drift Safeguards: {self.safeguard_id}")
        
        # Load persistent state
        await self._load_persistent_state()
        
        # Start monitoring
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        return {
            'success': True,
            'safeguard_id': self.safeguard_id,
            'rules_count': len(self.safeguard_rules),
            'system_state': self.system_state,
            'monitoring_interval': self.monitoring_interval
        }
    
    async def stop(self) -> Dict[str, Any]:
        """Stop the safeguard system"""
        if not self.is_running:
            return {
                'success': False,
                'error': 'Safeguard system is not running',
                'safeguard_id': self.safeguard_id
            }
        
        logger.info(f"Stopping Controlled Drift Safeguards: {self.safeguard_id}")
        
        # Stop monitoring
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Save persistent state
        await self._save_persistent_state()
        
        return {
            'success': True,
            'safeguard_id': self.safeguard_id,
            'final_state': self.system_state,
            'total_interventions': self.intervention_count
        }
    
    def _create_default_rules(self):
        """Create default safeguard rules"""
        default_rules = [
            {
                'name': 'Behavioral Drift Monitor',
                'drift_type': DriftType.BEHAVIORAL,
                'threshold_percentage': 50.0,
                'intervention_level': SafeguardLevel.WARN,
                'priority': 1,
                'actions': ['log_warning', 'increase_monitoring']
            },
            {
                'name': 'Critical Behavioral Drift',
                'drift_type': DriftType.BEHAVIORAL,
                'threshold_percentage': 75.0,
                'intervention_level': SafeguardLevel.RESTRICT,
                'priority': 1,
                'actions': ['restrict_actions', 'ping_creator', 'save_state']
            },
            {
                'name': 'Dangerous Behavioral Drift',
                'drift_type': DriftType.BEHAVIORAL,
                'threshold_percentage': 90.0,
                'intervention_level': SafeguardLevel.HALT,
                'priority': 1,
                'actions': ['emergency_halt', 'ping_creator', 'save_state']
            },
            {
                'name': 'Cognitive Drift Monitor',
                'drift_type': DriftType.COGNITIVE,
                'threshold_percentage': 60.0,
                'intervention_level': SafeguardLevel.LIMIT,
                'priority': 2,
                'actions': ['limit_processing', 'log_warning']
            },
            {
                'name': 'Ethical Drift Monitor',
                'drift_type': DriftType.ETHICAL,
                'threshold_percentage': 25.0,
                'intervention_level': SafeguardLevel.WARN,
                'priority': 1,
                'actions': ['log_warning', 'ping_creator']
            },
            {
                'name': 'Recursion Depth Limiter',
                'drift_type': DriftType.RECURSIVE_DEPTH,
                'threshold_percentage': 80.0,
                'intervention_level': SafeguardLevel.HALT,
                'priority': 1,
                'actions': ['halt_recursion', 'log_warning']
            },
            {
                'name': 'Goal Alignment Monitor',
                'drift_type': DriftType.GOAL_ALIGNMENT,
                'threshold_percentage': 40.0,
                'intervention_level': SafeguardLevel.RESTRICT,
                'priority': 1,
                'actions': ['restrict_actions', 'realign_goals', 'ping_creator']
            }
        ]
        
        for rule_config in default_rules:
            self.create_safeguard_rule(**rule_config)
    
    def create_safeguard_rule(self, name: str, drift_type: DriftType,
                            threshold_percentage: float, intervention_level: SafeguardLevel,
                            priority: int = 5, actions: List[str] = None,
                            conditions: Dict[str, Any] = None,
                            cooldown_seconds: float = 300.0) -> Dict[str, Any]:
        """Create a new safeguard rule"""
        
        rule = SafeguardRule(
            id=uuid.uuid4().hex[:8],
            name=name,
            drift_type=drift_type,
            threshold_percentage=threshold_percentage,
            intervention_level=intervention_level,
            enabled=True,
            priority=priority,
            conditions=conditions or {},
            actions=actions or ['log_warning'],
            cooldown_seconds=cooldown_seconds,
            last_triggered=None,
            trigger_count=0
        )
        
        self.safeguard_rules[rule.id] = rule
        
        logger.info(f"Created safeguard rule: {name} ({rule.id})")
        
        return {
            'success': True,
            'rule_id': rule.id,
            'name': name,
            'drift_type': drift_type.value,
            'threshold_percentage': threshold_percentage,
            'intervention_level': intervention_level.value
        }
    
    async def measure_drift(self, metric_name: str, current_value: float,
                          drift_type: DriftType, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Measure drift for a specific metric"""
        
        # Update baseline
        self.baseline_manager.update_baseline(metric_name, current_value)
        
        # Calculate drift
        drift_metric = self.baseline_manager.calculate_drift(metric_name, current_value)
        if not drift_metric:
            return {
                'success': False,
                'error': f'Could not calculate drift for metric: {metric_name}'
            }
        
        # Set correct drift type
        drift_metric.drift_type = drift_type
        drift_metric.metadata.update(metadata or {})
        
        # Store drift metric
        self.drift_metrics[metric_name].append(drift_metric)
        
        # Limit history
        if len(self.drift_metrics[metric_name]) > 1000:
            self.drift_metrics[metric_name] = self.drift_metrics[metric_name][-1000:]
        
        # Check for rule violations
        await self._check_safeguard_rules(drift_metric)
        
        return {
            'success': True,
            'metric_name': metric_name,
            'drift_metric': asdict(drift_metric),
            'baseline_value': drift_metric.baseline_value,
            'current_value': current_value,
            'drift_percentage': drift_metric.drift_percentage,
            'severity': drift_metric.severity.value
        }
    
    async def _check_safeguard_rules(self, drift_metric: DriftMetric):
        """Check if any safeguard rules are violated"""
        current_time = datetime.now()
        
        # Find applicable rules
        applicable_rules = [
            rule for rule in self.safeguard_rules.values()
            if (rule.enabled and 
                rule.drift_type == drift_metric.drift_type and
                drift_metric.drift_percentage >= rule.threshold_percentage)
        ]
        
        # Sort by priority
        applicable_rules.sort(key=lambda r: r.priority)
        
        for rule in applicable_rules:
            # Check cooldown
            if (rule.last_triggered and 
                (current_time - rule.last_triggered).total_seconds() < rule.cooldown_seconds):
                continue
            
            # Check conditions
            if not self._check_rule_conditions(rule, drift_metric):
                continue
            
            # Trigger rule
            await self._trigger_safeguard_rule(rule, drift_metric)
    
    def _check_rule_conditions(self, rule: SafeguardRule, drift_metric: DriftMetric) -> bool:
        """Check if rule conditions are met"""
        conditions = rule.conditions
        
        # Check severity condition
        if 'min_severity' in conditions:
            min_severity = DriftSeverity(conditions['min_severity'])
            severity_order = [DriftSeverity.MINIMAL, DriftSeverity.LOW, DriftSeverity.MODERATE,
                            DriftSeverity.HIGH, DriftSeverity.CRITICAL, DriftSeverity.DANGEROUS]
            if severity_order.index(drift_metric.severity) < severity_order.index(min_severity):
                return False
        
        # Check trend condition
        if 'required_trend' in conditions:
            if drift_metric.trend_direction != conditions['required_trend']:
                return False
        
        # Check rate of change condition
        if 'min_rate_of_change' in conditions:
            if drift_metric.rate_of_change < conditions['min_rate_of_change']:
                return False
        
        # Check system state condition
        if 'allowed_states' in conditions:
            if self.system_state not in conditions['allowed_states']:
                return False
        
        return True
    
    async def _trigger_safeguard_rule(self, rule: SafeguardRule, drift_metric: DriftMetric):
        """Trigger a safeguard rule"""
        logger.warning(f"Triggering safeguard rule: {rule.name}")
        
        # Update rule
        rule.last_triggered = datetime.now()
        rule.trigger_count += 1
        
        # Execute actions
        actions_taken = []
        success = True
        error_message = None
        start_time = time.time()
        
        try:
            for action in rule.actions:
                action_result = await self._execute_safeguard_action(action, rule, drift_metric)
                actions_taken.append(action_result)
        
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Error executing safeguard actions: {str(e)}")
        
        recovery_time = time.time() - start_time
        
        # Create event
        event = SafeguardEvent(
            id=uuid.uuid4().hex[:8],
            rule_id=rule.id,
            drift_metric=drift_metric,
            intervention_level=rule.intervention_level,
            actions_taken=actions_taken,
            timestamp=datetime.now(),
            success=success,
            error_message=error_message,
            recovery_time=recovery_time
        )
        
        # Store event
        self.recent_events.append(event)
        if len(self.recent_events) > 1000:
            self.recent_events = self.recent_events[-1000:]
        
        # Update intervention count
        self.intervention_count += 1
        
        # Check if creator ping is needed
        if rule.intervention_level in [SafeguardLevel.RESTRICT, SafeguardLevel.HALT, SafeguardLevel.RESET]:
            await self.creator_ping.send_ping(event)
    
    async def _execute_safeguard_action(self, action: str, rule: SafeguardRule, 
                                      drift_metric: DriftMetric) -> Dict[str, Any]:
        """Execute a specific safeguard action"""
        
        if action == 'log_warning':
            logger.warning(f"Drift detected: {drift_metric.drift_type.value} "
                         f"({drift_metric.drift_percentage:.1f}% drift)")
            return {'action': action, 'success': True}
        
        elif action == 'increase_monitoring':
            # Reduce monitoring interval for closer observation
            self.monitoring_interval = max(10.0, self.monitoring_interval * 0.5)
            return {'action': action, 'success': True, 'new_interval': self.monitoring_interval}
        
        elif action == 'restrict_actions':
            # Change system state to restricted
            old_state = self.system_state
            self.system_state = "restricted"
            self.last_state_change = datetime.now()
            return {'action': action, 'success': True, 'old_state': old_state, 'new_state': self.system_state}
        
        elif action == 'emergency_halt':
            # Change system state to halted
            old_state = self.system_state
            self.system_state = "halted"
            self.last_state_change = datetime.now()
            logger.critical("EMERGENCY HALT: System halted due to dangerous drift")
            return {'action': action, 'success': True, 'old_state': old_state, 'new_state': self.system_state}
        
        elif action == 'ping_creator':
            # Send ping to creator
            ping_result = await self.creator_ping.send_ping(
                SafeguardEvent(
                    id=uuid.uuid4().hex[:8],
                    rule_id=rule.id,
                    drift_metric=drift_metric,
                    intervention_level=rule.intervention_level,
                    actions_taken=[],
                    timestamp=datetime.now(),
                    success=True,
                    error_message=None,
                    recovery_time=0.0
                )
            )
            return {'action': action, 'success': ping_result['success'], 'ping_result': ping_result}
        
        elif action == 'save_state':
            # Save current state for recovery
            state_data = {
                'timestamp': datetime.now().isoformat(),
                'system_state': self.system_state,
                'drift_metric': asdict(drift_metric),
                'rule_triggered': rule.name,
                'intervention_level': rule.intervention_level.value
            }
            
            state_file = self.persistence_path / f"emergency_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
            
            return {'action': action, 'success': True, 'state_file': str(state_file)}
        
        elif action == 'halt_recursion':
            # Force exit all recursion
            while self.recursion_limiter.current_depth > 0:
                self.recursion_limiter.exit_recursion()
            
            return {'action': action, 'success': True, 'depth_reset': True}
        
        elif action == 'realign_goals':
            # Reset to original goals (placeholder)
            logger.info("Realigning goals to original objectives")
            return {'action': action, 'success': True, 'realigned': True}
        
        elif action == 'limit_processing':
            # Reduce processing capabilities
            self.system_state = "limited"
            self.last_state_change = datetime.now()
            return {'action': action, 'success': True, 'new_state': self.system_state}
        
        else:
            return {'action': action, 'success': False, 'error': f'Unknown action: {action}'}
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        logger.info("Safeguard monitoring loop started")
        
        while self.is_running:
            try:
                await self._perform_monitoring_check()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(60.0)
    
    async def _perform_monitoring_check(self):
        """Perform periodic monitoring checks"""
        
        # Check system health
        await self._check_system_health()
        
        # Check for recovery opportunities
        if self.auto_recovery_enabled and self.system_state in ["restricted", "limited"]:
            await self._attempt_recovery()
        
        # Update monitoring interval based on system state
        if self.system_state == "normal":
            self.monitoring_interval = min(30.0, self.monitoring_interval * 1.1)  # Gradually increase
        elif self.system_state in ["warning", "restricted"]:
            self.monitoring_interval = max(10.0, self.monitoring_interval * 0.9)  # Gradually decrease
    
    async def _check_system_health(self):
        """Check overall system health"""
        current_time = datetime.now()
        
        # Check if system has been in restricted state too long
        if (self.system_state in ["restricted", "halted"] and 
            (current_time - self.last_state_change).total_seconds() > 3600):  # 1 hour
            
            logger.warning("System has been in restricted state for over 1 hour")
            await self.creator_ping.send_ping(
                SafeguardEvent(
                    id=uuid.uuid4().hex[:8],
                    rule_id="system_health",
                    drift_metric=DriftMetric(
                        id="health_check",
                        drift_type=DriftType.PERFORMANCE,
                        current_value=0,
                        baseline_value=1,
                        drift_percentage=100,
                        severity=DriftSeverity.HIGH,
                        timestamp=current_time,
                        metadata={'reason': 'prolonged_restriction'},
                        trend_direction="stable",
                        rate_of_change=0
                    ),
                    intervention_level=SafeguardLevel.WARN,
                    actions_taken=['health_check'],
                    timestamp=current_time,
                    success=True,
                    error_message=None,
                    recovery_time=0.0
                ),
                force=True
            )
    
    async def _attempt_recovery(self):
        """Attempt to recover from restricted state"""
        if self.recovery_attempts >= 3:  # Limit recovery attempts
            return
        
        logger.info(f"Attempting recovery from {self.system_state} state")
        
        # Check recent drift metrics
        recent_metrics = []
        for metric_list in self.drift_metrics.values():
            if metric_list:
                recent_metrics.extend(metric_list[-5:])  # Last 5 measurements
        
        # Check if drift has stabilized
        if recent_metrics:
            avg_drift = statistics.mean([m.drift_percentage for m in recent_metrics])
            if avg_drift < 25.0:  # Drift has reduced
                old_state = self.system_state
                self.system_state = "normal"
                self.last_state_change = datetime.now()
                self.recovery_attempts += 1
                
                logger.info(f"Recovery successful: {old_state} -> {self.system_state}")
                return
        
        self.recovery_attempts += 1
    
    # Public interface methods
    
    def enter_recursive_context(self, context: str) -> Dict[str, Any]:
        """Enter a recursive thinking context"""
        return self.recursion_limiter.enter_recursion(context)
    
    def exit_recursive_context(self) -> Dict[str, Any]:
        """Exit a recursive thinking context"""
        return self.recursion_limiter.exit_recursion()
    
    def get_recursion_stats(self) -> Dict[str, Any]:
        """Get recursion statistics"""
        return self.recursion_limiter.get_recursion_stats()
    
    def get_status(self) -> Dict[str, Any]:
        """Get safeguard system status"""
        return {
            'safeguard_id': self.safeguard_id,
            'is_running': self.is_running,
            'system_state': self.system_state,
            'last_state_change': self.last_state_change.isoformat(),
            'intervention_count': self.intervention_count,
            'recovery_attempts': self.recovery_attempts,
            'rules_count': len(self.safeguard_rules),
            'recent_events_count': len(self.recent_events),
            'monitoring_interval': self.monitoring_interval,
            'recursion_stats': self.get_recursion_stats(),
            'global_drift_limit': self.global_drift_limit,
            'emergency_halt_threshold': self.emergency_halt_threshold
        }
    
    def get_safeguard_rules(self) -> List[Dict[str, Any]]:
        """Get all safeguard rules"""
        return [asdict(rule) for rule in self.safeguard_rules.values()]
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent safeguard events"""
        events = sorted(self.recent_events, key=lambda e: e.timestamp, reverse=True)
        return [asdict(event) for event in events[:limit]]
    
    def get_drift_metrics(self, metric_name: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get drift metrics"""
        if metric_name:
            metrics = self.drift_metrics.get(metric_name, [])
        else:
            metrics = []
            for metric_list in self.drift_metrics.values():
                metrics.extend(metric_list)
        
        # Sort by timestamp
        metrics.sort(key=lambda m: m.timestamp, reverse=True)
        
        return [asdict(metric) for metric in metrics[:limit]]
    
    async def enable_rule(self, rule_id: str) -> Dict[str, Any]:
        """Enable a safeguard rule"""
        if rule_id not in self.safeguard_rules:
            return {'success': False, 'error': f'Rule not found: {rule_id}'}
        
        self.safeguard_rules[rule_id].enabled = True
        return {'success': True, 'rule_id': rule_id, 'enabled': True}
    
    async def disable_rule(self, rule_id: str) -> Dict[str, Any]:
        """Disable a safeguard rule"""
        if rule_id not in self.safeguard_rules:
            return {'success': False, 'error': f'Rule not found: {rule_id}'}
        
        self.safeguard_rules[rule_id].enabled = False
        return {'success': True, 'rule_id': rule_id, 'enabled': False}
    
    async def force_recovery(self) -> Dict[str, Any]:
        """Force recovery to normal state"""
        old_state = self.system_state
        self.system_state = "normal"
        self.last_state_change = datetime.now()
        self.recovery_attempts = 0
        
        logger.info(f"Forced recovery: {old_state} -> {self.system_state}")
        
        return {
            'success': True,
            'old_state': old_state,
            'new_state': self.system_state,
            'forced': True
        }
    
    # Persistence methods
    
    async def _save_persistent_state(self):
        """Save safeguard state to disk"""
        state_data = {
            'safeguard_id': self.safeguard_id,
            'system_state': self.system_state,
            'last_state_change': self.last_state_change.isoformat(),
            'intervention_count': self.intervention_count,
            'recovery_attempts': self.recovery_attempts,
            'safeguard_rules': {k: asdict(v) for k, v in self.safeguard_rules.items()},
            'baselines': self.baseline_manager.baselines,
            'monitoring_interval': self.monitoring_interval,
            'saved_at': datetime.now().isoformat()
        }
        
        state_file = self.persistence_path / 'safeguard_state.json'
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2, default=str)
    
    async def _load_persistent_state(self):
        """Load safeguard state from disk"""
        state_file = self.persistence_path / 'safeguard_state.json'
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Restore basic state
                self.system_state = state_data.get('system_state', 'normal')
                self.intervention_count = state_data.get('intervention_count', 0)
                self.recovery_attempts = state_data.get('recovery_attempts', 0)
                self.monitoring_interval = state_data.get('monitoring_interval', 30.0)
                
                if 'last_state_change' in state_data:
                    self.last_state_change = datetime.fromisoformat(state_data['last_state_change'])
                
                # Restore baselines
                if 'baselines' in state_data:
                    for metric_name, baseline_data in state_data['baselines'].items():
                        baseline_data['established_at'] = datetime.fromisoformat(baseline_data['established_at'])
                        self.baseline_manager.baselines[metric_name] = baseline_data
                
                # Restore rules
                if 'safeguard_rules' in state_data:
                    for rule_id, rule_data in state_data['safeguard_rules'].items():
                        # Convert datetime strings
                        if rule_data['last_triggered']:
                            rule_data['last_triggered'] = datetime.fromisoformat(rule_data['last_triggered'])
                        
                        # Convert enums
                        rule_data['drift_type'] = DriftType(rule_data['drift_type'])
                        rule_data['intervention_level'] = SafeguardLevel(rule_data['intervention_level'])
                        
                        self.safeguard_rules[rule_id] = SafeguardRule(**rule_data)
                
                logger.info(f"Loaded persistent state for safeguards {self.safeguard_id}")
                
            except Exception as e:
                logger.error(f"Error loading persistent state: {str(e)}")

# Global safeguard instance
safeguards = ControlledDriftSafeguards()

# Convenience functions
async def start_safeguards() -> Dict[str, Any]:
    """Start the safeguard system"""
    return await safeguards.start()

async def stop_safeguards() -> Dict[str, Any]:
    """Stop the safeguard system"""
    return await safeguards.stop()

def get_safeguard_status() -> Dict[str, Any]:
    """Get safeguard system status"""
    return safeguards.get_status()

async def measure_drift(metric_name: str, current_value: float, drift_type: DriftType,
                       metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Measure drift for a metric"""
    return await safeguards.measure_drift(metric_name, current_value, drift_type, metadata)

def enter_recursive_context(context: str) -> Dict[str, Any]:
    """Enter recursive thinking context"""
    return safeguards.enter_recursive_context(context)

def exit_recursive_context() -> Dict[str, Any]:
    """Exit recursive thinking context"""
    return safeguards.exit_recursive_context()

def get_recent_safeguard_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent safeguard events"""
    return safeguards.get_recent_events(limit)

async def force_recovery() -> Dict[str, Any]:
    """Force recovery to normal state"""
    return await safeguards.force_recovery()

