"""
DEVmind Persistent Memory Cores
Advanced memory management system that maintains state across restarts

This module implements persistent memory cores that store the brain's current
mind state, thoughts, experiences, and learned patterns on disk, allowing
DEVmind to pick up exactly where it left off even after system restarts.
Like human long-term memory, this enables true continuity of consciousness.

Author: Sachib
Version: 1.0.0
"""

import asyncio
import json
import logging
import time
import threading
import os
import sys
import sqlite3
import pickle
import lz4.frame
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path
import numpy as np
from collections import defaultdict, deque
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryType(Enum):
    """Types of memory storage"""
    WORKING = "working"           # Current active thoughts and state
    SHORT_TERM = "short_term"     # Recent experiences and temporary data
    LONG_TERM = "long_term"       # Consolidated important memories
    EPISODIC = "episodic"         # Specific events and experiences
    SEMANTIC = "semantic"         # Facts and knowledge
    PROCEDURAL = "procedural"     # Skills and procedures
    EMOTIONAL = "emotional"       # Emotional associations and patterns
    CONTEXTUAL = "contextual"     # Context-dependent information
    CACHE = "cache"              # Frequently accessed data
    ARCHIVE = "archive"          # Historical data

class MemoryPriority(Enum):
    """Priority levels for memory storage"""
    CRITICAL = "critical"        # Must never be lost
    HIGH = "high"               # Very important
    MEDIUM = "medium"           # Normal importance
    LOW = "low"                 # Can be discarded if needed
    TEMPORARY = "temporary"     # Short-lived data

class MemoryStatus(Enum):
    """Status of memory entries"""
    ACTIVE = "active"           # Currently in use
    STORED = "stored"           # Safely stored
    CACHED = "cached"           # In cache for quick access
    COMPRESSED = "compressed"   # Compressed for space
    ARCHIVED = "archived"       # Moved to archive
    CORRUPTED = "corrupted"     # Data integrity issue
    DELETED = "deleted"         # Marked for deletion

@dataclass
class MemoryEntry:
    """Represents a single memory entry"""
    id: str
    key: str
    data: Any
    memory_type: MemoryType
    priority: MemoryPriority
    status: MemoryStatus
    created_at: datetime
    last_accessed: datetime
    access_count: int
    size_bytes: int
    checksum: str
    tags: Set[str]
    metadata: Dict[str, Any]
    expiry_date: Optional[datetime]
    compression_ratio: float
    emotional_weight: float
    importance_score: float
    related_memories: List[str]

@dataclass
class MemoryCore:
    """Represents a memory core storage unit"""
    id: str
    name: str
    memory_type: MemoryType
    max_size_mb: float
    current_size_mb: float
    entry_count: int
    compression_enabled: bool
    encryption_enabled: bool
    auto_cleanup: bool
    retention_days: int
    storage_path: Path
    database_path: Path
    created_at: datetime
    last_maintenance: datetime

@dataclass
class MemoryMetrics:
    """Metrics for memory management"""
    total_entries: int = 0
    total_size_mb: float = 0.0
    cores_count: int = 0
    cache_hit_rate: float = 0.0
    compression_ratio: float = 0.0
    access_frequency: float = 0.0
    cleanup_cycles: int = 0
    corruption_events: int = 0
    recovery_operations: int = 0
    memory_efficiency: float = 1.0

