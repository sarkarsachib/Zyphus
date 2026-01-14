
import numpy as np
from typing import Dict, List
from .emotion_200d_system import EmotionState, EmotionDimension

class EmotionEntropyFilter:
    def __init__(self, smoothing_factor: float = 0.2, max_spike_threshold: float = 0.2):
        self.smoothing_factor = smoothing_factor
        self.max_spike_threshold = max_spike_threshold

    def apply_filter(self, emotion_state: EmotionState, previous_emotion_state: EmotionState) -> EmotionState:
        """
        Applies an entropy filter to smooth out sudden spikes in emotional dimensions.
        Uses a simple exponential moving average (EMA) for smoothing and caps large changes.
        """
        new_emotion_state = EmotionState(dimension_values=emotion_state.dimension_values.copy())

        for dim in EmotionDimension:
            current_value = emotion_state.get_emotion_value(dim)
            previous_value = previous_emotion_state.get_emotion_value(dim)

            # Calculate the difference
            difference = current_value - previous_value

            # If the difference is a large spike, cap it
            if abs(difference) > self.max_spike_threshold:
                if difference > 0:
                    current_value = previous_value + self.max_spike_threshold
                else:
                    current_value = previous_value - self.max_spike_threshold

            # Apply exponential moving average for smoothing
            smoothed_value = (self.smoothing_factor * current_value) + \
                             ((1 - self.smoothing_factor) * previous_value)
            
            new_emotion_state.update_emotion(dim, smoothed_value)

        return new_emotion_state

# Example Usage:
if __name__ == "__main__":
    filter = EmotionEntropyFilter(smoothing_factor=0.2, max_spike_threshold=0.2)
    
    # Initial state
    initial_state = EmotionState()
    initial_state.update_emotion(EmotionDimension.JOY, 0.5)
    initial_state.update_emotion(EmotionDimension.ANGER, 0.5)
    print(f"Initial Joy: {initial_state.get_emotion_value(EmotionDimension.JOY)}")
    print(f"Initial Anger: {initial_state.get_emotion_value(EmotionDimension.ANGER)}")

    # Simulate a sudden spike in Joy
    current_state_spike = EmotionState()
    current_state_spike.update_emotion(EmotionDimension.JOY, 0.9) # Large jump
    current_state_spike.update_emotion(EmotionDimension.ANGER, 0.1) # Large drop

    filtered_state = filter.apply_filter(current_state_spike, initial_state)
    print(f"\nFiltered Joy (after spike): {filtered_state.get_emotion_value(EmotionDimension.JOY)}")
    print(f"Filtered Anger (after drop): {filtered_state.get_emotion_value(EmotionDimension.ANGER)}")

    # Simulate a small change
    current_state_small_change = EmotionState()
    current_state_small_change.update_emotion(EmotionDimension.JOY, 0.6)
    current_state_small_change.update_emotion(EmotionDimension.ANGER, 0.4)

    filtered_state_small_change = filter.apply_filter(current_state_small_change, initial_state)
    print(f"\nFiltered Joy (small change): {filtered_state_small_change.get_emotion_value(EmotionDimension.JOY)}")
    print(f"Filtered Anger (small change): {filtered_state_small_change.get_emotion_value(EmotionDimension.ANGER)}")




