"""
DEVmind Passive Task Manager
Background task processing that continues without explicit prompts

This module implements passive task management that allows DEVmind to continue
working on tasks, optimizing itself, learning from errors, and planning future
activities even when not actively prompted by users. Like human daydreaming
and background thinking, this enables continuous cognitive activity.

Author: Manus AI
Version: 1.0.0
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import os
import pickle
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskType(Enum):
    """Types of passive tasks"""
    OPTIMIZATION = "optimization"
    LEARNING = "learning"
    PLANNING = "planning"
    EXPLORATION = "exploration"
    MAINTENANCE = "maintenance"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    REFLECTION = "reflection"
    PREDICTION = "prediction"
    HEALING = "healing"

class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"      # Must be done immediately
    HIGH = "high"             # Should be done soon
    MEDIUM = "medium"         # Normal priority
    LOW = "low"              # Can be delayed
    BACKGROUND = "background" # Lowest priority, fill time

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"

@dataclass
class PassiveTask:
    """Represents a passive task"""
    id: str
    name: str
    description: str
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_duration: float  # seconds
    actual_duration: Optional[float]
    progress: float  # 0.0-1.0
    dependencies: List[str]  # Task IDs this task depends on
    metadata: Dict[str, Any]
    result: Optional[Any]
    error: Optional[str]
    retry_count: int
    max_retries: int
    last_heartbeat: Optional[datetime]
    resource_requirements: Dict[str, Any]
    tags: Set[str]

@dataclass
class TaskMetrics:
    """Metrics for task management"""
    total_tasks_created: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    average_completion_time: float = 0.0
    success_rate: float = 1.0
    active_tasks: int = 0
    queued_tasks: int = 0
    background_cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    optimization_cycles: int = 0
    learning_sessions: int = 0
    creative_outputs: int = 0

class TaskExecutor:
    """Executes individual tasks"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.is_running = False
        self.start_time = None
        self.last_progress_update = None
    
    async def execute(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute a passive task"""
        self.is_running = True
        self.start_time = time.time()
        task.started_at = datetime.now()
        task.status = TaskStatus.RUNNING
        
        try:
            # Execute based on task type
            if task.task_type == TaskType.OPTIMIZATION:
                result = await self._execute_optimization_task(task)
            elif task.task_type == TaskType.LEARNING:
                result = await self._execute_learning_task(task)
            elif task.task_type == TaskType.PLANNING:
                result = await self._execute_planning_task(task)
            elif task.task_type == TaskType.EXPLORATION:
                result = await self._execute_exploration_task(task)
            elif task.task_type == TaskType.MAINTENANCE:
                result = await self._execute_maintenance_task(task)
            elif task.task_type == TaskType.CREATIVE:
                result = await self._execute_creative_task(task)
            elif task.task_type == TaskType.ANALYSIS:
                result = await self._execute_analysis_task(task)
            elif task.task_type == TaskType.REFLECTION:
                result = await self._execute_reflection_task(task)
            elif task.task_type == TaskType.PREDICTION:
                result = await self._execute_prediction_task(task)
            elif task.task_type == TaskType.HEALING:
                result = await self._execute_healing_task(task)
            else:
                result = await self._execute_generic_task(task)
            
            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.actual_duration = time.time() - self.start_time
            task.progress = 1.0
            task.result = result
            
            return {
                'success': True,
                'task_id': task.id,
                'result': result,
                'duration': task.actual_duration
            }
            
        except Exception as e:
            # Mark as failed
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.actual_duration = time.time() - self.start_time
            
            logger.error(f"Task {task.id} failed: {str(e)}")
            
            return {
                'success': False,
                'task_id': task.id,
                'error': str(e),
                'duration': task.actual_duration
            }
        
        finally:
            self.is_running = False
    
    async def _execute_optimization_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute an optimization task"""
        optimization_type = task.metadata.get('optimization_type', 'general')
        
        if optimization_type == 'code_optimization':
            return await self._optimize_code()
        elif optimization_type == 'memory_optimization':
            return await self._optimize_memory()
        elif optimization_type == 'performance_optimization':
            return await self._optimize_performance()
        elif optimization_type == 'algorithm_optimization':
            return await self._optimize_algorithms()
        else:
            return await self._general_optimization()
    
    async def _execute_learning_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute a learning task"""
        learning_type = task.metadata.get('learning_type', 'pattern_recognition')
        
        if learning_type == 'error_analysis':
            return await self._learn_from_errors()
        elif learning_type == 'pattern_recognition':
            return await self._learn_patterns()
        elif learning_type == 'user_behavior':
            return await self._learn_user_behavior()
        elif learning_type == 'system_adaptation':
            return await self._learn_system_adaptation()
        else:
            return await self._general_learning()
    
    async def _execute_planning_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute a planning task"""
        planning_type = task.metadata.get('planning_type', 'future_tasks')
        
        if planning_type == 'future_tasks':
            return await self._plan_future_tasks()
        elif planning_type == 'resource_allocation':
            return await self._plan_resource_allocation()
        elif planning_type == 'goal_setting':
            return await self._plan_goals()
        elif planning_type == 'contingency_planning':
            return await self._plan_contingencies()
        else:
            return await self._general_planning()
    
    async def _execute_exploration_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute an exploration task"""
        exploration_type = task.metadata.get('exploration_type', 'data_discovery')
        
        if exploration_type == 'file_exploration':
            return await self._explore_files()
        elif exploration_type == 'data_discovery':
            return await self._discover_data_patterns()
        elif exploration_type == 'capability_testing':
            return await self._test_capabilities()
        elif exploration_type == 'environment_scanning':
            return await self._scan_environment()
        else:
            return await self._general_exploration()
    
    async def _execute_maintenance_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute a maintenance task"""
        maintenance_type = task.metadata.get('maintenance_type', 'cleanup')
        
        if maintenance_type == 'memory_cleanup':
            return await self._cleanup_memory()
        elif maintenance_type == 'log_rotation':
            return await self._rotate_logs()
        elif maintenance_type == 'cache_optimization':
            return await self._optimize_cache()
        elif maintenance_type == 'health_check':
            return await self._perform_health_check()
        else:
            return await self._general_maintenance()
    
    async def _execute_creative_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute a creative task"""
        creative_type = task.metadata.get('creative_type', 'idea_generation')
        
        if creative_type == 'idea_generation':
            return await self._generate_ideas()
        elif creative_type == 'solution_brainstorming':
            return await self._brainstorm_solutions()
        elif creative_type == 'innovation_exploration':
            return await self._explore_innovations()
        elif creative_type == 'artistic_creation':
            return await self._create_art()
        else:
            return await self._general_creativity()
    
    async def _execute_analysis_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute an analysis task"""
        analysis_type = task.metadata.get('analysis_type', 'data_analysis')
        
        if analysis_type == 'performance_analysis':
            return await self._analyze_performance()
        elif analysis_type == 'trend_analysis':
            return await self._analyze_trends()
        elif analysis_type == 'error_analysis':
            return await self._analyze_errors()
        elif analysis_type == 'usage_analysis':
            return await self._analyze_usage()
        else:
            return await self._general_analysis()
    
    async def _execute_reflection_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute a reflection task"""
        reflection_type = task.metadata.get('reflection_type', 'self_reflection')
        
        if reflection_type == 'self_reflection':
            return await self._perform_self_reflection()
        elif reflection_type == 'goal_reflection':
            return await self._reflect_on_goals()
        elif reflection_type == 'performance_reflection':
            return await self._reflect_on_performance()
        elif reflection_type == 'learning_reflection':
            return await self._reflect_on_learning()
        else:
            return await self._general_reflection()
    
    async def _execute_prediction_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute a prediction task"""
        prediction_type = task.metadata.get('prediction_type', 'future_needs')
        
        if prediction_type == 'user_needs':
            return await self._predict_user_needs()
        elif prediction_type == 'system_requirements':
            return await self._predict_system_requirements()
        elif prediction_type == 'failure_prediction':
            return await self._predict_failures()
        elif prediction_type == 'trend_prediction':
            return await self._predict_trends()
        else:
            return await self._general_prediction()
    
    async def _execute_healing_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute a healing/recovery task"""
        healing_type = task.metadata.get('healing_type', 'error_recovery')
        
        if healing_type == 'error_recovery':
            return await self._recover_from_errors()
        elif healing_type == 'system_repair':
            return await self._repair_system()
        elif healing_type == 'data_recovery':
            return await self._recover_data()
        elif healing_type == 'performance_recovery':
            return await self._recover_performance()
        else:
            return await self._general_healing()
    
    async def _execute_generic_task(self, task: PassiveTask) -> Dict[str, Any]:
        """Execute a generic task"""
        # Simulate task execution
        await asyncio.sleep(random.uniform(0.1, 2.0))
        
        return {
            'task_type': task.task_type.value,
            'execution_time': time.time() - self.start_time,
            'result': f"Generic task {task.name} completed successfully"
        }
    
    # Placeholder implementations for specific task types
    
    async def _optimize_code(self) -> Dict[str, Any]:
        """Optimize code performance"""
        await asyncio.sleep(random.uniform(1.0, 3.0))
        return {
            'optimization_type': 'code',
            'improvements': ['reduced complexity', 'improved readability', 'better performance'],
            'performance_gain': random.uniform(5, 25)
        }
    
    async def _optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage"""
        await asyncio.sleep(random.uniform(0.5, 2.0))
        return {
            'optimization_type': 'memory',
            'memory_freed_mb': random.uniform(10, 100),
            'fragmentation_reduced': random.uniform(5, 20)
        }
    
    async def _optimize_performance(self) -> Dict[str, Any]:
        """Optimize overall performance"""
        await asyncio.sleep(random.uniform(1.0, 4.0))
        return {
            'optimization_type': 'performance',
            'speed_improvement': random.uniform(10, 40),
            'efficiency_gain': random.uniform(5, 30)
        }
    
    async def _optimize_algorithms(self) -> Dict[str, Any]:
        """Optimize algorithms"""
        await asyncio.sleep(random.uniform(2.0, 5.0))
        return {
            'optimization_type': 'algorithms',
            'algorithms_optimized': random.randint(1, 5),
            'complexity_reduction': random.uniform(10, 50)
        }
    
    async def _general_optimization(self) -> Dict[str, Any]:
        """General optimization"""
        await asyncio.sleep(random.uniform(0.5, 2.0))
        return {
            'optimization_type': 'general',
            'areas_optimized': ['performance', 'memory', 'efficiency'],
            'overall_improvement': random.uniform(5, 20)
        }
    
    async def _learn_from_errors(self) -> Dict[str, Any]:
        """Learn from past errors"""
        await asyncio.sleep(random.uniform(1.0, 3.0))
        return {
            'learning_type': 'error_analysis',
            'errors_analyzed': random.randint(5, 20),
            'patterns_identified': random.randint(1, 5),
            'prevention_strategies': ['better validation', 'improved error handling', 'early detection']
        }
    
    async def _learn_patterns(self) -> Dict[str, Any]:
        """Learn patterns from data"""
        await asyncio.sleep(random.uniform(2.0, 4.0))
        return {
            'learning_type': 'pattern_recognition',
            'patterns_discovered': random.randint(3, 10),
            'confidence_level': random.uniform(0.7, 0.95),
            'applications': ['prediction', 'optimization', 'automation']
        }
    
    async def _learn_user_behavior(self) -> Dict[str, Any]:
        """Learn user behavior patterns"""
        await asyncio.sleep(random.uniform(1.5, 3.5))
        return {
            'learning_type': 'user_behavior',
            'behavior_patterns': random.randint(2, 8),
            'preferences_identified': random.randint(1, 5),
            'adaptation_suggestions': ['UI improvements', 'workflow optimization', 'personalization']
        }
    
    async def _learn_system_adaptation(self) -> Dict[str, Any]:
        """Learn system adaptation strategies"""
        await asyncio.sleep(random.uniform(1.0, 2.5))
        return {
            'learning_type': 'system_adaptation',
            'adaptation_strategies': random.randint(2, 6),
            'effectiveness_score': random.uniform(0.6, 0.9),
            'implementation_priority': ['high', 'medium', 'low'][random.randint(0, 2)]
        }
    
    async def _general_learning(self) -> Dict[str, Any]:
        """General learning"""
        await asyncio.sleep(random.uniform(1.0, 3.0))
        return {
            'learning_type': 'general',
            'knowledge_gained': random.randint(1, 10),
            'insights_generated': random.randint(1, 5),
            'applications': ['improvement', 'optimization', 'innovation']
        }
    
    async def _plan_future_tasks(self) -> Dict[str, Any]:
        """Plan future tasks"""
        await asyncio.sleep(random.uniform(1.0, 2.0))
        return {
            'planning_type': 'future_tasks',
            'tasks_planned': random.randint(5, 15),
            'time_horizon': 'next 24 hours',
            'priority_distribution': {'high': 20, 'medium': 60, 'low': 20}
        }
    
    async def _plan_resource_allocation(self) -> Dict[str, Any]:
        """Plan resource allocation"""
        await asyncio.sleep(random.uniform(0.5, 1.5))
        return {
            'planning_type': 'resource_allocation',
            'resources_planned': ['CPU', 'memory', 'storage', 'network'],
            'efficiency_improvement': random.uniform(10, 30),
            'cost_reduction': random.uniform(5, 20)
        }
    
    async def _plan_goals(self) -> Dict[str, Any]:
        """Plan goals"""
        await asyncio.sleep(random.uniform(1.5, 3.0))
        return {
            'planning_type': 'goal_setting',
            'goals_defined': random.randint(3, 8),
            'time_frame': 'next week',
            'success_metrics': ['performance', 'efficiency', 'user_satisfaction']
        }
    
    async def _plan_contingencies(self) -> Dict[str, Any]:
        """Plan contingencies"""
        await asyncio.sleep(random.uniform(1.0, 2.5))
        return {
            'planning_type': 'contingency',
            'scenarios_planned': random.randint(3, 7),
            'risk_mitigation': random.randint(2, 5),
            'response_strategies': ['immediate', 'short_term', 'long_term']
        }
    
    async def _general_planning(self) -> Dict[str, Any]:
        """General planning"""
        await asyncio.sleep(random.uniform(1.0, 2.0))
        return {
            'planning_type': 'general',
            'plans_created': random.randint(2, 6),
            'scope': 'operational',
            'implementation_timeline': 'next 48 hours'
        }

class PassiveTaskManager:
    """
    The Passive Task Manager - Continuous background processing
    
    This manager handles tasks that run continuously in the background,
    allowing DEVmind to optimize itself, learn from experience, plan
    future activities, and maintain its systems without explicit prompts.
    """
    
    def __init__(self, manager_id: str = None):
        self.manager_id = manager_id or f"ptm_{uuid.uuid4().hex[:8]}"
        self.is_running = False
        self.metrics = TaskMetrics()
        
        # Task storage
        self.tasks: Dict[str, PassiveTask] = {}
        self.task_queue = asyncio.Queue()
        self.priority_queues = {
            TaskPriority.CRITICAL: asyncio.Queue(),
            TaskPriority.HIGH: asyncio.Queue(),
            TaskPriority.MEDIUM: asyncio.Queue(),
            TaskPriority.LOW: asyncio.Queue(),
            TaskPriority.BACKGROUND: asyncio.Queue()
        }
        
        # Execution management
        self.max_concurrent_tasks = 5
        self.active_executors: Dict[str, TaskExecutor] = {}
        self.executor_pool = ThreadPoolExecutor(max_workers=10)
        
        # Task generation
        self.task_generators: List[Callable] = []
        self.generation_interval = 30.0  # seconds
        self.last_generation = None
        
        # Scheduling
        self.scheduler_task = None
        self.generator_task = None
        self.monitor_task = None
        
        # Configuration
        self.cpu_limit = 0.3  # Max 30% CPU usage
        self.memory_limit_mb = 500  # Max 500MB memory
        self.task_timeout = 300  # 5 minutes default timeout
        
        # Persistence
        self.persistence_path = Path(f"/tmp/devmind_ptm_{self.manager_id}")
        self.persistence_path.mkdir(exist_ok=True)
        
        # Built-in task generators
        self._register_builtin_generators()
        
        logger.info(f"Passive Task Manager initialized: {self.manager_id}")
    
    async def start(self) -> Dict[str, Any]:
        """Start the passive task manager"""
        if self.is_running:
            return {
                'success': False,
                'error': 'Passive task manager is already running',
                'manager_id': self.manager_id
            }
        
        logger.info(f"Starting Passive Task Manager: {self.manager_id}")
        
        # Load persistent state
        await self._load_persistent_state()
        
        # Start background tasks
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.generator_task = asyncio.create_task(self._generator_loop())
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
        # Generate initial tasks
        await self._generate_initial_tasks()
        
        return {
            'success': True,
            'manager_id': self.manager_id,
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'generation_interval': self.generation_interval,
            'initial_tasks_generated': len(self.tasks)
        }
    
    async def stop(self) -> Dict[str, Any]:
        """Stop the passive task manager"""
        if not self.is_running:
            return {
                'success': False,
                'error': 'Passive task manager is not running',
                'manager_id': self.manager_id
            }
        
        logger.info(f"Stopping Passive Task Manager: {self.manager_id}")
        
        # Stop background tasks
        self.is_running = False
        
        # Cancel running tasks
        for task_id, executor in self.active_executors.items():
            if executor.is_running:
                logger.info(f"Cancelling active task: {task_id}")
                # Mark task as cancelled
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.CANCELLED
        
        # Cancel background loops
        if self.scheduler_task:
            self.scheduler_task.cancel()
        if self.generator_task:
            self.generator_task.cancel()
        if self.monitor_task:
            self.monitor_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.sleep(1.0)
        
        # Save persistent state
        await self._save_persistent_state()
        
        return {
            'success': True,
            'manager_id': self.manager_id,
            'final_metrics': asdict(self.metrics),
            'tasks_completed': self.metrics.total_tasks_completed,
            'tasks_cancelled': len([t for t in self.tasks.values() if t.status == TaskStatus.CANCELLED])
        }
    
    async def _scheduler_loop(self):
        """Main scheduler loop that manages task execution"""
        logger.info("Scheduler loop started")
        
        while self.is_running:
            try:
                # Check resource usage
                if await self._check_resource_limits():
                    # Schedule tasks based on priority
                    await self._schedule_next_tasks()
                
                # Clean up completed tasks
                await self._cleanup_completed_tasks()
                
                # Update metrics
                await self._update_metrics()
                
                # Sleep briefly
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(5.0)
    
    async def _generator_loop(self):
        """Loop that generates new tasks automatically"""
        logger.info("Generator loop started")
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Check if it's time to generate new tasks
                if (not self.last_generation or 
                    (current_time - self.last_generation).total_seconds() >= self.generation_interval):
                    
                    await self._generate_automatic_tasks()
                    self.last_generation = current_time
                
                # Sleep until next generation cycle
                await asyncio.sleep(self.generation_interval / 4)
                
            except Exception as e:
                logger.error(f"Error in generator loop: {str(e)}")
                await asyncio.sleep(10.0)
    
    async def _monitor_loop(self):
        """Loop that monitors task execution and system health"""
        logger.info("Monitor loop started")
        
        while self.is_running:
            try:
                # Monitor active tasks
                await self._monitor_active_tasks()
                
                # Check for stuck tasks
                await self._check_stuck_tasks()
                
                # Monitor system resources
                await self._monitor_system_resources()
                
                # Sleep briefly
                await asyncio.sleep(5.0)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {str(e)}")
                await asyncio.sleep(10.0)
    
    async def _schedule_next_tasks(self):
        """Schedule the next tasks for execution"""
        # Check how many tasks we can start
        available_slots = self.max_concurrent_tasks - len(self.active_executors)
        
        if available_slots <= 0:
            return
        
        # Get tasks from priority queues
        tasks_to_start = []
        
        # Check each priority level
        for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, 
                        TaskPriority.MEDIUM, TaskPriority.LOW, TaskPriority.BACKGROUND]:
            
            queue = self.priority_queues[priority]
            
            while len(tasks_to_start) < available_slots and not queue.empty():
                try:
                    task_id = await asyncio.wait_for(queue.get(), timeout=0.1)
                    if task_id in self.tasks:
                        task = self.tasks[task_id]
                        if task.status == TaskStatus.QUEUED:
                            tasks_to_start.append(task)
                except asyncio.TimeoutError:
                    break
        
        # Start selected tasks
        for task in tasks_to_start:
            await self._start_task_execution(task)
    
    async def _start_task_execution(self, task: PassiveTask):
        """Start executing a task"""
        executor = TaskExecutor(task.id)
        self.active_executors[task.id] = executor
        
        # Start execution in background
        asyncio.create_task(self._execute_task_with_cleanup(task, executor))
        
        logger.info(f"Started task execution: {task.name} ({task.id})")
    
    async def _execute_task_with_cleanup(self, task: PassiveTask, executor: TaskExecutor):
        """Execute a task and clean up afterwards"""
        try:
            result = await executor.execute(task)
            
            # Update metrics
            if result['success']:
                self.metrics.total_tasks_completed += 1
            else:
                self.metrics.total_tasks_failed += 1
            
        except Exception as e:
            logger.error(f"Task execution error: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.metrics.total_tasks_failed += 1
        
        finally:
            # Clean up executor
            if task.id in self.active_executors:
                del self.active_executors[task.id]
    
    async def _generate_automatic_tasks(self):
        """Generate tasks automatically based on current conditions"""
        generated_tasks = []
        
        # Run all registered task generators
        for generator in self.task_generators:
            try:
                if asyncio.iscoroutinefunction(generator):
                    new_tasks = await generator()
                else:
                    new_tasks = generator()
                
                if new_tasks:
                    generated_tasks.extend(new_tasks)
                    
            except Exception as e:
                logger.error(f"Error in task generator: {str(e)}")
        
        # Add generated tasks to the system
        for task_data in generated_tasks:
            await self.create_task(**task_data)
        
        if generated_tasks:
            logger.info(f"Generated {len(generated_tasks)} automatic tasks")
    
    async def _generate_initial_tasks(self):
        """Generate initial set of tasks when starting"""
        initial_tasks = [
            {
                'name': 'System Health Check',
                'description': 'Perform initial system health check',
                'task_type': TaskType.MAINTENANCE,
                'priority': TaskPriority.HIGH,
                'estimated_duration': 30.0,
                'metadata': {'maintenance_type': 'health_check'}
            },
            {
                'name': 'Memory Optimization',
                'description': 'Optimize memory usage',
                'task_type': TaskType.OPTIMIZATION,
                'priority': TaskPriority.MEDIUM,
                'estimated_duration': 60.0,
                'metadata': {'optimization_type': 'memory_optimization'}
            },
            {
                'name': 'Error Analysis',
                'description': 'Analyze recent errors for learning',
                'task_type': TaskType.LEARNING,
                'priority': TaskPriority.MEDIUM,
                'estimated_duration': 120.0,
                'metadata': {'learning_type': 'error_analysis'}
            },
            {
                'name': 'Future Task Planning',
                'description': 'Plan tasks for the next period',
                'task_type': TaskType.PLANNING,
                'priority': TaskPriority.LOW,
                'estimated_duration': 90.0,
                'metadata': {'planning_type': 'future_tasks'}
            }
        ]
        
        for task_data in initial_tasks:
            await self.create_task(**task_data)
    
    def _register_builtin_generators(self):
        """Register built-in task generators"""
        self.task_generators.extend([
            self._generate_optimization_tasks,
            self._generate_learning_tasks,
            self._generate_maintenance_tasks,
            self._generate_exploration_tasks,
            self._generate_creative_tasks
        ])
    
    async def _generate_optimization_tasks(self) -> List[Dict[str, Any]]:
        """Generate optimization tasks"""
        tasks = []
        
        # Generate optimization tasks based on system state
        if self.metrics.success_rate < 0.8:
            tasks.append({
                'name': 'Performance Optimization',
                'description': 'Optimize performance due to low success rate',
                'task_type': TaskType.OPTIMIZATION,
                'priority': TaskPriority.HIGH,
                'estimated_duration': 180.0,
                'metadata': {'optimization_type': 'performance_optimization'}
            })
        
        if random.random() < 0.3:  # 30% chance
            tasks.append({
                'name': 'Algorithm Optimization',
                'description': 'Optimize algorithms for better efficiency',
                'task_type': TaskType.OPTIMIZATION,
                'priority': TaskPriority.MEDIUM,
                'estimated_duration': 240.0,
                'metadata': {'optimization_type': 'algorithm_optimization'}
            })
        
        return tasks
    
    async def _generate_learning_tasks(self) -> List[Dict[str, Any]]:
        """Generate learning tasks"""
        tasks = []
        
        # Generate learning tasks based on activity
        if self.metrics.total_tasks_failed > 5:
            tasks.append({
                'name': 'Error Pattern Learning',
                'description': 'Learn from recent error patterns',
                'task_type': TaskType.LEARNING,
                'priority': TaskPriority.MEDIUM,
                'estimated_duration': 150.0,
                'metadata': {'learning_type': 'error_analysis'}
            })
        
        if random.random() < 0.4:  # 40% chance
            tasks.append({
                'name': 'Pattern Recognition',
                'description': 'Identify new patterns in data',
                'task_type': TaskType.LEARNING,
                'priority': TaskPriority.LOW,
                'estimated_duration': 200.0,
                'metadata': {'learning_type': 'pattern_recognition'}
            })
        
        return tasks
    
    async def _generate_maintenance_tasks(self) -> List[Dict[str, Any]]:
        """Generate maintenance tasks"""
        tasks = []
        
        # Regular maintenance tasks
        if random.random() < 0.2:  # 20% chance
            tasks.append({
                'name': 'Memory Cleanup',
                'description': 'Clean up unused memory',
                'task_type': TaskType.MAINTENANCE,
                'priority': TaskPriority.BACKGROUND,
                'estimated_duration': 60.0,
                'metadata': {'maintenance_type': 'memory_cleanup'}
            })
        
        if random.random() < 0.1:  # 10% chance
            tasks.append({
                'name': 'Cache Optimization',
                'description': 'Optimize cache performance',
                'task_type': TaskType.MAINTENANCE,
                'priority': TaskPriority.LOW,
                'estimated_duration': 90.0,
                'metadata': {'maintenance_type': 'cache_optimization'}
            })
        
        return tasks
    
    async def _generate_exploration_tasks(self) -> List[Dict[str, Any]]:
        """Generate exploration tasks"""
        tasks = []
        
        # Exploration tasks for discovery
        if random.random() < 0.25:  # 25% chance
            tasks.append({
                'name': 'Environment Scanning',
                'description': 'Scan environment for changes',
                'task_type': TaskType.EXPLORATION,
                'priority': TaskPriority.LOW,
                'estimated_duration': 120.0,
                'metadata': {'exploration_type': 'environment_scanning'}
            })
        
        if random.random() < 0.15:  # 15% chance
            tasks.append({
                'name': 'Capability Testing',
                'description': 'Test new capabilities',
                'task_type': TaskType.EXPLORATION,
                'priority': TaskPriority.BACKGROUND,
                'estimated_duration': 180.0,
                'metadata': {'exploration_type': 'capability_testing'}
            })
        
        return tasks
    
    async def _generate_creative_tasks(self) -> List[Dict[str, Any]]:
        """Generate creative tasks"""
        tasks = []
        
        # Creative tasks for innovation
        if random.random() < 0.2:  # 20% chance
            tasks.append({
                'name': 'Idea Generation',
                'description': 'Generate new ideas for improvement',
                'task_type': TaskType.CREATIVE,
                'priority': TaskPriority.BACKGROUND,
                'estimated_duration': 300.0,
                'metadata': {'creative_type': 'idea_generation'}
            })
        
        if random.random() < 0.1:  # 10% chance
            tasks.append({
                'name': 'Solution Brainstorming',
                'description': 'Brainstorm solutions to known problems',
                'task_type': TaskType.CREATIVE,
                'priority': TaskPriority.LOW,
                'estimated_duration': 240.0,
                'metadata': {'creative_type': 'solution_brainstorming'}
            })
        
        return tasks
    
    # Public interface methods
    
    async def create_task(self, name: str, description: str, task_type: TaskType,
                         priority: TaskPriority = TaskPriority.MEDIUM,
                         estimated_duration: float = 60.0,
                         dependencies: List[str] = None,
                         metadata: Dict[str, Any] = None,
                         tags: Set[str] = None) -> Dict[str, Any]:
        """Create a new passive task"""
        
        task = PassiveTask(
            id=uuid.uuid4().hex[:8],
            name=name,
            description=description,
            task_type=task_type,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            estimated_duration=estimated_duration,
            actual_duration=None,
            progress=0.0,
            dependencies=dependencies or [],
            metadata=metadata or {},
            result=None,
            error=None,
            retry_count=0,
            max_retries=3,
            last_heartbeat=None,
            resource_requirements={},
            tags=tags or set()
        )
        
        # Store task
        self.tasks[task.id] = task
        self.metrics.total_tasks_created += 1
        
        # Queue task if dependencies are met
        if await self._check_dependencies(task):
            await self._queue_task(task)
        
        logger.info(f"Created task: {name} ({task.id})")
        
        return {
            'success': True,
            'task_id': task.id,
            'name': name,
            'priority': priority.value,
            'estimated_duration': estimated_duration
        }
    
    async def _queue_task(self, task: PassiveTask):
        """Queue a task for execution"""
        task.status = TaskStatus.QUEUED
        await self.priority_queues[task.priority].put(task.id)
        self.metrics.queued_tasks += 1
    
    async def _check_dependencies(self, task: PassiveTask) -> bool:
        """Check if task dependencies are satisfied"""
        for dep_id in task.dependencies:
            if dep_id in self.tasks:
                dep_task = self.tasks[dep_id]
                if dep_task.status != TaskStatus.COMPLETED:
                    return False
            else:
                # Dependency doesn't exist
                return False
        return True
    
    async def _check_resource_limits(self) -> bool:
        """Check if we're within resource limits"""
        # Simple resource check (placeholder)
        active_count = len(self.active_executors)
        return active_count < self.max_concurrent_tasks
    
    async def _cleanup_completed_tasks(self):
        """Clean up completed tasks"""
        completed_tasks = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            and task.completed_at
            and (datetime.now() - task.completed_at).total_seconds() > 3600  # 1 hour old
        ]
        
        for task_id in completed_tasks:
            # Archive task
            task = self.tasks[task_id]
            task.status = TaskStatus.ARCHIVED
            # Could move to separate archive storage
    
    async def _update_metrics(self):
        """Update task manager metrics"""
        # Update active and queued task counts
        self.metrics.active_tasks = len(self.active_executors)
        
        queued_count = 0
        for queue in self.priority_queues.values():
            queued_count += queue.qsize()
        self.metrics.queued_tasks = queued_count
        
        # Update success rate
        total_finished = self.metrics.total_tasks_completed + self.metrics.total_tasks_failed
        if total_finished > 0:
            self.metrics.success_rate = self.metrics.total_tasks_completed / total_finished
        
        # Update average completion time
        completed_tasks = [t for t in self.tasks.values() 
                          if t.status == TaskStatus.COMPLETED and t.actual_duration]
        if completed_tasks:
            total_duration = sum(t.actual_duration for t in completed_tasks)
            self.metrics.average_completion_time = total_duration / len(completed_tasks)
    
    async def _monitor_active_tasks(self):
        """Monitor actively running tasks"""
        current_time = datetime.now()
        
        for task_id, executor in list(self.active_executors.items()):
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                # Update heartbeat
                task.last_heartbeat = current_time
                
                # Check for timeout
                if (task.started_at and 
                    (current_time - task.started_at).total_seconds() > self.task_timeout):
                    
                    logger.warning(f"Task timeout: {task.name} ({task_id})")
                    task.status = TaskStatus.FAILED
                    task.error = "Task timeout"
                    
                    # Remove from active executors
                    del self.active_executors[task_id]
    
    async def _check_stuck_tasks(self):
        """Check for stuck tasks and handle them"""
        current_time = datetime.now()
        
        for task in self.tasks.values():
            if (task.status == TaskStatus.RUNNING and 
                task.last_heartbeat and
                (current_time - task.last_heartbeat).total_seconds() > 300):  # 5 minutes
                
                logger.warning(f"Stuck task detected: {task.name} ({task.id})")
                
                # Try to restart task if retries available
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    await self._queue_task(task)
                else:
                    task.status = TaskStatus.FAILED
                    task.error = "Task stuck - max retries exceeded"
    
    async def _monitor_system_resources(self):
        """Monitor system resource usage"""
        # Placeholder for resource monitoring
        # In a real implementation, this would check CPU, memory, etc.
        self.metrics.background_cpu_usage = random.uniform(0.1, 0.4)
        self.metrics.memory_usage_mb = random.uniform(100, 400)
    
    # Persistence methods
    
    async def _save_persistent_state(self):
        """Save task manager state to disk"""
        state_data = {
            'manager_id': self.manager_id,
            'metrics': asdict(self.metrics),
            'tasks': {k: asdict(v) for k, v in self.tasks.items()},
            'last_generation': self.last_generation.isoformat() if self.last_generation else None,
            'saved_at': datetime.now().isoformat()
        }
        
        state_file = self.persistence_path / 'ptm_state.json'
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2, default=str)
    
    async def _load_persistent_state(self):
        """Load task manager state from disk"""
        state_file = self.persistence_path / 'ptm_state.json'
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Restore metrics
                if 'metrics' in state_data:
                    self.metrics = TaskMetrics(**state_data['metrics'])
                
                # Restore tasks
                if 'tasks' in state_data:
                    for task_id, task_data in state_data['tasks'].items():
                        # Convert datetime strings back to datetime objects
                        task_data['created_at'] = datetime.fromisoformat(task_data['created_at'])
                        if task_data['started_at']:
                            task_data['started_at'] = datetime.fromisoformat(task_data['started_at'])
                        if task_data['completed_at']:
                            task_data['completed_at'] = datetime.fromisoformat(task_data['completed_at'])
                        if task_data['last_heartbeat']:
                            task_data['last_heartbeat'] = datetime.fromisoformat(task_data['last_heartbeat'])
                        
                        # Convert enums
                        task_data['task_type'] = TaskType(task_data['task_type'])
                        task_data['priority'] = TaskPriority(task_data['priority'])
                        task_data['status'] = TaskStatus(task_data['status'])
                        task_data['tags'] = set(task_data['tags'])
                        
                        self.tasks[task_id] = PassiveTask(**task_data)
                
                # Restore last generation time
                if state_data.get('last_generation'):
                    self.last_generation = datetime.fromisoformat(state_data['last_generation'])
                
                logger.info(f"Loaded persistent state for task manager {self.manager_id}")
                
            except Exception as e:
                logger.error(f"Error loading persistent state: {str(e)}")
    
    # Public interface methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get task manager status"""
        return {
            'manager_id': self.manager_id,
            'is_running': self.is_running,
            'metrics': asdict(self.metrics),
            'active_tasks': len(self.active_executors),
            'total_tasks': len(self.tasks),
            'task_generators': len(self.task_generators),
            'last_generation': self.last_generation.isoformat() if self.last_generation else None
        }
    
    def get_tasks(self, status: TaskStatus = None, task_type: TaskType = None, 
                  limit: int = 50) -> List[Dict[str, Any]]:
        """Get tasks, optionally filtered"""
        tasks = list(self.tasks.values())
        
        # Apply filters
        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        
        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        # Apply limit
        tasks = tasks[:limit]
        
        return [asdict(t) for t in tasks]
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task"""
        if task_id in self.tasks:
            return asdict(self.tasks[task_id])
        return None
    
    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a task"""
        if task_id not in self.tasks:
            return {
                'success': False,
                'error': f'Task not found: {task_id}'
            }
        
        task = self.tasks[task_id]
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return {
                'success': False,
                'error': f'Task cannot be cancelled - status: {task.status.value}'
            }
        
        # Cancel the task
        task.status = TaskStatus.CANCELLED
        
        # Remove from active executors if running
        if task_id in self.active_executors:
            del self.active_executors[task_id]
        
        return {
            'success': True,
            'task_id': task_id,
            'previous_status': task.status.value
        }
    
    def register_task_generator(self, generator: Callable):
        """Register a custom task generator"""
        self.task_generators.append(generator)
    
    async def trigger_generation(self) -> Dict[str, Any]:
        """Manually trigger task generation"""
        await self._generate_automatic_tasks()
        return {
            'success': True,
            'generation_triggered': True,
            'timestamp': datetime.now().isoformat()
        }

# Global passive task manager instance
passive_task_manager = PassiveTaskManager()

# Convenience functions
async def start_passive_tasks() -> Dict[str, Any]:
    """Start the passive task manager"""
    return await passive_task_manager.start()

async def stop_passive_tasks() -> Dict[str, Any]:
    """Stop the passive task manager"""
    return await passive_task_manager.stop()

def get_passive_task_status() -> Dict[str, Any]:
    """Get passive task manager status"""
    return passive_task_manager.get_status()

async def create_passive_task(name: str, description: str, task_type: TaskType,
                             priority: TaskPriority = TaskPriority.MEDIUM,
                             **kwargs) -> Dict[str, Any]:
    """Create a new passive task"""
    return await passive_task_manager.create_task(
        name, description, task_type, priority, **kwargs
    )

def get_passive_tasks(status: TaskStatus = None, task_type: TaskType = None, 
                     limit: int = 50) -> List[Dict[str, Any]]:
    """Get passive tasks"""
    return passive_task_manager.get_tasks(status, task_type, limit)

async def trigger_task_generation() -> Dict[str, Any]:
    """Trigger automatic task generation"""
    return await passive_task_manager.trigger_generation()

