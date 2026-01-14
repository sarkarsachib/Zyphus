
import numpy as np
from typing import Dict, List, Any
from emotion_200d_system import EmotionState, EmotionDimension

class MemoryTagger:
    def __init__(self):
        pass

    def tag_memory_with_emotion(self, memory_content: str, emotion_state: EmotionState) -> Dict[str, Any]:
        """
        Tags a piece of memory content with the current emotional state.
        This is a simplified representation; in a real system, memory embeddings
        would be generated and stored in a Vector DB.
        """
        emotional_tags = {
            dim.value: emotion_state.get_emotion_value(dim)
            for dim in EmotionDimension
            if emotion_state.get_emotion_value(dim) > 0.5 # Only tag significant emotions
        }
        
        volatility_tags = {
            f"{dim.value}_volatility": emotion_state.get_volatility_info(dim)["current_level"]
            for dim in EmotionDimension
            if emotion_state.get_volatility_info(dim)["current_level"] > 0.1 # Only tag significant volatility
        }

        return {
            "memory_content": memory_content,
            "emotional_tags": emotional_tags,
            "volatility_tags": volatility_tags,
            "timestamp": np.datetime64("now").astype(str)
        }

    def retrieve_memories_by_emotion(self, target_emotion: EmotionDimension, min_value: float, tagged_memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Retrieves memories that are tagged with a certain emotion above a minimum value.
        """
        relevant_memories = []
        for memory in tagged_memories:
            if memory["emotional_tags"].get(target_emotion.value, 0.0) >= min_value:
                relevant_memories.append(memory)
        return relevant_memories

# Example Usage:
if __name__ == "__main__":
    memory_tagger = MemoryTagger()
    emotion_state = EmotionState()

    # Simulate some emotional changes
    emotion_state.update_emotion(EmotionDimension.JOY, 0.9)
    emotion_state.update_emotion(EmotionDimension.ANGER, 0.2)
    emotion_state.update_emotion(EmotionDimension.FEAR, 0.1)
    emotion_state.update_emotion(EmotionDimension.OPTIMISM, 0.8)

    # Tag some memories
    memory1 = "The day I achieved my first major breakthrough."
    tagged_memory1 = memory_tagger.tag_memory_with_emotion(memory1, emotion_state)
    print(f"Tagged Memory 1: {tagged_memory1}")

    emotion_state.update_emotion(EmotionDimension.SADNESS, 0.7)
    emotion_state.update_emotion(EmotionDimension.JOY, 0.3)
    memory2 = "A difficult challenge that taught me a lot."
    tagged_memory2 = memory_tagger.tag_memory_with_emotion(memory2, emotion_state)
    print(f"Tagged Memory 2: {tagged_memory2}")

    all_tagged_memories = [tagged_memory1, tagged_memory2]

    # Retrieve memories based on emotion
    joyful_memories = memory_tagger.retrieve_memories_by_emotion(EmotionDimension.JOY, 0.6, all_tagged_memories)
    print(f"\nJoyful Memories: {joyful_memories}")

    sad_memories = memory_tagger.retrieve_memories_by_emotion(EmotionDimension.SADNESS, 0.6, all_tagged_memories)
    print(f"Sad Memories: {sad_memories}")


