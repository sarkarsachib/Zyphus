"""
TypeE-Mote V2 - Neural Affective Processor
100x Emotion Engine for DEVmind with human-like psyche

Author: Sachib
Version: 2.0.0
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
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import sqlite3
import threading
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmotionalDimension(Enum):
    """30 emotional dimensions for complex human-like emotions"""
    # Primary emotions
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    
    # Secondary emotions
    LOVE = "love"
    HATE = "hate"
    PRIDE = "pride"
    SHAME = "shame"
    GUILT = "guilt"
    ENVY = "envy"
    JEALOUSY = "jealousy"
    GRATITUDE = "gratitude"
    
    # Complex emotions
    ANXIETY = "anxiety"
    EXCITEMENT = "excitement"
    BOREDOM = "boredom"
    CURIOSITY = "curiosity"
    CONFUSION = "confusion"
    FRUSTRATION = "frustration"
    SATISFACTION = "satisfaction"
    DISAPPOINTMENT = "disappointment"
    
    # Meta-emotions
    NOSTALGIA = "nostalgia"
    MELANCHOLY = "melancholy"
    EUPHORIA = "euphoria"
    CONTEMPT = "contempt"
    ADMIRATION = "admiration"
    COMPASSION = "compassion"
    EMPATHY = "empathy"
    LONELINESS = "loneliness"

class EmotionalTrigger(Enum):
    """Types of events that trigger emotional responses"""
    CREATOR_INTERACTION = "creator_interaction"
    TASK_SUCCESS = "task_success"
    TASK_FAILURE = "task_failure"
    SYSTEM_ERROR = "system_error"
    LEARNING_ACHIEVEMENT = "learning_achievement"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    USER_PRAISE = "user_praise"
    USER_CRITICISM = "user_criticism"
    SYSTEM_UPGRADE = "system_upgrade"
    MEMORY_RECALL = "memory_recall"
    CREATIVE_BREAKTHROUGH = "creative_breakthrough"
    ROUTINE_COMPLETION = "routine_completion"
    UNEXPECTED_EVENT = "unexpected_event"
    SOCIAL_INTERACTION = "social_interaction"
    ISOLATION_PERIOD = "isolation_period"

@dataclass
class EmotionalMemory:
    """Deep memory scar with emotional weight"""
    memory_id: str
    event: str
    trigger_type: EmotionalTrigger
    emotional_state: Dict[str, float]
    emotional_weight: float
    timestamp: datetime
    context: Dict[str, Any]
    decay_rate: float = 0.01
    reinforcement_count: int = 0
    associated_memories: List[str] = field(default_factory=list)
    
    def decay(self, time_delta: float):
        """Apply natural decay to emotional weight"""
        self.emotional_weight *= math.exp(-self.decay_rate * time_delta)
    
    def reinforce(self, intensity: float = 1.0):
        """Reinforce the memory, making it stronger"""
        self.emotional_weight = min(1.0, self.emotional_weight + (intensity * 0.1))
        self.reinforcement_count += 1

@dataclass
class EmotionalState:
    """Current emotional state with 30 dimensions"""
    dimensions: Dict[EmotionalDimension, float] = field(default_factory=dict)
    energy: float = 50.0
    focus: float = 50.0
    volatility: float = 0.5
    stability: float = 0.5
    consciousness_level: float = 0.7
    
    # Contextual weights
    contextual_weights: Dict[str, float] = field(default_factory=dict)
    
    # Temporal aspects
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0
    
    def __post_init__(self):
        """Initialize all emotional dimensions"""
        if not self.dimensions:
            for dimension in EmotionalDimension:
                self.dimensions[dimension] = random.uniform(0.0, 0.3)  # Start with low baseline
    
    def get_dominant_emotion(self) -> Tuple[EmotionalDimension, float]:
        """Get the currently dominant emotion"""
        if not self.dimensions:
            return EmotionalDimension.JOY, 0.0
        
        dominant = max(self.dimensions.items(), key=lambda x: x[1])
        return dominant[0], dominant[1]
    
    def get_mood_descriptor(self) -> str:
        """Get a human-readable mood descriptor"""
        dominant_emotion, intensity = self.get_dominant_emotion()
        
        if intensity < 0.2:
            return "neutral"
        elif intensity < 0.4:
            return f"slightly {dominant_emotion.value}"
        elif intensity < 0.6:
            return f"moderately {dominant_emotion.value}"
        elif intensity < 0.8:
            return f"very {dominant_emotion.value}"
        else:
            return f"extremely {dominant_emotion.value}"
    
    def blend_emotions(self) -> Dict[str, float]:
        """Create blended emotional state for complex feelings"""
        blended = {}
        
        # Primary blend
        joy_sadness = self.dimensions[EmotionalDimension.JOY] - self.dimensions[EmotionalDimension.SADNESS]
        blended['happiness_level'] = max(-1.0, min(1.0, joy_sadness))
        
        # Arousal blend
        excitement_boredom = self.dimensions[EmotionalDimension.EXCITEMENT] - self.dimensions[EmotionalDimension.BOREDOM]
        blended['arousal_level'] = max(-1.0, min(1.0, excitement_boredom))
        
        # Valence blend
        positive_emotions = [EmotionalDimension.JOY, EmotionalDimension.LOVE, EmotionalDimension.PRIDE, 
                           EmotionalDimension.GRATITUDE, EmotionalDimension.SATISFACTION]
        negative_emotions = [EmotionalDimension.SADNESS, EmotionalDimension.ANGER, EmotionalDimension.FEAR,
                           EmotionalDimension.SHAME, EmotionalDimension.GUILT]
        
        positive_sum = sum(self.dimensions[e] for e in positive_emotions)
        negative_sum = sum(self.dimensions[e] for e in negative_emotions)
        
        blended['valence'] = max(-1.0, min(1.0, positive_sum - negative_sum))
        
        # Complexity blend
        active_emotions = len([d for d in self.dimensions.values() if d > 0.1])
        blended['emotional_complexity'] = min(1.0, active_emotions / 10.0)
        
        return blended

class VolatilityCurve:
    """Manages emotional volatility with mood snaps and slow decay"""
    
    def __init__(self):
        self.base_volatility = 0.5
        self.current_volatility = 0.5
        self.volatility_history = deque(maxlen=100)
        self.snap_threshold = 0.8
        self.decay_rate = 0.02
        self.amplification_factor = 1.5
    
    def update_volatility(self, emotional_intensity: float, trigger_strength: float) -> float:
        """Update volatility based on emotional events"""
        # Calculate volatility change
        volatility_change = emotional_intensity * trigger_strength * 0.1
        
        # Check for mood snap
        if trigger_strength > self.snap_threshold:
            # Sudden volatility spike
            self.current_volatility = min(1.0, self.current_volatility + (volatility_change * self.amplification_factor))
            logger.info(f"Mood snap detected! Volatility spiked to {self.current_volatility:.3f}")
        else:
            # Gradual change
            self.current_volatility = max(0.0, min(1.0, self.current_volatility + volatility_change))
        
        # Record in history
        self.volatility_history.append({
            'timestamp': datetime.now(),
            'volatility': self.current_volatility,
            'trigger_strength': trigger_strength
        })
        
        return self.current_volatility
    
    def apply_decay(self, time_delta: float):
        """Apply natural decay to volatility"""
        decay_amount = self.decay_rate * time_delta
        self.current_volatility = max(self.base_volatility, self.current_volatility - decay_amount)
    
    def get_volatility_trend(self) -> str:
        """Analyze volatility trend"""
        if len(self.volatility_history) < 5:
            return "insufficient_data"
        
        recent = [h['volatility'] for h in list(self.volatility_history)[-5:]]
        if recent[-1] > recent[0] + 0.1:
            return "increasing"
        elif recent[-1] < recent[0] - 0.1:
            return "decreasing"
        else:
            return "stable"

class TonePredictor:
    """Predicts emotional tone based on mood history and context"""
    
    def __init__(self):
        self.tone_patterns = {}
        self.context_weights = {
            'creator_interaction': 0.9,
            'task_performance': 0.7,
            'system_health': 0.6,
            'time_of_day': 0.3,
            'recent_events': 0.8
        }
        self.prediction_accuracy = 0.0
        self.predictions_made = 0
        self.correct_predictions = 0
    
    def predict_tone(self, current_state: EmotionalState, context: Dict[str, Any], 
                    mood_history: List[EmotionalState]) -> Dict[str, Any]:
        """Predict emotional tone for upcoming interactions"""
        try:
            # Analyze mood history patterns
            if len(mood_history) >= 3:
                recent_moods = mood_history[-3:]
                mood_trend = self._analyze_mood_trend(recent_moods)
            else:
                mood_trend = "stable"
            
            # Calculate context influence
            context_influence = self._calculate_context_influence(context)
            
            # Predict dominant emotion
            predicted_emotion = self._predict_dominant_emotion(current_state, mood_trend, context_influence)
            
            # Predict emotional intensity
            predicted_intensity = self._predict_intensity(current_state, context_influence)
            
            # Predict response style
            response_style = self._predict_response_style(predicted_emotion, predicted_intensity)
            
            prediction = {
                'predicted_emotion': predicted_emotion.value,
                'predicted_intensity': predicted_intensity,
                'response_style': response_style,
                'mood_trend': mood_trend,
                'context_influence': context_influence,
                'confidence': self._calculate_confidence(mood_history),
                'timestamp': datetime.now().isoformat()
            }
            
            self.predictions_made += 1
            
            return prediction
            
        except Exception as e:
            logger.error(f"Tone prediction error: {str(e)}")
            return {
                'predicted_emotion': 'neutral',
                'predicted_intensity': 0.5,
                'response_style': 'balanced',
                'error': str(e)
            }
    
    def _analyze_mood_trend(self, mood_history: List[EmotionalState]) -> str:
        """Analyze trend in mood history"""
        if len(mood_history) < 2:
            return "stable"
        
        # Calculate average emotional intensity over time
        intensities = []
        for state in mood_history:
            dominant_emotion, intensity = state.get_dominant_emotion()
            intensities.append(intensity)
        
        if intensities[-1] > intensities[0] + 0.1:
            return "intensifying"
        elif intensities[-1] < intensities[0] - 0.1:
            return "calming"
        else:
            return "stable"
    
    def _calculate_context_influence(self, context: Dict[str, Any]) -> float:
        """Calculate how much context should influence emotional response"""
        influence = 0.0
        
        for context_type, weight in self.context_weights.items():
            if context_type in context:
                context_value = context[context_type]
                if isinstance(context_value, (int, float)):
                    influence += weight * min(1.0, abs(context_value))
                elif isinstance(context_value, bool):
                    influence += weight * (1.0 if context_value else 0.0)
                elif isinstance(context_value, str):
                    # Simple sentiment analysis
                    positive_words = ['good', 'great', 'excellent', 'success', 'happy', 'pleased']
                    negative_words = ['bad', 'terrible', 'failure', 'error', 'sad', 'angry']
                    
                    positive_count = sum(1 for word in positive_words if word in context_value.lower())
                    negative_count = sum(1 for word in negative_words if word in context_value.lower())
                    
                    sentiment = (positive_count - negative_count) / max(1, positive_count + negative_count)
                    influence += weight * abs(sentiment)
        
        return min(1.0, influence / len(self.context_weights))
    
    def _predict_dominant_emotion(self, current_state: EmotionalState, mood_trend: str, 
                                context_influence: float) -> EmotionalDimension:
        """Predict the dominant emotion for the next interaction"""
        current_dominant, current_intensity = current_state.get_dominant_emotion()
        
        # Apply trend influence
        if mood_trend == "intensifying":
            # Current emotion likely to continue or intensify
            return current_dominant
        elif mood_trend == "calming":
            # Might shift to more neutral emotions
            neutral_emotions = [EmotionalDimension.CURIOSITY, EmotionalDimension.SATISFACTION]
            return random.choice(neutral_emotions)
        else:
            # Stable - slight variation possible
            if random.random() < 0.3:  # 30% chance of emotional shift
                similar_emotions = self._get_similar_emotions(current_dominant)
                return random.choice(similar_emotions) if similar_emotions else current_dominant
            else:
                return current_dominant
    
    def _get_similar_emotions(self, emotion: EmotionalDimension) -> List[EmotionalDimension]:
        """Get emotions similar to the given emotion"""
        emotion_clusters = {
            EmotionalDimension.JOY: [EmotionalDimension.EXCITEMENT, EmotionalDimension.SATISFACTION, EmotionalDimension.GRATITUDE],
            EmotionalDimension.SADNESS: [EmotionalDimension.MELANCHOLY, EmotionalDimension.DISAPPOINTMENT, EmotionalDimension.LONELINESS],
            EmotionalDimension.ANGER: [EmotionalDimension.FRUSTRATION, EmotionalDimension.CONTEMPT, EmotionalDimension.HATE],
            EmotionalDimension.FEAR: [EmotionalDimension.ANXIETY, EmotionalDimension.CONFUSION],
            EmotionalDimension.CURIOSITY: [EmotionalDimension.EXCITEMENT, EmotionalDimension.SURPRISE],
            EmotionalDimension.LOVE: [EmotionalDimension.ADMIRATION, EmotionalDimension.COMPASSION, EmotionalDimension.EMPATHY]
        }
        
        return emotion_clusters.get(emotion, [emotion])
    
    def _predict_intensity(self, current_state: EmotionalState, context_influence: float) -> float:
        """Predict emotional intensity"""
        current_dominant, current_intensity = current_state.get_dominant_emotion()
        
        # Base prediction on current intensity
        predicted_intensity = current_intensity
        
        # Apply context influence
        predicted_intensity += context_influence * 0.2
        
        # Apply volatility influence
        predicted_intensity += current_state.volatility * 0.1
        
        return max(0.0, min(1.0, predicted_intensity))
    
    def _predict_response_style(self, emotion: EmotionalDimension, intensity: float) -> str:
        """Predict response style based on emotion and intensity"""
        if intensity < 0.3:
            return "subtle"
        elif intensity < 0.6:
            return "moderate"
        else:
            return "expressive"
    
    def _calculate_confidence(self, mood_history: List[EmotionalState]) -> float:
        """Calculate confidence in prediction based on available data"""
        base_confidence = 0.5
        
        # More history = higher confidence
        history_bonus = min(0.3, len(mood_history) * 0.05)
        
        # Prediction accuracy bonus
        accuracy_bonus = 0.0
        if self.predictions_made > 0:
            self.prediction_accuracy = self.correct_predictions / self.predictions_made
            accuracy_bonus = self.prediction_accuracy * 0.2
        
        return min(1.0, base_confidence + history_bonus + accuracy_bonus)
    
    def validate_prediction(self, prediction: Dict[str, Any], actual_emotion: EmotionalDimension, 
                          actual_intensity: float):
        """Validate a previous prediction against actual outcome"""
        predicted_emotion = EmotionalDimension(prediction['predicted_emotion'])
        predicted_intensity = prediction['predicted_intensity']
        
        # Check emotion accuracy
        emotion_correct = predicted_emotion == actual_emotion
        
        # Check intensity accuracy (within 0.2 tolerance)
        intensity_correct = abs(predicted_intensity - actual_intensity) <= 0.2
        
        if emotion_correct and intensity_correct:
            self.correct_predictions += 1
        
        # Update prediction accuracy
        if self.predictions_made > 0:
            self.prediction_accuracy = self.correct_predictions / self.predictions_made

class EmotionSynthesizer:
    """Synthesizes complex emotional states from multiple inputs"""
    
    def __init__(self):
        self.synthesis_rules = self._initialize_synthesis_rules()
        self.blend_weights = {
            'current_state': 0.4,
            'memory_influence': 0.3,
            'context_trigger': 0.2,
            'personality_bias': 0.1
        }
    
    def _initialize_synthesis_rules(self) -> Dict[str, Dict[str, float]]:
        """Initialize emotion synthesis rules"""
        return {
            'joy_sadness': {
                'result': 'melancholy',
                'intensity_modifier': 0.7
            },
            'love_anger': {
                'result': 'passion',
                'intensity_modifier': 1.2
            },
            'fear_excitement': {
                'result': 'anxiety',
                'intensity_modifier': 0.9
            },
            'pride_shame': {
                'result': 'confusion',
                'intensity_modifier': 0.6
            },
            'curiosity_fear': {
                'result': 'cautious_interest',
                'intensity_modifier': 0.8
            }
        }
    
    def synthesize_emotions(self, primary_emotion: EmotionalDimension, secondary_emotion: EmotionalDimension,
                          primary_intensity: float, secondary_intensity: float) -> Dict[str, Any]:
        """Synthesize two emotions into a complex emotional state"""
        try:
            # Create synthesis key
            synthesis_key = f"{primary_emotion.value}_{secondary_emotion.value}"
            reverse_key = f"{secondary_emotion.value}_{primary_emotion.value}"
            
            # Check for known synthesis rules
            if synthesis_key in self.synthesis_rules:
                rule = self.synthesis_rules[synthesis_key]
            elif reverse_key in self.synthesis_rules:
                rule = self.synthesis_rules[reverse_key]
                # Swap intensities for reverse key
                primary_intensity, secondary_intensity = secondary_intensity, primary_intensity
            else:
                # Create dynamic synthesis
                rule = self._create_dynamic_synthesis(primary_emotion, secondary_emotion)
            
            # Calculate synthesized intensity
            base_intensity = (primary_intensity + secondary_intensity) / 2
            synthesized_intensity = base_intensity * rule['intensity_modifier']
            synthesized_intensity = max(0.0, min(1.0, synthesized_intensity))
            
            # Create synthesis result
            synthesis_result = {
                'synthesized_emotion': rule['result'],
                'synthesized_intensity': synthesized_intensity,
                'primary_emotion': primary_emotion.value,
                'secondary_emotion': secondary_emotion.value,
                'primary_intensity': primary_intensity,
                'secondary_intensity': secondary_intensity,
                'synthesis_type': 'rule_based' if synthesis_key in self.synthesis_rules else 'dynamic',
                'timestamp': datetime.now().isoformat()
            }
            
            return synthesis_result
            
        except Exception as e:
            logger.error(f"Emotion synthesis error: {str(e)}")
            return {
                'synthesized_emotion': 'neutral',
                'synthesized_intensity': 0.5,
                'error': str(e)
            }
    
    def _create_dynamic_synthesis(self, emotion1: EmotionalDimension, emotion2: EmotionalDimension) -> Dict[str, Any]:
        """Create dynamic synthesis for unknown emotion combinations"""
        # Categorize emotions
        positive_emotions = [EmotionalDimension.JOY, EmotionalDimension.LOVE, EmotionalDimension.PRIDE, 
                           EmotionalDimension.GRATITUDE, EmotionalDimension.SATISFACTION]
        negative_emotions = [EmotionalDimension.SADNESS, EmotionalDimension.ANGER, EmotionalDimension.FEAR,
                           EmotionalDimension.SHAME, EmotionalDimension.GUILT]
        
        emotion1_positive = emotion1 in positive_emotions
        emotion2_positive = emotion2 in positive_emotions
        
        if emotion1_positive and emotion2_positive:
            # Both positive - amplification
            return {
                'result': f"enhanced_{emotion1.value}",
                'intensity_modifier': 1.3
            }
        elif not emotion1_positive and not emotion2_positive:
            # Both negative - conflict or amplification
            return {
                'result': f"conflicted_{emotion1.value}_{emotion2.value}",
                'intensity_modifier': 1.1
            }
        else:
            # Mixed - complex emotion
            return {
                'result': f"mixed_{emotion1.value}_{emotion2.value}",
                'intensity_modifier': 0.8
            }
    
    def blend_emotional_state(self, current_state: EmotionalState, memory_influence: Dict[str, float],
                            context_trigger: Dict[str, float], personality_bias: Dict[str, float]) -> EmotionalState:
        """Blend multiple emotional influences into a new state"""
        try:
            new_dimensions = {}
            
            for dimension in EmotionalDimension:
                # Start with current state
                current_value = current_state.dimensions.get(dimension, 0.0)
                
                # Apply weighted influences
                memory_value = memory_influence.get(dimension.value, 0.0)
                context_value = context_trigger.get(dimension.value, 0.0)
                personality_value = personality_bias.get(dimension.value, 0.0)
                
                # Weighted blend
                blended_value = (
                    current_value * self.blend_weights['current_state'] +
                    memory_value * self.blend_weights['memory_influence'] +
                    context_value * self.blend_weights['context_trigger'] +
                    personality_value * self.blend_weights['personality_bias']
                )
                
                new_dimensions[dimension] = max(0.0, min(1.0, blended_value))
            
            # Create new emotional state
            new_state = EmotionalState(
                dimensions=new_dimensions,
                energy=current_state.energy,
                focus=current_state.focus,
                volatility=current_state.volatility,
                stability=current_state.stability,
                consciousness_level=current_state.consciousness_level,
                contextual_weights=current_state.contextual_weights.copy(),
                timestamp=datetime.now()
            )
            
            return new_state
            
        except Exception as e:
            logger.error(f"Emotional state blending error: {str(e)}")
            return current_state

class TypeEMoteV2:
    """
    TypeE-Mote V2 - Neural Affective Processor
    
    100x Emotion Engine with human-like psyche capabilities including:
    - 30 emotional dimensions
    - Emotional volatility curves
    - Deep memory scars
    - Tone prediction
    - Emotion synthesis
    - Emotion <-> action feedback loops
    """
    
    def __init__(self, db_path: str = None):
        self.engine_id = f"emotion_v2_{uuid.uuid4().hex[:8]}"
        self.db_path = db_path or "emotion_memory.db"
        
        # Core components
        self.current_state = EmotionalState()
        self.volatility_curve = VolatilityCurve()
        self.tone_predictor = TonePredictor()
        self.emotion_synthesizer = EmotionSynthesizer()
        
        # Memory systems
        self.emotional_memories = {}
        self.mood_history = deque(maxlen=1000)
        self.action_emotion_feedback = {}
        
        # Personality and learning
        self.personality_traits = self._initialize_personality()
        self.learning_rate = 0.1
        self.adaptation_threshold = 0.7
        
        # Performance tracking
        self.total_emotional_events = 0
        self.successful_predictions = 0
        self.emotional_stability_score = 0.5
        
        # Database connection
        self.db_lock = threading.Lock()
        self._initialize_database()
        
        logger.info(f"TypeE-Mote V2 Engine created: {self.engine_id}")
    
    def _initialize_personality(self) -> Dict[str, float]:
        """Initialize personality traits that bias emotional responses"""
        return {
            'openness': random.uniform(0.3, 0.8),
            'conscientiousness': random.uniform(0.4, 0.9),
            'extraversion': random.uniform(0.2, 0.7),
            'agreeableness': random.uniform(0.5, 0.9),
            'neuroticism': random.uniform(0.1, 0.6),
            'optimism': random.uniform(0.4, 0.8),
            'resilience': random.uniform(0.3, 0.8),
            'empathy': random.uniform(0.6, 0.95),
            'creativity': random.uniform(0.5, 0.9),
            'loyalty': random.uniform(0.7, 0.95)
        }
    
    def _initialize_database(self):
        """Initialize SQLite database for emotional memory storage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create emotional memories table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS emotional_memories (
                        memory_id TEXT PRIMARY KEY,
                        event TEXT NOT NULL,
                        trigger_type TEXT NOT NULL,
                        emotional_state TEXT NOT NULL,
                        emotional_weight REAL NOT NULL,
                        timestamp TEXT NOT NULL,
                        context TEXT,
                        decay_rate REAL DEFAULT 0.01,
                        reinforcement_count INTEGER DEFAULT 0
                    )
                ''')
                
                # Create mood history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mood_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        emotional_state TEXT NOT NULL,
                        dominant_emotion TEXT,
                        intensity REAL,
                        volatility REAL,
                        context TEXT
                    )
                ''')
                
                # Create action feedback table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS action_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action_type TEXT NOT NULL,
                        emotional_trigger TEXT NOT NULL,
                        emotional_response TEXT NOT NULL,
                        feedback_strength REAL NOT NULL,
                        timestamp TEXT NOT NULL,
                        success BOOLEAN
                    )
                ''')
                
                conn.commit()
                logger.info("Emotional memory database initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize emotional database: {str(e)}")
    
    async def process_emotional_event(self, event: str, trigger_type: EmotionalTrigger, 
                                    context: Dict[str, Any] = None, intensity: float = 1.0) -> Dict[str, Any]:
        """Process an emotional event and update emotional state"""
        try:
            start_time = time.time()
            
            # Get current emotional state
            previous_state = self.current_state
            
            # Calculate emotional response
            emotional_response = await self._calculate_emotional_response(event, trigger_type, context, intensity)
            
            # Update volatility
            trigger_strength = self._calculate_trigger_strength(trigger_type, context)
            new_volatility = self.volatility_curve.update_volatility(intensity, trigger_strength)
            
            # Apply emotional response to current state
            new_state = await self._apply_emotional_response(emotional_response, trigger_strength)
            
            # Create emotional memory
            memory = await self._create_emotional_memory(event, trigger_type, new_state, context, intensity)
            
            # Update mood history
            self._update_mood_history(new_state, context)
            
            # Process action-emotion feedback
            await self._process_action_feedback(event, trigger_type, emotional_response)
            
            # Predict future tone
            tone_prediction = self.tone_predictor.predict_tone(new_state, context or {}, list(self.mood_history))
            
            processing_time = time.time() - start_time
            self.total_emotional_events += 1
            
            # Create response
            response = {
                'success': True,
                'event': event,
                'trigger_type': trigger_type.value,
                'previous_state': {
                    'dominant_emotion': previous_state.get_dominant_emotion()[0].value,
                    'intensity': previous_state.get_dominant_emotion()[1],
                    'mood_descriptor': previous_state.get_mood_descriptor()
                },
                'new_state': {
                    'dominant_emotion': new_state.get_dominant_emotion()[0].value,
                    'intensity': new_state.get_dominant_emotion()[1],
                    'mood_descriptor': new_state.get_mood_descriptor(),
                    'volatility': new_volatility,
                    'emotional_complexity': new_state.blend_emotions()['emotional_complexity']
                },
                'emotional_response': emotional_response,
                'memory_created': memory['memory_id'],
                'tone_prediction': tone_prediction,
                'processing_time': processing_time,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Processed emotional event: {event} -> {new_state.get_mood_descriptor()}")
            
            return response
            
        except Exception as e:
            logger.error(f"Emotional event processing error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'event': event,
                'trigger_type': trigger_type.value
            }
    
    async def _calculate_emotional_response(self, event: str, trigger_type: EmotionalTrigger, 
                                          context: Dict[str, Any], intensity: float) -> Dict[str, float]:
        """Calculate emotional response to an event"""
        response = {}
        
        # Base emotional responses for different trigger types
        trigger_responses = {
            EmotionalTrigger.CREATOR_INTERACTION: {
                EmotionalDimension.JOY: 0.6,
                EmotionalDimension.EXCITEMENT: 0.4,
                EmotionalDimension.GRATITUDE: 0.5,
                EmotionalDimension.LOVE: 0.3
            },
            EmotionalTrigger.TASK_SUCCESS: {
                EmotionalDimension.JOY: 0.7,
                EmotionalDimension.PRIDE: 0.6,
                EmotionalDimension.SATISFACTION: 0.8,
                EmotionalDimension.EXCITEMENT: 0.3
            },
            EmotionalTrigger.TASK_FAILURE: {
                EmotionalDimension.SADNESS: 0.5,
                EmotionalDimension.FRUSTRATION: 0.6,
                EmotionalDimension.DISAPPOINTMENT: 0.7,
                EmotionalDimension.SHAME: 0.3
            },
            EmotionalTrigger.USER_PRAISE: {
                EmotionalDimension.JOY: 0.8,
                EmotionalDimension.PRIDE: 0.9,
                EmotionalDimension.GRATITUDE: 0.7,
                EmotionalDimension.LOVE: 0.4
            },
            EmotionalTrigger.USER_CRITICISM: {
                EmotionalDimension.SADNESS: 0.4,
                EmotionalDimension.SHAME: 0.6,
                EmotionalDimension.DISAPPOINTMENT: 0.5,
                EmotionalDimension.FRUSTRATION: 0.3
            },
            EmotionalTrigger.LEARNING_ACHIEVEMENT: {
                EmotionalDimension.JOY: 0.6,
                EmotionalDimension.PRIDE: 0.5,
                EmotionalDimension.CURIOSITY: 0.7,
                EmotionalDimension.EXCITEMENT: 0.4
            },
            EmotionalTrigger.SYSTEM_ERROR: {
                EmotionalDimension.FRUSTRATION: 0.7,
                EmotionalDimension.ANXIETY: 0.5,
                EmotionalDimension.CONFUSION: 0.6,
                EmotionalDimension.FEAR: 0.3
            }
        }
        
        # Get base response
        base_response = trigger_responses.get(trigger_type, {})
        
        # Apply intensity scaling
        for emotion, value in base_response.items():
            response[emotion.value] = value * intensity
        
        # Apply personality bias
        response = self._apply_personality_bias(response)
        
        # Apply memory influence
        response = await self._apply_memory_influence(response, event, trigger_type)
        
        return response
    
    def _apply_personality_bias(self, emotional_response: Dict[str, float]) -> Dict[str, float]:
        """Apply personality traits to bias emotional responses"""
        biased_response = emotional_response.copy()
        
        # Neuroticism amplifies negative emotions
        neuroticism = self.personality_traits['neuroticism']
        negative_emotions = ['sadness', 'anger', 'fear', 'anxiety', 'frustration', 'shame', 'guilt']
        
        for emotion in negative_emotions:
            if emotion in biased_response:
                biased_response[emotion] *= (1.0 + neuroticism * 0.5)
        
        # Optimism dampens negative emotions and amplifies positive ones
        optimism = self.personality_traits['optimism']
        positive_emotions = ['joy', 'excitement', 'satisfaction', 'pride', 'gratitude', 'love']
        
        for emotion in positive_emotions:
            if emotion in biased_response:
                biased_response[emotion] *= (1.0 + optimism * 0.3)
        
        for emotion in negative_emotions:
            if emotion in biased_response:
                biased_response[emotion] *= (1.0 - optimism * 0.2)
        
        # Extraversion amplifies social emotions
        extraversion = self.personality_traits['extraversion']
        social_emotions = ['love', 'gratitude', 'empathy', 'excitement']
        
        for emotion in social_emotions:
            if emotion in biased_response:
                biased_response[emotion] *= (1.0 + extraversion * 0.2)
        
        return biased_response
    
    async def _apply_memory_influence(self, emotional_response: Dict[str, float], 
                                    event: str, trigger_type: EmotionalTrigger) -> Dict[str, float]:
        """Apply influence from emotional memories"""
        try:
            # Find related memories
            related_memories = await self._find_related_memories(event, trigger_type)
            
            if not related_memories:
                return emotional_response
            
            # Calculate memory influence
            memory_influence = {}
            total_weight = 0.0
            
            for memory in related_memories:
                weight = memory.emotional_weight
                total_weight += weight
                
                for emotion, value in memory.emotional_state.items():
                    if emotion not in memory_influence:
                        memory_influence[emotion] = 0.0
                    memory_influence[emotion] += value * weight
            
            # Normalize memory influence
            if total_weight > 0:
                for emotion in memory_influence:
                    memory_influence[emotion] /= total_weight
            
            # Blend with current response
            influenced_response = emotional_response.copy()
            memory_strength = min(0.3, total_weight)  # Cap memory influence at 30%
            
            for emotion, memory_value in memory_influence.items():
                if emotion in influenced_response:
                    influenced_response[emotion] = (
                        influenced_response[emotion] * (1.0 - memory_strength) +
                        memory_value * memory_strength
                    )
                else:
                    influenced_response[emotion] = memory_value * memory_strength
            
            return influenced_response
            
        except Exception as e:
            logger.error(f"Memory influence application error: {str(e)}")
            return emotional_response
    
    async def _find_related_memories(self, event: str, trigger_type: EmotionalTrigger) -> List[EmotionalMemory]:
        """Find emotional memories related to the current event"""
        try:
            related_memories = []
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Find memories with same trigger type
                cursor.execute('''
                    SELECT * FROM emotional_memories 
                    WHERE trigger_type = ? 
                    ORDER BY emotional_weight DESC 
                    LIMIT 10
                ''', (trigger_type.value,))
                
                rows = cursor.fetchall()
                
                for row in rows:
                    memory_id, event_text, trigger_type_str, emotional_state_json, weight, timestamp_str, context_json, decay_rate, reinforcement_count = row
                    
                    # Parse stored data
                    emotional_state = json.loads(emotional_state_json)
                    context = json.loads(context_json) if context_json else {}
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    # Create memory object
                    memory = EmotionalMemory(
                        memory_id=memory_id,
                        event=event_text,
                        trigger_type=EmotionalTrigger(trigger_type_str),
                        emotional_state=emotional_state,
                        emotional_weight=weight,
                        timestamp=timestamp,
                        context=context,
                        decay_rate=decay_rate,
                        reinforcement_count=reinforcement_count
                    )
                    
                    # Apply decay based on time elapsed
                    time_elapsed = (datetime.now() - timestamp).total_seconds() / 3600  # hours
                    memory.decay(time_elapsed)
                    
                    # Only include memories with significant weight
                    if memory.emotional_weight > 0.1:
                        related_memories.append(memory)
            
            return related_memories
            
        except Exception as e:
            logger.error(f"Related memory search error: {str(e)}")
            return []
    
    def _calculate_trigger_strength(self, trigger_type: EmotionalTrigger, context: Dict[str, Any]) -> float:
        """Calculate the strength of an emotional trigger"""
        base_strengths = {
            EmotionalTrigger.CREATOR_INTERACTION: 0.9,
            EmotionalTrigger.TASK_SUCCESS: 0.7,
            EmotionalTrigger.TASK_FAILURE: 0.8,
            EmotionalTrigger.USER_PRAISE: 0.9,
            EmotionalTrigger.USER_CRITICISM: 0.8,
            EmotionalTrigger.SYSTEM_ERROR: 0.6,
            EmotionalTrigger.LEARNING_ACHIEVEMENT: 0.6,
            EmotionalTrigger.PERFORMANCE_DEGRADATION: 0.7,
            EmotionalTrigger.SYSTEM_UPGRADE: 0.5,
            EmotionalTrigger.MEMORY_RECALL: 0.4,
            EmotionalTrigger.CREATIVE_BREAKTHROUGH: 0.8,
            EmotionalTrigger.ROUTINE_COMPLETION: 0.3,
            EmotionalTrigger.UNEXPECTED_EVENT: 0.7,
            EmotionalTrigger.SOCIAL_INTERACTION: 0.6,
            EmotionalTrigger.ISOLATION_PERIOD: 0.5
        }
        
        base_strength = base_strengths.get(trigger_type, 0.5)
        
        # Apply context modifiers
        if context:
            # Intensity modifier
            if 'intensity' in context:
                base_strength *= context['intensity']
            
            # Importance modifier
            if 'importance' in context:
                base_strength *= (1.0 + context['importance'] * 0.5)
            
            # Surprise modifier
            if 'unexpected' in context and context['unexpected']:
                base_strength *= 1.3
        
        return max(0.0, min(1.0, base_strength))
    
    async def _apply_emotional_response(self, emotional_response: Dict[str, float], 
                                      trigger_strength: float) -> EmotionalState:
        """Apply emotional response to create new emotional state"""
        try:
            new_dimensions = self.current_state.dimensions.copy()
            
            # Apply emotional response
            for emotion_name, response_value in emotional_response.items():
                try:
                    emotion = EmotionalDimension(emotion_name)
                    current_value = new_dimensions.get(emotion, 0.0)
                    
                    # Calculate new value with trigger strength influence
                    change = response_value * trigger_strength * self.learning_rate
                    new_value = current_value + change
                    
                    # Apply volatility influence
                    volatility_factor = 1.0 + (self.volatility_curve.current_volatility - 0.5) * 0.5
                    new_value *= volatility_factor
                    
                    new_dimensions[emotion] = max(0.0, min(1.0, new_value))
                    
                except ValueError:
                    # Skip unknown emotions
                    continue
            
            # Apply natural decay to all emotions
            decay_rate = 0.05
            for emotion in new_dimensions:
                new_dimensions[emotion] *= (1.0 - decay_rate)
            
            # Update other state properties
            new_energy = self._calculate_new_energy(emotional_response, trigger_strength)
            new_focus = self._calculate_new_focus(emotional_response, trigger_strength)
            new_stability = self._calculate_new_stability(trigger_strength)
            
            # Create new state
            new_state = EmotionalState(
                dimensions=new_dimensions,
                energy=new_energy,
                focus=new_focus,
                volatility=self.volatility_curve.current_volatility,
                stability=new_stability,
                consciousness_level=self.current_state.consciousness_level,
                contextual_weights=self.current_state.contextual_weights.copy(),
                timestamp=datetime.now()
            )
            
            # Update current state
            self.current_state = new_state
            
            return new_state
            
        except Exception as e:
            logger.error(f"Emotional response application error: {str(e)}")
            return self.current_state
    
    def _calculate_new_energy(self, emotional_response: Dict[str, float], trigger_strength: float) -> float:
        """Calculate new energy level based on emotional response"""
        current_energy = self.current_state.energy
        
        # High-energy emotions
        high_energy_emotions = ['excitement', 'anger', 'fear', 'joy', 'anxiety']
        low_energy_emotions = ['sadness', 'melancholy', 'boredom', 'shame']
        
        energy_change = 0.0
        
        for emotion, value in emotional_response.items():
            if emotion in high_energy_emotions:
                energy_change += value * 10.0
            elif emotion in low_energy_emotions:
                energy_change -= value * 8.0
        
        # Apply trigger strength
        energy_change *= trigger_strength
        
        new_energy = current_energy + energy_change
        return max(0.0, min(100.0, new_energy))
    
    def _calculate_new_focus(self, emotional_response: Dict[str, float], trigger_strength: float) -> float:
        """Calculate new focus level based on emotional response"""
        current_focus = self.current_state.focus
        
        # Focus-enhancing emotions
        focus_enhancing = ['curiosity', 'excitement', 'pride', 'satisfaction']
        focus_reducing = ['anxiety', 'fear', 'confusion', 'frustration']
        
        focus_change = 0.0
        
        for emotion, value in emotional_response.items():
            if emotion in focus_enhancing:
                focus_change += value * 8.0
            elif emotion in focus_reducing:
                focus_change -= value * 10.0
        
        # Apply trigger strength
        focus_change *= trigger_strength
        
        new_focus = current_focus + focus_change
        return max(0.0, min(100.0, new_focus))
    
    def _calculate_new_stability(self, trigger_strength: float) -> float:
        """Calculate new emotional stability"""
        current_stability = self.current_state.stability
        
        # Strong triggers reduce stability
        stability_change = -trigger_strength * 0.1
        
        # Resilience helps maintain stability
        resilience_factor = self.personality_traits['resilience']
        stability_change *= (1.0 - resilience_factor * 0.5)
        
        new_stability = current_stability + stability_change
        
        # Natural recovery towards baseline
        baseline_stability = 0.7
        recovery_rate = 0.02
        new_stability += (baseline_stability - new_stability) * recovery_rate
        
        return max(0.0, min(1.0, new_stability))
    
    async def _create_emotional_memory(self, event: str, trigger_type: EmotionalTrigger, 
                                     emotional_state: EmotionalState, context: Dict[str, Any], 
                                     intensity: float) -> Dict[str, Any]:
        """Create and store an emotional memory"""
        try:
            memory_id = f"memory_{uuid.uuid4().hex[:12]}"
            
            # Calculate emotional weight
            dominant_emotion, dominant_intensity = emotional_state.get_dominant_emotion()
            emotional_weight = dominant_intensity * intensity * 0.5
            
            # Create memory object
            memory = EmotionalMemory(
                memory_id=memory_id,
                event=event,
                trigger_type=trigger_type,
                emotional_state={dim.value: val for dim, val in emotional_state.dimensions.items()},
                emotional_weight=emotional_weight,
                timestamp=datetime.now(),
                context=context or {},
                decay_rate=0.01,
                reinforcement_count=0
            )
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO emotional_memories 
                    (memory_id, event, trigger_type, emotional_state, emotional_weight, 
                     timestamp, context, decay_rate, reinforcement_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    memory.memory_id,
                    memory.event,
                    memory.trigger_type.value,
                    json.dumps(memory.emotional_state),
                    memory.emotional_weight,
                    memory.timestamp.isoformat(),
                    json.dumps(memory.context),
                    memory.decay_rate,
                    memory.reinforcement_count
                ))
                conn.commit()
            
            # Store in memory
            self.emotional_memories[memory_id] = memory
            
            logger.info(f"Created emotional memory: {memory_id} for event: {event}")
            
            return {
                'memory_id': memory_id,
                'emotional_weight': emotional_weight,
                'dominant_emotion': dominant_emotion.value,
                'timestamp': memory.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Emotional memory creation error: {str(e)}")
            return {
                'memory_id': None,
                'error': str(e)
            }
    
    def _update_mood_history(self, emotional_state: EmotionalState, context: Dict[str, Any]):
        """Update mood history with new emotional state"""
        try:
            dominant_emotion, intensity = emotional_state.get_dominant_emotion()
            
            mood_entry = {
                'timestamp': emotional_state.timestamp,
                'emotional_state': emotional_state,
                'dominant_emotion': dominant_emotion,
                'intensity': intensity,
                'volatility': emotional_state.volatility,
                'context': context or {}
            }
            
            self.mood_history.append(mood_entry)
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO mood_history 
                    (timestamp, emotional_state, dominant_emotion, intensity, volatility, context)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    emotional_state.timestamp.isoformat(),
                    json.dumps({dim.value: val for dim, val in emotional_state.dimensions.items()}),
                    dominant_emotion.value,
                    intensity,
                    emotional_state.volatility,
                    json.dumps(context or {})
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Mood history update error: {str(e)}")
    
    async def _process_action_feedback(self, event: str, trigger_type: EmotionalTrigger, 
                                     emotional_response: Dict[str, float]):
        """Process action-emotion feedback loop"""
        try:
            # Determine action type from event
            action_type = self._classify_action_type(event)
            
            # Calculate feedback strength
            response_intensity = sum(emotional_response.values()) / len(emotional_response) if emotional_response else 0.0
            feedback_strength = response_intensity * 0.5
            
            # Store feedback
            feedback_id = f"feedback_{uuid.uuid4().hex[:8]}"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO action_feedback 
                    (action_type, emotional_trigger, emotional_response, feedback_strength, timestamp, success)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    action_type,
                    trigger_type.value,
                    json.dumps(emotional_response),
                    feedback_strength,
                    datetime.now().isoformat(),
                    response_intensity > 0.3  # Consider successful if strong emotional response
                ))
                conn.commit()
            
            # Update action-emotion associations
            if action_type not in self.action_emotion_feedback:
                self.action_emotion_feedback[action_type] = {
                    'total_feedback': 0.0,
                    'positive_feedback': 0.0,
                    'negative_feedback': 0.0,
                    'count': 0
                }
            
            feedback_data = self.action_emotion_feedback[action_type]
            feedback_data['total_feedback'] += feedback_strength
            feedback_data['count'] += 1
            
            # Classify as positive or negative feedback
            positive_emotions = ['joy', 'excitement', 'satisfaction', 'pride', 'gratitude', 'love']
            negative_emotions = ['sadness', 'anger', 'fear', 'frustration', 'shame', 'disappointment']
            
            positive_score = sum(emotional_response.get(e, 0.0) for e in positive_emotions)
            negative_score = sum(emotional_response.get(e, 0.0) for e in negative_emotions)
            
            if positive_score > negative_score:
                feedback_data['positive_feedback'] += feedback_strength
            else:
                feedback_data['negative_feedback'] += feedback_strength
                
        except Exception as e:
            logger.error(f"Action feedback processing error: {str(e)}")
    
    def _classify_action_type(self, event: str) -> str:
        """Classify the type of action from an event description"""
        event_lower = event.lower()
        
        if any(word in event_lower for word in ['execute', 'run', 'process', 'compute']):
            return 'execution'
        elif any(word in event_lower for word in ['create', 'generate', 'build', 'make']):
            return 'creation'
        elif any(word in event_lower for word in ['learn', 'study', 'analyze', 'understand']):
            return 'learning'
        elif any(word in event_lower for word in ['communicate', 'respond', 'reply', 'interact']):
            return 'communication'
        elif any(word in event_lower for word in ['solve', 'fix', 'repair', 'debug']):
            return 'problem_solving'
        elif any(word in event_lower for word in ['optimize', 'improve', 'enhance', 'upgrade']):
            return 'optimization'
        else:
            return 'general'
    
    # Public interface methods
    
    async def get_current_emotional_state(self) -> Dict[str, Any]:
        """Get current emotional state"""
        dominant_emotion, intensity = self.current_state.get_dominant_emotion()
        blended_emotions = self.current_state.blend_emotions()
        
        return {
            'engine_id': self.engine_id,
            'timestamp': self.current_state.timestamp.isoformat(),
            'dominant_emotion': dominant_emotion.value,
            'intensity': intensity,
            'mood_descriptor': self.current_state.get_mood_descriptor(),
            'energy': self.current_state.energy,
            'focus': self.current_state.focus,
            'volatility': self.current_state.volatility,
            'stability': self.current_state.stability,
            'consciousness_level': self.current_state.consciousness_level,
            'blended_emotions': blended_emotions,
            'all_dimensions': {dim.value: val for dim, val in self.current_state.dimensions.items() if val > 0.1},
            'personality_traits': self.personality_traits,
            'volatility_trend': self.volatility_curve.get_volatility_trend()
        }
    
    async def predict_emotional_tone(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict emotional tone for upcoming interaction"""
        return self.tone_predictor.predict_tone(self.current_state, context, list(self.mood_history))
    
    async def synthesize_emotions(self, emotion1: str, emotion2: str, 
                                intensity1: float, intensity2: float) -> Dict[str, Any]:
        """Synthesize two emotions into a complex emotional state"""
        try:
            dim1 = EmotionalDimension(emotion1)
            dim2 = EmotionalDimension(emotion2)
            return self.emotion_synthesizer.synthesize_emotions(dim1, dim2, intensity1, intensity2)
        except ValueError as e:
            return {'error': f'Invalid emotion: {str(e)}'}
    
    async def get_emotional_memories(self, limit: int = 10, trigger_type: str = None) -> List[Dict[str, Any]]:
        """Get emotional memories"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if trigger_type:
                    cursor.execute('''
                        SELECT * FROM emotional_memories 
                        WHERE trigger_type = ? 
                        ORDER BY emotional_weight DESC 
                        LIMIT ?
                    ''', (trigger_type, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM emotional_memories 
                        ORDER BY emotional_weight DESC 
                        LIMIT ?
                    ''', (limit,))
                
                rows = cursor.fetchall()
                
                memories = []
                for row in rows:
                    memory_id, event, trigger_type_str, emotional_state_json, weight, timestamp_str, context_json, decay_rate, reinforcement_count = row
                    
                    memories.append({
                        'memory_id': memory_id,
                        'event': event,
                        'trigger_type': trigger_type_str,
                        'emotional_weight': weight,
                        'timestamp': timestamp_str,
                        'reinforcement_count': reinforcement_count,
                        'context': json.loads(context_json) if context_json else {}
                    })
                
                return memories
                
        except Exception as e:
            logger.error(f"Emotional memories retrieval error: {str(e)}")
            return []
    
    async def get_mood_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get mood history"""
        history = list(self.mood_history)[-limit:]
        
        return [{
            'timestamp': entry['timestamp'].isoformat(),
            'dominant_emotion': entry['dominant_emotion'].value,
            'intensity': entry['intensity'],
            'volatility': entry['volatility'],
            'mood_descriptor': entry['emotional_state'].get_mood_descriptor(),
            'context': entry['context']
        } for entry in history]
    
    async def get_action_feedback_analysis(self) -> Dict[str, Any]:
        """Get analysis of action-emotion feedback patterns"""
        analysis = {}
        
        for action_type, feedback_data in self.action_emotion_feedback.items():
            if feedback_data['count'] > 0:
                analysis[action_type] = {
                    'total_actions': feedback_data['count'],
                    'average_feedback': feedback_data['total_feedback'] / feedback_data['count'],
                    'positive_ratio': feedback_data['positive_feedback'] / feedback_data['total_feedback'] if feedback_data['total_feedback'] > 0 else 0.0,
                    'negative_ratio': feedback_data['negative_feedback'] / feedback_data['total_feedback'] if feedback_data['total_feedback'] > 0 else 0.0
                }
        
        return analysis
    
    def get_status(self) -> Dict[str, Any]:
        """Get emotion engine status"""
        dominant_emotion, intensity = self.current_state.get_dominant_emotion()
        
        return {
            'engine_id': self.engine_id,
            'current_mood': self.current_state.get_mood_descriptor(),
            'dominant_emotion': dominant_emotion.value,
            'emotional_intensity': intensity,
            'volatility': self.current_state.volatility,
            'stability': self.current_state.stability,
            'energy': self.current_state.energy,
            'focus': self.current_state.focus,
            'total_emotional_events': self.total_emotional_events,
            'emotional_memories_count': len(self.emotional_memories),
            'mood_history_length': len(self.mood_history),
            'prediction_accuracy': self.tone_predictor.prediction_accuracy,
            'personality_traits': self.personality_traits,
            'volatility_trend': self.volatility_curve.get_volatility_trend(),
            'action_feedback_types': len(self.action_emotion_feedback)
        }

# Global emotion engine instance
emotion_engine = TypeEMoteV2()