class MemoryIndex:
    """Advanced indexing system for fast memory retrieval"""
    
    def __init__(self, core_id: str):
        self.core_id = core_id
        self.key_index: Dict[str, str] = {}  # key -> memory_id
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)  # tag -> memory_ids
        self.type_index: Dict[MemoryType, Set[str]] = defaultdict(set)  # type -> memory_ids
        self.time_index: Dict[str, Set[str]] = defaultdict(set)  # date -> memory_ids
        self.importance_index: List[Tuple[float, str]] = []  # (importance, memory_id)
        self.access_index: List[Tuple[int, str]] = []  # (access_count, memory_id)
        self.size_index: List[Tuple[int, str]] = []  # (size, memory_id)
        
        # Full-text search index (simplified)
        self.text_index: Dict[str, Set[str]] = defaultdict(set)  # word -> memory_ids
    
    def add_entry(self, memory_entry: MemoryEntry):
        """Add a memory entry to all indexes"""
        memory_id = memory_entry.id
        
        # Key index
        self.key_index[memory_entry.key] = memory_id
        
        # Tag index
        for tag in memory_entry.tags:
            self.tag_index[tag].add(memory_id)
        
        # Type index
        self.type_index[memory_entry.memory_type].add(memory_id)
        
        # Time index
        date_key = memory_entry.created_at.strftime('%Y-%m-%d')
        self.time_index[date_key].add(memory_id)
        
        # Importance index
        self.importance_index.append((memory_entry.importance_score, memory_id))
        self.importance_index.sort(reverse=True)
        if len(self.importance_index) > 10000:  # Limit size
            self.importance_index = self.importance_index[:10000]
        
        # Access index
        self.access_index.append((memory_entry.access_count, memory_id))
        self.access_index.sort(reverse=True)
        if len(self.access_index) > 10000:
            self.access_index = self.access_index[:10000]
        
        # Size index
        self.size_index.append((memory_entry.size_bytes, memory_id))
        self.size_index.sort(reverse=True)
        if len(self.size_index) > 10000:
            self.size_index = self.size_index[:10000]
        
        # Text index (if data is text)
        if isinstance(memory_entry.data, str):
            words = memory_entry.data.lower().split()
            for word in words:
                if len(word) > 2:  # Skip very short words
                    self.text_index[word].add(memory_id)
    
    def remove_entry(self, memory_entry: MemoryEntry):
        """Remove a memory entry from all indexes"""
        memory_id = memory_entry.id
        
        # Key index
        if memory_entry.key in self.key_index:
            del self.key_index[memory_entry.key]
        
        # Tag index
        for tag in memory_entry.tags:
            self.tag_index[tag].discard(memory_id)
        
        # Type index
        self.type_index[memory_entry.memory_type].discard(memory_id)
        
        # Time index
        date_key = memory_entry.created_at.strftime('%Y-%m-%d')
        self.time_index[date_key].discard(memory_id)
        
        # Remove from sorted indexes
        self.importance_index = [(score, mid) for score, mid in self.importance_index if mid != memory_id]
        self.access_index = [(count, mid) for count, mid in self.access_index if mid != memory_id]
        self.size_index = [(size, mid) for size, mid in self.size_index if mid != memory_id]
        
        # Text index
        if isinstance(memory_entry.data, str):
            words = memory_entry.data.lower().split()
            for word in words:
                if len(word) > 2:
                    self.text_index[word].discard(memory_id)
    
    def search_by_key(self, key: str) -> Optional[str]:
        """Search by exact key"""
        return self.key_index.get(key)
    
    def search_by_tags(self, tags: List[str]) -> Set[str]:
        """Search by tags (intersection)"""
        if not tags:
            return set()
        
        result = self.tag_index[tags[0]].copy()
        for tag in tags[1:]:
            result &= self.tag_index[tag]
        
        return result
    
    def search_by_type(self, memory_type: MemoryType) -> Set[str]:
        """Search by memory type"""
        return self.type_index[memory_type].copy()
    
    def search_by_date_range(self, start_date: datetime, end_date: datetime) -> Set[str]:
        """Search by date range"""
        result = set()
        current_date = start_date
        
        while current_date <= end_date:
            date_key = current_date.strftime('%Y-%m-%d')
            result.update(self.time_index[date_key])
            current_date += timedelta(days=1)
        
        return result
    
    def search_by_text(self, query: str) -> Set[str]:
        """Simple text search"""
        words = query.lower().split()
        if not words:
            return set()
        
        result = self.text_index[words[0]].copy()
        for word in words[1:]:
            result &= self.text_index[word]
        
        return result
    
    def get_most_important(self, limit: int = 10) -> List[str]:
        """Get most important memories"""
        return [memory_id for _, memory_id in self.importance_index[:limit]]
    
    def get_most_accessed(self, limit: int = 10) -> List[str]:
        """Get most accessed memories"""
        return [memory_id for _, memory_id in self.access_index[:limit]]
    
    def get_largest(self, limit: int = 10) -> List[str]:
        """Get largest memories"""
        return [memory_id for _, memory_id in self.size_index[:limit]]

class MemoryCompressor:
    """Handles memory compression and decompression"""
    
    @staticmethod
    def compress_data(data: Any) -> Tuple[bytes, float]:
        """Compress data and return compressed bytes and compression ratio"""
        # Serialize data
        serialized = pickle.dumps(data)
        original_size = len(serialized)
        
        # Compress using LZ4
        compressed = lz4.frame.compress(serialized)
        compressed_size = len(compressed)
        
        # Calculate compression ratio
        ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        return compressed, ratio
    
    @staticmethod
    def decompress_data(compressed_data: bytes) -> Any:
        """Decompress data and return original object"""
        # Decompress
        decompressed = lz4.frame.decompress(compressed_data)
        
        # Deserialize
        data = pickle.loads(decompressed)
        
        return data
    
    @staticmethod
    def calculate_checksum(data: Any) -> str:
        """Calculate checksum for data integrity"""
        serialized = pickle.dumps(data)
        return hashlib.sha256(serialized).hexdigest()

