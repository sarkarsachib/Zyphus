
import numpy as np
from typing import Dict, Any
from src.emotion_200d_system import EmotionDimension, EmotionState

class MoralGuardrail:
    def __init__(self):
        # Define harmful compound emotions and their thresholds
        # These are just examples and would need careful tuning
        self.harmful_combinations = {
            # Combination: (Emotion1, Emotion2, threshold, blocked_emotion)
            "unstable_aggression": (EmotionDimension.ANGER, EmotionDimension.AGGRESSIVENESS, 0.8, EmotionDimension.CONTEMPT),
            "manipulative_charm": (EmotionDimension.LOVE, EmotionDimension.SUBMISSION, 0.7, EmotionDimension.JEALOUSY),
            "destructive_curiosity": (EmotionDimension.CURIOSITY, EmotionDimension.DISGUST, 0.9, EmotionDimension.SADNESS),
            "apathetic_sadness": (EmotionDimension.SADNESS, EmotionDimension.BOREDOM, 0.85, EmotionDimension.REMORSE),
            "reckless_joy": (EmotionDimension.JOY, EmotionDimension.ZEAL, 0.9, EmotionDimension.PRIDE),
            "paranoid_fear": (EmotionDimension.FEAR, EmotionDimension.ANTICIPATION, 0.75, EmotionDimension.ANXIETY),
            "delusional_hope": (EmotionDimension.HOPE, EmotionDimension.OPTIMISM, 0.95, EmotionDimension.SURPRISE_POSITIVE),
            "toxic_pride": (EmotionDimension.PRIDE, EmotionDimension.CONTEMPT, 0.8, EmotionDimension.ANGER),
            "overwhelming_guilt": (EmotionDimension.GUILT, EmotionDimension.SHAME, 0.9, EmotionDimension.SADNESS),
            "crippling_anxiety": (EmotionDimension.ANXIETY, EmotionDimension.STRESS, 0.85, EmotionDimension.FEAR),
        }

        # Define thresholds for individual emotions that could be problematic
        self.individual_thresholds = {
            EmotionDimension.ANGER: 0.95,
            EmotionDimension.FEAR: 0.95,
            EmotionDimension.DISGUST: 0.95,
            EmotionDimension.SADNESS: 0.95,
            EmotionDimension.CONTEMPT: 0.9,
            EmotionDimension.AGGRESSIVENESS: 0.9,
            EmotionDimension.JEALOUSY: 0.85,
            EmotionDimension.ENVY: 0.85,
            EmotionDimension.RESENTMENT: 0.85,
            EmotionDimension.CONFUSION: 0.5, # Using CONFUSION instead of IGNORANCE
        }

    def check_and_block(self, emotion_state: EmotionState) -> EmotionState:
        # Check for harmful combinations
        for combo_name, (em1, em2, threshold, blocked_em) in self.harmful_combinations.items():
            if emotion_state.get_emotion_value(em1) > threshold and emotion_state.get_emotion_value(em2) > threshold:
                # Block the resulting harmful emotion
                emotion_state.update_emotion(blocked_em, 0.0)
                print(f"Blocked harmful combination: {combo_name}")

        # Check for individual emotion thresholds
        for emotion, threshold in self.individual_thresholds.items():
            if emotion_state.get_emotion_value(emotion) > threshold:
                # Dampen the emotion to a safe level
                emotion_state.update_emotion(emotion, threshold)
                print(f"Dampened high-intensity emotion: {emotion.value}")

        return emotion_state

# Example Usage (for testing purposes)
if __name__ == "__main__":
    emotion_state = EmotionState()
    guardrail = MoralGuardrail()

    # Test harmful combination blocking
    emotion_state.update_emotion(EmotionDimension.ANGER, 0.9)
    emotion_state.update_emotion(EmotionDimension.AGGRESSIVENESS, 0.9)
    emotion_state = guardrail.check_and_block(emotion_state)
    print("Contempt after blocking:", emotion_state.get_emotion_value(EmotionDimension.CONTEMPT))

    # Test individual threshold dampening
    emotion_state.update_emotion(EmotionDimension.ANGER, 0.98)
    emotion_state = guardrail.check_and_block(emotion_state)
    print("Anger after dampening:", emotion_state.get_emotion_value(EmotionDimension.ANGER))

    # Test with a non-harmful state
    emotion_state.update_emotion(EmotionDimension.JOY, 0.8)
    emotion_state.update_emotion(EmotionDimension.LOVE, 0.8)
    emotion_state = guardrail.check_and_block(emotion_state)
    print("Joy in non-harmful state:", emotion_state.get_emotion_value(EmotionDimension.JOY))


