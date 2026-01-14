"""
DEVmind Unlimited Context Manager
Advanced context management system with no hard limits but intelligent overload handling

Author: Sachib
Version: 1.0.0
Date: January 10, 2025

This system implements a revolutionary approach to context management that eliminates
traditional context limits while providing sophisticated overload handling through
intelligent prioritization, compression, and archival mechanisms.
"""

import asyncio
import json
import time
import logging
import hashlib
import pickle
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict, deque
import threading
import psutil
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContextType(Enum):
    """Types of context managed by the system"""
    CONVERSATIONAL_HISTORY = "conversational_history"
    INTERNAL_THOUGHT_LOGS = "internal_thought_logs"
    LONG_TERM_MEMORY = "long_term_memory"
    EXTERNAL_KNOWLEDGE = "external_knowledge"
    EMOTIONAL_TIMELINE = "emotional_timeline"
    SENSOR_RUNTIME_STREAM = "sensor_runtime_stream"
    EXECUTION_CONTEXT = "execution_context"

class MemoryPriority(Enum):
    """Memory priority levels for context management"""
    CRITICAL = 1.0      # Never prune, highest priority
    HIGH = 0.8          # Rarely prune, high importance
    MEDIUM = 0.6        # Standard priority
    LOW = 0.4           # Can be pruned if needed
    MINIMAL = 0.2       # First to be pruned

class CompressionLevel(Enum):
    """Compression levels for memory storage"""
    NONE = 0            # No compression, fastest access
    LIGHT = 1           # Light compression, fast access
    MEDIUM = 2          # Medium compression, balanced
    HEAVY = 3           # Heavy compression, slower access
    MAXIMUM = 4         # Maximum compression, slowest access

@dataclass
class ContextEntry:
    """Individual context entry with metadata"""
    id: str
    context_type: ContextType
    content: Any
    timestamp: datetime
    priority: MemoryPriority
    emotional_weight: float
    relevance_score: float
    access_count: int
    last_accessed: datetime
    compression_level: CompressionLevel
    metadata: Dict[str, Any]
    
    def calculate_retention_score(self) -> float:
        """Calculate how important this context is for retention"""
        # Time decay factor (newer is better)
        time_factor = max(0.1, 1.0 - (datetime.now() - self.timestamp).total_seconds() / (30 * 24 * 3600))
        
        # Access frequency factor
        access_factor = min(1.0, self.access_count / 10.0)
        
        # Emotional significance factor
        emotion_factor = abs(self.emotional_weight)
        
        # Priority factor
        priority_factor = self.priority.value
        
        # Combined retention score
        retention_score = (
            time_factor * 0.3 +
            access_factor * 0.2 +
            emotion_factor * 0.3 +
            priority_factor * 0.2
        )
        
        return min(1.0, retention_score)

@dataclass
class MemoryCluster:
    """Cluster of related context entries"""
    id: str
    entries: List[ContextEntry]
    topic: str
    creation_time: datetime
    last_updated: datetime
    cluster_weight: float
    compression_ratio: float
    
    def get_cluster_size(self) -> int:
        """Get total size of cluster in bytes"""
        total_size = 0
        for entry in self.entries:
            if isinstance(entry.content, str):
                total_size += len(entry.content.encode('utf-8'))
            else:
                total_size += len(pickle.dumps(entry.content))
        return total_size
    
    def get_average_retention_score(self) -> float:
        """Get average retention score for the cluster"""
        if not self.entries:
            return 0.0
        return sum(entry.calculate_retention_score() for entry in self.entries) / len(self.entries)