class MemoryDatabase:
    """SQLite database interface for memory storage"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection = None
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.connection.execute('PRAGMA journal_mode=WAL')  # Better concurrency
        self.connection.execute('PRAGMA synchronous=NORMAL')  # Better performance
        
        # Create tables
        self.connection.execute('''
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                key TEXT UNIQUE,
                memory_type TEXT,
                priority TEXT,
                status TEXT,
                created_at TEXT,
                last_accessed TEXT,
                access_count INTEGER,
                size_bytes INTEGER,
                checksum TEXT,
                tags TEXT,
                metadata TEXT,
                expiry_date TEXT,
                compression_ratio REAL,
                emotional_weight REAL,
                importance_score REAL,
                related_memories TEXT,
                data_blob BLOB
            )
        ''')
        
        # Create indexes
        self.connection.execute('CREATE INDEX IF NOT EXISTS idx_key ON memory_entries(key)')
        self.connection.execute('CREATE INDEX IF NOT EXISTS idx_type ON memory_entries(memory_type)')
        self.connection.execute('CREATE INDEX IF NOT EXISTS idx_created ON memory_entries(created_at)')
        self.connection.execute('CREATE INDEX IF NOT EXISTS idx_importance ON memory_entries(importance_score)')
        self.connection.execute('CREATE INDEX IF NOT EXISTS idx_access ON memory_entries(access_count)')
        
        self.connection.commit()
    
    def store_entry(self, memory_entry: MemoryEntry, compressed_data: bytes):
        """Store a memory entry in the database"""
        cursor = self.connection.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO memory_entries (
                id, key, memory_type, priority, status, created_at, last_accessed,
                access_count, size_bytes, checksum, tags, metadata, expiry_date,
                compression_ratio, emotional_weight, importance_score, related_memories, data_blob
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory_entry.id,
            memory_entry.key,
            memory_entry.memory_type.value,
            memory_entry.priority.value,
            memory_entry.status.value,
            memory_entry.created_at.isoformat(),
            memory_entry.last_accessed.isoformat(),
            memory_entry.access_count,
            memory_entry.size_bytes,
            memory_entry.checksum,
            json.dumps(list(memory_entry.tags)),
            json.dumps(memory_entry.metadata),
            memory_entry.expiry_date.isoformat() if memory_entry.expiry_date else None,
            memory_entry.compression_ratio,
            memory_entry.emotional_weight,
            memory_entry.importance_score,
            json.dumps(memory_entry.related_memories),
            compressed_data
        ))
        
        self.connection.commit()
    
    def load_entry(self, memory_id: str) -> Optional[Tuple[MemoryEntry, bytes]]:
        """Load a memory entry from the database"""
        cursor = self.connection.cursor()
        
        cursor.execute('SELECT * FROM memory_entries WHERE id = ?', (memory_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Parse row data
        (id, key, memory_type, priority, status, created_at, last_accessed,
         access_count, size_bytes, checksum, tags, metadata, expiry_date,
         compression_ratio, emotional_weight, importance_score, related_memories, data_blob) = row
        
        memory_entry = MemoryEntry(
            id=id,
            key=key,
            data=None,  # Will be decompressed separately
            memory_type=MemoryType(memory_type),
            priority=MemoryPriority(priority),
            status=MemoryStatus(status),
            created_at=datetime.fromisoformat(created_at),
            last_accessed=datetime.fromisoformat(last_accessed),
            access_count=access_count,
            size_bytes=size_bytes,
            checksum=checksum,
            tags=set(json.loads(tags)),
            metadata=json.loads(metadata),
            expiry_date=datetime.fromisoformat(expiry_date) if expiry_date else None,
            compression_ratio=compression_ratio,
            emotional_weight=emotional_weight,
            importance_score=importance_score,
            related_memories=json.loads(related_memories)
        )
        
        return memory_entry, data_blob
    
    def delete_entry(self, memory_id: str):
        """Delete a memory entry from the database"""
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM memory_entries WHERE id = ?', (memory_id,))
        self.connection.commit()
    
    def get_entries_by_type(self, memory_type: MemoryType) -> List[str]:
        """Get all entry IDs of a specific type"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT id FROM memory_entries WHERE memory_type = ?', (memory_type.value,))
        return [row[0] for row in cursor.fetchall()]
    
    def get_expired_entries(self) -> List[str]:
        """Get IDs of expired entries"""
        cursor = self.connection.cursor()
        current_time = datetime.now().isoformat()
        cursor.execute('SELECT id FROM memory_entries WHERE expiry_date IS NOT NULL AND expiry_date < ?', (current_time,))
        return [row[0] for row in cursor.fetchall()]
    
    def get_database_size(self) -> int:
        """Get database file size in bytes"""
        return self.db_path.stat().st_size if self.db_path.exists() else 0
    
    def vacuum_database(self):
        """Optimize database storage"""
        self.connection.execute('VACUUM')
        self.connection.commit()
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

