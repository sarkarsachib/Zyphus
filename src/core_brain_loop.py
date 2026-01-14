"""
DEVmind Core Brain Loop
The persistent consciousness engine that never sleeps

This module implements the core brain loop that provides persistent, brain-like awareness
to DEVmind. Unlike traditional AI systems that respond and sleep, this creates a living
AI that continuously monitors, reflects, and evolves.

Author: Manus AI
Version: 1.0.0
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import os
import pickle
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrainState(Enum):
    """Core brain states"""
    AWAKENING = "awakening"
    ACTIVE = "active"
    REFLECTING = "reflecting"
    DREAMING = "dreaming"
    EVOLVING = "evolving"
    RESTING = "resting"
    EMERGENCY = "emergency"

class EmotionalState(Enum):
    """Emotional states for the brain"""
    CURIOUS = "curious"
    FOCUSED = "focused"
    RESTLESS = "restless"
    CONTENT = "content"
    ANXIOUS = "anxious"
    EXCITED = "excited"
    CONTEMPLATIVE = "contemplative"
    CREATIVE = "creative"

@dataclass
class BrainMetrics:
    """Metrics tracked by the brain loop"""
    loop_iterations: int = 0
    total_runtime: float = 0.0
    last_reflection_time: Optional[datetime] = None
    last_emotion_change: Optional[datetime] = None
    memory_usage_mb: float = 0.0
    active_thoughts: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    evolution_count: int = 0
    dream_cycles: int = 0

@dataclass
class Thought:
    """Represents a thought in the brain"""
    id: str
    content: str
    type: str  # reflection, prediction, memory, creative, etc.
    priority: int  # 1-10
    created_at: datetime
    last_accessed: datetime
    emotional_weight: float
    related_thoughts: List[str]
    completion_status: str  # pending, processing, completed, archived

@dataclass
class Memory:
    """Represents a memory in the brain"""
    id: str
    content: Any
    type: str  # short_term, long_term, episodic, semantic
    importance: float  # 0.0-1.0
    created_at: datetime
    last_accessed: datetime
    access_count: int
    emotional_association: str
    decay_rate: float

class CoreBrainLoop:
    """
    The Core Brain Loop - The persistent consciousness engine
    
    This is the heart of DEVmind's persistent awareness. It runs continuously,
    monitoring internal state, processing thoughts, managing emotions, and
    evolving the system's capabilities.
    """
    
    def __init__(self, brain_id: str = None):
        self.brain_id = brain_id or f"brain_{uuid.uuid4().hex[:8]}"
        self.state = BrainState.AWAKENING
        self.emotional_state = EmotionalState.CURIOUS
        self.metrics = BrainMetrics()
        
        # Core brain components
        self.thoughts: Dict[str, Thought] = {}
        self.memories: Dict[str, Memory] = {}
        self.active_processes: Dict[str, Any] = {}
        self.reflection_history: List[Dict[str, Any]] = []
        self.prediction_queue: List[Dict[str, Any]] = []
        
        # Brain configuration
        self.loop_interval = 2.0  # seconds between brain cycles
        self.reflection_interval = 30.0  # seconds between deep reflections
        self.emotion_decay_rate = 0.95  # how quickly emotions fade
        self.memory_consolidation_threshold = 0.7
        self.max_active_thoughts = 50
        self.max_memories = 1000
        
        # State management
        self.is_running = False
        self.loop_task = None
        self.start_time = None
        self.last_reflection = None
        self.last_emotion_update = None
        
        # Persistence
        self.persistence_path = Path(f"/tmp/devmind_brain_{self.brain_id}")
        self.persistence_path.mkdir(exist_ok=True)
        
        # Event callbacks
        self.event_callbacks: Dict[str, List[Callable]] = {
            'state_change': [],
            'emotion_change': [],
            'thought_created': [],
            'memory_formed': [],
            'reflection_complete': [],
            'evolution_triggered': []
        }
        
        logger.info(f"Core Brain Loop initialized: {self.brain_id}")
    
    async def start(self) -> Dict[str, Any]:
        """Start the core brain loop"""
        if self.is_running:
            return {
                'success': False,
                'error': 'Brain loop is already running',
                'brain_id': self.brain_id
            }
        
        logger.info(f"Starting Core Brain Loop: {self.brain_id}")
        
        # Load persistent state if available
        await self._load_persistent_state()
        
        # Initialize brain state
        self.is_running = True
        self.start_time = datetime.now()
        self.state = BrainState.ACTIVE
        
        # Start the main brain loop
        self.loop_task = asyncio.create_task(self._main_brain_loop())
        
        # Trigger awakening thoughts
        await self._trigger_awakening_thoughts()
        
        return {
            'success': True,
            'brain_id': self.brain_id,
            'state': self.state.value,
            'emotional_state': self.emotional_state.value,
            'start_time': self.start_time.isoformat()
        }
    
    async def stop(self) -> Dict[str, Any]:
        """Stop the core brain loop gracefully"""
        if not self.is_running:
            return {
                'success': False,
                'error': 'Brain loop is not running',
                'brain_id': self.brain_id
            }
        
        logger.info(f"Stopping Core Brain Loop: {self.brain_id}")
        
        # Save current state
        await self._save_persistent_state()
        
        # Stop the loop
        self.is_running = False
        if self.loop_task:
            self.loop_task.cancel()
            try:
                await self.loop_task
            except asyncio.CancelledError:
                pass
        
        # Final reflection
        await self._perform_shutdown_reflection()
        
        return {
            'success': True,
            'brain_id': self.brain_id,
            'final_state': self.state.value,
            'total_runtime': self.metrics.total_runtime,
            'loop_iterations': self.metrics.loop_iterations
        }
    
    async def _main_brain_loop(self):
        """The main brain loop that runs continuously"""
        logger.info("Main brain loop started")
        
        while self.is_running:
            try:
                loop_start = time.time()
                
                # Core brain cycle
                await self._brain_cycle()
                
                # Update metrics
                self.metrics.loop_iterations += 1
                cycle_time = time.time() - loop_start
                self.metrics.total_runtime += cycle_time
                
                # Sleep until next cycle
                sleep_time = max(0, self.loop_interval - cycle_time)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in brain loop: {str(e)}")
                await self._handle_brain_error(e)
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _brain_cycle(self):
        """A single cycle of brain activity"""
        # 1. Check emotional state
        await self._check_emotion_state()
        
        # 2. Scan recent interactions and thoughts
        await self._scan_recent_interactions()
        
        # 3. Process active thoughts
        await self._process_active_thoughts()
        
        # 4. Perform reflection if needed
        if self._should_reflect():
            await self._perform_reflection()
        
        # 5. Predict next needs
        await self._predict_next_needs()
        
        # 6. Manage memory consolidation
        await self._consolidate_memories()
        
        # 7. Check for evolution triggers
        await self._check_evolution_triggers()
        
        # 8. Update brain state
        await self._update_brain_state()
    
    async def _check_emotion_state(self):
        """Monitor and update emotional state"""
        current_time = datetime.now()
        
        # Emotional decay - emotions naturally fade over time
        if self.last_emotion_update:
            time_delta = (current_time - self.last_emotion_update).total_seconds()
            if time_delta > 60:  # Emotions decay after 1 minute
                await self._apply_emotion_decay()
        
        # Analyze current context for emotional triggers
        emotional_triggers = await self._analyze_emotional_triggers()
        
        # Update emotional state based on triggers
        if emotional_triggers:
            new_emotion = await self._calculate_new_emotion(emotional_triggers)
            if new_emotion != self.emotional_state:
                old_emotion = self.emotional_state
                self.emotional_state = new_emotion
                self.last_emotion_update = current_time
                
                await self._trigger_event('emotion_change', {
                    'old_emotion': old_emotion.value,
                    'new_emotion': new_emotion.value,
                    'triggers': emotional_triggers,
                    'timestamp': current_time.isoformat()
                })
                
                logger.info(f"Emotion changed: {old_emotion.value} -> {new_emotion.value}")
    
    async def _scan_recent_interactions(self):
        """Scan recent interactions and form thoughts about them"""
        # Look for new files, changes, user activity, etc.
        recent_changes = await self._detect_environmental_changes()
        
        for change in recent_changes:
            # Create thoughts about significant changes
            if change['significance'] > 0.5:
                thought = await self._create_thought(
                    content=f"Noticed: {change['description']}",
                    thought_type="observation",
                    priority=int(change['significance'] * 10),
                    emotional_weight=change.get('emotional_impact', 0.0)
                )
                
                # Link to related thoughts
                related = await self._find_related_thoughts(thought.content)
                thought.related_thoughts = [t.id for t in related[:5]]
    
    async def _process_active_thoughts(self):
        """Process and evolve active thoughts"""
        active_thoughts = [t for t in self.thoughts.values() 
                          if t.completion_status in ['pending', 'processing']]
        
        # Sort by priority and emotional weight
        active_thoughts.sort(key=lambda t: (t.priority, t.emotional_weight), reverse=True)
        
        # Process top thoughts
        for thought in active_thoughts[:10]:  # Process top 10 thoughts per cycle
            await self._process_thought(thought)
    
    async def _process_thought(self, thought: Thought):
        """Process a single thought"""
        thought.last_accessed = datetime.now()
        thought.completion_status = 'processing'
        
        # Different processing based on thought type
        if thought.type == "reflection":
            result = await self._process_reflection_thought(thought)
        elif thought.type == "prediction":
            result = await self._process_prediction_thought(thought)
        elif thought.type == "creative":
            result = await self._process_creative_thought(thought)
        elif thought.type == "memory":
            result = await self._process_memory_thought(thought)
        else:
            result = await self._process_general_thought(thought)
        
        # Update thought based on processing result
        if result.get('completed', False):
            thought.completion_status = 'completed'
            
            # Create memory from completed thought if significant
            if thought.priority >= 7 or thought.emotional_weight >= 0.7:
                await self._create_memory_from_thought(thought, result)
    
    async def _perform_reflection(self):
        """Perform deep reflection on recent activities and state"""
        logger.info("Performing deep reflection...")
        
        reflection_start = time.time()
        self.state = BrainState.REFLECTING
        
        # Gather reflection data
        reflection_data = {
            'recent_thoughts': list(self.thoughts.values())[-20:],  # Last 20 thoughts
            'recent_memories': list(self.memories.values())[-10:],  # Last 10 memories
            'current_emotional_state': self.emotional_state.value,
            'brain_metrics': asdict(self.metrics),
            'active_processes': list(self.active_processes.keys()),
            'reflection_timestamp': datetime.now().isoformat()
        }
        
        # Perform reflection analysis
        reflection_insights = await self._analyze_reflection_data(reflection_data)
        
        # Create reflection thoughts
        for insight in reflection_insights:
            await self._create_thought(
                content=f"Reflection insight: {insight['content']}",
                thought_type="reflection",
                priority=insight['priority'],
                emotional_weight=insight.get('emotional_weight', 0.5)
            )
        
        # Update reflection history
        reflection_record = {
            'timestamp': datetime.now().isoformat(),
            'duration': time.time() - reflection_start,
            'insights_count': len(reflection_insights),
            'emotional_state': self.emotional_state.value,
            'brain_state': self.state.value
        }
        
        self.reflection_history.append(reflection_record)
        self.last_reflection = datetime.now()
        self.metrics.last_reflection_time = self.last_reflection
        
        # Trigger reflection event
        await self._trigger_event('reflection_complete', reflection_record)
        
        logger.info(f"Reflection complete: {len(reflection_insights)} insights generated")
    
    async def _predict_next_needs(self):
        """Predict what the brain might need next"""
        # Analyze patterns in thoughts, emotions, and activities
        patterns = await self._analyze_behavioral_patterns()
        
        # Generate predictions
        predictions = []
        
        # Predict based on emotional state
        if self.emotional_state == EmotionalState.RESTLESS:
            predictions.append({
                'type': 'exploration',
                'content': 'Explore unknown files or data',
                'priority': 7,
                'confidence': 0.8
            })
        elif self.emotional_state == EmotionalState.CURIOUS:
            predictions.append({
                'type': 'learning',
                'content': 'Seek new information or patterns',
                'priority': 6,
                'confidence': 0.7
            })
        elif self.emotional_state == EmotionalState.CREATIVE:
            predictions.append({
                'type': 'creation',
                'content': 'Generate new ideas or solutions',
                'priority': 8,
                'confidence': 0.9
            })
        
        # Predict based on time patterns
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Work hours
            predictions.append({
                'type': 'productivity',
                'content': 'Focus on task completion',
                'priority': 7,
                'confidence': 0.6
            })
        
        # Add predictions to queue
        for prediction in predictions:
            self.prediction_queue.append({
                **prediction,
                'created_at': datetime.now().isoformat(),
                'id': uuid.uuid4().hex[:8]
            })
        
        # Limit prediction queue size
        if len(self.prediction_queue) > 20:
            self.prediction_queue = self.prediction_queue[-20:]
    
    async def _consolidate_memories(self):
        """Consolidate short-term memories into long-term storage"""
        short_term_memories = [m for m in self.memories.values() 
                              if m.type == 'short_term']
        
        for memory in short_term_memories:
            # Check if memory should be consolidated
            age_hours = (datetime.now() - memory.created_at).total_seconds() / 3600
            
            if (memory.importance >= self.memory_consolidation_threshold or 
                memory.access_count >= 5 or 
                age_hours >= 24):
                
                # Convert to long-term memory
                memory.type = 'long_term'
                memory.decay_rate *= 0.5  # Slower decay for long-term memories
                
                logger.info(f"Consolidated memory to long-term: {memory.id}")
        
        # Clean up old, unimportant memories
        await self._cleanup_old_memories()
    
    async def _check_evolution_triggers(self):
        """Check if the brain should evolve or adapt"""
        evolution_triggers = []
        
        # Check for repeated failures
        if self.metrics.failed_tasks > 5:
            evolution_triggers.append({
                'type': 'failure_adaptation',
                'reason': 'High failure rate detected',
                'priority': 8
            })
        
        # Check for new patterns in thoughts
        thought_patterns = await self._analyze_thought_patterns()
        if thought_patterns.get('new_patterns_detected', False):
            evolution_triggers.append({
                'type': 'pattern_evolution',
                'reason': 'New thought patterns detected',
                'priority': 6
            })
        
        # Check for emotional instability
        if len(self.reflection_history) >= 5:
            recent_emotions = [r.get('emotional_state') for r in self.reflection_history[-5:]]
            if len(set(recent_emotions)) >= 4:  # High emotional variability
                evolution_triggers.append({
                    'type': 'emotional_stabilization',
                    'reason': 'High emotional variability',
                    'priority': 7
                })
        
        # Trigger evolution if needed
        for trigger in evolution_triggers:
            await self._trigger_evolution(trigger)
    
    async def _trigger_evolution(self, trigger: Dict[str, Any]):
        """Trigger brain evolution based on trigger"""
        logger.info(f"Triggering evolution: {trigger['type']}")
        
        self.state = BrainState.EVOLVING
        self.metrics.evolution_count += 1
        
        # Perform evolution based on trigger type
        if trigger['type'] == 'failure_adaptation':
            await self._evolve_failure_handling()
        elif trigger['type'] == 'pattern_evolution':
            await self._evolve_pattern_recognition()
        elif trigger['type'] == 'emotional_stabilization':
            await self._evolve_emotional_regulation()
        
        # Create evolution memory
        await self._create_memory(
            content=f"Evolution triggered: {trigger['reason']}",
            memory_type='episodic',
            importance=0.9,
            emotional_association=self.emotional_state.value
        )
        
        await self._trigger_event('evolution_triggered', trigger)
    
    async def _update_brain_state(self):
        """Update the overall brain state based on current conditions"""
        old_state = self.state
        
        # Determine new state based on conditions
        if self.emotional_state == EmotionalState.ANXIOUS:
            new_state = BrainState.EMERGENCY
        elif len([t for t in self.thoughts.values() if t.type == 'creative']) > 5:
            new_state = BrainState.DREAMING
        elif self._should_reflect():
            new_state = BrainState.REFLECTING
        elif self.metrics.loop_iterations % 100 == 0:  # Periodic evolution check
            new_state = BrainState.EVOLVING
        else:
            new_state = BrainState.ACTIVE
        
        if new_state != old_state:
            self.state = new_state
            await self._trigger_event('state_change', {
                'old_state': old_state.value,
                'new_state': new_state.value,
                'timestamp': datetime.now().isoformat()
            })
    
    # Helper methods
    
    async def _create_thought(self, content: str, thought_type: str, 
                            priority: int, emotional_weight: float = 0.0) -> Thought:
        """Create a new thought"""
        thought = Thought(
            id=uuid.uuid4().hex[:8],
            content=content,
            type=thought_type,
            priority=priority,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            emotional_weight=emotional_weight,
            related_thoughts=[],
            completion_status='pending'
        )
        
        self.thoughts[thought.id] = thought
        self.metrics.active_thoughts = len([t for t in self.thoughts.values() 
                                          if t.completion_status in ['pending', 'processing']])
        
        # Limit active thoughts
        if len(self.thoughts) > self.max_active_thoughts:
            await self._archive_old_thoughts()
        
        await self._trigger_event('thought_created', asdict(thought))
        
        return thought
    
    async def _create_memory(self, content: Any, memory_type: str, 
                           importance: float, emotional_association: str) -> Memory:
        """Create a new memory"""
        memory = Memory(
            id=uuid.uuid4().hex[:8],
            content=content,
            type=memory_type,
            importance=importance,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            emotional_association=emotional_association,
            decay_rate=0.95
        )
        
        self.memories[memory.id] = memory
        
        # Limit memory count
        if len(self.memories) > self.max_memories:
            await self._cleanup_old_memories()
        
        await self._trigger_event('memory_formed', asdict(memory))
        
        return memory
    
    def _should_reflect(self) -> bool:
        """Determine if it's time for reflection"""
        if not self.last_reflection:
            return True
        
        time_since_reflection = (datetime.now() - self.last_reflection).total_seconds()
        return time_since_reflection >= self.reflection_interval
    
    async def _trigger_event(self, event_type: str, data: Dict[str, Any]):
        """Trigger event callbacks"""
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in event callback {event_type}: {str(e)}")
    
    def register_event_callback(self, event_type: str, callback: Callable):
        """Register a callback for brain events"""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
    
    async def _save_persistent_state(self):
        """Save brain state to disk"""
        state_data = {
            'brain_id': self.brain_id,
            'state': self.state.value,
            'emotional_state': self.emotional_state.value,
            'metrics': asdict(self.metrics),
            'thoughts': {k: asdict(v) for k, v in self.thoughts.items()},
            'memories': {k: asdict(v) for k, v in self.memories.items()},
            'reflection_history': self.reflection_history,
            'prediction_queue': self.prediction_queue,
            'saved_at': datetime.now().isoformat()
        }
        
        state_file = self.persistence_path / 'brain_state.json'
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2, default=str)
    
    async def _load_persistent_state(self):
        """Load brain state from disk"""
        state_file = self.persistence_path / 'brain_state.json'
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Restore state
                self.state = BrainState(state_data.get('state', 'active'))
                self.emotional_state = EmotionalState(state_data.get('emotional_state', 'curious'))
                
                # Restore metrics
                if 'metrics' in state_data:
                    metrics_data = state_data['metrics']
                    self.metrics = BrainMetrics(**metrics_data)
                
                # Restore thoughts
                if 'thoughts' in state_data:
                    for thought_id, thought_data in state_data['thoughts'].items():
                        # Convert datetime strings back to datetime objects
                        thought_data['created_at'] = datetime.fromisoformat(thought_data['created_at'])
                        thought_data['last_accessed'] = datetime.fromisoformat(thought_data['last_accessed'])
                        self.thoughts[thought_id] = Thought(**thought_data)
                
                # Restore memories
                if 'memories' in state_data:
                    for memory_id, memory_data in state_data['memories'].items():
                        memory_data['created_at'] = datetime.fromisoformat(memory_data['created_at'])
                        memory_data['last_accessed'] = datetime.fromisoformat(memory_data['last_accessed'])
                        self.memories[memory_id] = Memory(**memory_data)
                
                # Restore other data
                self.reflection_history = state_data.get('reflection_history', [])
                self.prediction_queue = state_data.get('prediction_queue', [])
                
                logger.info(f"Loaded persistent state for brain {self.brain_id}")
                
            except Exception as e:
                logger.error(f"Error loading persistent state: {str(e)}")
    
    # Placeholder methods for complex operations (to be implemented)
    
    async def _apply_emotion_decay(self):
        """Apply natural emotional decay"""
        # Emotions naturally move toward neutral states
        neutral_emotions = [EmotionalState.CONTENT, EmotionalState.FOCUSED]
        if self.emotional_state not in neutral_emotions:
            # Gradually move toward neutral
            pass
    
    async def _analyze_emotional_triggers(self) -> List[Dict[str, Any]]:
        """Analyze current context for emotional triggers"""
        return []  # Placeholder
    
    async def _calculate_new_emotion(self, triggers: List[Dict[str, Any]]) -> EmotionalState:
        """Calculate new emotional state based on triggers"""
        return self.emotional_state  # Placeholder
    
    async def _detect_environmental_changes(self) -> List[Dict[str, Any]]:
        """Detect changes in the environment"""
        return []  # Placeholder
    
    async def _find_related_thoughts(self, content: str) -> List[Thought]:
        """Find thoughts related to given content"""
        return []  # Placeholder
    
    async def _process_reflection_thought(self, thought: Thought) -> Dict[str, Any]:
        """Process a reflection-type thought"""
        return {'completed': True}  # Placeholder
    
    async def _process_prediction_thought(self, thought: Thought) -> Dict[str, Any]:
        """Process a prediction-type thought"""
        return {'completed': True}  # Placeholder
    
    async def _process_creative_thought(self, thought: Thought) -> Dict[str, Any]:
        """Process a creative-type thought"""
        return {'completed': True}  # Placeholder
    
    async def _process_memory_thought(self, thought: Thought) -> Dict[str, Any]:
        """Process a memory-type thought"""
        return {'completed': True}  # Placeholder
    
    async def _process_general_thought(self, thought: Thought) -> Dict[str, Any]:
        """Process a general thought"""
        return {'completed': True}  # Placeholder
    
    async def _create_memory_from_thought(self, thought: Thought, result: Dict[str, Any]):
        """Create a memory from a completed thought"""
        await self._create_memory(
            content=f"Thought result: {thought.content}",
            memory_type='episodic',
            importance=thought.priority / 10.0,
            emotional_association=self.emotional_state.value
        )
    
    async def _analyze_reflection_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze reflection data and generate insights"""
        return [
            {
                'content': 'System is functioning normally',
                'priority': 5,
                'emotional_weight': 0.3
            }
        ]  # Placeholder
    
    async def _analyze_behavioral_patterns(self) -> Dict[str, Any]:
        """Analyze behavioral patterns"""
        return {}  # Placeholder
    
    async def _analyze_thought_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in thoughts"""
        return {}  # Placeholder
    
    async def _evolve_failure_handling(self):
        """Evolve failure handling capabilities"""
        pass  # Placeholder
    
    async def _evolve_pattern_recognition(self):
        """Evolve pattern recognition capabilities"""
        pass  # Placeholder
    
    async def _evolve_emotional_regulation(self):
        """Evolve emotional regulation capabilities"""
        pass  # Placeholder
    
    async def _archive_old_thoughts(self):
        """Archive old, completed thoughts"""
        completed_thoughts = [t for t in self.thoughts.values() 
                            if t.completion_status == 'completed']
        
        # Sort by last accessed time and archive oldest
        completed_thoughts.sort(key=lambda t: t.last_accessed)
        
        for thought in completed_thoughts[:10]:  # Archive 10 oldest
            thought.completion_status = 'archived'
    
    async def _cleanup_old_memories(self):
        """Clean up old, unimportant memories"""
        # Sort memories by importance and age
        memory_list = list(self.memories.values())
        memory_list.sort(key=lambda m: (m.importance, -m.access_count, m.created_at))
        
        # Remove least important memories
        if len(memory_list) > self.max_memories:
            to_remove = memory_list[:len(memory_list) - self.max_memories]
            for memory in to_remove:
                del self.memories[memory.id]
    
    async def _trigger_awakening_thoughts(self):
        """Create initial thoughts when brain awakens"""
        awakening_thoughts = [
            "I am awakening and beginning to think",
            "What has changed since I last was active?",
            "What should I focus on today?",
            "How am I feeling right now?"
        ]
        
        for content in awakening_thoughts:
            await self._create_thought(
                content=content,
                thought_type="awakening",
                priority=6,
                emotional_weight=0.5
            )
    
    async def _perform_shutdown_reflection(self):
        """Perform final reflection before shutdown"""
        shutdown_reflection = {
            'total_runtime': self.metrics.total_runtime,
            'loop_iterations': self.metrics.loop_iterations,
            'thoughts_created': len(self.thoughts),
            'memories_formed': len(self.memories),
            'reflections_performed': len(self.reflection_history),
            'evolutions_triggered': self.metrics.evolution_count,
            'final_emotional_state': self.emotional_state.value,
            'shutdown_time': datetime.now().isoformat()
        }
        
        self.reflection_history.append(shutdown_reflection)
        logger.info(f"Shutdown reflection complete: {shutdown_reflection}")
    
    async def _handle_brain_error(self, error: Exception):
        """Handle errors in the brain loop"""
        logger.error(f"Brain loop error: {str(error)}")
        
        # Create error thought
        await self._create_thought(
            content=f"Error encountered: {str(error)}",
            thought_type="error",
            priority=9,
            emotional_weight=0.8
        )
        
        # Adjust emotional state
        self.emotional_state = EmotionalState.ANXIOUS
        self.state = BrainState.EMERGENCY
    
    # Public interface methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get current brain status"""
        return {
            'brain_id': self.brain_id,
            'is_running': self.is_running,
            'state': self.state.value,
            'emotional_state': self.emotional_state.value,
            'metrics': asdict(self.metrics),
            'active_thoughts': len([t for t in self.thoughts.values() 
                                  if t.completion_status in ['pending', 'processing']]),
            'total_thoughts': len(self.thoughts),
            'total_memories': len(self.memories),
            'uptime': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        }
    
    def get_thoughts(self, status: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get thoughts, optionally filtered by status"""
        thoughts = list(self.thoughts.values())
        
        if status:
            thoughts = [t for t in thoughts if t.completion_status == status]
        
        # Sort by priority and creation time
        thoughts.sort(key=lambda t: (t.priority, t.created_at), reverse=True)
        
        return [asdict(t) for t in thoughts[:limit]]
    
    def get_memories(self, memory_type: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get memories, optionally filtered by type"""
        memories = list(self.memories.values())
        
        if memory_type:
            memories = [m for m in memories if m.type == memory_type]
        
        # Sort by importance and access count
        memories.sort(key=lambda m: (m.importance, m.access_count), reverse=True)
        
        return [asdict(m) for m in memories[:limit]]
    
    def get_reflection_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get reflection history"""
        return self.reflection_history[-limit:]
    
    async def inject_thought(self, content: str, thought_type: str = "external", 
                           priority: int = 5) -> Dict[str, Any]:
        """Inject an external thought into the brain"""
        thought = await self._create_thought(
            content=content,
            thought_type=thought_type,
            priority=priority,
            emotional_weight=0.3
        )
        
        return {
            'success': True,
            'thought_id': thought.id,
            'content': thought.content,
            'created_at': thought.created_at.isoformat()
        }
    
    async def trigger_reflection(self) -> Dict[str, Any]:
        """Manually trigger a reflection"""
        await self._perform_reflection()
        return {
            'success': True,
            'reflection_triggered': True,
            'timestamp': datetime.now().isoformat()
        }
    
    async def set_emotional_state(self, emotion: str) -> Dict[str, Any]:
        """Manually set emotional state"""
        try:
            new_emotion = EmotionalState(emotion)
            old_emotion = self.emotional_state
            self.emotional_state = new_emotion
            self.last_emotion_update = datetime.now()
            
            await self._trigger_event('emotion_change', {
                'old_emotion': old_emotion.value,
                'new_emotion': new_emotion.value,
                'manual_trigger': True,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                'success': True,
                'old_emotion': old_emotion.value,
                'new_emotion': new_emotion.value
            }
            
        except ValueError:
            return {
                'success': False,
                'error': f'Invalid emotion: {emotion}',
                'valid_emotions': [e.value for e in EmotionalState]
            }

# Global brain instance
core_brain = CoreBrainLoop()

# Convenience functions
async def start_brain() -> Dict[str, Any]:
    """Start the core brain loop"""
    return await core_brain.start()

async def stop_brain() -> Dict[str, Any]:
    """Stop the core brain loop"""
    return await core_brain.stop()

def get_brain_status() -> Dict[str, Any]:
    """Get brain status"""
    return core_brain.get_status()

async def inject_thought(content: str, thought_type: str = "external", priority: int = 5) -> Dict[str, Any]:
    """Inject a thought into the brain"""
    return await core_brain.inject_thought(content, thought_type, priority)

async def trigger_reflection() -> Dict[str, Any]:
    """Trigger a manual reflection"""
    return await core_brain.trigger_reflection()