class TypeFocus:
    """Working memory engine that manages active thought stacks"""
    
    def __init__(self, max_active_stacks: int = 7):
        self.max_active_stacks = max_active_stacks
        self.active_stacks: Dict[str, Dict[str, Any]] = {}
        self.stack_priorities: Dict[str, float] = {}
        self.stack_access_times: Dict[str, datetime] = {}
        self.lock = threading.Lock()
        
    def add_thought_stack(self, stack_id: str, content: Dict[str, Any], priority: float = 0.5):
        """Add a new thought stack to working memory"""
        with self.lock:
            if len(self.active_stacks) >= self.max_active_stacks:
                self._evict_lowest_priority_stack()
            
            self.active_stacks[stack_id] = content
            self.stack_priorities[stack_id] = priority
            self.stack_access_times[stack_id] = datetime.now()
            
            logger.info(f"Added thought stack: {stack_id} with priority {priority}")
    
    def get_thought_stack(self, stack_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a thought stack from working memory"""
        with self.lock:
            if stack_id in self.active_stacks:
                self.stack_access_times[stack_id] = datetime.now()
                return self.active_stacks[stack_id]
            return None
    
    def update_stack_priority(self, stack_id: str, new_priority: float):
        """Update the priority of a thought stack"""
        with self.lock:
            if stack_id in self.stack_priorities:
                self.stack_priorities[stack_id] = new_priority
                logger.info(f"Updated stack {stack_id} priority to {new_priority}")
    
    def _evict_lowest_priority_stack(self):
        """Remove the lowest priority stack to make room"""
        if not self.active_stacks:
            return
        
        # Find stack with lowest priority (considering recency)
        lowest_score = float('inf')
        lowest_stack = None
        
        for stack_id in self.active_stacks:
            priority = self.stack_priorities[stack_id]
            time_factor = (datetime.now() - self.stack_access_times[stack_id]).total_seconds() / 3600
            score = priority - (time_factor * 0.1)  # Reduce score for older stacks
            
            if score < lowest_score:
                lowest_score = score
                lowest_stack = stack_id
        
        if lowest_stack:
            del self.active_stacks[lowest_stack]
            del self.stack_priorities[lowest_stack]
            del self.stack_access_times[lowest_stack]
            logger.info(f"Evicted thought stack: {lowest_stack}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics"""
        with self.lock:
            total_size = sum(len(pickle.dumps(stack)) for stack in self.active_stacks.values())
            return {
                "active_stacks": len(self.active_stacks),
                "max_stacks": self.max_active_stacks,
                "total_size_bytes": total_size,
                "average_priority": sum(self.stack_priorities.values()) / len(self.stack_priorities) if self.stack_priorities else 0
            }

class UnlimitedContextManager:
    """
    Core unlimited context management system for DEVmind
    
    This system provides unlimited context storage with intelligent management,
    compression, and retrieval capabilities. It maintains multiple context types
    simultaneously while providing sophisticated overload handling.
    """
    
    def __init__(self, 
                 working_memory_limit: int = 1000,
                 compression_threshold: int = 10000,
                 archive_threshold: int = 100000):
        """
        Initialize the unlimited context manager
        
        Args:
            working_memory_limit: Maximum entries in working memory
            compression_threshold: Size threshold for compression
            archive_threshold: Size threshold for archival
        """
        self.working_memory_limit = working_memory_limit
        self.compression_threshold = compression_threshold
        self.archive_threshold = archive_threshold
        
        # Core storage systems
        self.working_memory: Dict[str, ContextEntry] = {}
        self.compressed_memory: Dict[str, bytes] = {}
        self.archived_memory: Dict[str, str] = {}  # File paths to archived data
        
        # Memory clusters for organization
        self.memory_clusters: Dict[str, MemoryCluster] = {}
        
        # Working memory engine
        self.type_focus = TypeFocus()
        
        # Indexing and retrieval systems
        self.context_index: Dict[ContextType, Set[str]] = defaultdict(set)
        self.emotional_index: Dict[float, Set[str]] = defaultdict(set)
        self.temporal_index: Dict[str, Set[str]] = defaultdict(set)  # Date-based indexing
        
        # Performance monitoring
        self.access_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self.compression_stats: Dict[str, Dict[str, Any]] = {}
        
        # Threading and async support
        self.lock = threading.Lock()
        self.background_tasks: List[asyncio.Task] = []
        
        # Initialize storage directories
        self.archive_dir = "/tmp/devmind_context_archive"
        os.makedirs(self.archive_dir, exist_ok=True)
        
        logger.info("UnlimitedContextManager initialized")
    
    def add_context(self, 
                   context_id: str,
                   context_type: ContextType,
                   content: Any,
                   priority: MemoryPriority = MemoryPriority.MEDIUM,
                   emotional_weight: float = 0.0,
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add new context to the system
        
        Args:
            context_id: Unique identifier for the context
            context_type: Type of context being added
            content: The actual context content
            priority: Priority level for retention
            emotional_weight: Emotional significance (-1.0 to 1.0)
            metadata: Additional metadata
            
        Returns:
            str: The context ID that was added
        """
        with self.lock:
            # Create context entry
            entry = ContextEntry(
                id=context_id,
                context_type=context_type,
                content=content,
                timestamp=datetime.now(),
                priority=priority,
                emotional_weight=emotional_weight,
                relevance_score=1.0,  # Initial relevance
                access_count=0,
                last_accessed=datetime.now(),
                compression_level=CompressionLevel.NONE,
                metadata=metadata or {}
            )
            
            # Add to working memory
            self.working_memory[context_id] = entry
            
            # Update indexes
            self.context_index[context_type].add(context_id)
            self.emotional_index[round(emotional_weight, 1)].add(context_id)
            date_key = entry.timestamp.strftime("%Y-%m-%d")
            self.temporal_index[date_key].add(context_id)
            
            # Check if we need to manage memory
            if len(self.working_memory) > self.working_memory_limit:
                self._trigger_memory_management()
            
            logger.info(f"Added context: {context_id} ({context_type.value})")
            return context_id
    
    def get_context(self, context_id: str) -> Optional[ContextEntry]:
        """
        Retrieve context by ID with intelligent loading
        
        Args:
            context_id: The context ID to retrieve
            
        Returns:
            ContextEntry or None if not found
        """
        with self.lock:
            # Check working memory first
            if context_id in self.working_memory:
                entry = self.working_memory[context_id]
                entry.access_count += 1
                entry.last_accessed = datetime.now()
                self.access_patterns[context_id].append(datetime.now())
                return entry
            
            # Check compressed memory
            if context_id in self.compressed_memory:
                entry = self._decompress_context(context_id)
                if entry:
                    # Move back to working memory if frequently accessed
                    if entry.access_count > 5:
                        self.working_memory[context_id] = entry
                        del self.compressed_memory[context_id]
                    return entry
            
            # Check archived memory
            if context_id in self.archived_memory:
                entry = self._load_archived_context(context_id)
                if entry:
                    # Move to compressed memory for faster future access
                    self._compress_context(entry)
                    return entry
            
            logger.warning(f"Context not found: {context_id}")
            return None
    
    def search_context(self, 
                      query: str,
                      context_types: Optional[List[ContextType]] = None,
                      emotional_range: Optional[Tuple[float, float]] = None,
                      time_range: Optional[Tuple[datetime, datetime]] = None,
                      limit: int = 10) -> List[ContextEntry]:
        """
        Search for context entries based on various criteria
        
        Args:
            query: Text query to search for
            context_types: Filter by context types
            emotional_range: Filter by emotional weight range
            time_range: Filter by time range
            limit: Maximum number of results
            
        Returns:
            List of matching context entries
        """
        with self.lock:
            candidates = set()
            
            # Filter by context type
            if context_types:
                for context_type in context_types:
                    candidates.update(self.context_index[context_type])
            else:
                for context_set in self.context_index.values():
                    candidates.update(context_set)
            
            # Filter by emotional range
            if emotional_range:
                emotional_candidates = set()
                min_emotion, max_emotion = emotional_range
                for emotion_level, context_set in self.emotional_index.items():
                    if min_emotion <= emotion_level <= max_emotion:
                        emotional_candidates.update(context_set)
                candidates = candidates.intersection(emotional_candidates)
            
            # Filter by time range
            if time_range:
                temporal_candidates = set()
                start_date, end_date = time_range
                current_date = start_date
                while current_date <= end_date:
                    date_key = current_date.strftime("%Y-%m-%d")
                    temporal_candidates.update(self.temporal_index[date_key])
                    current_date += timedelta(days=1)
                candidates = candidates.intersection(temporal_candidates)
            
            # Score and rank results
            results = []
            for context_id in candidates:
                entry = self.get_context(context_id)
                if entry and self._matches_query(entry, query):
                    score = self._calculate_relevance_score(entry, query)
                    results.append((score, entry))
            
            # Sort by relevance and return top results
            results.sort(key=lambda x: x[0], reverse=True)
            return [entry for score, entry in results[:limit]]
    
    def create_memory_cluster(self, 
                            cluster_id: str,
                            topic: str,
                            context_ids: List[str]) -> bool:
        """
        Create a memory cluster from related context entries
        
        Args:
            cluster_id: Unique identifier for the cluster
            topic: Topic or theme of the cluster
            context_ids: List of context IDs to include
            
        Returns:
            bool: True if cluster was created successfully
        """
        with self.lock:
            entries = []
            for context_id in context_ids:
                entry = self.get_context(context_id)
                if entry:
                    entries.append(entry)
            
            if not entries:
                logger.warning(f"No valid entries found for cluster: {cluster_id}")
                return False
            
            cluster = MemoryCluster(
                id=cluster_id,
                entries=entries,
                topic=topic,
                creation_time=datetime.now(),
                last_updated=datetime.now(),
                cluster_weight=sum(entry.calculate_retention_score() for entry in entries) / len(entries),
                compression_ratio=1.0
            )
            
            self.memory_clusters[cluster_id] = cluster
            logger.info(f"Created memory cluster: {cluster_id} with {len(entries)} entries")
            return True
    
    def _trigger_memory_management(self):
        """Trigger intelligent memory management when limits are reached"""
        logger.info("Triggering memory management due to capacity limits")
        
        # Identify candidates for compression
        compression_candidates = []
        for context_id, entry in self.working_memory.items():
            if entry.access_count < 3 and (datetime.now() - entry.last_accessed).total_seconds() > 3600:
                compression_candidates.append((entry.calculate_retention_score(), context_id))
        
        # Compress least important entries
        compression_candidates.sort(key=lambda x: x[0])
        for score, context_id in compression_candidates[:len(compression_candidates)//2]:
            entry = self.working_memory[context_id]
            self._compress_context(entry)
            del self.working_memory[context_id]
        
        logger.info(f"Compressed {len(compression_candidates)//2} context entries")
    
    def _compress_context(self, entry: ContextEntry) -> bool:
        """Compress a context entry for storage"""
        try:
            # Serialize and compress the entry
            serialized = pickle.dumps(entry)
            compressed = gzip.compress(serialized)
            
            # Store in compressed memory
            self.compressed_memory[entry.id] = compressed
            
            # Update compression stats
            original_size = len(serialized)
            compressed_size = len(compressed)
            compression_ratio = compressed_size / original_size
            
            self.compression_stats[entry.id] = {
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "compression_time": datetime.now()
            }
            
            logger.info(f"Compressed context {entry.id}: {compression_ratio:.2f} ratio")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compress context {entry.id}: {e}")
            return False
    
    def _decompress_context(self, context_id: str) -> Optional[ContextEntry]:
        """Decompress a context entry from storage"""
        try:
            if context_id not in self.compressed_memory:
                return None
            
            # Decompress and deserialize
            compressed_data = self.compressed_memory[context_id]
            decompressed = gzip.decompress(compressed_data)
            entry = pickle.loads(decompressed)
            
            # Update access information
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            
            logger.info(f"Decompressed context: {context_id}")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to decompress context {context_id}: {e}")
            return None
    
    def _load_archived_context(self, context_id: str) -> Optional[ContextEntry]:
        """Load a context entry from archive"""
        try:
            if context_id not in self.archived_memory:
                return None
            
            file_path = self.archived_memory[context_id]
            if not os.path.exists(file_path):
                logger.warning(f"Archived file not found: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                compressed_data = f.read()
            
            decompressed = gzip.decompress(compressed_data)
            entry = pickle.loads(decompressed)
            
            # Update access information
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            
            logger.info(f"Loaded archived context: {context_id}")
            return entry
            
        except Exception as e:
            logger.error(f"Failed to load archived context {context_id}: {e}")
            return None
    
    def _matches_query(self, entry: ContextEntry, query: str) -> bool:
        """Check if a context entry matches a search query"""
        query_lower = query.lower()
        
        # Search in content
        if isinstance(entry.content, str):
            if query_lower in entry.content.lower():
                return True
        
        # Search in metadata
        for key, value in entry.metadata.items():
            if isinstance(value, str) and query_lower in value.lower():
                return True
        
        return False
    
    def _calculate_relevance_score(self, entry: ContextEntry, query: str) -> float:
        """Calculate relevance score for search results"""
        score = 0.0
        query_lower = query.lower()
        
        # Content relevance
        if isinstance(entry.content, str):
            content_lower = entry.content.lower()
            if query_lower in content_lower:
                # Count occurrences and position
                occurrences = content_lower.count(query_lower)
                score += occurrences * 0.5
                
                # Boost if query appears early
                first_occurrence = content_lower.find(query_lower)
                if first_occurrence < 100:
                    score += 0.3
        
        # Recency boost
        days_old = (datetime.now() - entry.timestamp).days
        recency_score = max(0, 1.0 - days_old / 30.0)
        score += recency_score * 0.2
        
        # Priority boost
        score += entry.priority.value * 0.2
        
        # Emotional weight boost
        score += abs(entry.emotional_weight) * 0.1
        
        # Access frequency boost
        score += min(1.0, entry.access_count / 10.0) * 0.1
        
        return score
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        with self.lock:
            working_memory_size = sum(len(pickle.dumps(entry)) for entry in self.working_memory.values())
            compressed_memory_size = sum(len(data) for data in self.compressed_memory.values())
            
            return {
                "working_memory": {
                    "entries": len(self.working_memory),
                    "size_bytes": working_memory_size,
                    "limit": self.working_memory_limit
                },
                "compressed_memory": {
                    "entries": len(self.compressed_memory),
                    "size_bytes": compressed_memory_size
                },
                "archived_memory": {
                    "entries": len(self.archived_memory)
                },
                "memory_clusters": {
                    "count": len(self.memory_clusters),
                    "total_entries": sum(len(cluster.entries) for cluster in self.memory_clusters.values())
                },
                "type_focus": self.type_focus.get_memory_usage(),
                "context_types": {ct.value: len(ids) for ct, ids in self.context_index.items()},
                "system_memory": {
                    "process_memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
                    "system_memory_percent": psutil.virtual_memory().percent
                }
            }
    
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        logger.info("Starting background maintenance tasks")
        
        # Memory optimization task
        async def memory_optimization_task():
            while True:
                await asyncio.sleep(300)  # Run every 5 minutes
                self._optimize_memory_usage()
        
        # Index maintenance task
        async def index_maintenance_task():
            while True:
                await asyncio.sleep(600)  # Run every 10 minutes
                self._maintain_indexes()
        
        # Archive old data task
        async def archival_task():
            while True:
                await asyncio.sleep(3600)  # Run every hour
                self._archive_old_data()
        
        # Start tasks
        self.background_tasks = [
            asyncio.create_task(memory_optimization_task()),
            asyncio.create_task(index_maintenance_task()),
            asyncio.create_task(archival_task())
        ]
    
    def _optimize_memory_usage(self):
        """Optimize memory usage by compressing and archiving data"""
        with self.lock:
            logger.info("Running memory optimization")
            
            # Find entries that haven't been accessed recently
            cutoff_time = datetime.now() - timedelta(hours=6)
            candidates_for_compression = []
            
            for context_id, entry in self.working_memory.items():
                if entry.last_accessed < cutoff_time and entry.priority != MemoryPriority.CRITICAL:
                    candidates_for_compression.append(context_id)
            
            # Compress candidates
            for context_id in candidates_for_compression:
                entry = self.working_memory[context_id]
                if self._compress_context(entry):
                    del self.working_memory[context_id]
            
            logger.info(f"Optimized memory: compressed {len(candidates_for_compression)} entries")
    
    def _maintain_indexes(self):
        """Maintain and optimize indexes"""
        with self.lock:
            logger.info("Maintaining indexes")
            
            # Clean up empty index entries
            for context_type in list(self.context_index.keys()):
                self.context_index[context_type] = {
                    cid for cid in self.context_index[context_type]
                    if cid in self.working_memory or cid in self.compressed_memory or cid in self.archived_memory
                }
            
            # Clean up emotional index
            for emotion_level in list(self.emotional_index.keys()):
                self.emotional_index[emotion_level] = {
                    cid for cid in self.emotional_index[emotion_level]
                    if cid in self.working_memory or cid in self.compressed_memory or cid in self.archived_memory
                }
    
    def _archive_old_data(self):
        """Archive very old data to disk"""
        with self.lock:
            logger.info("Archiving old data")
            
            # Find old compressed entries for archival
            cutoff_time = datetime.now() - timedelta(days=7)
            candidates_for_archival = []
            
            for context_id, compressed_data in self.compressed_memory.items():
                # Check if this entry is old enough for archival
                if context_id in self.compression_stats:
                    compression_time = self.compression_stats[context_id]["compression_time"]
                    if compression_time < cutoff_time:
                        candidates_for_archival.append(context_id)
            
            # Archive candidates
            for context_id in candidates_for_archival:
                file_path = os.path.join(self.archive_dir, f"{context_id}.gz")
                try:
                    with open(file_path, 'wb') as f:
                        f.write(self.compressed_memory[context_id])
                    
                    self.archived_memory[context_id] = file_path
                    del self.compressed_memory[context_id]
                    
                except Exception as e:
                    logger.error(f"Failed to archive {context_id}: {e}")
            
            logger.info(f"Archived {len(candidates_for_archival)} entries")
    
    async def shutdown(self):
        """Gracefully shutdown the context manager"""
        logger.info("Shutting down UnlimitedContextManager")
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("UnlimitedContextManager shutdown complete")

# Example usage and testing
if __name__ == "__main__":
    async def test_unlimited_context_manager():
        """Test the unlimited context manager"""
        manager = UnlimitedContextManager()
        
        # Start background tasks
        await manager.start_background_tasks()
        
        # Add various types of context
        manager.add_context(
            "conv_001",
            ContextType.CONVERSATIONAL_HISTORY,
            "User asked about implementing neural networks",
            MemoryPriority.HIGH,
            0.7,
            {"user_id": "user123", "topic": "AI"}
        )
        
        manager.add_context(
            "thought_001",
            ContextType.INTERNAL_THOUGHT_LOGS,
            "Reflecting on the complexity of consciousness implementation",
            MemoryPriority.MEDIUM,
            0.5,
            {"reflection_type": "philosophical"}
        )
        
        manager.add_context(
            "emotion_001",
            ContextType.EMOTIONAL_TIMELINE,
            "Feeling excited about breakthrough in emotion system",
            MemoryPriority.HIGH,
            0.9,
            {"emotion": "excitement", "intensity": "high"}
        )
        
        # Test retrieval
        context = manager.get_context("conv_001")
        print(f"Retrieved context: {context.content if context else 'Not found'}")
        
        # Test search
        results = manager.search_context("neural", limit=5)
        print(f"Search results: {len(results)} found")
        
        # Test memory cluster creation
        manager.create_memory_cluster(
            "ai_discussion",
            "AI and Neural Networks",
            ["conv_001", "thought_001"]
        )
        
        # Get system stats
        stats = manager.get_system_stats()
        print(f"System stats: {json.dumps(stats, indent=2, default=str)}")
        
        # Shutdown
        await manager.shutdown()
    
    # Run the test
    asyncio.run(test_unlimited_context_manager())

