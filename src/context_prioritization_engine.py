"""
Context Prioritization Engine
Advanced context prioritization, pruning, and offloading mechanisms for DEVmind

Author: Sachib
Version: 1.0.0
Date: January 10, 2025

This system implements sophisticated algorithms for context prioritization,
intelligent pruning, and strategic offloading to maintain optimal performance
while preserving the most valuable contextual information.
"""

import asyncio
import json
import time
import logging
import threading
import hashlib
import pickle
import gzip
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict, deque, Counter
import heapq
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriorityLevel(Enum):
    """Context priority levels"""
    CRITICAL = 1.0      # Never prune, highest priority
    ESSENTIAL = 0.9     # Rarely prune, very important
    HIGH = 0.8          # High importance, prune only under pressure
    MEDIUM = 0.6        # Standard priority, can be pruned
    LOW = 0.4           # Low importance, prune when needed
    MINIMAL = 0.2       # First to be pruned
    DISPOSABLE = 0.1    # Can be discarded immediately

class ContextCategory(Enum):
    """Categories for context classification"""
    CORE_MEMORY = "core_memory"           # Fundamental memories and experiences
    ACTIVE_TASK = "active_task"           # Currently active tasks and goals
    EMOTIONAL_SIGNIFICANT = "emotional"   # Emotionally significant content
    LEARNING_PATTERN = "learning"         # Learning patterns and insights
    RELATIONSHIP = "relationship"         # Relationship and social context
    SKILL_KNOWLEDGE = "skill"            # Skills and procedural knowledge
    REFERENCE_DATA = "reference"         # Reference information and facts
    TEMPORARY_WORKING = "temporary"      # Temporary working memory
    ARCHIVED_HISTORY = "archived"       # Historical archived content

class OffloadStrategy(Enum):
    """Strategies for offloading context"""
    COMPRESS_IN_PLACE = "compress_in_place"     # Compress without moving
    MOVE_TO_COLD_STORAGE = "move_to_cold"       # Move to cold storage
    SUMMARIZE_AND_COMPRESS = "summarize"        # Summarize then compress
    CLUSTER_AND_ARCHIVE = "cluster_archive"     # Cluster related items and archive
    DISTRIBUTED_STORAGE = "distributed"        # Distribute across multiple stores
    HIERARCHICAL_STORAGE = "hierarchical"      # Use hierarchical storage management

@dataclass
class ContextPriorityScore:
    """Comprehensive priority scoring for context"""
    base_priority: float           # Base priority level
    recency_score: float          # How recent the context is
    frequency_score: float        # How frequently accessed
    emotional_score: float        # Emotional significance
    relevance_score: float        # Relevance to current tasks
    relationship_score: float     # Relationship to other contexts
    learning_score: float         # Learning and growth value
    uniqueness_score: float       # How unique/irreplaceable the context is
    
    def calculate_total_score(self) -> float:
        """Calculate total priority score with weighted factors"""
        weights = {
            'base': 0.2,
            'recency': 0.15,
            'frequency': 0.15,
            'emotional': 0.2,
            'relevance': 0.15,
            'relationship': 0.05,
            'learning': 0.05,
            'uniqueness': 0.05
        }
        
        total_score = (
            self.base_priority * weights['base'] +
            self.recency_score * weights['recency'] +
            self.frequency_score * weights['frequency'] +
            self.emotional_score * weights['emotional'] +
            self.relevance_score * weights['relevance'] +
            self.relationship_score * weights['relationship'] +
            self.learning_score * weights['learning'] +
            self.uniqueness_score * weights['uniqueness']
        )
        
        return min(1.0, max(0.0, total_score))

@dataclass
class ContextRelationship:
    """Relationship between contexts"""
    source_id: str
    target_id: str
    relationship_type: str
    strength: float
    bidirectional: bool
    metadata: Dict[str, Any]

@dataclass
class PruningCandidate:
    """Candidate for pruning with scoring"""
    context_id: str
    priority_score: float
    size_bytes: int
    last_accessed: datetime
    access_count: int
    pruning_benefit: float  # Benefit of pruning this item
    
    def __lt__(self, other):
        """For heap operations - lower priority score = higher pruning priority"""
        return self.priority_score < other.priority_score

@dataclass
class OffloadCandidate:
    """Candidate for offloading with strategy"""
    context_id: str
    current_size: int
    estimated_compressed_size: int
    offload_strategy: OffloadStrategy
    offload_benefit: float
    access_pattern: Dict[str, Any]

