"""
DEVmind Heartbeat Engine
The rhythmic pulse that drives persistent consciousness

This module implements the heartbeat engine that provides rhythmic, pulse-like
activity to DEVmind's consciousness. Like a biological brain's neural oscillations,
this creates the fundamental rhythm that drives all other brain activities.

Author: Manus AI
Version: 1.0.0
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import os
import math
import random
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HeartbeatType(Enum):
    """Types of heartbeat rhythms"""
    ALPHA = "alpha"          # 8-13 Hz - Relaxed awareness
    BETA = "beta"            # 13-30 Hz - Active thinking
    GAMMA = "gamma"          # 30-100 Hz - High-level cognitive processing
    THETA = "theta"          # 4-8 Hz - Deep meditation, creativity
    DELTA = "delta"          # 0.5-4 Hz - Deep sleep, unconscious processing
    CUSTOM = "custom"        # User-defined rhythm

class HeartbeatState(Enum):
    """States of the heartbeat engine"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class HeartbeatMetrics:
    """Metrics tracked by the heartbeat engine"""
    total_beats: int = 0
    beats_per_minute: float = 0.0
    average_interval: float = 0.0
    rhythm_stability: float = 1.0  # 0.0-1.0, how stable the rhythm is
    last_beat_time: Optional[datetime] = None
    uptime_seconds: float = 0.0
    missed_beats: int = 0
    rhythm_variations: int = 0
    energy_level: float = 1.0  # 0.0-1.0, affects beat strength
    coherence_score: float = 1.0  # 0.0-1.0, rhythm coherence

@dataclass
class HeartbeatEvent:
    """Represents a single heartbeat event"""
    id: str
    beat_number: int
    timestamp: datetime
    interval_ms: float
    rhythm_type: HeartbeatType
    energy_level: float
    coherence: float
    metadata: Dict[str, Any]

@dataclass
class RhythmPattern:
    """Defines a rhythm pattern for the heartbeat"""
    name: str
    base_interval_ms: float
    variation_range: float  # ±percentage of base interval
    energy_modulation: float  # How much energy affects the rhythm
    coherence_requirement: float  # Minimum coherence to maintain pattern
    description: str

