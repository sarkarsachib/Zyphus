"""
DEVmind Awareness Integration

This module integrates various core components of DEVmind to create a unified
and self-aware system. It acts as the central hub for orchestrating interactions
between the brain loop, heartbeat engine, task manager, interrupt watchers,
and persistent memory.

Author: Sachib
Version: 1.0.0
"""

import asyncio
import logging
from typing import Dict, Any

# Import core components
from .core_brain_loop import CoreBrainLoop
from .heartbeat_engine import HeartbeatEngine
from .passive_task_manager import PassiveTaskManager
from .interrupt_watchers import InterruptManager
from .persistent_memory_cores import (
    PersistentMemoryManager, 
    start_memory_cores, 
    stop_memory_cores, 
    get_memory_status,
    store_memory,
    retrieve_memory,
    delete_memory,
    search_memories,
    save_mind_state,
    load_mind_state,
    get_current_mind_state
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AwarenessIntegration:
    """
    Integrates and orchestrates various DEVmind core components.
    """

    def __init__(self):
        self.brain_loop = CoreBrainLoop()
        self.heartbeat_engine = HeartbeatEngine()
        self.passive_task_manager = PassiveTaskManager()
        self.interrupt_manager = InterruptManager()
        self.memory_manager = PersistentMemoryManager() # Use the global instance
        logger.info("Awareness Integration initialized")

    async def start_all_components(self):
        """Starts all integrated DEVmind components."""
        logger.info("Starting all DEVmind components...")
        await self.brain_loop.start()
        await self.heartbeat_engine.start()
        await self.passive_task_manager.start()
        await self.interrupt_manager.start()
        await start_memory_cores() # Use the global convenience function
        logger.info("All DEVmind components started.")

    async def stop_all_components(self):
        """Stops all integrated DEVmind components."""
        logger.info("Stopping all DEVmind components...")
        await self.brain_loop.stop()
        await self.heartbeat_engine.stop()
        await self.passive_task_manager.stop()
        await self.interrupt_manager.stop()
        await stop_memory_cores() # Use the global convenience function
        logger.info("All DEVmind components stopped.")

    async def get_system_status(self) -> Dict[str, Any]:
        """Retrieves the status of all integrated components."""
        return {
            "brain_loop_status": self.brain_loop.get_status(),
            "heartbeat_status": self.heartbeat_engine.get_status(),
            "passive_task_manager_status": self.passive_task_manager.get_status(),
            "interrupt_manager_status": self.interrupt_manager.get_status(),
            "memory_manager_status": get_memory_status() # Use the global convenience function
        }

    # Expose memory manager functions directly for convenience
    async def store_memory(self, key: str, data: Any, memory_type: Any = None, priority: Any = None, **kwargs):
        return await store_memory(key, data, memory_type, priority, **kwargs)

    async def retrieve_memory(self, key: str, memory_type: Any = None):
        return await retrieve_memory(key, memory_type)

    async def delete_memory(self, key: str, memory_type: Any = None):
        return await delete_memory(key, memory_type)

    async def search_memories(self, query: Dict[str, Any], memory_types: Any = None):
        return await search_memories(query, memory_types)

    async def save_mind_state(self, state_data: Dict[str, Any], checkpoint_name: str = None):
        return await save_mind_state(state_data, checkpoint_name)

    async def load_mind_state(self, checkpoint_name: str = None):
        return await load_mind_state(checkpoint_name)

    def get_current_mind_state(self):
        return get_current_mind_state()


