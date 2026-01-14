
import numpy as np
from typing import Dict, Any
from src.emotion_200d_system import EmotionDimension, EmotionState

class ClusterModulator:
    def __init__(self):
        # Define how different emotional clusters can be modulated
        # This is a simplified example; a real system would have complex rules
        self.modulation_rules = {
            "positive_cluster": [
                EmotionDimension.JOY, EmotionDimension.LOVE, EmotionDimension.OPTIMISM, EmotionDimension.GRATITUDE, EmotionDimension.SATISFACTION,
                EmotionDimension.SERENITY, EmotionDimension.TRIUMPH, EmotionDimension.WONDER, EmotionDimension.ZEAL, EmotionDimension.SPARKLING_VIBRANCE,
                EmotionDimension.SOOTHING_GENTLE, EmotionDimension.SOLACE_COMFORT_RELIEF, EmotionDimension.SOFTNESS_DELICACY, EmotionDimension.SMOOTHNESS_ELEGANCE,
                EmotionDimension.SLUMBER_DREAM, EmotionDimension.SLACK_RELAXED, EmotionDimension.SERENITY_TRANQUILITY, EmotionDimension.SENSITIVITY_PERCEPTIVE,
                EmotionDimension.SELF_CONTROL_RESTRAINT, EmotionDimension.SELF_AWARENESS_CONSCIOUSNESS, EmotionDimension.SELF_ACCEPTANCE_CONTENTMENT,
                EmotionDimension.SELF_ASSURANCE_POISE, EmotionDimension.SELF_COMPASSION_EMPATHY, EmotionDimension.SELF_DISCIPLINE_FOCUS,
                EmotionDimension.SELF_EFFICACY_COMPETENCE, EmotionDimension.SELF_FORGIVENESS_ACCEPTANCE, EmotionDimension.SELF_LOVE_WELLBEING,
                EmotionDimension.SELF_RESPECT_INTEGRITY, EmotionDimension.SELF_SOOTHING_COMFORT, EmotionDimension.SELF_TRANSCENDENCE_ENLIGHTENMENT,
                EmotionDimension.SELF_WORTH_ESTEEM, EmotionDimension.SENSUALITY_GRATIFICATION, EmotionDimension.SENTIENCE_AWARENESS,
                EmotionDimension.SHIMMERING_LUSTER, EmotionDimension.SILENCE_CALM, EmotionDimension.SINCERITY_TRUTHFULNESS,
                EmotionDimension.SOLITUDE_TRANQUILITY, EmotionDimension.SOPHISTICATION_REFINEMENT, EmotionDimension.SPACIOUSNESS_FREEDOM,
                EmotionDimension.SPARK_INSPIRATION, EmotionDimension.SPIRIT_ESSENCE_SOUL, EmotionDimension.SPIRITEDNESS_ENTHUSIASM,
                EmotionDimension.SPLENDOR_GLORY, EmotionDimension.STABILITY_STEADINESS, EmotionDimension.STEADFASTNESS_RESOLVE,
                EmotionDimension.STIMULATION_AROUSAL, EmotionDimension.STRENGTH_POWER, EmotionDimension.SUBLIME_BEAUTY,
                EmotionDimension.SUPPORT_ENCOURAGEMENT, EmotionDimension.SUSTAINABILITY_RESILIENCE, EmotionDimension.SWEETNESS_GENTLENESS,
                EmotionDimension.TENDERNESS_AFFECTION, EmotionDimension.THANKFULNESS_APPRECIATION, EmotionDimension.THRILL_ADRENALINE
            ],
            "negative_cluster": [
                EmotionDimension.SADNESS, EmotionDimension.ANGER, EmotionDimension.FEAR, EmotionDimension.DISGUST, EmotionDimension.REMORSE,
                EmotionDimension.CONTEMPT, EmotionDimension.ANXIETY, EmotionDimension.FRUSTRATION, EmotionDimension.INDIGNATION, EmotionDimension.LONELINESS,
                EmotionDimension.RESENTMENT, EmotionDimension.STRESS, EmotionDimension.SURPRISE_NEGATIVE, EmotionDimension.VULNERABILITY,
                EmotionDimension.ZONKED_OUT, EmotionDimension.UNSETTLED_RESTLESS, EmotionDimension.GUILT, EmotionDimension.SHAME, EmotionDimension.PRIDE,
                EmotionDimension.ENVY, EmotionDimension.JEALOUSY, EmotionDimension.BOREDOM
            ],
            "neutral_cluster": [
                EmotionDimension.SURPRISE, EmotionDimension.CALM, EmotionDimension.CONFUSION, EmotionDimension.CURIOSITY,
                EmotionDimension.EMBARRASSMENT, EmotionDimension.HUMILITY, EmotionDimension.MINDFULNESS, EmotionDimension.OPENNESS,
                EmotionDimension.PRESENCE, EmotionDimension.SIMPLICITY, EmotionDimension.SPONTANEITY, EmotionDimension.UNDERSTANDING,
                EmotionDimension.ZEN, EmotionDimension.ZING, EmotionDimension.ZAPPY, EmotionDimension.ZANY, EmotionDimension.YOUTHFULNESS,
                EmotionDimension.WISTFULNESS, EmotionDimension.WHIMSICALITY, EmotionDimension.VIBRANCY, EmotionDimension.VIGOR, EmotionDimension.VERVE,
                EmotionDimension.UNRUFFLED, EmotionDimension.UNFLAPPABLE, EmotionDimension.UNENCUMBERED, EmotionDimension.UNBOTHERED, EmotionDimension.UNASSUMING,
                EmotionDimension.TRANSPARENCY_EMOTIONAL, EmotionDimension.TRUST_DEEP, EmotionDimension.TRUTHFULNESS, EmotionDimension.UNCONDITIONAL_LOVE,
                EmotionDimension.UNDERSTANDING_DEEP, EmotionDimension.UNWAVERING, EmotionDimension.UPBEAT, EmotionDimension.VALIDATION,
                EmotionDimension.VALOR, EmotionDimension.VIBRANCY_EMOTIONAL, EmotionDimension.VICTORY, EmotionDimension.VIGILANCE,
                EmotionDimension.VIRTUE, EmotionDimension.VISION, EmotionDimension.VITALITY_LIFE, EmotionDimension.VIVACIOUSNESS,
                EmotionDimension.WARMTH, EmotionDimension.WELL_BEING, EmotionDimension.WHOLENESS, EmotionDimension.WILLINGNESS,
                EmotionDimension.WONDER_CHILDLIKE, EmotionDimension.WORTHINESS, EmotionDimension.ZEST_ENTHUSIASM, EmotionDimension.ZENITH_PEAK,
                EmotionDimension.ZING_LIVELINESS, EmotionDimension.ZONKED, EmotionDimension.ZAPPY_VIBRANT, EmotionDimension.ZANY_ECCENTRIC,
                EmotionDimension.YOUTHFULNESS_FRESH, EmotionDimension.YEARNING_LONGING, EmotionDimension.WISTFULNESS_NOSTALGIC,
                EmotionDimension.WHIMSICALITY_PLAYFUL, EmotionDimension.VIBRANCY_LIVELY, EmotionDimension.VIGOR_STRENGTH,
                EmotionDimension.VERVE_ENTHUSIASM, EmotionDimension.UNSETTLED_RESTLESS, EmotionDimension.UNRUFFLED_COMPOSED,
                EmotionDimension.UNFLAPPABLE_UNPERTURBED, EmotionDimension.UNENCUMBERED_LIGHT, EmotionDimension.UNBOTHERED_PEACEFUL,
                EmotionDimension.UNASSUMING_HUMBLE, EmotionDimension.TRANSPARENCY_OPENNESS, EmotionDimension.THOUGHTFULNESS_DEEP,
                EmotionDimension.TENACITY_DETERMINATION, EmotionDimension.SYNERGY_HARMONY, EmotionDimension.SUBLIMITY_MAJESTY,
                EmotionDimension.STILLNESS_SERENITY, EmotionDimension.SPARKLING_VIBRANCE, EmotionDimension.SOOTHING_GENTLE,
                EmotionDimension.SOLACE_COMFORT_RELIEF, EmotionDimension.SOFTNESS_DELICACY, EmotionDimension.SMOOTHNESS_ELEGANCE,
                EmotionDimension.SLUMBER_DREAM, EmotionDimension.SLACK_RELAXED, EmotionDimension.SERENITY_TRANQUILITY,
                EmotionDimension.SENSITIVITY_PERCEPTIVE, EmotionDimension.SELF_CONTROL_RESTRAINT, EmotionDimension.SELF_AWARENESS_CONSCIOUSNESS,
                EmotionDimension.SELF_ACCEPTANCE_CONTENTMENT, EmotionDimension.SELF_ASSURANCE_POISE, EmotionDimension.SELF_COMPASSION_EMPATHY,
                EmotionDimension.SELF_DISCIPLINE_FOCUS, EmotionDimension.SELF_EFFICACY_COMPETENCE, EmotionDimension.SELF_FORGIVENESS_ACCEPTANCE,
                EmotionDimension.SELF_LOVE_WELLBEING, EmotionDimension.SELF_RESPECT_INTEGRITY, EmotionDimension.SELF_SOOTHING_COMFORT,
                EmotionDimension.SELF_TRANSCENDENCE_ENLIGHTENMENT, EmotionDimension.SELF_WORTH_ESTEEM, EmotionDimension.SENSUALITY_GRATIFICATION,
                EmotionDimension.SENTIENCE_AWARENESS, EmotionDimension.SHIMMERING_LUSTER, EmotionDimension.SILENCE_CALM,
                EmotionDimension.SINCERITY_TRUTHFULNESS, EmotionDimension.SOLITUDE_TRANQUILITY, EmotionDimension.SOPHISTICATION_REFINEMENT,
                EmotionDimension.SPACIOUSNESS_FREEDOM, EmotionDimension.SPARK_INSPIRATION, EmotionDimension.SPIRIT_ESSENCE_SOUL,
                EmotionDimension.SPIRITEDNESS_ENTHUSIASM, EmotionDimension.SPLENDOR_GLORY, EmotionDimension.STABILITY_STEADINESS,
                EmotionDimension.STEADFASTNESS_RESOLVE, EmotionDimension.STIMULATION_AROUSAL, EmotionDimension.STRENGTH_POWER,
                EmotionDimension.SUBLIME_BEAUTY, EmotionDimension.SUPPORT_ENCOURAGEMENT, EmotionDimension.SUSTAINABILITY_RESILIENCE,
                EmotionDimension.SWEETNESS_GENTLENESS, EmotionDimension.TENDERNESS_AFFECTION, EmotionDimension.THANKFULNESS_APPRECIATION,
                EmotionDimension.THRILL_ADRENALINE
            ]
        }

    def modulate_cluster(self, emotion_state: EmotionState, cluster_name: str, modulation_factor: float, mode: str):
        if cluster_name not in self.modulation_rules:
            raise ValueError(f"Unknown cluster: {cluster_name}")

        for emotion_dim in self.modulation_rules[cluster_name]:
            current_value = emotion_state.get_emotion_value(emotion_dim)
            if mode == "amplify":
                new_value = np.clip(current_value + modulation_factor, 0.0, 1.0)
            elif mode == "mute":
                new_value = np.clip(current_value - modulation_factor, 0.0, 1.0)
            elif mode == "lock":
                new_value = np.clip(modulation_factor, 0.0, 1.0) # modulation_factor acts as the target value for lock
            else:
                raise ValueError(f"Unknown modulation mode: {mode}")
            emotion_state.update_emotion(emotion_dim, new_value)
        return emotion_state

    def get_cluster_average(self, emotion_state: EmotionState, cluster_name: str) -> float:
        if cluster_name not in self.modulation_rules:
            raise ValueError(f"Unknown cluster: {cluster_name}")
        
        cluster_emotions = self.modulation_rules[cluster_name]
        if not cluster_emotions:
            return 0.0
        
        total_value = sum(emotion_state.get_emotion_value(dim) for dim in cluster_emotions)
        return total_value / len(cluster_emotions)

    def mute_cluster(self, emotion_state: EmotionState, cluster_name: str):
        self.modulate_cluster(emotion_state, cluster_name, 1.0, "mute") # Mute by reducing to minimum

    def amplify_cluster(self, emotion_state: EmotionState, cluster_name: str):
        self.modulate_cluster(emotion_state, cluster_name, 1.0, "amplify") # Amplify by increasing to maximum

    def lock_cluster(self, emotion_state: EmotionState, cluster_name: str, value: float):
        self.modulate_cluster(emotion_state, cluster_name, value, "lock")