class PersistentMemoryCore:
    """
    A single persistent memory core that manages a specific type of memory
    """
    
    def __init__(self, core_id: str, name: str, memory_type: MemoryType,
                 max_size_mb: float = 1000.0, storage_path: Path = None):
        self.core_id = core_id
        self.name = name
        self.memory_type = memory_type
        self.max_size_mb = max_size_mb
        self.current_size_mb = 0.0
        self.entry_count = 0
        
        # Configuration
        self.compression_enabled = True
        self.encryption_enabled = False  # Future feature
        self.auto_cleanup = True
        self.retention_days = 365  # Default retention
        
        # Storage
        self.storage_path = storage_path or Path(f"/tmp/devmind_memory_{core_id}")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.database_path = self.storage_path / f"{core_id}.db"
        
        # Components
        self.database = MemoryDatabase(self.database_path)
        self.index = MemoryIndex(core_id)
        self.compressor = MemoryCompressor()
        
        # Cache
        self.cache: Dict[str, MemoryEntry] = {}
        self.cache_max_size = 100  # Number of entries to cache
        self.cache_access_order = deque()
        
        # Metrics
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_accesses = 0
        
        # Timestamps
        self.created_at = datetime.now()
        self.last_maintenance = datetime.now()
        
        # Load existing entries into index
        self._rebuild_index()
        
        logger.info(f"Memory core initialized: {name} ({core_id})")
    
    def _rebuild_index(self):
        """Rebuild the index from database"""
        try:
            # Get all entry IDs from database
            cursor = self.database.connection.cursor()
            cursor.execute('SELECT id FROM memory_entries')
            entry_ids = [row[0] for row in cursor.fetchall()]
            
            # Load each entry and add to index
            for entry_id in entry_ids:
                entry_data = self.database.load_entry(entry_id)
                if entry_data:
                    memory_entry, _ = entry_data
                    self.index.add_entry(memory_entry)
                    self.entry_count += 1
                    self.current_size_mb += memory_entry.size_bytes / (1024 * 1024)
            
            logger.info(f"Rebuilt index for core {self.core_id}: {self.entry_count} entries")
            
        except Exception as e:
            logger.error(f"Error rebuilding index for core {self.core_id}: {str(e)}")
    
    async def store(self, key: str, data: Any, priority: MemoryPriority = MemoryPriority.MEDIUM,
                   tags: Set[str] = None, metadata: Dict[str, Any] = None,
                   expiry_date: Optional[datetime] = None,
                   emotional_weight: float = 0.0,
                   importance_score: float = 0.5) -> Dict[str, Any]:
        """Store data in the memory core"""
        
        # Check if key already exists
        existing_id = self.index.search_by_key(key)
        if existing_id:
            return await self._update_existing(existing_id, data, priority, tags, metadata,
                                             expiry_date, emotional_weight, importance_score)
        
        # Create memory entry
        memory_id = uuid.uuid4().hex[:16]
        
        # Compress data if enabled
        if self.compression_enabled:
            compressed_data, compression_ratio = self.compressor.compress_data(data)
        else:
            compressed_data = pickle.dumps(data)
            compression_ratio = 1.0
        
        # Calculate size and checksum
        size_bytes = len(compressed_data)
        checksum = self.compressor.calculate_checksum(data)
        
        # Create memory entry
        memory_entry = MemoryEntry(
            id=memory_id,
            key=key,
            data=data,  # Keep uncompressed in memory
            memory_type=self.memory_type,
            priority=priority,
            status=MemoryStatus.ACTIVE,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            size_bytes=size_bytes,
            checksum=checksum,
            tags=tags or set(),
            metadata=metadata or {},
            expiry_date=expiry_date,
            compression_ratio=compression_ratio,
            emotional_weight=emotional_weight,
            importance_score=importance_score,
            related_memories=[]
        )
        
        # Check storage limits
        new_size_mb = self.current_size_mb + (size_bytes / (1024 * 1024))
        if new_size_mb > self.max_size_mb:
            await self._cleanup_storage()
            new_size_mb = self.current_size_mb + (size_bytes / (1024 * 1024))
            
            if new_size_mb > self.max_size_mb:
                return {
                    'success': False,
                    'error': 'Storage limit exceeded',
                    'current_size_mb': self.current_size_mb,
                    'max_size_mb': self.max_size_mb
                }
        
        # Store in database
        self.database.store_entry(memory_entry, compressed_data)
        
        # Add to index
        self.index.add_entry(memory_entry)
        
        # Add to cache
        self._add_to_cache(memory_entry)
        
        # Update metrics
        self.entry_count += 1
        self.current_size_mb = new_size_mb
        
        logger.info(f"Stored memory: {key} ({memory_id}) in core {self.core_id}")
        
        return {
            'success': True,
            'memory_id': memory_id,
            'key': key,
            'size_bytes': size_bytes,
            'compression_ratio': compression_ratio,
            'core_id': self.core_id
        }
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data by key"""
        self.total_accesses += 1
        
        # Check cache first
        if key in self.cache:
            self.cache_hits += 1
            memory_entry = self.cache[key]
            memory_entry.last_accessed = datetime.now()
            memory_entry.access_count += 1
            self._update_cache_access(key)
            return memory_entry.data
        
        # Search in index
        memory_id = self.index.search_by_key(key)
        if not memory_id:
            self.cache_misses += 1
            return None
        
        # Load from database
        entry_data = self.database.load_entry(memory_id)
        if not entry_data:
            self.cache_misses += 1
            return None
        
        memory_entry, compressed_data = entry_data
        
        # Decompress data
        if self.compression_enabled:
            data = self.compressor.decompress_data(compressed_data)
        else:
            data = pickle.loads(compressed_data)
        
        # Verify checksum
        calculated_checksum = self.compressor.calculate_checksum(data)
        if calculated_checksum != memory_entry.checksum:
            logger.error(f"Checksum mismatch for memory {memory_id}")
            memory_entry.status = MemoryStatus.CORRUPTED
            return None
        
        # Update entry
        memory_entry.data = data
        memory_entry.last_accessed = datetime.now()
        memory_entry.access_count += 1
        
        # Add to cache
        self._add_to_cache(memory_entry)
        
        # Update database
        if self.compression_enabled:
            compressed_data, _ = self.compressor.compress_data(data)
        else:
            compressed_data = pickle.dumps(data)
        
        self.database.store_entry(memory_entry, compressed_data)
        
        self.cache_misses += 1
        return data
    
    async def delete(self, key: str) -> Dict[str, Any]:
        """Delete data by key"""
        memory_id = self.index.search_by_key(key)
        if not memory_id:
            return {
                'success': False,
                'error': f'Key not found: {key}'
            }
        
        # Load entry to get size
        entry_data = self.database.load_entry(memory_id)
        if entry_data:
            memory_entry, _ = entry_data
            
            # Remove from index
            self.index.remove_entry(memory_entry)
            
            # Remove from cache
            if key in self.cache:
                del self.cache[key]
                if key in self.cache_access_order:
                    self.cache_access_order.remove(key)
            
            # Delete from database
            self.database.delete_entry(memory_id)
            
            # Update metrics
            self.entry_count -= 1
            self.current_size_mb -= memory_entry.size_bytes / (1024 * 1024)
            
            logger.info(f"Deleted memory: {key} ({memory_id}) from core {self.core_id}")
            
            return {
                'success': True,
                'memory_id': memory_id,
                'key': key,
                'freed_bytes': memory_entry.size_bytes
            }
        
        return {
            'success': False,
            'error': f'Failed to load entry for key: {key}'
        }
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search memories based on various criteria"""
        result_ids = set()
        
        # Search by tags
        if 'tags' in query:
            tag_results = self.index.search_by_tags(query['tags'])
            if not result_ids:
                result_ids = tag_results
            else:
                result_ids &= tag_results
        
        # Search by date range
        if 'start_date' in query and 'end_date' in query:
            date_results = self.index.search_by_date_range(
                datetime.fromisoformat(query['start_date']),
                datetime.fromisoformat(query['end_date'])
            )
            if not result_ids:
                result_ids = date_results
            else:
                result_ids &= date_results
        
        # Search by text
        if 'text' in query:
            text_results = self.index.search_by_text(query['text'])
            if not result_ids:
                result_ids = text_results
            else:
                result_ids &= text_results
        
        # If no specific criteria, get all
        if not result_ids and not query:
            result_ids = set(self.index.key_index.values())
        
        # Load and return results
        results = []
        for memory_id in list(result_ids)[:query.get('limit', 50)]:
            entry_data = self.database.load_entry(memory_id)
            if entry_data:
                memory_entry, _ = entry_data
                results.append({
                    'id': memory_entry.id,
                    'key': memory_entry.key,
                    'memory_type': memory_entry.memory_type.value,
                    'priority': memory_entry.priority.value,
                    'created_at': memory_entry.created_at.isoformat(),
                    'last_accessed': memory_entry.last_accessed.isoformat(),
                    'access_count': memory_entry.access_count,
                    'size_bytes': memory_entry.size_bytes,
                    'tags': list(memory_entry.tags),
                    'importance_score': memory_entry.importance_score,
                    'emotional_weight': memory_entry.emotional_weight
                })
        
        return results
    
    async def _update_existing(self, memory_id: str, data: Any, priority: MemoryPriority,
                             tags: Set[str], metadata: Dict[str, Any],
                             expiry_date: Optional[datetime],
                             emotional_weight: float, importance_score: float) -> Dict[str, Any]:
        """Update an existing memory entry"""
        entry_data = self.database.load_entry(memory_id)
        if not entry_data:
            return {
                'success': False,
                'error': f'Memory entry not found: {memory_id}'
            }
        
        memory_entry, old_compressed_data = entry_data
        
        # Update entry
        memory_entry.data = data
        memory_entry.priority = priority
        memory_entry.tags = tags or memory_entry.tags
        memory_entry.metadata.update(metadata or {})
        memory_entry.expiry_date = expiry_date
        memory_entry.emotional_weight = emotional_weight
        memory_entry.importance_score = importance_score
        memory_entry.last_accessed = datetime.now()
        memory_entry.access_count += 1
        
        # Recompress data
        if self.compression_enabled:
            compressed_data, compression_ratio = self.compressor.compress_data(data)
        else:
            compressed_data = pickle.dumps(data)
            compression_ratio = 1.0
        
        # Update size and checksum
        old_size = memory_entry.size_bytes
        memory_entry.size_bytes = len(compressed_data)
        memory_entry.checksum = self.compressor.calculate_checksum(data)
        memory_entry.compression_ratio = compression_ratio
        
        # Store updated entry
        self.database.store_entry(memory_entry, compressed_data)
        
        # Update cache
        if memory_entry.key in self.cache:
            self.cache[memory_entry.key] = memory_entry
        
        # Update metrics
        size_diff = memory_entry.size_bytes - old_size
        self.current_size_mb += size_diff / (1024 * 1024)
        
        return {
            'success': True,
            'memory_id': memory_id,
            'key': memory_entry.key,
            'updated': True,
            'size_change_bytes': size_diff
        }
    
    def _add_to_cache(self, memory_entry: MemoryEntry):
        """Add entry to cache with LRU eviction"""
        key = memory_entry.key
        
        # Remove if already in cache
        if key in self.cache:
            self.cache_access_order.remove(key)
        
        # Add to cache
        self.cache[key] = memory_entry
        self.cache_access_order.append(key)
        
        # Evict if cache is full
        while len(self.cache) > self.cache_max_size:
            oldest_key = self.cache_access_order.popleft()
            del self.cache[oldest_key]
    
    def _update_cache_access(self, key: str):
        """Update cache access order"""
        if key in self.cache_access_order:
            self.cache_access_order.remove(key)
            self.cache_access_order.append(key)
    
    async def _cleanup_storage(self):
        """Clean up storage to free space"""
        logger.info(f"Starting cleanup for core {self.core_id}")
        
        # Get expired entries
        expired_ids = self.database.get_expired_entries()
        for memory_id in expired_ids:
            entry_data = self.database.load_entry(memory_id)
            if entry_data:
                memory_entry, _ = entry_data
                await self.delete(memory_entry.key)
        
        # If still over limit, remove least important entries
        if self.current_size_mb > self.max_size_mb * 0.9:  # 90% threshold
            # Get least important entries
            cursor = self.database.connection.cursor()
            cursor.execute('''
                SELECT id, key, importance_score, size_bytes 
                FROM memory_entries 
                WHERE priority != ? 
                ORDER BY importance_score ASC, access_count ASC 
                LIMIT 100
            ''', (MemoryPriority.CRITICAL.value,))
            
            candidates = cursor.fetchall()
            freed_mb = 0
            target_free_mb = self.max_size_mb * 0.1  # Free 10%
            
            for memory_id, key, importance, size_bytes in candidates:
                if freed_mb >= target_free_mb:
                    break
                
                await self.delete(key)
                freed_mb += size_bytes / (1024 * 1024)
        
        # Vacuum database
        self.database.vacuum_database()
        
        logger.info(f"Cleanup completed for core {self.core_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get memory core status"""
        cache_hit_rate = self.cache_hits / max(self.total_accesses, 1)
        
        return {
            'core_id': self.core_id,
            'name': self.name,
            'memory_type': self.memory_type.value,
            'entry_count': self.entry_count,
            'current_size_mb': round(self.current_size_mb, 2),
            'max_size_mb': self.max_size_mb,
            'usage_percentage': round((self.current_size_mb / self.max_size_mb) * 100, 2),
            'cache_hit_rate': round(cache_hit_rate, 3),
            'cache_size': len(self.cache),
            'compression_enabled': self.compression_enabled,
            'auto_cleanup': self.auto_cleanup,
            'created_at': self.created_at.isoformat(),
            'last_maintenance': self.last_maintenance.isoformat()
        }

class PersistentMemoryManager:
    """
    The Persistent Memory Manager - Manages multiple memory cores
    
    This manager coordinates multiple memory cores, handles cross-core
    operations, and provides a unified interface for memory management.
    It ensures that DEVmind's state is continuously preserved and can
    be restored exactly after any restart.
    """
    
    def __init__(self, manager_id: str = None):
        self.manager_id = manager_id or f"pmm_{uuid.uuid4().hex[:8]}"
        self.is_running = False
        self.metrics = MemoryMetrics()
        
        # Memory cores
        self.cores: Dict[str, PersistentMemoryCore] = {}
        self.core_assignments: Dict[MemoryType, str] = {}
        
        # Background tasks
        self.maintenance_task = None
        self.sync_task = None
        self.maintenance_interval = 300.0  # 5 minutes
        self.sync_interval = 60.0  # 1 minute
        
        # Configuration
        self.total_memory_limit_mb = 5000.0  # 5GB total limit
        self.auto_create_cores = True
        self.cross_core_search = True
        
        # State tracking
        self.current_mind_state = {}
        self.state_checkpoints = deque(maxlen=100)  # Keep last 100 checkpoints
        
        # Persistence
        self.persistence_path = Path(f"/tmp/devmind_memory_manager_{self.manager_id}")
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Persistent Memory Manager initialized: {self.manager_id}")
    
    async def start(self) -> Dict[str, Any]:
        """Start the memory manager"""
        if self.is_running:
            return {
                'success': False,
                'error': 'Memory manager is already running',
                'manager_id': self.manager_id
            }
        
        logger.info(f"Starting Persistent Memory Manager: {self.manager_id}")
        
        # Load persistent state
        await self._load_persistent_state()
        
        # Create default cores if needed
        if not self.cores and self.auto_create_cores:
            await self._create_default_cores()
        
        # Start background tasks
        self.is_running = True
        self.maintenance_task = asyncio.create_task(self._maintenance_loop())
        self.sync_task = asyncio.create_task(self._sync_loop())
        
        # Load current mind state
        await self._load_current_mind_state()
        
        return {
            'success': True,
            'manager_id': self.manager_id,
            'cores_count': len(self.cores),
            'total_memory_mb': sum(core.current_size_mb for core in self.cores.values()),
            'mind_state_loaded': bool(self.current_mind_state)
        }
    
    async def stop(self) -> Dict[str, Any]:
        """Stop the memory manager"""
        if not self.is_running:
            return {
                'success': False,
                'error': 'Memory manager is not running',
                'manager_id': self.manager_id
            }
        
        logger.info(f"Stopping Persistent Memory Manager: {self.manager_id}")
        
        # Save current mind state
        await self._save_current_mind_state()
        
        # Stop background tasks
        self.is_running = False
        
        if self.maintenance_task:
            self.maintenance_task.cancel()
        if self.sync_task:
            self.sync_task.cancel()
        
        # Close all cores
        for core in self.cores.values():
            core.database.close()
        
        # Save persistent state
        await self._save_persistent_state()
        
        return {
            'success': True,
            'manager_id': self.manager_id,
            'final_metrics': asdict(self.metrics),
            'cores_closed': len(self.cores)
        }
    
    async def _create_default_cores(self):
        """Create default memory cores for each memory type"""
        default_cores = [
            ('working_memory', MemoryType.WORKING, 500.0),
            ('short_term_memory', MemoryType.SHORT_TERM, 1000.0),
            ('long_term_memory', MemoryType.LONG_TERM, 2000.0),
            ('episodic_memory', MemoryType.EPISODIC, 1000.0),
            ('semantic_memory', MemoryType.SEMANTIC, 1500.0),
            ('emotional_memory', MemoryType.EMOTIONAL, 500.0),
            ('cache_memory', MemoryType.CACHE, 200.0)
        ]
        
        for name, memory_type, max_size_mb in default_cores:
            await self.create_core(name, memory_type, max_size_mb)
    
    async def create_core(self, name: str, memory_type: MemoryType, 
                         max_size_mb: float = 1000.0) -> Dict[str, Any]:
        """Create a new memory core"""
        core_id = f"{memory_type.value}_{uuid.uuid4().hex[:8]}"
        
        # Check total memory limit
        total_allocated = sum(core.max_size_mb for core in self.cores.values())
        if total_allocated + max_size_mb > self.total_memory_limit_mb:
            return {
                'success': False,
                'error': 'Total memory limit would be exceeded',
                'current_allocated_mb': total_allocated,
                'requested_mb': max_size_mb,
                'limit_mb': self.total_memory_limit_mb
            }
        
        # Create storage path
        storage_path = self.persistence_path / core_id
        
        # Create core
        core = PersistentMemoryCore(
            core_id=core_id,
            name=name,
            memory_type=memory_type,
            max_size_mb=max_size_mb,
            storage_path=storage_path
        )
        
        # Add to manager
        self.cores[core_id] = core
        self.core_assignments[memory_type] = core_id
        self.metrics.cores_count += 1
        
        logger.info(f"Created memory core: {name} ({core_id})")
        
        return {
            'success': True,
            'core_id': core_id,
            'name': name,
            'memory_type': memory_type.value,
            'max_size_mb': max_size_mb
        }
    
    async def store_memory(self, key: str, data: Any, memory_type: MemoryType = MemoryType.WORKING,
                          priority: MemoryPriority = MemoryPriority.MEDIUM,
                          **kwargs) -> Dict[str, Any]:
        """Store data in the appropriate memory core"""
        
        # Find appropriate core
        core_id = self.core_assignments.get(memory_type)
        if not core_id or core_id not in self.cores:
            if self.auto_create_cores:
                # Create core for this memory type
                result = await self.create_core(f"{memory_type.value}_memory", memory_type)
                if not result['success']:
                    return result
                core_id = result['core_id']
            else:
                return {
                    'success': False,
                    'error': f'No core available for memory type: {memory_type.value}'
                }
        
        core = self.cores[core_id]
        result = await core.store(key, data, priority, **kwargs)
        
        if result['success']:
            self.metrics.total_entries += 1
            self._update_metrics()
        
        return result
    
    async def retrieve_memory(self, key: str, memory_type: MemoryType = None) -> Optional[Any]:
        """Retrieve data by key, optionally from specific memory type"""
        
        if memory_type:
            # Search in specific core
            core_id = self.core_assignments.get(memory_type)
            if core_id and core_id in self.cores:
                return await self.cores[core_id].retrieve(key)
        else:
            # Search across all cores
            for core in self.cores.values():
                data = await core.retrieve(key)
                if data is not None:
                    return data
        
        return None
    
    async def delete_memory(self, key: str, memory_type: MemoryType = None) -> Dict[str, Any]:
        """Delete data by key"""
        
        if memory_type:
            # Delete from specific core
            core_id = self.core_assignments.get(memory_type)
            if core_id and core_id in self.cores:
                result = await self.cores[core_id].delete(key)
                if result['success']:
                    self.metrics.total_entries -= 1
                    self._update_metrics()
                return result
        else:
            # Search and delete from any core
            for core in self.cores.values():
                result = await core.delete(key)
                if result['success']:
                    self.metrics.total_entries -= 1
                    self._update_metrics()
                    return result
        
        return {
            'success': False,
            'error': f'Key not found: {key}'
        }
    
    async def search_memories(self, query: Dict[str, Any], 
                            memory_types: List[MemoryType] = None) -> List[Dict[str, Any]]:
        """Search memories across cores"""
        results = []
        
        # Determine which cores to search
        cores_to_search = []
        if memory_types:
            for memory_type in memory_types:
                core_id = self.core_assignments.get(memory_type)
                if core_id and core_id in self.cores:
                    cores_to_search.append(self.cores[core_id])
        else:
            cores_to_search = list(self.cores.values())
        
        # Search each core
        for core in cores_to_search:
            core_results = await core.search(query)
            for result in core_results:
                result['core_id'] = core.core_id
                result['core_name'] = core.name
            results.extend(core_results)
        
        # Sort by importance and access count
        results.sort(key=lambda x: (x['importance_score'], x['access_count']), reverse=True)
        
        return results[:query.get('limit', 100)]
    
    async def save_mind_state(self, state_data: Dict[str, Any], 
                            checkpoint_name: str = None) -> Dict[str, Any]:
        """Save current mind state"""
        
        checkpoint_name = checkpoint_name or f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create checkpoint
        checkpoint = {
            'name': checkpoint_name,
            'timestamp': datetime.now().isoformat(),
            'state_data': state_data,
            'checksum': hashlib.sha256(json.dumps(state_data, sort_keys=True).encode()).hexdigest()
        }
        
        # Store in working memory
        await self.store_memory(
            key=f"mind_state_{checkpoint_name}",
            data=checkpoint,
            memory_type=MemoryType.WORKING,
            priority=MemoryPriority.CRITICAL,
            tags={'mind_state', 'checkpoint'},
            importance_score=1.0
        )
        
        # Update current state
        self.current_mind_state = state_data.copy()
        
        # Add to checkpoint history
        self.state_checkpoints.append(checkpoint)
        
        logger.info(f"Saved mind state checkpoint: {checkpoint_name}")
        
        return {
            'success': True,
            'checkpoint_name': checkpoint_name,
            'timestamp': checkpoint['timestamp'],
            'checksum': checkpoint['checksum']
        }
    
    async def load_mind_state(self, checkpoint_name: str = None) -> Optional[Dict[str, Any]]:
        """Load mind state from checkpoint"""
        
        if checkpoint_name:
            # Load specific checkpoint
            checkpoint = await self.retrieve_memory(f"mind_state_{checkpoint_name}", MemoryType.WORKING)
        else:
            # Load most recent checkpoint
            search_results = await self.search_memories(
                {'tags': ['mind_state', 'checkpoint']},
                [MemoryType.WORKING]
            )
            
            if not search_results:
                return None
            
            # Get most recent
            most_recent = max(search_results, key=lambda x: x['created_at'])
            checkpoint = await self.retrieve_memory(most_recent['key'], MemoryType.WORKING)
        
        if checkpoint:
            # Verify checksum
            calculated_checksum = hashlib.sha256(
                json.dumps(checkpoint['state_data'], sort_keys=True).encode()
            ).hexdigest()
            
            if calculated_checksum == checkpoint['checksum']:
                self.current_mind_state = checkpoint['state_data'].copy()
                logger.info(f"Loaded mind state checkpoint: {checkpoint['name']}")
                return checkpoint['state_data']
            else:
                logger.error(f"Checksum mismatch for checkpoint: {checkpoint['name']}")
        
        return None
    
    async def _load_current_mind_state(self):
        """Load the most recent mind state"""
        state_data = await self.load_mind_state()
        if state_data:
            logger.info("Current mind state loaded successfully")
        else:
            logger.info("No previous mind state found, starting fresh")
    
    async def _save_current_mind_state(self):
        """Save current mind state before shutdown"""
        if self.current_mind_state:
            await self.save_mind_state(self.current_mind_state, "shutdown_state")
    
    async def _maintenance_loop(self):
        """Background maintenance loop"""
        logger.info("Memory maintenance loop started")
        
        while self.is_running:
            try:
                await self._perform_maintenance()
                await asyncio.sleep(self.maintenance_interval)
            except Exception as e:
                logger.error(f"Error in maintenance loop: {str(e)}")
                await asyncio.sleep(60.0)
    
    async def _sync_loop(self):
        """Background synchronization loop"""
        logger.info("Memory sync loop started")
        
        while self.is_running:
            try:
                await self._sync_cores()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Error in sync loop: {str(e)}")
                await asyncio.sleep(30.0)
    
    async def _perform_maintenance(self):
        """Perform maintenance on all cores"""
        logger.info("Starting memory maintenance")
        
        for core in self.cores.values():
            # Update last maintenance time
            core.last_maintenance = datetime.now()
            
            # Perform cleanup if needed
            if core.current_size_mb > core.max_size_mb * 0.8:  # 80% threshold
                await core._cleanup_storage()
        
        # Update global metrics
        self._update_metrics()
        
        logger.info("Memory maintenance completed")
    
    async def _sync_cores(self):
        """Synchronize data between cores if needed"""
        # Placeholder for cross-core synchronization
        pass
    
    def _update_metrics(self):
        """Update global memory metrics"""
        self.metrics.total_entries = sum(core.entry_count for core in self.cores.values())
        self.metrics.total_size_mb = sum(core.current_size_mb for core in self.cores.values())
        self.metrics.cores_count = len(self.cores)
        
        # Calculate average cache hit rate
        total_accesses = sum(core.total_accesses for core in self.cores.values())
        total_hits = sum(core.cache_hits for core in self.cores.values())
        self.metrics.cache_hit_rate = total_hits / max(total_accesses, 1)
        
        # Calculate memory efficiency
        total_allocated = sum(core.max_size_mb for core in self.cores.values())
        self.metrics.memory_efficiency = self.metrics.total_size_mb / max(total_allocated, 1)
    
    # Public interface methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get memory manager status"""
        return {
            'manager_id': self.manager_id,
            'is_running': self.is_running,
            'metrics': asdict(self.metrics),
            'cores': {core_id: core.get_status() for core_id, core in self.cores.items()},
            'total_memory_limit_mb': self.total_memory_limit_mb,
            'current_mind_state_size': len(self.current_mind_state),
            'checkpoints_count': len(self.state_checkpoints)
        }
    
    def get_cores(self) -> List[Dict[str, Any]]:
        """Get information about all cores"""
        return [core.get_status() for core in self.cores.values()]
    
    def get_mind_state(self) -> Dict[str, Any]:
        """Get current mind state"""
        return self.current_mind_state.copy()
    
    def get_checkpoints(self) -> List[Dict[str, Any]]:
        """Get list of available checkpoints"""
        return [
            {
                'name': cp['name'],
                'timestamp': cp['timestamp'],
                'checksum': cp['checksum']
            }
            for cp in self.state_checkpoints
        ]
    
    async def _save_persistent_state(self):
        """Save manager state to disk"""
        state_data = {
            'manager_id': self.manager_id,
            'metrics': asdict(self.metrics),
            'core_assignments': {k.value: v for k, v in self.core_assignments.items()},
            'current_mind_state': self.current_mind_state,
            'checkpoints': list(self.state_checkpoints),
            'saved_at': datetime.now().isoformat()
        }
        
        state_file = self.persistence_path / 'manager_state.json'
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2, default=str)
    
    async def _load_persistent_state(self):
        """Load manager state from disk"""
        state_file = self.persistence_path / 'manager_state.json'
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Restore metrics
                if 'metrics' in state_data:
                    self.metrics = MemoryMetrics(**state_data['metrics'])
                
                # Restore core assignments
                if 'core_assignments' in state_data:
                    self.core_assignments = {
                        MemoryType(k): v for k, v in state_data['core_assignments'].items()
                    }
                
                # Restore mind state
                self.current_mind_state = state_data.get('current_mind_state', {})
                
                # Restore checkpoints
                if 'checkpoints' in state_data:
                    self.state_checkpoints.extend(state_data['checkpoints'])
                
                # Recreate cores
                for memory_type, core_id in self.core_assignments.items():
                    storage_path = self.persistence_path / core_id
                    if storage_path.exists():
                        core = PersistentMemoryCore(
                            core_id=core_id,
                            name=f"{memory_type.value}_memory",
                            memory_type=memory_type,
                            storage_path=storage_path
                        )
                        self.cores[core_id] = core
                
                logger.info(f"Loaded persistent state for memory manager {self.manager_id}")
                
            except Exception as e:
                logger.error(f"Error loading persistent state: {str(e)}")

