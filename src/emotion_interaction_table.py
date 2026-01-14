
import numpy as np
from typing import Dict, List
from .emotion_200d_system import EmotionDimension, EmotionState

class EmotionInteractionTable:
    def __init__(self):
        self.interaction_matrix = self._initialize_interaction_matrix()

    def _initialize_interaction_matrix(self) -> Dict[EmotionDimension, Dict[EmotionDimension, float]]:
        matrix = {dim: {other_dim: 0.0 for other_dim in EmotionDimension} for dim in EmotionDimension}
        
        # Define some example interactions (a full implementation would be more extensive)
        matrix[EmotionDimension.JOY][EmotionDimension.TRUST] = 0.5 # Joy and Trust reinforce each other
        matrix[EmotionDimension.TRUST][EmotionDimension.JOY] = 0.5

        matrix[EmotionDimension.FEAR][EmotionDimension.ANGER] = 0.3 # Fear can lead to anger
        matrix[EmotionDimension.ANGER][EmotionDimension.FEAR] = 0.3

        matrix[EmotionDimension.SADNESS][EmotionDimension.JOY] = -0.4 # Sadness dampens joy
        matrix[EmotionDimension.JOY][EmotionDimension.SADNESS] = -0.4

        return matrix

    def blend_emotions(self, emotion_state: EmotionState) -> EmotionState:
        new_values = emotion_state.dimension_values.copy()
        for dim, interactions in self.interaction_matrix.items():
            for other_dim, weight in interactions.items():
                if weight != 0.0:
                    influence = emotion_state.get_emotion_value(other_dim) * weight
                    new_values[dim] = np.clip(new_values[dim] + influence, 0.0, 1.0)
        
        emotion_state.dimension_values = new_values
        return emotion_state

# Example Usage:
if __name__ == "__main__":
    interaction_table = EmotionInteractionTable()
    emotion_state = EmotionState()

    emotion_state.update_emotion(EmotionDimension.JOY, 0.8)
    emotion_state.update_emotion(EmotionDimension.TRUST, 0.7)
    print(f"Initial Joy: {emotion_state.get_emotion_value(EmotionDimension.JOY)}")
    print(f"Initial Trust: {emotion_state.get_emotion_value(EmotionDimension.TRUST)}")

    blended_state = interaction_table.blend_emotions(emotion_state)
    print(f"\nBlended Joy: {blended_state.get_emotion_value(EmotionDimension.JOY)}")
    print(f"Blended Trust: {blended_state.get_emotion_value(EmotionDimension.TRUST)}")

    emotion_state.update_emotion(EmotionDimension.SADNESS, 0.9)
    print(f"\nInitial Sadness: {emotion_state.get_emotion_value(EmotionDimension.SADNESS)}")
    blended_state = interaction_table.blend_emotions(emotion_state)
    print(f"Joy after sadness blend: {blended_state.get_emotion_value(EmotionDimension.JOY)}")