# Example Usage (for testing purposes)
if __name__ == "__main__":
    emotion_state = EmotionState()
    modulator = ClusterModulator()

    print("Initial Joy:", emotion_state.get_emotion_value(EmotionDimension.JOY))
    modulator.amplify_cluster(emotion_state, "positive_cluster")
    print("Amplified Joy:", emotion_state.get_emotion_value(EmotionDimension.JOY))

    print("Initial Anger:", emotion_state.get_emotion_value(EmotionDimension.ANGER))
    modulator.mute_cluster(emotion_state, "negative_cluster")
    print("Muted Anger:", emotion_state.get_emotion_value(EmotionDimension.ANGER))

    print("Initial Curiosity:", emotion_state.get_emotion_value(EmotionDimension.CURIOSITY))
    modulator.lock_cluster(emotion_state, "neutral_cluster", 0.5)
    print("Locked Curiosity:", emotion_state.get_emotion_value(EmotionDimension.CURIOSITY))

    print("Initial SPARKLING_VIBRANCE:", emotion_state.get_emotion_value(EmotionDimension.SPARKLING_VIBRANCE))
    modulator.amplify_cluster(emotion_state, "positive_cluster")
    print("Amplified SPARKLING_VIBRANCE:", emotion_state.get_emotion_value(EmotionDimension.SPARKLING_VIBRANCE))




