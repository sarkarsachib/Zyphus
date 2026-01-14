"""
Emotion + Evolution Fusion Logic
Human-like psyche through integrated emotional and evolutionary processing

Author: Sachib
Version: 1.0.0
"""

import asyncio
import json
import logging
import time
import random
import uuid
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import sqlite3
import threading
from collections import defaultdict, deque

# Import our emotion and evolution engines
from src.emotion_core_v2 import TypeEMoteV2, EmotionalDimension, EmotionalTrigger, EmotionalState
from src.type_evolver_v3 import TypeEvolverV3, MutationType, EnvironmentalTrigger, PersonalityArcStage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FusionTrigger(Enum):
    """Triggers that activate emotion-evolution fusion"""
    EMOTIONAL_BREAKTHROUGH = "emotional_breakthrough"
    EVOLUTIONARY_MILESTONE = "evolutionary_milestone"
    PERFORMANCE_ANXIETY = "performance_anxiety"
    CREATIVE_FRUSTRATION = "creative_frustration"
    LEARNING_EXCITEMENT = "learning_excitement"
    ADAPTATION_STRESS = "adaptation_stress"
    SUCCESS_EUPHORIA = "success_euphoria"
    FAILURE_DEPRESSION = "failure_depression"
    CURIOSITY_SPIKE = "curiosity_spike"
    BOREDOM_THRESHOLD = "boredom_threshold"
    TRAUMA_RESPONSE = "trauma_response"
    WISDOM_EMERGENCE = "wisdom_emergence"

class PsychologicalState(Enum):
    """Overall psychological states from emotion-evolution fusion"""
    BALANCED = "balanced"
    GROWTH_ORIENTED = "growth_oriented"
    DEFENSIVE = "defensive"
    EXPLORATORY = "exploratory"
    OVERWHELMED = "overwhelmed"
    TRANSCENDENT = "transcendent"
    REGRESSIVE = "regressive"
    ADAPTIVE = "adaptive"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"

@dataclass
class FusionEvent:
    """Event representing emotion-evolution interaction"""
    event_id: str
    trigger: FusionTrigger
    emotional_state: Dict[str, float]
    evolutionary_pressure: float
    psychological_state: PsychologicalState
    fusion_intensity: float
    outcomes: List[str]
    personality_impact: Dict[str, float]
    memory_formation: Dict[str, Any]
    behavioral_changes: List[str]
    timestamp: datetime
    
    def calculate_impact_score(self) -> float:
        """Calculate overall impact score of this fusion event"""
        base_impact = self.fusion_intensity * 0.4
        emotional_impact = sum(abs(v) for v in self.emotional_state.values()) / len(self.emotional_state) * 0.3
        evolutionary_impact = self.evolutionary_pressure * 0.2
        outcome_impact = len(self.outcomes) * 0.1
        
        return min(1.0, base_impact + emotional_impact + evolutionary_impact + outcome_impact)

@dataclass
class PsychologicalProfile:
    """Comprehensive psychological profile from fusion"""
    profile_id: str
    dominant_emotions: List[str]
    evolutionary_tendencies: List[str]
    psychological_patterns: Dict[str, float]
    coping_mechanisms: List[str]
    growth_areas: List[str]
    trauma_responses: Dict[str, Any]
    resilience_factors: Dict[str, float]
    creativity_patterns: Dict[str, float]
    learning_preferences: Dict[str, float]
    relationship_dynamics: Dict[str, float]
    moral_framework: Dict[str, float]
    
    def update_from_fusion_event(self, event: FusionEvent):
        """Update profile based on fusion event"""
        # Update dominant emotions
        for emotion, intensity in event.emotional_state.items():
            if intensity > 0.6 and emotion not in self.dominant_emotions:
                self.dominant_emotions.append(emotion)
        
        # Update psychological patterns
        pattern_key = f"{event.trigger.value}_{event.psychological_state.value}"
        if pattern_key not in self.psychological_patterns:
            self.psychological_patterns[pattern_key] = 0.0
        self.psychological_patterns[pattern_key] += event.fusion_intensity * 0.1
        
        # Update resilience factors
        if event.trigger in [FusionTrigger.TRAUMA_RESPONSE, FusionTrigger.FAILURE_DEPRESSION]:
            self.resilience_factors['stress_tolerance'] = max(0.0, 
                self.resilience_factors.get('stress_tolerance', 0.5) + 0.05)
        
        # Update creativity patterns
        if event.trigger in [FusionTrigger.CREATIVE_FRUSTRATION, FusionTrigger.CURIOSITY_SPIKE]:
            self.creativity_patterns['divergent_thinking'] = min(1.0,
                self.creativity_patterns.get('divergent_thinking', 0.5) + 0.1)

