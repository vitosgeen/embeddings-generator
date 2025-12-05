"""SQLite-based task queue for background job processing."""

import json
import uuid
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import logging

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Boolean,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

Base = declarative_base()


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class Task(Base):
    """Task model for job queue."""
    
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=TaskStatus.PENDING, index=True)
    priority = Column(Integer, nullable=False, default=TaskPriority.NORMAL, index=True)
    
    # Task data
    task_type = Column(String(100), nullable=False, index=True)
    params_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Retry logic
    max_retries = Column(Integer, default=3, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Progress tracking
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    progress_message = Column(String(500), nullable=True)


class TaskQueue:
    """SQLite-based task queue manager."""
    
    def __init__(self, db_path: str = "./data/tasks.db"):
        """Initialize task queue.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Task handlers registry
        self.handlers: Dict[str, Callable] = {}
        
        # Worker thread
        self.worker_thread: Optional[threading.Thread] = None
        self._stop_worker = threading.Event()
        self.running = False
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def register_handler(self, task_type: str, handler: Callable):
        """Register a task handler function.
        
        Args:
            task_type: Type of task (e.g., "batch_embedding", "cleanup")
            handler: Function to execute the task. Should accept (task_id, params) and return result
        """
        self.handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    def create_task(
        self,
        task_type: str,
        params: Dict[str, Any],
        name: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        created_by: Optional[str] = None,
        max_retries: int = 3,
    ) -> str:
        """Create a new task.
        
        Args:
            task_type: Type of task to execute
            params: Task parameters as dictionary
            name: Human-readable task name
            priority: Task priority
            created_by: User who created the task
            max_retries: Maximum retry attempts
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        with self.get_session() as session:
            task = Task(
                id=task_id,
                name=name or f"{task_type}_{task_id[:8]}",
                task_type=task_type,
                params_json=json.dumps(params),
                priority=priority,
                status=TaskStatus.PENDING,
                created_by=created_by,
                max_retries=max_retries,
            )
            session.add(task)
            session.commit()
        
        logger.info(f"Created task: {task_id} ({task_type})")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task dictionary or None
        """
        with self.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None
            
            return {
                "id": task.id,
                "name": task.name,
                "task_type": task.task_type,
                "status": task.status,
                "priority": task.priority,
                "params": json.loads(task.params_json) if task.params_json else None,
                "result": json.loads(task.result_json) if task.result_json else None,
                "error_message": task.error_message,
                "progress": task.progress,
                "progress_message": task.progress_message,
                "created_by": task.created_by,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
            }
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filtering.
        
        Args:
            status: Filter by status
            task_type: Filter by task type
            limit: Maximum results
            
        Returns:
            List of task dictionaries
        """
        with self.get_session() as session:
            query = session.query(Task)
            
            if status:
                query = query.filter(Task.status == status)
            if task_type:
                query = query.filter(Task.task_type == task_type)
            
            query = query.order_by(Task.created_at.desc()).limit(limit)
            tasks = query.all()
            
            return [
                {
                    "id": task.id,
                    "name": task.name,
                    "task_type": task.task_type,
                    "status": task.status,
                    "priority": task.priority,
                    "progress": task.progress,
                    "progress_message": task.progress_message,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "retry_count": task.retry_count,
                }
                for task in tasks
            ]
    
    def update_progress(self, task_id: str, progress: int, message: Optional[str] = None):
        """Update task progress.
        
        Args:
            task_id: Task identifier
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        with self.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.progress = max(0, min(100, progress))
                if message:
                    task.progress_message = message
                session.commit()
                logger.debug(f"Task {task_id} progress: {progress}% - {message}")
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if cancelled, False otherwise
        """
        with self.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                session.commit()
                logger.info(f"Cancelled task: {task_id}")
                return True
            return False
    
    def _get_next_task(self) -> Optional[str]:
        """Get next pending task ID to execute (highest priority first)."""
        with self.get_session() as session:
            task = (
                session.query(Task)
                .filter(Task.status == TaskStatus.PENDING)
                .order_by(Task.priority.desc(), Task.created_at.asc())
                .first()
            )
            
            if task:
                # Mark as running
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                task_id = task.id
                session.commit()
                return task_id
            
            return None
    
    def _execute_task(self, task_id: str):
        """Execute a single task.
        
        Args:
            task_id: Task ID to execute
        """
        logger.info(f"Executing task: {task_id}")
        
        # Get task details in this thread's session
        with self.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"Task not found: {task_id}")
                return
            
            task_type = task.task_type
            params_json = task.params_json
            max_retries = task.max_retries
            retry_count = task.retry_count
        
        try:
            # Get handler
            handler = self.handlers.get(task_type)
            if not handler:
                raise ValueError(f"No handler registered for task type: {task_type}")
            
            # Parse parameters
            params = json.loads(params_json) if params_json else {}
            
            # Execute handler
            result = handler(task_id, params)
            
            # Mark as completed
            with self.get_session() as session:
                db_task = session.query(Task).filter(Task.id == task_id).first()
                if db_task:
                    db_task.status = TaskStatus.COMPLETED
                    db_task.result_json = json.dumps(result) if result else None
                    db_task.completed_at = datetime.utcnow()
                    db_task.progress = 100
                    session.commit()
            
            logger.info(f"Task completed: {task_id}")
            
        except Exception as e:
            logger.error(f"Task failed: {task_id} - {str(e)}")
            
            # Update task with error
            with self.get_session() as session:
                db_task = session.query(Task).filter(Task.id == task_id).first()
                if db_task:
                    db_task.retry_count += 1
                    
                    # Check if should retry
                    if db_task.retry_count < max_retries:
                        db_task.status = TaskStatus.PENDING
                        db_task.started_at = None
                        logger.info(f"Task will retry: {task_id} (attempt {db_task.retry_count + 1}/{max_retries})")
                    else:
                        db_task.status = TaskStatus.FAILED
                        db_task.completed_at = datetime.utcnow()
                        logger.error(f"Task failed permanently: {task_id}")
                    
                    db_task.error_message = str(e)
                    session.commit()
    
    def _worker_loop(self):
        """Worker thread main loop."""
        logger.info("Task queue worker started")
        
        while not self._stop_worker.is_set():
            try:
                # Get next task ID
                task_id = self._get_next_task()
                
                if task_id:
                    self._execute_task(task_id)
                else:
                    # No tasks, sleep briefly
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(5)
        
        logger.info("Task queue worker stopped")
    
    def start_worker(self):
        """Start background worker thread."""
        if self.running:
            logger.warning("Worker already running")
            return
        
        self.running = True
        self._stop_worker.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Started task queue worker")
    
    def stop_worker(self):
        """Stop background worker thread."""
        if not self.running:
            return
        
        logger.info("Stopping task queue worker...")
        self._stop_worker.set()
        
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        
        self.running = False
        logger.info("Task queue worker stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics.
        
        Returns:
            Dictionary with queue stats
        """
        with self.get_session() as session:
            total = session.query(Task).count()
            pending = session.query(Task).filter(Task.status == TaskStatus.PENDING).count()
            running = session.query(Task).filter(Task.status == TaskStatus.RUNNING).count()
            completed = session.query(Task).filter(Task.status == TaskStatus.COMPLETED).count()
            failed = session.query(Task).filter(Task.status == TaskStatus.FAILED).count()
            cancelled = session.query(Task).filter(Task.status == TaskStatus.CANCELLED).count()
            
            return {
                "total": total,
                "pending": pending,
                "running": running,
                "completed": completed,
                "failed": failed,
                "cancelled": cancelled,
                "worker_running": self.running,
            }


# Global task queue instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get global task queue instance."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
