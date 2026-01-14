
import numpy as np
from typing import Dict, List
from .emotion_200d_system import EmotionState, EmotionDimension
from .cluster_modulation import ClusterModulator

class MoodStabilizer:
    def __init__(self, target_energy_level: float = 0.5, stabilization_factor: float = 0.5):
        self.target_energy_level = target_energy_level
        self.stabilization_factor = stabilization_factor
        self.cluster_modulator = ClusterModulator() # Ensure this is correctly initialized

    def normalize_cluster_energy(self, emotion_state: EmotionState, cluster_name: str) -> EmotionState:
        """
        Normalizes the energy level of a specific emotional cluster towards a target.
        Energy level is approximated by the average value of emotions within the cluster.
        """
        current_average = self.cluster_modulator.get_cluster_average(emotion_state, cluster_name)
        
        if current_average > self.target_energy_level:
            # If too high, mute the cluster
            modulation_factor = min(self.stabilization_factor, current_average - self.target_energy_level)
            emotion_state = self.cluster_modulator.modulate_cluster(emotion_state, cluster_name, modulation_factor, "mute")
        elif current_average < self.target_energy_level:
            # If too low, amplify the cluster
            modulation_factor = min(self.stabilization_factor, self.target_energy_level - current_average)
            emotion_state = self.cluster_modulator.modulate_cluster(emotion_state, cluster_name, modulation_factor, "amplify")
        
        return emotion_state

    def stabilize_all_clusters(self, emotion_state: EmotionState) -> EmotionState:
        """
        Applies stabilization to all defined emotional clusters.
        """
        for cluster_name in self.cluster_modulator.modulation_rules.keys():
            emotion_state = self.normalize_cluster_energy(emotion_state, cluster_name)
        return emotion_state

# Example Usage:
if __name__ == "__main__":
    stabilizer = MoodStabilizer(target_energy_level=0.6, stabilization_factor=0.1)
    emotion_state = EmotionState()

    # Set initial values for positive affect to be high
    emotion_state.update_emotion(EmotionDimension.JOY, 0.9)
    emotion_state.update_emotion(EmotionDimension.OPTIMISM, 0.8)
    print(f"Initial Joy: {emotion_state.get_emotion_value(EmotionDimension.JOY)}")
    print(f"Initial Optimism: {emotion_state.get_emotion_value(EmotionDimension.OPTIMISM)}")
    print(f"Initial Average Positive Cluster: {stabilizer.cluster_modulator.get_cluster_average(emotion_state, 'positive_cluster')}")

    # Stabilize positive affect
    print("\nStabilizing positive_cluster...")
    emotion_state = stabilizer.normalize_cluster_energy(emotion_state, "positive_cluster")
    print(f"Joy after stabilization: {emotion_state.get_emotion_value(EmotionDimension.JOY)}")
    print(f"Optimism after stabilization: {emotion_state.get_emotion_value(EmotionDimension.OPTIMISM)}")
    print(f"Average Positive Cluster after stabilization: {stabilizer.cluster_modulator.get_cluster_average(emotion_state, 'positive_cluster')}")

    # Set initial values for negative affect to be low
    emotion_state.update_emotion(EmotionDimension.SADNESS, 0.1)
    emotion_state.update_emotion(EmotionDimension.ANGER, 0.2)
    print(f"\nInitial Sadness: {emotion_state.get_emotion_value(EmotionDimension.SADNESS)}")
    print(f"Initial Anger: {emotion_state.get_emotion_value(EmotionDimension.ANGER)}")
    print(f"Initial Average Negative Cluster: {stabilizer.cluster_modulator.get_cluster_average(emotion_state, 'negative_cluster')}")

    # Stabilize all clusters
    print("\nStabilizing all clusters...")
    emotion_state = stabilizer.stabilize_all_clusters(emotion_state)
    print(f"Sadness after stabilization: {emotion_state.get_emotion_value(EmotionDimension.SADNESS)}")
    print(f"Anger after stabilization: {emotion_state.get_emotion_value(EmotionDimension.ANGER)}")
    print(f"Average Negative Cluster after stabilization: {stabilizer.cluster_modulator.get_cluster_average(emotion_state, 'negative_cluster')}")