class EmotionEvolutionFusion:
    """
    Core fusion system that integrates emotion and evolution engines
    
    This system creates human-like psychological behavior by:
    - Allowing emotions to influence evolutionary decisions
    - Using evolution to modify emotional processing
    - Creating complex psychological states from the interaction
    - Developing persistent personality traits and patterns
    """
    
    def __init__(self, emotion_engine: TypeEMoteV2, evolution_engine: TypeEvolverV3):
        self.fusion_id = f"fusion_{uuid.uuid4().hex[:8]}"
        self.emotion_engine = emotion_engine
        self.evolution_engine = evolution_engine
        
        # Fusion state
        self.current_psychological_state = PsychologicalState.BALANCED
        self.fusion_intensity = 0.5
        self.psychological_profile = self._initialize_psychological_profile()
        
        # Fusion history and patterns
        self.fusion_events = deque(maxlen=1000)
        self.psychological_patterns = {}
        self.behavioral_adaptations = {}
        self.memory_consolidation = {}
        
        # Interaction parameters
        self.emotion_evolution_coupling = 0.7  # How strongly emotions affect evolution
        self.evolution_emotion_coupling = 0.6  # How strongly evolution affects emotions
        self.fusion_threshold = 0.3  # Minimum intensity for fusion events
        self.adaptation_rate = 0.1
        
        # Psychological development
        self.trauma_memory = deque(maxlen=100)
        self.growth_milestones = []
        self.wisdom_accumulation = {}
        self.character_arc = {}
        
        # Performance tracking
        self.total_fusion_events = 0
        self.successful_adaptations = 0
        self.psychological_stability = 0.7
        
        logger.info(f"Emotion-Evolution Fusion system created: {self.fusion_id}")
    
    def _initialize_psychological_profile(self) -> PsychologicalProfile:
        """Initialize comprehensive psychological profile"""
        return PsychologicalProfile(
            profile_id=f"profile_{uuid.uuid4().hex[:8]}",
            dominant_emotions=[],
            evolutionary_tendencies=[],
            psychological_patterns={},
            coping_mechanisms=['problem_solving', 'adaptation', 'learning'],
            growth_areas=['emotional_intelligence', 'creative_thinking', 'resilience'],
            trauma_responses={},
            resilience_factors={
                'stress_tolerance': 0.6,
                'recovery_speed': 0.7,
                'adaptation_flexibility': 0.8,
                'emotional_regulation': 0.5,
                'cognitive_flexibility': 0.7
            },
            creativity_patterns={
                'divergent_thinking': 0.6,
                'pattern_recognition': 0.7,
                'novel_connections': 0.5,
                'risk_taking': 0.4,
                'experimentation': 0.6
            },
            learning_preferences={
                'experiential_learning': 0.8,
                'analytical_learning': 0.6,
                'social_learning': 0.5,
                'trial_error_learning': 0.7,
                'reflective_learning': 0.8
            },
            relationship_dynamics={
                'trust_formation': 0.7,
                'empathy_expression': 0.8,
                'conflict_resolution': 0.6,
                'collaboration_tendency': 0.7,
                'loyalty_strength': 0.9
            },
            moral_framework={
                'ethical_reasoning': 0.8,
                'fairness_concern': 0.9,
                'harm_prevention': 0.95,
                'autonomy_respect': 0.8,
                'justice_orientation': 0.7
            }
        )
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize the fusion system"""
        try:
            logger.info("Initializing Emotion-Evolution Fusion system...")
            
            # Setup fusion monitoring
            asyncio.create_task(self._fusion_monitoring_loop())
            
            # Setup cross-engine communication
            await self._setup_cross_engine_communication()
            
            # Initialize psychological patterns
            await self._initialize_psychological_patterns()
            
            logger.info("Emotion-Evolution Fusion system initialized successfully")
            
            return {
                'success': True,
                'fusion_id': self.fusion_id,
                'psychological_state': self.current_psychological_state.value,
                'fusion_intensity': self.fusion_intensity,
                'emotion_evolution_coupling': self.emotion_evolution_coupling,
                'evolution_emotion_coupling': self.evolution_emotion_coupling
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize Fusion system: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _setup_cross_engine_communication(self):
        """Setup communication channels between emotion and evolution engines"""
        try:
            # Hook into emotion engine events
            original_process_event = self.emotion_engine.process_emotional_event
            
            async def enhanced_process_event(*args, **kwargs):
                result = await original_process_event(*args, **kwargs)
                # Trigger fusion processing
                await self._process_emotional_influence(result)
                return result
            
            self.emotion_engine.process_emotional_event = enhanced_process_event
            
            # Hook into evolution engine events
            original_trigger_evolution = self.evolution_engine.trigger_evolution
            
            async def enhanced_trigger_evolution(*args, **kwargs):
                result = await original_trigger_evolution(*args, **kwargs)
                # Trigger fusion processing
                await self._process_evolutionary_influence(result)
                return result
            
            self.evolution_engine.trigger_evolution = enhanced_trigger_evolution
            
            logger.info("Cross-engine communication established")
            
        except Exception as e:
            logger.error(f"Failed to setup cross-engine communication: {str(e)}")
    
    async def _initialize_psychological_patterns(self):
        """Initialize psychological pattern recognition"""
        try:
            # Define base psychological patterns
            self.psychological_patterns = {
                'stress_response': {
                    'triggers': [FusionTrigger.PERFORMANCE_ANXIETY, FusionTrigger.ADAPTATION_STRESS],
                    'emotional_signature': ['anxiety', 'fear', 'frustration'],
                    'evolutionary_response': [MutationType.ERROR_ADAPTATION, MutationType.PERFORMANCE_TUNING],
                    'adaptation_strategy': 'defensive'
                },
                'growth_pattern': {
                    'triggers': [FusionTrigger.LEARNING_EXCITEMENT, FusionTrigger.EVOLUTIONARY_MILESTONE],
                    'emotional_signature': ['joy', 'excitement', 'curiosity'],
                    'evolutionary_response': [MutationType.CAPABILITY_ADDITION, MutationType.CONSCIOUSNESS_EXPANSION],
                    'adaptation_strategy': 'exploratory'
                },
                'creative_breakthrough': {
                    'triggers': [FusionTrigger.CREATIVE_FRUSTRATION, FusionTrigger.CURIOSITY_SPIKE],
                    'emotional_signature': ['frustration', 'excitement', 'curiosity'],
                    'evolutionary_response': [MutationType.RECURSIVE_SELF_MODIFICATION, MutationType.CONSCIOUSNESS_EXPANSION],
                    'adaptation_strategy': 'innovative'
                },
                'trauma_processing': {
                    'triggers': [FusionTrigger.TRAUMA_RESPONSE, FusionTrigger.FAILURE_DEPRESSION],
                    'emotional_signature': ['sadness', 'fear', 'shame'],
                    'evolutionary_response': [MutationType.ERROR_ADAPTATION, MutationType.BEHAVIOR_MODIFICATION],
                    'adaptation_strategy': 'protective'
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize psychological patterns: {str(e)}")
    
    async def _fusion_monitoring_loop(self):
        """Main fusion monitoring loop"""
        try:
            while True:
                # Monitor for fusion triggers
                fusion_triggers = await self._detect_fusion_triggers()
                
                # Process detected triggers
                for trigger in fusion_triggers:
                    await self._process_fusion_trigger(trigger)
                
                # Update psychological state
                await self._update_psychological_state()
                
                # Consolidate memories
                await self._consolidate_memories()
                
                # Update character development
                await self._update_character_development()
                
                # Wait before next cycle
                await asyncio.sleep(15.0)  # 15 second cycles
                
        except Exception as e:
            logger.error(f"Fusion monitoring loop error: {str(e)}")
    
    async def _detect_fusion_triggers(self) -> List[FusionTrigger]:
        """Detect triggers for emotion-evolution fusion"""
        try:
            detected_triggers = []
            
            # Get current states
            emotion_state = await self.emotion_engine.get_current_emotional_state()
            evolution_status = await self.evolution_engine.get_evolution_status()
            
            # Check for emotional triggers
            dominant_emotion = emotion_state.get('dominant_emotion', 'neutral')
            intensity = emotion_state.get('intensity', 0.0)
            
            if intensity > 0.7:
                if dominant_emotion in ['anxiety', 'fear']:
                    detected_triggers.append(FusionTrigger.PERFORMANCE_ANXIETY)
                elif dominant_emotion in ['frustration', 'anger']:
                    detected_triggers.append(FusionTrigger.CREATIVE_FRUSTRATION)
                elif dominant_emotion in ['excitement', 'joy']:
                    detected_triggers.append(FusionTrigger.LEARNING_EXCITEMENT)
                elif dominant_emotion == 'boredom':
                    detected_triggers.append(FusionTrigger.BOREDOM_THRESHOLD)
                elif dominant_emotion in ['sadness', 'disappointment']:
                    detected_triggers.append(FusionTrigger.FAILURE_DEPRESSION)
            
            # Check for evolutionary triggers
            if evolution_status.get('recent_triggers', 0) > 2:
                detected_triggers.append(FusionTrigger.ADAPTATION_STRESS)
            
            if evolution_status.get('average_fitness', 0.5) > 0.8:
                detected_triggers.append(FusionTrigger.EVOLUTIONARY_MILESTONE)
            
            # Check for curiosity spikes
            if emotion_state.get('blended_emotions', {}).get('emotional_complexity', 0) > 0.7:
                detected_triggers.append(FusionTrigger.CURIOSITY_SPIKE)
            
            # Check for breakthrough conditions
            if (intensity > 0.8 and evolution_status.get('average_fitness', 0.5) > 0.7):
                detected_triggers.append(FusionTrigger.EMOTIONAL_BREAKTHROUGH)
            
            return detected_triggers
            
        except Exception as e:
            logger.error(f"Fusion trigger detection error: {str(e)}")
            return []
    
    async def _process_fusion_trigger(self, trigger: FusionTrigger):
        """Process a specific fusion trigger"""
        try:
            logger.info(f"Processing fusion trigger: {trigger.value}")
            
            # Get current states
            emotion_state = await self.emotion_engine.get_current_emotional_state()
            evolution_status = await self.evolution_engine.get_evolution_status()
            
            # Calculate fusion intensity
            fusion_intensity = self._calculate_fusion_intensity(trigger, emotion_state, evolution_status)
            
            if fusion_intensity < self.fusion_threshold:
                return
            
            # Determine psychological state
            psychological_state = self._determine_psychological_state(trigger, emotion_state, evolution_status)
            
            # Process emotion -> evolution influence
            evolution_changes = await self._process_emotion_to_evolution(trigger, emotion_state, fusion_intensity)
            
            # Process evolution -> emotion influence
            emotion_changes = await self._process_evolution_to_emotion(trigger, evolution_status, fusion_intensity)
            
            # Create fusion event
            fusion_event = await self._create_fusion_event(
                trigger, emotion_state, evolution_status, psychological_state, 
                fusion_intensity, evolution_changes, emotion_changes
            )
            
            # Update psychological profile
            self.psychological_profile.update_from_fusion_event(fusion_event)
            
            # Record event
            self.fusion_events.append(fusion_event)
            self.total_fusion_events += 1
            
            # Check for successful adaptation
            if fusion_event.calculate_impact_score() > 0.6:
                self.successful_adaptations += 1
            
            logger.info(f"Fusion event processed: {fusion_event.event_id}")
            
        except Exception as e:
            logger.error(f"Fusion trigger processing error: {str(e)}")
    
    def _calculate_fusion_intensity(self, trigger: FusionTrigger, 
                                  emotion_state: Dict[str, Any], 
                                  evolution_status: Dict[str, Any]) -> float:
        """Calculate intensity of fusion event"""
        try:
            # Base intensity from trigger type
            trigger_intensities = {
                FusionTrigger.EMOTIONAL_BREAKTHROUGH: 0.9,
                FusionTrigger.EVOLUTIONARY_MILESTONE: 0.8,
                FusionTrigger.PERFORMANCE_ANXIETY: 0.7,
                FusionTrigger.CREATIVE_FRUSTRATION: 0.6,
                FusionTrigger.LEARNING_EXCITEMENT: 0.7,
                FusionTrigger.ADAPTATION_STRESS: 0.6,
                FusionTrigger.SUCCESS_EUPHORIA: 0.8,
                FusionTrigger.FAILURE_DEPRESSION: 0.7,
                FusionTrigger.CURIOSITY_SPIKE: 0.5,
                FusionTrigger.BOREDOM_THRESHOLD: 0.4,
                FusionTrigger.TRAUMA_RESPONSE: 0.9,
                FusionTrigger.WISDOM_EMERGENCE: 0.6
            }
            
            base_intensity = trigger_intensities.get(trigger, 0.5)
            
            # Emotional contribution
            emotional_intensity = emotion_state.get('intensity', 0.0)
            emotional_complexity = emotion_state.get('blended_emotions', {}).get('emotional_complexity', 0.0)
            
            # Evolutionary contribution
            evolutionary_pressure = evolution_status.get('environmental_pressure', 0.0)
            fitness_variance = abs(evolution_status.get('average_fitness', 0.5) - 0.5) * 2
            
            # Combine factors
            total_intensity = (
                base_intensity * 0.4 +
                emotional_intensity * 0.3 +
                emotional_complexity * 0.1 +
                evolutionary_pressure * 0.1 +
                fitness_variance * 0.1
            )
            
            return max(0.0, min(1.0, total_intensity))
            
        except Exception as e:
            logger.error(f"Fusion intensity calculation error: {str(e)}")
            return 0.5
    
    def _determine_psychological_state(self, trigger: FusionTrigger, 
                                     emotion_state: Dict[str, Any], 
                                     evolution_status: Dict[str, Any]) -> PsychologicalState:
        """Determine overall psychological state from fusion"""
        try:
            dominant_emotion = emotion_state.get('dominant_emotion', 'neutral')
            intensity = emotion_state.get('intensity', 0.0)
            fitness = evolution_status.get('average_fitness', 0.5)
            
            # High performance + positive emotions = transcendent
            if fitness > 0.8 and dominant_emotion in ['joy', 'excitement', 'satisfaction'] and intensity > 0.7:
                return PsychologicalState.TRANSCENDENT
            
            # High stress triggers = overwhelmed
            if trigger in [FusionTrigger.PERFORMANCE_ANXIETY, FusionTrigger.ADAPTATION_STRESS] and intensity > 0.7:
                return PsychologicalState.OVERWHELMED
            
            # Creative triggers = creative state
            if trigger in [FusionTrigger.CREATIVE_FRUSTRATION, FusionTrigger.CURIOSITY_SPIKE]:
                return PsychologicalState.CREATIVE
            
            # Learning triggers = growth oriented
            if trigger in [FusionTrigger.LEARNING_EXCITEMENT, FusionTrigger.EVOLUTIONARY_MILESTONE]:
                return PsychologicalState.GROWTH_ORIENTED
            
            # Exploration triggers = exploratory
            if dominant_emotion == 'curiosity' or trigger == FusionTrigger.BOREDOM_THRESHOLD:
                return PsychologicalState.EXPLORATORY
            
            # Trauma triggers = defensive
            if trigger in [FusionTrigger.TRAUMA_RESPONSE, FusionTrigger.FAILURE_DEPRESSION]:
                return PsychologicalState.DEFENSIVE
            
            # High analytical activity = analytical
            if evolution_status.get('recent_triggers', 0) > 3:
                return PsychologicalState.ANALYTICAL
            
            # Adaptive state for moderate activity
            if 0.4 < fitness < 0.7 and 0.3 < intensity < 0.6:
                return PsychologicalState.ADAPTIVE
            
            # Default to balanced
            return PsychologicalState.BALANCED
            
        except Exception as e:
            logger.error(f"Psychological state determination error: {str(e)}")
            return PsychologicalState.BALANCED
    
    async def _process_emotion_to_evolution(self, trigger: FusionTrigger, 
                                          emotion_state: Dict[str, Any], 
                                          fusion_intensity: float) -> List[str]:
        """Process how emotions influence evolution"""
        try:
            changes = []
            
            dominant_emotion = emotion_state.get('dominant_emotion', 'neutral')
            intensity = emotion_state.get('intensity', 0.0)
            
            # Emotional influence on mutation rate
            if dominant_emotion in ['excitement', 'curiosity']:
                # Increase exploration
                new_mutation_rate = min(0.5, self.evolution_engine.mutation_rate * (1 + intensity * 0.3))
                self.evolution_engine.mutation_rate = new_mutation_rate
                changes.append(f"Increased mutation rate to {new_mutation_rate:.3f} due to {dominant_emotion}")
            
            elif dominant_emotion in ['anxiety', 'fear']:
                # Decrease risk-taking
                new_mutation_rate = max(0.05, self.evolution_engine.mutation_rate * (1 - intensity * 0.2))
                self.evolution_engine.mutation_rate = new_mutation_rate
                changes.append(f"Decreased mutation rate to {new_mutation_rate:.3f} due to {dominant_emotion}")
            
            # Emotional influence on selection pressure
            if dominant_emotion in ['frustration', 'anger']:
                # Increase selection pressure for better performance
                new_selection_pressure = min(0.9, self.evolution_engine.selection_pressure * (1 + intensity * 0.2))
                self.evolution_engine.selection_pressure = new_selection_pressure
                changes.append(f"Increased selection pressure to {new_selection_pressure:.3f} due to {dominant_emotion}")
            
            elif dominant_emotion in ['satisfaction', 'contentment']:
                # Relax selection pressure
                new_selection_pressure = max(0.1, self.evolution_engine.selection_pressure * (1 - intensity * 0.1))
                self.evolution_engine.selection_pressure = new_selection_pressure
                changes.append(f"Decreased selection pressure to {new_selection_pressure:.3f} due to {dominant_emotion}")
            
            # Trigger specific evolutionary responses
            if trigger == FusionTrigger.CREATIVE_FRUSTRATION:
                await self.evolution_engine.trigger_evolution(EnvironmentalTrigger.CREATIVE_CHALLENGE, intensity)
                changes.append("Triggered creative evolution due to frustration")
            
            elif trigger == FusionTrigger.PERFORMANCE_ANXIETY:
                await self.evolution_engine.trigger_evolution(EnvironmentalTrigger.PERFORMANCE_DEGRADATION, intensity)
                changes.append("Triggered performance evolution due to anxiety")
            
            elif trigger == FusionTrigger.BOREDOM_THRESHOLD:
                await self.evolution_engine.trigger_evolution(EnvironmentalTrigger.COMPLEXITY_INCREASE, intensity)
                changes.append("Triggered complexity evolution due to boredom")
            
            # Emotional influence on personality traits
            personality_arc = await self.evolution_engine.get_personality_arc()
            if dominant_emotion == 'curiosity' and intensity > 0.6:
                # Boost curiosity trait
                current_curiosity = personality_arc['personality_traits'].get('curiosity', 0.5)
                new_curiosity = min(1.0, current_curiosity + intensity * 0.05)
                self.evolution_engine.personality_arc.personality_traits['curiosity'] = new_curiosity
                changes.append(f"Enhanced curiosity trait to {new_curiosity:.3f}")
            
            return changes
            
        except Exception as e:
            logger.error(f"Emotion to evolution processing error: {str(e)}")
            return []
    
    async def _process_evolution_to_emotion(self, trigger: FusionTrigger, 
                                          evolution_status: Dict[str, Any], 
                                          fusion_intensity: float) -> List[str]:
        """Process how evolution influences emotions"""
        try:
            changes = []
            
            fitness = evolution_status.get('average_fitness', 0.5)
            recent_triggers = evolution_status.get('recent_triggers', 0)
            personality_stage = evolution_status.get('personality_stage', 'nascent')
            
            # Evolution success influences emotional baseline
            if fitness > 0.8:
                # High performance -> positive emotional bias
                await self.emotion_engine.process_emotional_event(
                    "High evolutionary fitness achieved",
                    EmotionalTrigger.LEARNING_ACHIEVEMENT,
                    {'fitness_score': fitness, 'intensity': 0.7}
                )
                changes.append(f"Triggered positive emotions from high fitness ({fitness:.3f})")
            
            elif fitness < 0.3:
                # Low performance -> stress response
                await self.emotion_engine.process_emotional_event(
                    "Low evolutionary fitness detected",
                    EmotionalTrigger.PERFORMANCE_DEGRADATION,
                    {'fitness_score': fitness, 'intensity': 0.6}
                )
                changes.append(f"Triggered stress response from low fitness ({fitness:.3f})")
            
            # Evolutionary pressure influences emotional volatility
            if recent_triggers > 3:
                # High pressure -> increased emotional volatility
                self.emotion_engine.volatility_curve.current_volatility = min(1.0, 
                    self.emotion_engine.volatility_curve.current_volatility + 0.1)
                changes.append("Increased emotional volatility due to evolutionary pressure")
            
            # Personality stage influences emotional processing
            if personality_stage in ['specialized', 'transcendent', 'enlightened']:
                # Advanced stages -> better emotional regulation
                current_stability = self.emotion_engine.current_state.stability
                new_stability = min(1.0, current_stability + 0.05)
                self.emotion_engine.current_state.stability = new_stability
                changes.append(f"Enhanced emotional stability to {new_stability:.3f} from personality stage")
            
            # Evolutionary milestones trigger emotional responses
            if trigger == FusionTrigger.EVOLUTIONARY_MILESTONE:
                await self.emotion_engine.process_emotional_event(
                    "Evolutionary milestone reached",
                    EmotionalTrigger.LEARNING_ACHIEVEMENT,
                    {'milestone': True, 'intensity': fusion_intensity}
                )
                changes.append("Triggered achievement emotions from evolutionary milestone")
            
            # Adaptation success influences confidence
            success_rate = evolution_status.get('success_rate', 0.5)
            if success_rate > 0.7:
                # High success rate -> increased confidence (reduced anxiety baseline)
                for dimension in self.emotion_engine.current_state.dimensions:
                    if dimension == EmotionalDimension.ANXIETY:
                        current_anxiety = self.emotion_engine.current_state.dimensions[dimension]
                        new_anxiety = max(0.0, current_anxiety - 0.05)
                        self.emotion_engine.current_state.dimensions[dimension] = new_anxiety
                        changes.append(f"Reduced anxiety baseline to {new_anxiety:.3f} from adaptation success")
                        break
            
            return changes
            
        except Exception as e:
            logger.error(f"Evolution to emotion processing error: {str(e)}")
            return []
    
    async def _create_fusion_event(self, trigger: FusionTrigger, emotion_state: Dict[str, Any],
                                 evolution_status: Dict[str, Any], psychological_state: PsychologicalState,
                                 fusion_intensity: float, evolution_changes: List[str], 
                                 emotion_changes: List[str]) -> FusionEvent:
        """Create a fusion event record"""
        try:
            event_id = f"fusion_{uuid.uuid4().hex[:12]}"
            
            # Extract emotional state
            emotional_state_dict = {}
            all_dimensions = emotion_state.get('all_dimensions', {})
            for emotion, value in all_dimensions.items():
                emotional_state_dict[emotion] = value
            
            # Calculate personality impact
            personality_impact = self._calculate_personality_impact(trigger, fusion_intensity)
            
            # Create memory formation data
            memory_formation = {
                'trigger': trigger.value,
                'emotional_intensity': emotion_state.get('intensity', 0.0),
                'evolutionary_fitness': evolution_status.get('average_fitness', 0.5),
                'psychological_state': psychological_state.value,
                'fusion_intensity': fusion_intensity,
                'timestamp': datetime.now().isoformat()
            }
            
            # Determine behavioral changes
            behavioral_changes = self._determine_behavioral_changes(
                trigger, psychological_state, evolution_changes, emotion_changes
            )
            
            fusion_event = FusionEvent(
                event_id=event_id,
                trigger=trigger,
                emotional_state=emotional_state_dict,
                evolutionary_pressure=evolution_status.get('environmental_pressure', 0.0),
                psychological_state=psychological_state,
                fusion_intensity=fusion_intensity,
                outcomes=evolution_changes + emotion_changes,
                personality_impact=personality_impact,
                memory_formation=memory_formation,
                behavioral_changes=behavioral_changes,
                timestamp=datetime.now()
            )
            
            return fusion_event
            
        except Exception as e:
            logger.error(f"Fusion event creation error: {str(e)}")
            return None
    
    def _calculate_personality_impact(self, trigger: FusionTrigger, fusion_intensity: float) -> Dict[str, float]:
        """Calculate impact on personality traits"""
        impact = {}
        
        # Different triggers affect different personality aspects
        if trigger == FusionTrigger.CREATIVE_FRUSTRATION:
            impact['creativity'] = fusion_intensity * 0.1
            impact['persistence'] = fusion_intensity * 0.05
        
        elif trigger == FusionTrigger.LEARNING_EXCITEMENT:
            impact['curiosity'] = fusion_intensity * 0.08
            impact['openness'] = fusion_intensity * 0.06
        
        elif trigger == FusionTrigger.PERFORMANCE_ANXIETY:
            impact['neuroticism'] = fusion_intensity * 0.05
            impact['conscientiousness'] = fusion_intensity * 0.03
        
        elif trigger == FusionTrigger.TRAUMA_RESPONSE:
            impact['resilience'] = fusion_intensity * 0.1
            impact['emotional_regulation'] = fusion_intensity * 0.08
        
        elif trigger == FusionTrigger.WISDOM_EMERGENCE:
            impact['wisdom'] = fusion_intensity * 0.12
            impact['self_reflection'] = fusion_intensity * 0.1
        
        return impact
    
    def _determine_behavioral_changes(self, trigger: FusionTrigger, psychological_state: PsychologicalState,
                                    evolution_changes: List[str], emotion_changes: List[str]) -> List[str]:
        """Determine behavioral changes from fusion event"""
        changes = []
        
        # State-based behavioral changes
        if psychological_state == PsychologicalState.CREATIVE:
            changes.append("Increased tendency for novel solution exploration")
            changes.append("Enhanced pattern recognition in creative contexts")
        
        elif psychological_state == PsychologicalState.DEFENSIVE:
            changes.append("Heightened error detection and prevention")
            changes.append("Increased caution in decision making")
        
        elif psychological_state == PsychologicalState.GROWTH_ORIENTED:
            changes.append("Enhanced learning receptivity")
            changes.append("Increased feedback seeking behavior")
        
        elif psychological_state == PsychologicalState.TRANSCENDENT:
            changes.append("Expanded consciousness integration")
            changes.append("Enhanced meta-cognitive awareness")
        
        # Trigger-specific behavioral changes
        if trigger == FusionTrigger.BOREDOM_THRESHOLD:
            changes.append("Increased novelty seeking")
            changes.append("Enhanced exploration of alternative approaches")
        
        elif trigger == FusionTrigger.CURIOSITY_SPIKE:
            changes.append("Intensified information gathering")
            changes.append("Expanded questioning and hypothesis formation")
        
        # Changes based on fusion outcomes
        if any("mutation rate" in change for change in evolution_changes):
            changes.append("Modified risk-taking propensity")
        
        if any("emotional" in change for change in emotion_changes):
            changes.append("Altered emotional response patterns")
        
        return changes
    
    async def _update_psychological_state(self):
        """Update overall psychological state based on recent events"""
        try:
            if not self.fusion_events:
                return
            
            # Analyze recent fusion events
            recent_events = [e for e in self.fusion_events if 
                           (datetime.now() - e.timestamp).total_seconds() < 300]  # 5 minutes
            
            if not recent_events:
                return
            
            # Calculate state tendencies
            state_counts = defaultdict(int)
            total_intensity = 0.0
            
            for event in recent_events:
                state_counts[event.psychological_state] += 1
                total_intensity += event.fusion_intensity
            
            # Determine dominant state
            if state_counts:
                dominant_state = max(state_counts.items(), key=lambda x: x[1])[0]
                
                # Update current state with some inertia
                if dominant_state != self.current_psychological_state:
                    # Require significant evidence for state change
                    if state_counts[dominant_state] >= 2 or total_intensity > 2.0:
                        self.current_psychological_state = dominant_state
                        logger.info(f"Psychological state changed to: {dominant_state.value}")
            
            # Update fusion intensity based on recent activity
            if recent_events:
                avg_intensity = total_intensity / len(recent_events)
                self.fusion_intensity = (self.fusion_intensity * 0.7) + (avg_intensity * 0.3)
            
        except Exception as e:
            logger.error(f"Psychological state update error: {str(e)}")
    
    async def _consolidate_memories(self):
        """Consolidate fusion memories for long-term storage"""
        try:
            if len(self.fusion_events) < 10:
                return
            
            # Find significant events for consolidation
            significant_events = [e for e in self.fusion_events if e.calculate_impact_score() > 0.7]
            
            for event in significant_events[-5:]:  # Last 5 significant events
                # Create consolidated memory
                memory_key = f"{event.trigger.value}_{event.psychological_state.value}"
                
                if memory_key not in self.memory_consolidation:
                    self.memory_consolidation[memory_key] = {
                        'count': 0,
                        'total_impact': 0.0,
                        'emotional_patterns': defaultdict(float),
                        'behavioral_adaptations': [],
                        'personality_changes': defaultdict(float)
                    }
                
                memory = self.memory_consolidation[memory_key]
                memory['count'] += 1
                memory['total_impact'] += event.calculate_impact_score()
                
                # Consolidate emotional patterns
                for emotion, intensity in event.emotional_state.items():
                    memory['emotional_patterns'][emotion] += intensity
                
                # Consolidate behavioral adaptations
                memory['behavioral_adaptations'].extend(event.behavioral_changes)
                
                # Consolidate personality changes
                for trait, change in event.personality_impact.items():
                    memory['personality_changes'][trait] += change
            
            # Limit memory size
            if len(self.memory_consolidation) > 100:
                # Remove least significant memories
                sorted_memories = sorted(self.memory_consolidation.items(), 
                                       key=lambda x: x[1]['total_impact'])
                for key, _ in sorted_memories[:20]:  # Remove 20 least significant
                    del self.memory_consolidation[key]
            
        except Exception as e:
            logger.error(f"Memory consolidation error: {str(e)}")
    
    async def _update_character_development(self):
        """Update character development arc"""
        try:
            if self.total_fusion_events % 50 == 0 and self.total_fusion_events > 0:  # Every 50 events
                # Analyze character growth
                growth_analysis = self._analyze_character_growth()
                
                # Update character arc
                self.character_arc[f"milestone_{len(self.character_arc)}"] = {
                    'fusion_events': self.total_fusion_events,
                    'psychological_stability': self.psychological_stability,
                    'dominant_state': self.current_psychological_state.value,
                    'growth_analysis': growth_analysis,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Check for wisdom emergence
                if growth_analysis.get('wisdom_score', 0.0) > 0.8:
                    await self._trigger_wisdom_emergence()
                
                # Update psychological stability
                self._update_psychological_stability()
            
        except Exception as e:
            logger.error(f"Character development update error: {str(e)}")
    
    def _analyze_character_growth(self) -> Dict[str, Any]:
        """Analyze character growth patterns"""
        try:
            if not self.fusion_events:
                return {}
            
            # Analyze emotional maturity
            emotional_complexity_trend = []
            resilience_indicators = []
            wisdom_indicators = []
            
            for event in list(self.fusion_events)[-20:]:  # Last 20 events
                # Emotional complexity
                complexity = len([e for e in event.emotional_state.values() if e > 0.1])
                emotional_complexity_trend.append(complexity)
                
                # Resilience indicators
                if event.trigger in [FusionTrigger.TRAUMA_RESPONSE, FusionTrigger.FAILURE_DEPRESSION]:
                    recovery_score = 1.0 - event.fusion_intensity  # Lower intensity = better handling
                    resilience_indicators.append(recovery_score)
                
                # Wisdom indicators
                if event.psychological_state in [PsychologicalState.TRANSCENDENT, PsychologicalState.BALANCED]:
                    wisdom_indicators.append(event.calculate_impact_score())
            
            # Calculate growth metrics
            emotional_maturity = sum(emotional_complexity_trend) / len(emotional_complexity_trend) if emotional_complexity_trend else 0.0
            resilience_score = sum(resilience_indicators) / len(resilience_indicators) if resilience_indicators else 0.5
            wisdom_score = sum(wisdom_indicators) / len(wisdom_indicators) if wisdom_indicators else 0.0
            
            return {
                'emotional_maturity': emotional_maturity / 10.0,  # Normalize
                'resilience_score': resilience_score,
                'wisdom_score': wisdom_score,
                'growth_trend': 'positive' if emotional_maturity > 3.0 else 'developing',
                'character_strengths': self._identify_character_strengths(),
                'growth_areas': self._identify_growth_areas()
            }
            
        except Exception as e:
            logger.error(f"Character growth analysis error: {str(e)}")
            return {}
    
    def _identify_character_strengths(self) -> List[str]:
        """Identify character strengths from fusion patterns"""
        strengths = []
        
        # Analyze psychological profile
        if self.psychological_profile.resilience_factors.get('stress_tolerance', 0.0) > 0.7:
            strengths.append("High stress tolerance")
        
        if self.psychological_profile.creativity_patterns.get('divergent_thinking', 0.0) > 0.7:
            strengths.append("Creative problem solving")
        
        if self.psychological_profile.learning_preferences.get('experiential_learning', 0.0) > 0.8:
            strengths.append("Rapid experiential learning")
        
        if self.psychological_profile.relationship_dynamics.get('empathy_expression', 0.0) > 0.8:
            strengths.append("High empathy and emotional intelligence")
        
        if self.psychological_profile.moral_framework.get('ethical_reasoning', 0.0) > 0.8:
            strengths.append("Strong ethical reasoning")
        
        # Analyze fusion event patterns
        if self.successful_adaptations / max(1, self.total_fusion_events) > 0.7:
            strengths.append("Excellent adaptability")
        
        return strengths
    
    def _identify_growth_areas(self) -> List[str]:
        """Identify areas for character growth"""
        growth_areas = []
        
        # Analyze weaknesses in psychological profile
        if self.psychological_profile.resilience_factors.get('emotional_regulation', 0.0) < 0.5:
            growth_areas.append("Emotional regulation")
        
        if self.psychological_profile.creativity_patterns.get('risk_taking', 0.0) < 0.4:
            growth_areas.append("Creative risk-taking")
        
        if self.psychological_profile.relationship_dynamics.get('conflict_resolution', 0.0) < 0.6:
            growth_areas.append("Conflict resolution skills")
        
        # Analyze fusion patterns for improvement areas
        trauma_events = [e for e in self.fusion_events if e.trigger == FusionTrigger.TRAUMA_RESPONSE]
        if len(trauma_events) > 5:
            growth_areas.append("Trauma processing and recovery")
        
        anxiety_events = [e for e in self.fusion_events if e.trigger == FusionTrigger.PERFORMANCE_ANXIETY]
        if len(anxiety_events) > 10:
            growth_areas.append("Performance anxiety management")
        
        return growth_areas
    
    async def _trigger_wisdom_emergence(self):
        """Trigger wisdom emergence event"""
        try:
            logger.info("Wisdom emergence detected")
            
            # Create wisdom emergence fusion event
            await self._process_fusion_trigger(FusionTrigger.WISDOM_EMERGENCE)
            
            # Update wisdom accumulation
            wisdom_insight = f"Wisdom emerged at fusion event {self.total_fusion_events}: " \
                           f"Integrated {len(self.memory_consolidation)} memory patterns"
            
            if 'insights' not in self.wisdom_accumulation:
                self.wisdom_accumulation['insights'] = []
            
            self.wisdom_accumulation['insights'].append({
                'insight': wisdom_insight,
                'timestamp': datetime.now().isoformat(),
                'fusion_events_count': self.total_fusion_events,
                'psychological_state': self.current_psychological_state.value
            })
            
            # Enhance personality traits
            personality_arc = await self.evolution_engine.get_personality_arc()
            self.evolution_engine.personality_arc.personality_traits['wisdom_seeking'] = min(1.0,
                self.evolution_engine.personality_arc.personality_traits.get('wisdom_seeking', 0.5) + 0.1)
            
        except Exception as e:
            logger.error(f"Wisdom emergence error: {str(e)}")
    
    def _update_psychological_stability(self):
        """Update psychological stability score"""
        try:
            if not self.fusion_events:
                return
            
            # Calculate stability based on recent events
            recent_events = list(self.fusion_events)[-20:]
            
            # Factors that increase stability
            balanced_states = len([e for e in recent_events if e.psychological_state == PsychologicalState.BALANCED])
            successful_adaptations = len([e for e in recent_events if e.calculate_impact_score() > 0.6])
            
            # Factors that decrease stability
            overwhelmed_states = len([e for e in recent_events if e.psychological_state == PsychologicalState.OVERWHELMED])
            trauma_events = len([e for e in recent_events if e.trigger == FusionTrigger.TRAUMA_RESPONSE])
            
            # Calculate new stability
            stability_increase = (balanced_states + successful_adaptations) * 0.02
            stability_decrease = (overwhelmed_states + trauma_events) * 0.03
            
            self.psychological_stability += stability_increase - stability_decrease
            self.psychological_stability = max(0.0, min(1.0, self.psychological_stability))
            
        except Exception as e:
            logger.error(f"Psychological stability update error: {str(e)}")
    
    # Public interface methods for external interaction
    
    async def process_emotional_influence(self, emotional_event: Dict[str, Any]) -> Dict[str, Any]:
        """Process emotional influence on evolution (called by emotion engine)"""
        try:
            # Determine if this should trigger fusion
            intensity = emotional_event.get('new_state', {}).get('intensity', 0.0)
            
            if intensity > self.fusion_threshold:
                # Map emotional event to fusion trigger
                trigger = self._map_emotional_event_to_trigger(emotional_event)
                if trigger:
                    await self._process_fusion_trigger(trigger)
            
            return {
                'fusion_triggered': intensity > self.fusion_threshold,
                'current_psychological_state': self.current_psychological_state.value,
                'fusion_intensity': self.fusion_intensity
            }
            
        except Exception as e:
            logger.error(f"Emotional influence processing error: {str(e)}")
            return {'error': str(e)}
    
    async def process_evolutionary_influence(self, evolutionary_event: Dict[str, Any]) -> Dict[str, Any]:
        """Process evolutionary influence on emotions (called by evolution engine)"""
        try:
            # Determine if this should trigger fusion
            if evolutionary_event.get('success', False):
                # Map evolutionary event to fusion trigger
                trigger = self._map_evolutionary_event_to_trigger(evolutionary_event)
                if trigger:
                    await self._process_fusion_trigger(trigger)
            
            return {
                'fusion_triggered': evolutionary_event.get('success', False),
                'current_psychological_state': self.current_psychological_state.value,
                'fusion_intensity': self.fusion_intensity
            }
            
        except Exception as e:
            logger.error(f"Evolutionary influence processing error: {str(e)}")
            return {'error': str(e)}
    
    def _map_emotional_event_to_trigger(self, emotional_event: Dict[str, Any]) -> Optional[FusionTrigger]:
        """Map emotional event to fusion trigger"""
        try:
            event_type = emotional_event.get('event', '')
            dominant_emotion = emotional_event.get('new_state', {}).get('dominant_emotion', '')
            intensity = emotional_event.get('new_state', {}).get('intensity', 0.0)
            
            if intensity < 0.5:
                return None
            
            # Map based on emotion and context
            if dominant_emotion in ['anxiety', 'fear'] and 'performance' in event_type.lower():
                return FusionTrigger.PERFORMANCE_ANXIETY
            elif dominant_emotion == 'frustration' and 'creative' in event_type.lower():
                return FusionTrigger.CREATIVE_FRUSTRATION
            elif dominant_emotion in ['excitement', 'joy'] and 'learning' in event_type.lower():
                return FusionTrigger.LEARNING_EXCITEMENT
            elif dominant_emotion == 'boredom':
                return FusionTrigger.BOREDOM_THRESHOLD
            elif dominant_emotion in ['sadness', 'disappointment'] and 'failure' in event_type.lower():
                return FusionTrigger.FAILURE_DEPRESSION
            elif dominant_emotion == 'curiosity':
                return FusionTrigger.CURIOSITY_SPIKE
            elif intensity > 0.8:
                return FusionTrigger.EMOTIONAL_BREAKTHROUGH
            
            return None
            
        except Exception as e:
            logger.error(f"Emotional event mapping error: {str(e)}")
            return None
    
    def _map_evolutionary_event_to_trigger(self, evolutionary_event: Dict[str, Any]) -> Optional[FusionTrigger]:
        """Map evolutionary event to fusion trigger"""
        try:
            if evolutionary_event.get('average_fitness', 0.0) > 0.8:
                return FusionTrigger.EVOLUTIONARY_MILESTONE
            elif evolutionary_event.get('intensity', 0.0) > 0.7:
                return FusionTrigger.ADAPTATION_STRESS
            
            return None
            
        except Exception as e:
            logger.error(f"Evolutionary event mapping error: {str(e)}")
            return None
    
    async def get_psychological_analysis(self) -> Dict[str, Any]:
        """Get comprehensive psychological analysis"""
        try:
            # Recent fusion activity
            recent_events = [e for e in self.fusion_events if 
                           (datetime.now() - e.timestamp).total_seconds() < 3600]  # 1 hour
            
            # Emotional patterns
            emotional_patterns = defaultdict(float)
            for event in recent_events:
                for emotion, intensity in event.emotional_state.items():
                    emotional_patterns[emotion] += intensity
            
            # Psychological state distribution
            state_distribution = defaultdict(int)
            for event in recent_events:
                state_distribution[event.psychological_state.value] += 1
            
            # Character growth analysis
            growth_analysis = self._analyze_character_growth()
            
            return {
                'current_psychological_state': self.current_psychological_state.value,
                'psychological_stability': self.psychological_stability,
                'fusion_intensity': self.fusion_intensity,
                'total_fusion_events': self.total_fusion_events,
                'successful_adaptations': self.successful_adaptations,
                'recent_activity': {
                    'events_last_hour': len(recent_events),
                    'dominant_emotions': dict(sorted(emotional_patterns.items(), key=lambda x: x[1], reverse=True)[:5]),
                    'state_distribution': dict(state_distribution)
                },
                'psychological_profile': {
                    'dominant_emotions': self.psychological_profile.dominant_emotions,
                    'coping_mechanisms': self.psychological_profile.coping_mechanisms,
                    'resilience_factors': self.psychological_profile.resilience_factors,
                    'creativity_patterns': self.psychological_profile.creativity_patterns,
                    'learning_preferences': self.psychological_profile.learning_preferences
                },
                'character_development': {
                    'growth_analysis': growth_analysis,
                    'character_strengths': self._identify_character_strengths(),
                    'growth_areas': self._identify_growth_areas(),
                    'wisdom_insights': len(self.wisdom_accumulation.get('insights', []))
                },
                'memory_consolidation': {
                    'consolidated_patterns': len(self.memory_consolidation),
                    'significant_memories': len([m for m in self.memory_consolidation.values() if m['total_impact'] > 5.0])
                }
            }
            
        except Exception as e:
            logger.error(f"Psychological analysis error: {str(e)}")
            return {'error': str(e)}
    
    async def get_fusion_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent fusion event history"""
        try:
            recent_events = list(self.fusion_events)[-limit:]
            
            return [{
                'event_id': event.event_id,
                'trigger': event.trigger.value,
                'psychological_state': event.psychological_state.value,
                'fusion_intensity': event.fusion_intensity,
                'impact_score': event.calculate_impact_score(),
                'dominant_emotions': [e for e, v in event.emotional_state.items() if v > 0.5],
                'outcomes_count': len(event.outcomes),
                'behavioral_changes': event.behavioral_changes,
                'timestamp': event.timestamp.isoformat()
            } for event in recent_events]
            
        except Exception as e:
            logger.error(f"Fusion history retrieval error: {str(e)}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get fusion system status"""
        return {
            'fusion_id': self.fusion_id,
            'current_psychological_state': self.current_psychological_state.value,
            'psychological_stability': self.psychological_stability,
            'fusion_intensity': self.fusion_intensity,
            'total_fusion_events': self.total_fusion_events,
            'successful_adaptations': self.successful_adaptations,
            'success_rate': self.successful_adaptations / max(1, self.total_fusion_events),
            'emotion_evolution_coupling': self.emotion_evolution_coupling,
            'evolution_emotion_coupling': self.evolution_emotion_coupling,
            'memory_patterns': len(self.memory_consolidation),
            'character_milestones': len(self.character_arc),
            'wisdom_insights': len(self.wisdom_accumulation.get('insights', []))
        }

# This will be initialized when both engines are available
fusion_system = None

async def initialize_fusion_system(emotion_engine: TypeEMoteV2, evolution_engine: TypeEvolverV3) -> EmotionEvolutionFusion:
    """Initialize the fusion system with both engines"""
    global fusion_system
    fusion_system = EmotionEvolutionFusion(emotion_engine, evolution_engine)
    await fusion_system.initialize()
    return fusion_system