class ContextGraph:
    """Graph structure for context relationships"""
    
    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: Dict[str, List[ContextRelationship]] = defaultdict(list)
        self.reverse_edges: Dict[str, List[ContextRelationship]] = defaultdict(list)
        self.node_metadata: Dict[str, Dict[str, Any]] = {}
    
    def add_node(self, node_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a node to the graph"""
        self.nodes.add(node_id)
        if metadata:
            self.node_metadata[node_id] = metadata
    
    def add_relationship(self, relationship: ContextRelationship):
        """Add a relationship between contexts"""
        self.edges[relationship.source_id].append(relationship)
        self.reverse_edges[relationship.target_id].append(relationship)
        
        if relationship.bidirectional:
            reverse_rel = ContextRelationship(
                source_id=relationship.target_id,
                target_id=relationship.source_id,
                relationship_type=relationship.relationship_type,
                strength=relationship.strength,
                bidirectional=False,  # Avoid infinite recursion
                metadata=relationship.metadata
            )
            self.edges[relationship.target_id].append(reverse_rel)
            self.reverse_edges[relationship.source_id].append(reverse_rel)
    
    def get_connected_contexts(self, context_id: str, max_depth: int = 2) -> Set[str]:
        """Get all contexts connected to the given context within max_depth"""
        visited = set()
        queue = deque([(context_id, 0)])
        
        while queue:
            current_id, depth = queue.popleft()
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            
            # Add connected contexts
            for relationship in self.edges[current_id]:
                if relationship.target_id not in visited:
                    queue.append((relationship.target_id, depth + 1))
        
        return visited
    
    def calculate_centrality(self, context_id: str) -> float:
        """Calculate centrality score for a context"""
        if context_id not in self.nodes:
            return 0.0
        
        # Simple degree centrality
        in_degree = len(self.reverse_edges[context_id])
        out_degree = len(self.edges[context_id])
        total_degree = in_degree + out_degree
        
        # Normalize by total possible connections
        max_connections = len(self.nodes) - 1
        if max_connections == 0:
            return 0.0
        
        return total_degree / max_connections
    
    def find_clusters(self, min_cluster_size: int = 3) -> List[Set[str]]:
        """Find clusters of related contexts"""
        visited = set()
        clusters = []
        
        for node in self.nodes:
            if node not in visited:
                cluster = self._dfs_cluster(node, visited)
                if len(cluster) >= min_cluster_size:
                    clusters.append(cluster)
        
        return clusters
    
    def _dfs_cluster(self, start_node: str, visited: Set[str]) -> Set[str]:
        """DFS to find connected cluster"""
        cluster = set()
        stack = [start_node]
        
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            
            visited.add(node)
            cluster.add(node)
            
            # Add strongly connected neighbors
            for relationship in self.edges[node]:
                if relationship.strength > 0.5 and relationship.target_id not in visited:
                    stack.append(relationship.target_id)
        
        return cluster

class ContextPrioritizationEngine:
    """
    Advanced context prioritization engine for DEVmind
    
    This system provides sophisticated algorithms for context prioritization,
    intelligent pruning, and strategic offloading to maintain optimal performance
    while preserving the most valuable contextual information.
    """
    
    def __init__(self, 
                 context_manager=None,
                 emotion_system=None,
                 max_working_memory: int = 1000,
                 target_memory_usage: float = 0.8):
        """
        Initialize the context prioritization engine
        
        Args:
            context_manager: Reference to the context management system
            emotion_system: Reference to the emotion system
            max_working_memory: Maximum number of items in working memory
            target_memory_usage: Target memory usage ratio (0.0-1.0)
        """
        self.context_manager = context_manager
        self.emotion_system = emotion_system
        self.max_working_memory = max_working_memory
        self.target_memory_usage = target_memory_usage
        
        # Core components
        self.context_graph = ContextGraph()
        self.priority_scores: Dict[str, ContextPriorityScore] = {}
        self.access_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self.context_categories: Dict[str, ContextCategory] = {}
        
        # Pruning and offloading
        self.pruning_history: List[Dict[str, Any]] = []
        self.offloading_history: List[Dict[str, Any]] = []
        self.pruning_candidates_cache: List[PruningCandidate] = []
        self.offload_candidates_cache: List[OffloadCandidate] = []
        
        # Performance tracking
        self.prioritization_stats: Dict[str, Any] = {
            "total_prioritizations": 0,
            "total_prunings": 0,
            "total_offloads": 0,
            "memory_saved_bytes": 0,
            "average_priority_score": 0.0
        }
        
        # Configuration
        self.pruning_thresholds = {
            PriorityLevel.CRITICAL: 0.0,      # Never prune
            PriorityLevel.ESSENTIAL: 0.05,    # Prune only 5% when critical
            PriorityLevel.HIGH: 0.15,         # Prune 15% when needed
            PriorityLevel.MEDIUM: 0.4,        # Prune 40% when needed
            PriorityLevel.LOW: 0.7,           # Prune 70% when needed
            PriorityLevel.MINIMAL: 0.9,       # Prune 90% when needed
            PriorityLevel.DISPOSABLE: 1.0     # Prune 100% immediately
        }
        
        # Threading
        self.lock = threading.Lock()
        self.background_tasks: List[asyncio.Task] = []
        self.active = False
        
        logger.info("ContextPrioritizationEngine initialized")
    
    def start(self):
        """Start the prioritization engine"""
        if self.active:
            return
        
        self.active = True
        logger.info("ContextPrioritizationEngine started")
    
    def stop(self):
        """Stop the prioritization engine"""
        if not self.active:
            return
        
        self.active = False
        logger.info("ContextPrioritizationEngine stopped")
    
    def register_context_access(self, context_id: str):
        """Register an access to a context for pattern tracking"""
        with self.lock:
            self.access_patterns[context_id].append(datetime.now())
            
            # Keep only recent access history (last 100 accesses)
            if len(self.access_patterns[context_id]) > 100:
                self.access_patterns[context_id] = self.access_patterns[context_id][-100:]
    
    def add_context_relationship(self, 
                               source_id: str, 
                               target_id: str, 
                               relationship_type: str,
                               strength: float = 0.5,
                               bidirectional: bool = True,
                               metadata: Optional[Dict[str, Any]] = None):
        """Add a relationship between contexts"""
        with self.lock:
            relationship = ContextRelationship(
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                strength=strength,
                bidirectional=bidirectional,
                metadata=metadata or {}
            )
            
            self.context_graph.add_relationship(relationship)
            logger.debug(f"Added relationship: {source_id} -> {target_id} ({relationship_type})")
    
    def categorize_context(self, context_id: str, category: ContextCategory):
        """Categorize a context for better prioritization"""
        with self.lock:
            self.context_categories[context_id] = category
            logger.debug(f"Categorized context {context_id} as {category.value}")
    
    def calculate_priority_score(self, context_id: str, context_entry=None) -> ContextPriorityScore:
        """Calculate comprehensive priority score for a context"""
        if not context_entry and self.context_manager:
            context_entry = self.context_manager.get_context(context_id)
        
        if not context_entry:
            # Default low priority for unknown contexts
            return ContextPriorityScore(
                base_priority=0.1,
                recency_score=0.0,
                frequency_score=0.0,
                emotional_score=0.0,
                relevance_score=0.0,
                relationship_score=0.0,
                learning_score=0.0,
                uniqueness_score=0.0
            )
        
        # Base priority from context entry
        base_priority = context_entry.priority.value if hasattr(context_entry, 'priority') else 0.5
        
        # Recency score (newer is better)
        if hasattr(context_entry, 'timestamp'):
            time_diff = (datetime.now() - context_entry.timestamp).total_seconds()
            recency_score = max(0.0, 1.0 - time_diff / (30 * 24 * 3600))  # 30 days decay
        else:
            recency_score = 0.5
        
        # Frequency score (more accessed is better)
        access_history = self.access_patterns.get(context_id, [])
        if access_history:
            # Recent access frequency (last 7 days)
            recent_cutoff = datetime.now() - timedelta(days=7)
            recent_accesses = [a for a in access_history if a > recent_cutoff]
            frequency_score = min(1.0, len(recent_accesses) / 10.0)  # Normalize to 10 accesses
        else:
            frequency_score = 0.0
        
        # Emotional score
        emotional_score = abs(context_entry.emotional_weight) if hasattr(context_entry, 'emotional_weight') else 0.0
        
        # Relevance score (based on current tasks and context)
        relevance_score = self._calculate_relevance_score(context_id, context_entry)
        
        # Relationship score (based on connections to other important contexts)
        relationship_score = self._calculate_relationship_score(context_id)
        
        # Learning score (based on learning value and growth potential)
        learning_score = self._calculate_learning_score(context_id, context_entry)
        
        # Uniqueness score (how irreplaceable this context is)
        uniqueness_score = self._calculate_uniqueness_score(context_id, context_entry)
        
        priority_score = ContextPriorityScore(
            base_priority=base_priority,
            recency_score=recency_score,
            frequency_score=frequency_score,
            emotional_score=emotional_score,
            relevance_score=relevance_score,
            relationship_score=relationship_score,
            learning_score=learning_score,
            uniqueness_score=uniqueness_score
        )
        
        # Cache the score
        self.priority_scores[context_id] = priority_score
        
        return priority_score
    
    def _calculate_relevance_score(self, context_id: str, context_entry) -> float:
        """Calculate relevance score based on current tasks and context"""
        # This would integrate with task management and current focus
        # For now, use category-based relevance
        category = self.context_categories.get(context_id, ContextCategory.TEMPORARY_WORKING)
        
        relevance_weights = {
            ContextCategory.CORE_MEMORY: 0.9,
            ContextCategory.ACTIVE_TASK: 1.0,
            ContextCategory.EMOTIONAL_SIGNIFICANT: 0.8,
            ContextCategory.LEARNING_PATTERN: 0.7,
            ContextCategory.RELATIONSHIP: 0.6,
            ContextCategory.SKILL_KNOWLEDGE: 0.7,
            ContextCategory.REFERENCE_DATA: 0.4,
            ContextCategory.TEMPORARY_WORKING: 0.3,
            ContextCategory.ARCHIVED_HISTORY: 0.2
        }
        
        return relevance_weights.get(category, 0.5)
    
    def _calculate_relationship_score(self, context_id: str) -> float:
        """Calculate relationship score based on connections"""
        centrality = self.context_graph.calculate_centrality(context_id)
        
        # Boost score for contexts connected to high-priority contexts
        connected_contexts = self.context_graph.get_connected_contexts(context_id, max_depth=1)
        high_priority_connections = 0
        
        for connected_id in connected_contexts:
            if connected_id in self.priority_scores:
                connected_score = self.priority_scores[connected_id].calculate_total_score()
                if connected_score > 0.7:
                    high_priority_connections += 1
        
        connection_boost = min(0.5, high_priority_connections * 0.1)
        
        return min(1.0, centrality + connection_boost)
    
    def _calculate_learning_score(self, context_id: str, context_entry) -> float:
        """Calculate learning value score"""
        # Check if this context represents learning or growth
        if hasattr(context_entry, 'metadata'):
            metadata = context_entry.metadata
            learning_indicators = ['learning', 'insight', 'discovery', 'breakthrough', 'understanding']
            
            for indicator in learning_indicators:
                if any(indicator in str(value).lower() for value in metadata.values()):
                    return 0.8
        
        # Check context type for learning value
        if hasattr(context_entry, 'context_type'):
            learning_types = ['INTERNAL_THOUGHT_LOGS', 'LONG_TERM_MEMORY']
            if context_entry.context_type.value in learning_types:
                return 0.6
        
        return 0.3
    
    def _calculate_uniqueness_score(self, context_id: str, context_entry) -> float:
        """Calculate how unique and irreplaceable this context is"""
        # Check for unique identifiers or rare content
        uniqueness_factors = []
        
        # Content uniqueness (simplified)
        if hasattr(context_entry, 'content') and isinstance(context_entry.content, str):
            content_length = len(context_entry.content)
            if content_length > 1000:  # Long content is often more unique
                uniqueness_factors.append(0.3)
            
            # Check for unique patterns (URLs, IDs, specific terms)
            unique_patterns = ['http', 'id:', 'uuid', 'timestamp', 'error', 'exception']
            for pattern in unique_patterns:
                if pattern in context_entry.content.lower():
                    uniqueness_factors.append(0.2)
                    break
        
        # Metadata uniqueness
        if hasattr(context_entry, 'metadata'):
            if len(context_entry.metadata) > 3:  # Rich metadata suggests uniqueness
                uniqueness_factors.append(0.2)
        
        # Relationship uniqueness
        if context_id in self.context_graph.nodes:
            connections = len(self.context_graph.edges[context_id])
            if connections > 5:  # Highly connected contexts are often unique
                uniqueness_factors.append(0.3)
        
        return min(1.0, sum(uniqueness_factors))
    
    def identify_pruning_candidates(self, target_count: int) -> List[PruningCandidate]:
        """Identify candidates for pruning based on priority scores"""
        with self.lock:
            if not self.context_manager:
                return []
            
            candidates = []
            
            # Get all contexts from working memory
            working_memory = getattr(self.context_manager, 'working_memory', {})
            
            for context_id, context_entry in working_memory.items():
                # Calculate priority score
                priority_score = self.calculate_priority_score(context_id, context_entry)
                total_score = priority_score.calculate_total_score()
                
                # Calculate size
                size_bytes = len(pickle.dumps(context_entry)) if context_entry else 0
                
                # Calculate pruning benefit (inverse of priority, adjusted by size)
                pruning_benefit = (1.0 - total_score) * math.log(max(1, size_bytes))
                
                candidate = PruningCandidate(
                    context_id=context_id,
                    priority_score=total_score,
                    size_bytes=size_bytes,
                    last_accessed=getattr(context_entry, 'last_accessed', datetime.now()),
                    access_count=getattr(context_entry, 'access_count', 0),
                    pruning_benefit=pruning_benefit
                )
                
                candidates.append(candidate)
            
            # Sort by pruning benefit (higher benefit = better candidate for pruning)
            candidates.sort(key=lambda x: x.pruning_benefit, reverse=True)
            
            # Cache the candidates
            self.pruning_candidates_cache = candidates[:target_count * 2]  # Cache extra for flexibility
            
            return candidates[:target_count]
    
    def identify_offload_candidates(self, target_size_bytes: int) -> List[OffloadCandidate]:
        """Identify candidates for offloading to different storage tiers"""
        with self.lock:
            if not self.context_manager:
                return []
            
            candidates = []
            total_size_identified = 0
            
            # Get contexts from working memory
            working_memory = getattr(self.context_manager, 'working_memory', {})
            
            for context_id, context_entry in working_memory.items():
                if total_size_identified >= target_size_bytes:
                    break
                
                # Calculate current size
                current_size = len(pickle.dumps(context_entry)) if context_entry else 0
                
                # Estimate compressed size
                estimated_compressed_size = int(current_size * 0.3)  # Assume 70% compression
                
                # Determine best offload strategy
                offload_strategy = self._determine_offload_strategy(context_id, context_entry)
                
                # Calculate offload benefit
                priority_score = self.calculate_priority_score(context_id, context_entry)
                total_score = priority_score.calculate_total_score()
                
                # Lower priority = higher offload benefit
                offload_benefit = (1.0 - total_score) * current_size
                
                # Get access pattern
                access_pattern = self._analyze_access_pattern(context_id)
                
                candidate = OffloadCandidate(
                    context_id=context_id,
                    current_size=current_size,
                    estimated_compressed_size=estimated_compressed_size,
                    offload_strategy=offload_strategy,
                    offload_benefit=offload_benefit,
                    access_pattern=access_pattern
                )
                
                candidates.append(candidate)
                total_size_identified += current_size
            
            # Sort by offload benefit
            candidates.sort(key=lambda x: x.offload_benefit, reverse=True)
            
            # Cache the candidates
            self.offload_candidates_cache = candidates
            
            return candidates
    
    def _determine_offload_strategy(self, context_id: str, context_entry) -> OffloadStrategy:
        """Determine the best offload strategy for a context"""
        # Get priority score
        priority_score = self.calculate_priority_score(context_id, context_entry)
        total_score = priority_score.calculate_total_score()
        
        # Get access pattern
        access_pattern = self._analyze_access_pattern(context_id)
        
        # Strategy selection logic
        if total_score > 0.8:
            # High priority - just compress in place
            return OffloadStrategy.COMPRESS_IN_PLACE
        elif total_score > 0.6:
            # Medium priority - summarize and compress
            return OffloadStrategy.SUMMARIZE_AND_COMPRESS
        elif access_pattern['frequency'] < 0.1:
            # Rarely accessed - move to cold storage
            return OffloadStrategy.MOVE_TO_COLD_STORAGE
        elif len(self.context_graph.get_connected_contexts(context_id)) > 3:
            # Well connected - cluster and archive
            return OffloadStrategy.CLUSTER_AND_ARCHIVE
        else:
            # Default - hierarchical storage
            return OffloadStrategy.HIERARCHICAL_STORAGE
    
    def _analyze_access_pattern(self, context_id: str) -> Dict[str, Any]:
        """Analyze access pattern for a context"""
        access_history = self.access_patterns.get(context_id, [])
        
        if not access_history:
            return {
                "frequency": 0.0,
                "recency": 0.0,
                "pattern": "never_accessed",
                "trend": "stable"
            }
        
        now = datetime.now()
        
        # Calculate frequency (accesses per day)
        if len(access_history) > 1:
            time_span = (access_history[-1] - access_history[0]).total_seconds() / (24 * 3600)
            frequency = len(access_history) / max(1, time_span)
        else:
            frequency = 0.1
        
        # Calculate recency
        last_access = access_history[-1]
        recency = max(0.0, 1.0 - (now - last_access).total_seconds() / (7 * 24 * 3600))
        
        # Determine pattern
        if len(access_history) < 3:
            pattern = "sparse"
        elif frequency > 1.0:
            pattern = "frequent"
        elif recency > 0.8:
            pattern = "recent"
        else:
            pattern = "occasional"
        
        # Determine trend
        if len(access_history) >= 5:
            recent_accesses = [a for a in access_history if (now - a).total_seconds() < 7 * 24 * 3600]
            older_accesses = [a for a in access_history if (now - a).total_seconds() >= 7 * 24 * 3600]
            
            recent_rate = len(recent_accesses) / 7  # per day
            older_rate = len(older_accesses) / max(1, len(older_accesses))
            
            if recent_rate > older_rate * 1.5:
                trend = "increasing"
            elif recent_rate < older_rate * 0.5:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "unknown"
        
        return {
            "frequency": frequency,
            "recency": recency,
            "pattern": pattern,
            "trend": trend,
            "total_accesses": len(access_history)
        }
    
    def execute_pruning(self, candidates: List[PruningCandidate]) -> Dict[str, Any]:
        """Execute pruning of selected candidates"""
        with self.lock:
            if not self.context_manager:
                return {"success": False, "error": "No context manager available"}
            
            pruned_count = 0
            total_size_freed = 0
            errors = []
            
            working_memory = getattr(self.context_manager, 'working_memory', {})
            
            for candidate in candidates:
                try:
                    if candidate.context_id in working_memory:
                        # Get the context entry
                        context_entry = working_memory[candidate.context_id]
                        
                        # Check if it's safe to prune (respect priority thresholds)
                        priority_level = self._get_priority_level(candidate.priority_score)
                        threshold = self.pruning_thresholds.get(priority_level, 0.5)
                        
                        if candidate.priority_score <= threshold:
                            # Archive before pruning if it has some value
                            if candidate.priority_score > 0.2:
                                self.context_manager._compress_context(context_entry)
                            
                            # Remove from working memory
                            del working_memory[candidate.context_id]
                            
                            pruned_count += 1
                            total_size_freed += candidate.size_bytes
                            
                            logger.info(f"Pruned context {candidate.context_id} (priority: {candidate.priority_score:.3f})")
                        else:
                            logger.debug(f"Skipped pruning {candidate.context_id} - above threshold")
                
                except Exception as e:
                    error_msg = f"Failed to prune {candidate.context_id}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Update statistics
            self.prioritization_stats["total_prunings"] += pruned_count
            self.prioritization_stats["memory_saved_bytes"] += total_size_freed
            
            # Record pruning event
            pruning_event = {
                "timestamp": datetime.now().isoformat(),
                "pruned_count": pruned_count,
                "total_size_freed": total_size_freed,
                "candidates_processed": len(candidates),
                "errors": errors
            }
            self.pruning_history.append(pruning_event)
            
            logger.info(f"Pruning completed: {pruned_count} items, {total_size_freed} bytes freed")
            
            return {
                "success": True,
                "pruned_count": pruned_count,
                "total_size_freed": total_size_freed,
                "errors": errors
            }
    
    def execute_offloading(self, candidates: List[OffloadCandidate]) -> Dict[str, Any]:
        """Execute offloading of selected candidates"""
        with self.lock:
            if not self.context_manager:
                return {"success": False, "error": "No context manager available"}
            
            offloaded_count = 0
            total_size_moved = 0
            errors = []
            
            working_memory = getattr(self.context_manager, 'working_memory', {})
            
            for candidate in candidates:
                try:
                    if candidate.context_id in working_memory:
                        context_entry = working_memory[candidate.context_id]
                        
                        # Execute the appropriate offload strategy
                        success = self._execute_offload_strategy(
                            candidate.context_id, 
                            context_entry, 
                            candidate.offload_strategy
                        )
                        
                        if success:
                            offloaded_count += 1
                            total_size_moved += candidate.current_size
                            logger.info(f"Offloaded context {candidate.context_id} using {candidate.offload_strategy.value}")
                        else:
                            errors.append(f"Failed to offload {candidate.context_id}")
                
                except Exception as e:
                    error_msg = f"Failed to offload {candidate.context_id}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Update statistics
            self.prioritization_stats["total_offloads"] += offloaded_count
            self.prioritization_stats["memory_saved_bytes"] += total_size_moved
            
            # Record offloading event
            offloading_event = {
                "timestamp": datetime.now().isoformat(),
                "offloaded_count": offloaded_count,
                "total_size_moved": total_size_moved,
                "candidates_processed": len(candidates),
                "errors": errors
            }
            self.offloading_history.append(offloading_event)
            
            logger.info(f"Offloading completed: {offloaded_count} items, {total_size_moved} bytes moved")
            
            return {
                "success": True,
                "offloaded_count": offloaded_count,
                "total_size_moved": total_size_moved,
                "errors": errors
            }
    
    def _execute_offload_strategy(self, context_id: str, context_entry, strategy: OffloadStrategy) -> bool:
        """Execute a specific offload strategy"""
        try:
            if strategy == OffloadStrategy.COMPRESS_IN_PLACE:
                return self.context_manager._compress_context(context_entry)
            
            elif strategy == OffloadStrategy.MOVE_TO_COLD_STORAGE:
                # Move to archived storage
                file_path = f"{self.context_manager.archive_dir}/{context_id}.gz"
                compressed_data = gzip.compress(pickle.dumps(context_entry))
                with open(file_path, 'wb') as f:
                    f.write(compressed_data)
                
                self.context_manager.archived_memory[context_id] = file_path
                del self.context_manager.working_memory[context_id]
                return True
            
            elif strategy == OffloadStrategy.SUMMARIZE_AND_COMPRESS:
                # Summarize content if it's text
                if hasattr(context_entry, 'content') and isinstance(context_entry.content, str):
                    if len(context_entry.content) > 500:
                        # Simple summarization (in practice, would use more sophisticated methods)
                        summary = context_entry.content[:200] + "... [summarized]"
                        context_entry.content = summary
                        context_entry.metadata['summarized'] = True
                
                return self.context_manager._compress_context(context_entry)
            
            elif strategy == OffloadStrategy.CLUSTER_AND_ARCHIVE:
                # Find related contexts and archive together
                connected_contexts = self.context_graph.get_connected_contexts(context_id, max_depth=1)
                cluster_data = {
                    "main_context": context_entry,
                    "related_contexts": {}
                }
                
                for related_id in connected_contexts:
                    if related_id in self.context_manager.working_memory:
                        cluster_data["related_contexts"][related_id] = self.context_manager.working_memory[related_id]
                
                # Archive the cluster
                file_path = f"{self.context_manager.archive_dir}/cluster_{context_id}.gz"
                compressed_data = gzip.compress(pickle.dumps(cluster_data))
                with open(file_path, 'wb') as f:
                    f.write(compressed_data)
                
                self.context_manager.archived_memory[f"cluster_{context_id}"] = file_path
                del self.context_manager.working_memory[context_id]
                return True
            
            elif strategy == OffloadStrategy.HIERARCHICAL_STORAGE:
                # Use hierarchical storage management
                return self.context_manager._compress_context(context_entry)
            
            else:
                logger.warning(f"Unknown offload strategy: {strategy}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to execute offload strategy {strategy}: {e}")
            return False
    
    def _get_priority_level(self, priority_score: float) -> PriorityLevel:
        """Convert priority score to priority level"""
        if priority_score >= 0.9:
            return PriorityLevel.CRITICAL
        elif priority_score >= 0.8:
            return PriorityLevel.ESSENTIAL
        elif priority_score >= 0.7:
            return PriorityLevel.HIGH
        elif priority_score >= 0.5:
            return PriorityLevel.MEDIUM
        elif priority_score >= 0.3:
            return PriorityLevel.LOW
        elif priority_score >= 0.1:
            return PriorityLevel.MINIMAL
        else:
            return PriorityLevel.DISPOSABLE
    
    def optimize_memory_usage(self, target_usage: Optional[float] = None) -> Dict[str, Any]:
        """Optimize memory usage through intelligent pruning and offloading"""
        target = target_usage or self.target_memory_usage
        
        if not self.context_manager:
            return {"success": False, "error": "No context manager available"}
        
        # Get current memory usage
        current_stats = self.context_manager.get_system_stats()
        working_memory_count = current_stats["working_memory"]["entries"]
        
        optimization_results = {
            "initial_memory_count": working_memory_count,
            "target_memory_count": int(self.max_working_memory * target),
            "pruning_results": {},
            "offloading_results": {},
            "final_memory_count": 0
        }
        
        if working_memory_count > self.max_working_memory * target:
            # Calculate how many items to remove
            items_to_remove = working_memory_count - int(self.max_working_memory * target)
            
            # Split between pruning and offloading
            items_to_prune = int(items_to_remove * 0.3)  # 30% pruning
            items_to_offload = items_to_remove - items_to_prune  # 70% offloading
            
            # Execute pruning
            if items_to_prune > 0:
                pruning_candidates = self.identify_pruning_candidates(items_to_prune)
                optimization_results["pruning_results"] = self.execute_pruning(pruning_candidates)
            
            # Execute offloading
            if items_to_offload > 0:
                # Estimate target size for offloading
                avg_item_size = current_stats["working_memory"]["size_bytes"] / max(1, working_memory_count)
                target_offload_size = int(avg_item_size * items_to_offload)
                
                offload_candidates = self.identify_offload_candidates(target_offload_size)
                optimization_results["offloading_results"] = self.execute_offloading(offload_candidates)
        
        # Get final memory usage
        final_stats = self.context_manager.get_system_stats()
        optimization_results["final_memory_count"] = final_stats["working_memory"]["entries"]
        
        logger.info(f"Memory optimization completed: {working_memory_count} -> {optimization_results['final_memory_count']} items")
        
        return optimization_results
    
    def get_prioritization_stats(self) -> Dict[str, Any]:
        """Get comprehensive prioritization statistics"""
        with self.lock:
            # Calculate average priority score
            if self.priority_scores:
                total_score = sum(score.calculate_total_score() for score in self.priority_scores.values())
                avg_score = total_score / len(self.priority_scores)
                self.prioritization_stats["average_priority_score"] = avg_score
            
            # Add recent activity
            recent_prunings = len([p for p in self.pruning_history if 
                                 (datetime.now() - datetime.fromisoformat(p["timestamp"])).total_seconds() < 3600])
            recent_offloads = len([o for o in self.offloading_history if 
                                 (datetime.now() - datetime.fromisoformat(o["timestamp"])).total_seconds() < 3600])
            
            stats = dict(self.prioritization_stats)
            stats.update({
                "recent_prunings_1h": recent_prunings,
                "recent_offloads_1h": recent_offloads,
                "total_contexts_scored": len(self.priority_scores),
                "context_categories": dict(Counter(self.context_categories.values())),
                "graph_nodes": len(self.context_graph.nodes),
                "graph_edges": sum(len(edges) for edges in self.context_graph.edges.values())
            })
            
            return stats
    
    async def start_background_optimization(self):
        """Start background optimization tasks"""
        logger.info("Starting background prioritization optimization")
        
        async def priority_update_task():
            while self.active:
                await asyncio.sleep(300)  # Run every 5 minutes
                self._update_priority_scores()
        
        async def memory_optimization_task():
            while self.active:
                await asyncio.sleep(600)  # Run every 10 minutes
                self.optimize_memory_usage()
        
        async def relationship_analysis_task():
            while self.active:
                await asyncio.sleep(900)  # Run every 15 minutes
                self._analyze_context_relationships()
        
        # Start tasks
        self.background_tasks = [
            asyncio.create_task(priority_update_task()),
            asyncio.create_task(memory_optimization_task()),
            asyncio.create_task(relationship_analysis_task())
        ]
    
    def _update_priority_scores(self):
        """Update priority scores for all contexts"""
        if not self.context_manager:
            return
        
        working_memory = getattr(self.context_manager, 'working_memory', {})
        updated_count = 0
        
        for context_id, context_entry in working_memory.items():
            try:
                self.calculate_priority_score(context_id, context_entry)
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update priority score for {context_id}: {e}")
        
        self.prioritization_stats["total_prioritizations"] += updated_count
        logger.debug(f"Updated priority scores for {updated_count} contexts")
    
    def _analyze_context_relationships(self):
        """Analyze and update context relationships"""
        if not self.context_manager:
            return
        
        # Find clusters of related contexts
        clusters = self.context_graph.find_clusters()
        
        # Update relationships based on access patterns
        for context_id in self.access_patterns:
            access_times = self.access_patterns[context_id]
            
            # Find contexts accessed around the same time
            for other_id in self.access_patterns:
                if other_id != context_id:
                    other_times = self.access_patterns[other_id]
                    
                    # Check for temporal correlation
                    correlation = self._calculate_temporal_correlation(access_times, other_times)
                    if correlation > 0.5:
                        # Add or strengthen relationship
                        self.add_context_relationship(
                            context_id, other_id, "temporal_correlation", 
                            strength=correlation, bidirectional=True
                        )
        
        logger.debug(f"Analyzed relationships for {len(clusters)} clusters")
    
    def _calculate_temporal_correlation(self, times1: List[datetime], times2: List[datetime]) -> float:
        """Calculate temporal correlation between two access patterns"""
        if not times1 or not times2:
            return 0.0
        
        # Simple correlation based on access time proximity
        correlations = []
        
        for t1 in times1[-10:]:  # Use last 10 accesses
            for t2 in times2[-10:]:
                time_diff = abs((t1 - t2).total_seconds())
                if time_diff < 300:  # Within 5 minutes
                    correlation = max(0, 1.0 - time_diff / 300.0)
                    correlations.append(correlation)
        
        return sum(correlations) / max(1, len(correlations))
    
    async def shutdown(self):
        """Gracefully shutdown the prioritization engine"""
        logger.info("Shutting down ContextPrioritizationEngine")
        
        self.stop()
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("ContextPrioritizationEngine shutdown complete")

# Example usage and testing
if __name__ == "__main__":
    async def test_context_prioritization_engine():
        """Test the context prioritization engine"""
        engine = ContextPrioritizationEngine()
        
        # Start the engine
        engine.start()
        
        # Start background optimization
        await engine.start_background_optimization()
        
        # Simulate some context relationships
        engine.add_context_relationship("ctx1", "ctx2", "semantic_similarity", 0.8)
        engine.add_context_relationship("ctx2", "ctx3", "temporal_sequence", 0.6)
        
        # Categorize contexts
        engine.categorize_context("ctx1", ContextCategory.CORE_MEMORY)
        engine.categorize_context("ctx2", ContextCategory.ACTIVE_TASK)
        
        # Register some access patterns
        engine.register_context_access("ctx1")
        engine.register_context_access("ctx2")
        
        # Wait for some processing
        await asyncio.sleep(2)
        
        # Get statistics
        stats = engine.get_prioritization_stats()
        print(f"Prioritization stats: {json.dumps(stats, indent=2, default=str)}")
        
        # Shutdown
        await engine.shutdown()
    
    # Run the test
    asyncio.run(test_context_prioritization_engine())