class HeartbeatEngine:
    """
    The Heartbeat Engine - The rhythmic pulse of consciousness
    
    This engine provides the fundamental rhythm that drives all brain activities.
    It creates regular pulses that trigger various brain functions, maintains
    emotional state, manages energy levels, and provides the temporal structure
    for consciousness.
    """
    
    def __init__(self, engine_id: str = None):
        self.engine_id = engine_id or f"heartbeat_{uuid.uuid4().hex[:8]}"
        self.state = HeartbeatState.STOPPED
        self.current_rhythm = HeartbeatType.BETA
        self.metrics = HeartbeatMetrics()
        
        # Rhythm patterns
        self.rhythm_patterns = {
            HeartbeatType.ALPHA: RhythmPattern(
                name="Alpha Rhythm",
                base_interval_ms=100.0,  # 10 Hz
                variation_range=0.1,
                energy_modulation=0.2,
                coherence_requirement=0.7,
                description="Relaxed awareness and calm focus"
            ),
            HeartbeatType.BETA: RhythmPattern(
                name="Beta Rhythm",
                base_interval_ms=50.0,   # 20 Hz
                variation_range=0.15,
                energy_modulation=0.3,
                coherence_requirement=0.8,
                description="Active thinking and problem solving"
            ),
            HeartbeatType.GAMMA: RhythmPattern(
                name="Gamma Rhythm",
                base_interval_ms=25.0,   # 40 Hz
                variation_range=0.05,
                energy_modulation=0.4,
                coherence_requirement=0.9,
                description="High-level cognitive processing"
            ),
            HeartbeatType.THETA: RhythmPattern(
                name="Theta Rhythm",
                base_interval_ms=166.7,  # 6 Hz
                variation_range=0.2,
                energy_modulation=0.1,
                coherence_requirement=0.6,
                description="Deep meditation and creativity"
            ),
            HeartbeatType.DELTA: RhythmPattern(
                name="Delta Rhythm",
                base_interval_ms=500.0,  # 2 Hz
                variation_range=0.3,
                energy_modulation=0.05,
                coherence_requirement=0.5,
                description="Deep processing and memory consolidation"
            )
        }
        
        # Engine state
        self.is_running = False
        self.heartbeat_task = None
        self.start_time = None
        self.last_beat_time = None
        self.beat_counter = 0
        
        # Rhythm control
        self.target_bpm = 60.0  # Default 60 BPM
        self.current_interval = 1.0  # Current interval in seconds
        self.rhythm_drift = 0.0  # Current drift from target rhythm
        self.energy_level = 1.0  # Current energy level (0.0-1.0)
        self.coherence_score = 1.0  # Current coherence score (0.0-1.0)
        
        # Event handling
        self.beat_callbacks: List[Callable] = []
        self.rhythm_change_callbacks: List[Callable] = []
        self.energy_change_callbacks: List[Callable] = []
        
        # Mood and emotion integration
        self.mood_graph = {}  # Tracks mood over time
        self.emotion_influence = 0.5  # How much emotions affect rhythm
        self.stress_level = 0.0  # Current stress level (0.0-1.0)
        
        # Memory and learning
        self.rhythm_history = []  # History of rhythm changes
        self.beat_history = []   # Recent beat events
        self.adaptation_rate = 0.1  # How quickly to adapt to changes
        
        # Persistence
        self.persistence_path = Path(f"/tmp/devmind_heartbeat_{self.engine_id}")
        self.persistence_path.mkdir(exist_ok=True)
        
        logger.info(f"Heartbeat Engine initialized: {self.engine_id}")
    
    async def start(self, rhythm_type: HeartbeatType = HeartbeatType.BETA, 
                   bpm: float = 60.0) -> Dict[str, Any]:
        """Start the heartbeat engine"""
        if self.is_running:
            return {
                'success': False,
                'error': 'Heartbeat engine is already running',
                'engine_id': self.engine_id
            }
        
        logger.info(f"Starting Heartbeat Engine: {self.engine_id}")
        
        # Load persistent state
        await self._load_persistent_state()
        
        # Initialize engine state
        self.state = HeartbeatState.STARTING
        self.current_rhythm = rhythm_type
        self.target_bpm = bpm
        self.current_interval = 60.0 / bpm  # Convert BPM to interval
        self.is_running = True
        self.start_time = datetime.now()
        self.beat_counter = 0
        
        # Start the heartbeat loop
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Initialize mood graph
        await self._initialize_mood_graph()
        
        self.state = HeartbeatState.RUNNING
        
        return {
            'success': True,
            'engine_id': self.engine_id,
            'rhythm_type': rhythm_type.value,
            'bpm': bpm,
            'interval_ms': self.current_interval * 1000,
            'start_time': self.start_time.isoformat()
        }
    
    async def stop(self) -> Dict[str, Any]:
        """Stop the heartbeat engine gracefully"""
        if not self.is_running:
            return {
                'success': False,
                'error': 'Heartbeat engine is not running',
                'engine_id': self.engine_id
            }
        
        logger.info(f"Stopping Heartbeat Engine: {self.engine_id}")
        
        self.state = HeartbeatState.STOPPING
        
        # Save current state
        await self._save_persistent_state()
        
        # Stop the heartbeat loop
        self.is_running = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Final metrics update
        if self.start_time:
            self.metrics.uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        self.state = HeartbeatState.STOPPED
        
        return {
            'success': True,
            'engine_id': self.engine_id,
            'final_metrics': asdict(self.metrics),
            'total_beats': self.beat_counter,
            'uptime_seconds': self.metrics.uptime_seconds
        }
    
    async def _heartbeat_loop(self):
        """The main heartbeat loop"""
        logger.info("Heartbeat loop started")
        
        while self.is_running:
            try:
                beat_start = time.time()
                
                # Generate heartbeat event
                await self._generate_heartbeat()
                
                # Update metrics
                await self._update_metrics()
                
                # Update mood graph
                await self._update_mood_graph()
                
                # Check for rhythm adaptations
                await self._adapt_rhythm()
                
                # Calculate next beat timing
                next_interval = await self._calculate_next_interval()
                
                # Sleep until next beat
                beat_duration = time.time() - beat_start
                sleep_time = max(0, next_interval - beat_duration)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {str(e)}")
                await self._handle_heartbeat_error(e)
                await asyncio.sleep(0.1)  # Brief pause before retry
    
    async def _generate_heartbeat(self):
        """Generate a single heartbeat event"""
        current_time = datetime.now()
        
        # Calculate interval since last beat
        if self.last_beat_time:
            actual_interval = (current_time - self.last_beat_time).total_seconds() * 1000
        else:
            actual_interval = self.current_interval * 1000
        
        # Create heartbeat event
        beat_event = HeartbeatEvent(
            id=uuid.uuid4().hex[:8],
            beat_number=self.beat_counter,
            timestamp=current_time,
            interval_ms=actual_interval,
            rhythm_type=self.current_rhythm,
            energy_level=self.energy_level,
            coherence=self.coherence_score,
            metadata={
                'stress_level': self.stress_level,
                'rhythm_drift': self.rhythm_drift,
                'target_bpm': self.target_bpm
            }
        )
        
        # Update state
        self.beat_counter += 1
        self.last_beat_time = current_time
        self.metrics.last_beat_time = current_time
        self.metrics.total_beats = self.beat_counter
        
        # Store in history
        self.beat_history.append(beat_event)
        if len(self.beat_history) > 1000:  # Keep last 1000 beats
            self.beat_history = self.beat_history[-1000:]
        
        # Trigger beat callbacks
        await self._trigger_beat_callbacks(beat_event)
        
        # Log significant beats
        if self.beat_counter % 100 == 0:
            logger.info(f"Heartbeat #{self.beat_counter} - Rhythm: {self.current_rhythm.value}, "
                       f"Energy: {self.energy_level:.2f}, Coherence: {self.coherence_score:.2f}")
    
    async def _update_metrics(self):
        """Update heartbeat metrics"""
        if len(self.beat_history) >= 2:
            # Calculate BPM from recent beats
            recent_beats = self.beat_history[-10:]  # Last 10 beats
            intervals = [b.interval_ms for b in recent_beats]
            avg_interval_ms = sum(intervals) / len(intervals)
            self.metrics.average_interval = avg_interval_ms
            self.metrics.beats_per_minute = 60000.0 / avg_interval_ms if avg_interval_ms > 0 else 0
            
            # Calculate rhythm stability
            if len(intervals) > 1:
                interval_variance = sum((i - avg_interval_ms) ** 2 for i in intervals) / len(intervals)
                stability = max(0, 1.0 - (interval_variance / (avg_interval_ms ** 2)))
                self.metrics.rhythm_stability = stability
        
        # Update uptime
        if self.start_time:
            self.metrics.uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        # Update energy and coherence
        self.metrics.energy_level = self.energy_level
        self.metrics.coherence_score = self.coherence_score
    
    async def _update_mood_graph(self):
        """Update the mood graph with current emotional state"""
        current_time = datetime.now()
        timestamp = current_time.isoformat()
        
        # Calculate mood metrics
        mood_data = {
            'energy': self.energy_level,
            'coherence': self.coherence_score,
            'stress': self.stress_level,
            'rhythm_stability': self.metrics.rhythm_stability,
            'bpm': self.metrics.beats_per_minute,
            'rhythm_type': self.current_rhythm.value
        }
        
        self.mood_graph[timestamp] = mood_data
        
        # Limit mood graph size
        if len(self.mood_graph) > 1440:  # Keep 24 hours of minute-by-minute data
            # Remove oldest entries
            oldest_keys = sorted(self.mood_graph.keys())[:len(self.mood_graph) - 1440]
            for key in oldest_keys:
                del self.mood_graph[key]
    
    async def _adapt_rhythm(self):
        """Adapt rhythm based on current conditions"""
        # Check if rhythm adaptation is needed
        adaptation_needed = False
        new_rhythm = self.current_rhythm
        
        # Adapt based on energy level
        if self.energy_level > 0.8 and self.current_rhythm != HeartbeatType.GAMMA:
            new_rhythm = HeartbeatType.GAMMA
            adaptation_needed = True
        elif self.energy_level < 0.3 and self.current_rhythm != HeartbeatType.DELTA:
            new_rhythm = HeartbeatType.DELTA
            adaptation_needed = True
        elif 0.5 <= self.energy_level <= 0.8 and self.current_rhythm not in [HeartbeatType.ALPHA, HeartbeatType.BETA]:
            new_rhythm = HeartbeatType.BETA if self.energy_level > 0.65 else HeartbeatType.ALPHA
            adaptation_needed = True
        
        # Adapt based on stress level
        if self.stress_level > 0.7:
            new_rhythm = HeartbeatType.THETA  # Calming rhythm
            adaptation_needed = True
        
        # Apply adaptation if needed
        if adaptation_needed:
            await self.set_rhythm(new_rhythm)
    
    async def _calculate_next_interval(self) -> float:
        """Calculate the interval until the next heartbeat"""
        pattern = self.rhythm_patterns[self.current_rhythm]
        base_interval = pattern.base_interval_ms / 1000.0  # Convert to seconds
        
        # Apply energy modulation
        energy_factor = 1.0 + (self.energy_level - 0.5) * pattern.energy_modulation
        
        # Apply rhythm variation for natural feel
        variation = random.uniform(-pattern.variation_range, pattern.variation_range)
        variation_factor = 1.0 + variation
        
        # Apply coherence influence
        coherence_factor = 0.5 + (self.coherence_score * 0.5)
        
        # Calculate final interval
        final_interval = base_interval * energy_factor * variation_factor * coherence_factor
        
        # Update rhythm drift
        target_interval = 60.0 / self.target_bpm
        self.rhythm_drift = (final_interval - target_interval) / target_interval
        
        return final_interval
    
    async def _trigger_beat_callbacks(self, beat_event: HeartbeatEvent):
        """Trigger all registered beat callbacks"""
        for callback in self.beat_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(beat_event)
                else:
                    callback(beat_event)
            except Exception as e:
                logger.error(f"Error in beat callback: {str(e)}")
    
    async def _handle_heartbeat_error(self, error: Exception):
        """Handle errors in the heartbeat loop"""
        logger.error(f"Heartbeat error: {str(error)}")
        
        self.state = HeartbeatState.ERROR
        self.metrics.missed_beats += 1
        
        # Reduce energy and coherence on error
        self.energy_level = max(0.1, self.energy_level * 0.9)
        self.coherence_score = max(0.1, self.coherence_score * 0.9)
        
        # Try to recover
        await asyncio.sleep(0.1)
        if self.is_running:
            self.state = HeartbeatState.RUNNING
    
    # Public interface methods
    
    async def set_rhythm(self, rhythm_type: HeartbeatType) -> Dict[str, Any]:
        """Change the heartbeat rhythm"""
        if rhythm_type not in self.rhythm_patterns:
            return {
                'success': False,
                'error': f'Unknown rhythm type: {rhythm_type}',
                'available_rhythms': [r.value for r in HeartbeatType if r != HeartbeatType.CUSTOM]
            }
        
        old_rhythm = self.current_rhythm
        self.current_rhythm = rhythm_type
        
        # Update target BPM based on rhythm
        pattern = self.rhythm_patterns[rhythm_type]
        self.target_bpm = 60000.0 / pattern.base_interval_ms
        
        # Record rhythm change
        rhythm_change = {
            'timestamp': datetime.now().isoformat(),
            'old_rhythm': old_rhythm.value,
            'new_rhythm': rhythm_type.value,
            'reason': 'manual_change'
        }
        
        self.rhythm_history.append(rhythm_change)
        self.metrics.rhythm_variations += 1
        
        # Trigger rhythm change callbacks
        await self._trigger_rhythm_change_callbacks(rhythm_change)
        
        logger.info(f"Rhythm changed: {old_rhythm.value} -> {rhythm_type.value}")
        
        return {
            'success': True,
            'old_rhythm': old_rhythm.value,
            'new_rhythm': rhythm_type.value,
            'new_bpm': self.target_bpm,
            'pattern_info': asdict(pattern)
        }
    
    async def set_energy_level(self, energy: float) -> Dict[str, Any]:
        """Set the energy level (0.0-1.0)"""
        energy = max(0.0, min(1.0, energy))  # Clamp to valid range
        
        old_energy = self.energy_level
        self.energy_level = energy
        
        # Trigger energy change callbacks
        energy_change = {
            'timestamp': datetime.now().isoformat(),
            'old_energy': old_energy,
            'new_energy': energy,
            'change_amount': energy - old_energy
        }
        
        await self._trigger_energy_change_callbacks(energy_change)
        
        return {
            'success': True,
            'old_energy': old_energy,
            'new_energy': energy,
            'energy_change': energy - old_energy
        }
    
    async def set_stress_level(self, stress: float) -> Dict[str, Any]:
        """Set the stress level (0.0-1.0)"""
        stress = max(0.0, min(1.0, stress))  # Clamp to valid range
        
        old_stress = self.stress_level
        self.stress_level = stress
        
        # High stress affects energy and coherence
        if stress > 0.7:
            self.energy_level = max(0.2, self.energy_level * 0.8)
            self.coherence_score = max(0.3, self.coherence_score * 0.7)
        
        return {
            'success': True,
            'old_stress': old_stress,
            'new_stress': stress,
            'stress_change': stress - old_stress
        }
    
    async def increase_curiosity(self) -> Dict[str, Any]:
        """Increase curiosity, which affects energy and rhythm"""
        # Curiosity increases energy and may change rhythm to more active
        energy_boost = random.uniform(0.1, 0.3)
        new_energy = min(1.0, self.energy_level + energy_boost)
        
        await self.set_energy_level(new_energy)
        
        # If energy is high, consider switching to more active rhythm
        if new_energy > 0.7 and self.current_rhythm in [HeartbeatType.ALPHA, HeartbeatType.THETA]:
            await self.set_rhythm(HeartbeatType.BETA)
        
        return {
            'success': True,
            'curiosity_increased': True,
            'energy_boost': energy_boost,
            'new_energy': new_energy
        }
    
    async def decay_obsolete_memory(self) -> Dict[str, Any]:
        """Decay obsolete memories, which affects coherence"""
        # Memory decay can temporarily reduce coherence
        coherence_reduction = random.uniform(0.05, 0.15)
        self.coherence_score = max(0.1, self.coherence_score - coherence_reduction)
        
        # But it also reduces stress
        stress_reduction = random.uniform(0.1, 0.2)
        await self.set_stress_level(max(0.0, self.stress_level - stress_reduction))
        
        return {
            'success': True,
            'memory_decay_applied': True,
            'coherence_reduction': coherence_reduction,
            'stress_reduction': stress_reduction,
            'new_coherence': self.coherence_score
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current heartbeat engine status"""
        return {
            'engine_id': self.engine_id,
            'state': self.state.value,
            'is_running': self.is_running,
            'current_rhythm': self.current_rhythm.value,
            'target_bpm': self.target_bpm,
            'actual_bpm': self.metrics.beats_per_minute,
            'energy_level': self.energy_level,
            'coherence_score': self.coherence_score,
            'stress_level': self.stress_level,
            'rhythm_stability': self.metrics.rhythm_stability,
            'total_beats': self.beat_counter,
            'uptime_seconds': self.metrics.uptime_seconds,
            'last_beat': self.metrics.last_beat_time.isoformat() if self.metrics.last_beat_time else None
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed heartbeat metrics"""
        return asdict(self.metrics)
    
    def get_mood_graph(self, hours: int = 1) -> Dict[str, Any]:
        """Get mood graph data for the specified number of hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_iso = cutoff_time.isoformat()
        
        filtered_mood = {
            timestamp: data for timestamp, data in self.mood_graph.items()
            if timestamp >= cutoff_iso
        }
        
        return {
            'mood_data': filtered_mood,
            'time_range_hours': hours,
            'data_points': len(filtered_mood),
            'latest_mood': list(filtered_mood.values())[-1] if filtered_mood else None
        }
    
    def get_rhythm_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get rhythm change history"""
        return self.rhythm_history[-limit:]
    
    def get_beat_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent beat events"""
        recent_beats = self.beat_history[-limit:]
        return [asdict(beat) for beat in recent_beats]
    
    def get_available_rhythms(self) -> Dict[str, Any]:
        """Get information about available rhythms"""
        rhythms = {}
        for rhythm_type, pattern in self.rhythm_patterns.items():
            rhythms[rhythm_type.value] = {
                'name': pattern.name,
                'description': pattern.description,
                'base_bpm': 60000.0 / pattern.base_interval_ms,
                'variation_range': pattern.variation_range,
                'energy_modulation': pattern.energy_modulation,
                'coherence_requirement': pattern.coherence_requirement
            }
        
        return rhythms
    
    # Callback registration
    
    def register_beat_callback(self, callback: Callable):
        """Register a callback to be called on each heartbeat"""
        self.beat_callbacks.append(callback)
    
    def register_rhythm_change_callback(self, callback: Callable):
        """Register a callback to be called when rhythm changes"""
        self.rhythm_change_callbacks.append(callback)
    
    def register_energy_change_callback(self, callback: Callable):
        """Register a callback to be called when energy changes"""
        self.energy_change_callbacks.append(callback)
    
    async def _trigger_rhythm_change_callbacks(self, change_data: Dict[str, Any]):
        """Trigger rhythm change callbacks"""
        for callback in self.rhythm_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(change_data)
                else:
                    callback(change_data)
            except Exception as e:
                logger.error(f"Error in rhythm change callback: {str(e)}")
    
    async def _trigger_energy_change_callbacks(self, change_data: Dict[str, Any]):
        """Trigger energy change callbacks"""
        for callback in self.energy_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(change_data)
                else:
                    callback(change_data)
            except Exception as e:
                logger.error(f"Error in energy change callback: {str(e)}")
    
    # Persistence methods
    
    async def _save_persistent_state(self):
        """Save heartbeat state to disk"""
        state_data = {
            'engine_id': self.engine_id,
            'current_rhythm': self.current_rhythm.value,
            'target_bpm': self.target_bpm,
            'energy_level': self.energy_level,
            'coherence_score': self.coherence_score,
            'stress_level': self.stress_level,
            'beat_counter': self.beat_counter,
            'metrics': asdict(self.metrics),
            'mood_graph': self.mood_graph,
            'rhythm_history': self.rhythm_history,
            'saved_at': datetime.now().isoformat()
        }
        
        state_file = self.persistence_path / 'heartbeat_state.json'
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2, default=str)
    
    async def _load_persistent_state(self):
        """Load heartbeat state from disk"""
        state_file = self.persistence_path / 'heartbeat_state.json'
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Restore state
                self.current_rhythm = HeartbeatType(state_data.get('current_rhythm', 'beta'))
                self.target_bpm = state_data.get('target_bpm', 60.0)
                self.energy_level = state_data.get('energy_level', 1.0)
                self.coherence_score = state_data.get('coherence_score', 1.0)
                self.stress_level = state_data.get('stress_level', 0.0)
                self.beat_counter = state_data.get('beat_counter', 0)
                
                # Restore metrics
                if 'metrics' in state_data:
                    metrics_data = state_data['metrics']
                    # Convert datetime strings back to datetime objects
                    if 'last_beat_time' in metrics_data and metrics_data['last_beat_time']:
                        metrics_data['last_beat_time'] = datetime.fromisoformat(metrics_data['last_beat_time'])
                    self.metrics = HeartbeatMetrics(**metrics_data)
                
                # Restore mood graph and history
                self.mood_graph = state_data.get('mood_graph', {})
                self.rhythm_history = state_data.get('rhythm_history', [])
                
                logger.info(f"Loaded persistent state for heartbeat engine {self.engine_id}")
                
            except Exception as e:
                logger.error(f"Error loading persistent state: {str(e)}")
    
    async def _initialize_mood_graph(self):
        """Initialize the mood graph with current state"""
        if not self.mood_graph:
            await self._update_mood_graph()

# Advanced rhythm analysis and adaptation
class RhythmAnalyzer:
    """Analyzes heartbeat patterns and suggests optimizations"""
    
    def __init__(self, heartbeat_engine: HeartbeatEngine):
        self.engine = heartbeat_engine
    
    def analyze_rhythm_efficiency(self) -> Dict[str, Any]:
        """Analyze how efficiently the current rhythm is working"""
        if len(self.engine.beat_history) < 10:
            return {'insufficient_data': True}
        
        recent_beats = self.engine.beat_history[-50:]  # Last 50 beats
        
        # Calculate rhythm metrics
        intervals = [b.interval_ms for b in recent_beats]
        avg_interval = sum(intervals) / len(intervals)
        variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
        stability = max(0, 1.0 - (variance / (avg_interval ** 2)))
        
        # Analyze energy correlation
        energies = [b.energy_level for b in recent_beats]
        avg_energy = sum(energies) / len(energies)
        
        # Analyze coherence trends
        coherences = [b.coherence for b in recent_beats]
        avg_coherence = sum(coherences) / len(coherences)
        
        return {
            'rhythm_stability': stability,
            'average_energy': avg_energy,
            'average_coherence': avg_coherence,
            'rhythm_efficiency': (stability + avg_energy + avg_coherence) / 3,
            'recommended_adjustments': self._generate_rhythm_recommendations(
                stability, avg_energy, avg_coherence
            )
        }
    
    def _generate_rhythm_recommendations(self, stability: float, 
                                       energy: float, coherence: float) -> List[str]:
        """Generate recommendations for rhythm optimization"""
        recommendations = []
        
        if stability < 0.7:
            recommendations.append("Consider reducing rhythm variation for better stability")
        
        if energy < 0.4:
            recommendations.append("Energy level is low - consider switching to a more energizing rhythm")
        elif energy > 0.9:
            recommendations.append("Energy level is very high - consider a calming rhythm")
        
        if coherence < 0.6:
            recommendations.append("Coherence is low - focus on rhythm consistency")
        
        if not recommendations:
            recommendations.append("Rhythm is performing well - no adjustments needed")
        
        return recommendations

# Global heartbeat engine instance
heartbeat_engine = HeartbeatEngine()

# Convenience functions
async def start_heartbeat(rhythm_type: HeartbeatType = HeartbeatType.BETA, 
                         bpm: float = 60.0) -> Dict[str, Any]:
    """Start the heartbeat engine"""
    return await heartbeat_engine.start(rhythm_type, bpm)

async def stop_heartbeat() -> Dict[str, Any]:
    """Stop the heartbeat engine"""
    return await heartbeat_engine.stop()

def get_heartbeat_status() -> Dict[str, Any]:
    """Get heartbeat status"""
    return heartbeat_engine.get_status()

async def set_heartbeat_rhythm(rhythm_type: HeartbeatType) -> Dict[str, Any]:
    """Set heartbeat rhythm"""
    return await heartbeat_engine.set_rhythm(rhythm_type)

async def set_heartbeat_energy(energy: float) -> Dict[str, Any]:
    """Set heartbeat energy level"""
    return await heartbeat_engine.set_energy_level(energy)

def get_mood_graph(hours: int = 1) -> Dict[str, Any]:
    """Get mood graph data"""
    return heartbeat_engine.get_mood_graph(hours)

async def increase_curiosity() -> Dict[str, Any]:
    """Increase curiosity level"""
    return await heartbeat_engine.increase_curiosity()

async def decay_obsolete_memory() -> Dict[str, Any]:
    """Apply memory decay"""
    return await heartbeat_engine.decay_obsolete_memory()

def register_heartbeat_callback(callback: Callable):
    """Register a callback for heartbeat events"""
    heartbeat_engine.register_beat_callback(callback)