# Global memory manager instance
memory_manager = PersistentMemoryManager()

# Convenience functions
async def start_memory_cores() -> Dict[str, Any]:
    """Start the memory manager"""
    return await memory_manager.start()

async def stop_memory_cores() -> Dict[str, Any]:
    """Stop the memory manager"""
    return await memory_manager.stop()

def get_memory_status() -> Dict[str, Any]:
    """Get memory manager status"""
    return memory_manager.get_status()

async def store_memory(key: str, data: Any, memory_type: MemoryType = MemoryType.WORKING,
                      priority: MemoryPriority = MemoryPriority.MEDIUM, **kwargs) -> Dict[str, Any]:
    """Store data in memory"""
    return await memory_manager.store_memory(key, data, memory_type, priority, **kwargs)

async def retrieve_memory(key: str, memory_type: MemoryType = None) -> Optional[Any]:
    """Retrieve data from memory"""
    return await memory_manager.retrieve_memory(key, memory_type)

async def delete_memory(key: str, memory_type: MemoryType = None) -> Dict[str, Any]:
    """Delete data from memory"""
    return await memory_manager.delete_memory(key, memory_type)

async def search_memories(query: Dict[str, Any], memory_types: List[MemoryType] = None) -> List[Dict[str, Any]]:
    """Search memories"""
    return await memory_manager.search_memories(query, memory_types)

async def save_mind_state(state_data: Dict[str, Any], checkpoint_name: str = None) -> Dict[str, Any]:
    """Save current mind state"""
    return await memory_manager.save_mind_state(state_data, checkpoint_name)

async def load_mind_state(checkpoint_name: str = None) -> Optional[Dict[str, Any]]:
    """Load mind state"""
    return await memory_manager.load_mind_state(checkpoint_name)

def get_current_mind_state() -> Dict[str, Any]:
    """Get current mind state"""
    return memory_manager.get_mind_state()

