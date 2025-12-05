"""REST API endpoints for task queue management."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.adapters.infra.task_queue import (
    get_task_queue,
    TaskQueue,
    TaskStatus,
    TaskPriority,
)
from app.adapters.rest.admin_routes import get_admin_user
from app.domain.auth import AuthContext

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    """Request to create a new task."""
    
    task_type: str = Field(..., description="Type of task to execute")
    params: dict = Field(default_factory=dict, description="Task parameters")
    name: Optional[str] = Field(None, description="Human-readable task name")
    priority: int = Field(default=1, description="Task priority (0=low, 1=normal, 2=high, 3=urgent)")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class CreateTaskResponse(BaseModel):
    """Response after creating a task."""
    
    task_id: str
    status: str
    message: str


class TaskResponse(BaseModel):
    """Task details response."""
    
    id: str
    name: str
    task_type: str
    status: str
    priority: int
    params: Optional[dict]
    result: Optional[dict]
    error_message: Optional[str]
    progress: int
    progress_message: Optional[str]
    created_by: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    retry_count: int
    max_retries: int


class TaskListItem(BaseModel):
    """Task list item (summary)."""
    
    id: str
    name: str
    task_type: str
    status: str
    priority: int
    progress: int
    progress_message: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    retry_count: int


class TaskListResponse(BaseModel):
    """List of tasks response."""
    
    tasks: list[TaskListItem]
    count: int


class QueueStatsResponse(BaseModel):
    """Queue statistics response."""
    
    total: int
    pending: int
    running: int
    completed: int
    failed: int
    cancelled: int
    worker_running: bool


@router.post("/", response_model=CreateTaskResponse)
def create_task(
    req: CreateTaskRequest,
    auth: AuthContext = Depends(get_admin_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """Create a new background task.
    
    Args:
        req: Task creation request
        auth: Authentication context
        queue: Task queue instance
        
    Returns:
        Task creation response with task ID
    """
    try:
        task_id = queue.create_task(
            task_type=req.task_type,
            params=req.params,
            name=req.name,
            priority=TaskPriority(req.priority),
            created_by=auth.username,
            max_retries=req.max_retries,
        )
        
        return CreateTaskResponse(
            task_id=task_id,
            status="pending",
            message="Task created successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    auth: AuthContext = Depends(get_admin_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """Get task details by ID.
    
    Args:
        task_id: Task identifier
        auth: Authentication context
        queue: Task queue instance
        
    Returns:
        Task details
    """
    task = queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(**task)


@router.get("/", response_model=TaskListResponse)
def list_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 100,
    auth: AuthContext = Depends(get_admin_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """List tasks with optional filtering.
    
    Args:
        status: Filter by status (pending/running/completed/failed/cancelled)
        task_type: Filter by task type
        limit: Maximum number of results
        auth: Authentication context
        queue: Task queue instance
        
    Returns:
        List of tasks
    """
    try:
        task_status = TaskStatus(status) if status else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    tasks = queue.list_tasks(
        status=task_status,
        task_type=task_type,
        limit=min(limit, 1000),
    )
    
    return TaskListResponse(
        tasks=[TaskListItem(**task) for task in tasks],
        count=len(tasks),
    )


@router.delete("/{task_id}")
def cancel_task(
    task_id: str,
    auth: AuthContext = Depends(get_admin_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """Cancel a pending task.
    
    Args:
        task_id: Task identifier
        auth: Authentication context
        queue: Task queue instance
        
    Returns:
        Success message
    """
    success = queue.cancel_task(task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Task cannot be cancelled (not pending or already completed)",
        )
    
    return {"message": "Task cancelled successfully"}


@router.get("/stats/queue", response_model=QueueStatsResponse)
def get_queue_stats(
    auth: AuthContext = Depends(get_admin_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """Get queue statistics.
    
    Args:
        auth: Authentication context
        queue: Task queue instance
        
    Returns:
        Queue statistics
    """
    stats = queue.get_stats()
    return QueueStatsResponse(**stats)


@router.post("/worker/start")
def start_worker(
    auth: AuthContext = Depends(get_admin_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """Start the task queue worker.
    
    Args:
        auth: Authentication context
        queue: Task queue instance
        
    Returns:
        Success message
    """
    queue.start_worker()
    return {"message": "Worker started successfully"}


@router.post("/worker/stop")
def stop_worker(
    auth: AuthContext = Depends(get_admin_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """Stop the task queue worker.
    
    Args:
        auth: Authentication context
        queue: Task queue instance
        
    Returns:
        Success message
    """
    queue.stop_worker()
    return {"message": "Worker stopped successfully"}
