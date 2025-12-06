#!/usr/bin/env python3
"""Demo script for task queue functionality."""

import time
import requests
import json

BASE_URL = "http://localhost:8000"
API_KEY = "sk-admin-m1YHp13elEvafGYLT27H0gmD"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def create_task(task_type, params, name=None, priority=1):
    """Create a new task."""
    data = {
        "task_type": task_type,
        "params": params,
        "priority": priority,
    }
    if name:
        data["name"] = name
    
    response = requests.post(f"{BASE_URL}/tasks/", json=data, headers=headers)
    response.raise_for_status()
    return response.json()


def get_task(task_id):
    """Get task details."""
    response = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)
    response.raise_for_status()
    return response.json()


def list_tasks(status=None, task_type=None):
    """List tasks."""
    params = {}
    if status:
        params["status"] = status
    if task_type:
        params["task_type"] = task_type
    
    response = requests.get(f"{BASE_URL}/tasks/", params=params, headers=headers)
    response.raise_for_status()
    return response.json()


def get_stats():
    """Get queue statistics."""
    response = requests.get(f"{BASE_URL}/tasks/stats/queue", headers=headers)
    response.raise_for_status()
    return response.json()


def wait_for_task(task_id, timeout=60):
    """Wait for task to complete."""
    start = time.time()
    while time.time() - start < timeout:
        task = get_task(task_id)
        status = task["status"]
        progress = task["progress"]
        progress_msg = task.get("progress_message", "")
        
        print(f"Task {task_id[:8]}... - Status: {status}, Progress: {progress}% - {progress_msg}")
        
        if status in ["completed", "failed", "cancelled"]:
            return task
        
        time.sleep(2)
    
    raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")


def main():
    """Run task queue demo."""
    print("\n🚀 Task Queue Demo")
    print("=" * 70)
    
    # Check queue stats
    print_section("1. Queue Statistics")
    stats = get_stats()
    print(f"Total tasks: {stats['total']}")
    print(f"Pending: {stats['pending']}")
    print(f"Running: {stats['running']}")
    print(f"Completed: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Worker running: {stats['worker_running']}")
    
    # Create batch embedding task
    print_section("2. Create Batch Embedding Task")
    
    documents = [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is a subset of artificial intelligence",
        "Python is a popular programming language",
        "Neural networks are inspired by biological neurons",
        "Data science combines statistics and programming",
    ]
    
    task_result = create_task(
        task_type="batch_embedding",
        params={
            "project_id": "demo_project",
            "collection": "demo_collection",
            "documents": documents,
            "metadata": [
                {"category": "animals", "source": "example"},
                {"category": "tech", "source": "example"},
                {"category": "tech", "source": "example"},
                {"category": "tech", "source": "example"},
                {"category": "tech", "source": "example"},
            ],
        },
        name="Demo batch embedding",
        priority=2,
    )
    
    task_id = task_result["task_id"]
    print(f"✅ Created task: {task_id}")
    print(f"Status: {task_result['status']}")
    print(f"Message: {task_result['message']}")
    
    # Wait for task to complete
    print_section("3. Monitor Task Progress")
    completed_task = wait_for_task(task_id, timeout=120)
    
    print(f"\n✅ Task completed!")
    print(f"Status: {completed_task['status']}")
    if completed_task.get("result"):
        result = completed_task["result"]
        print(f"\nResult:")
        print(f"  Total documents: {result.get('total', 0)}")
        print(f"  Successful: {result.get('successful', 0)}")
        print(f"  Failed: {result.get('failed', 0)}")
    
    # Create export task
    print_section("4. Create Export Task")
    
    export_task = create_task(
        task_type="export_collection",
        params={
            "project_id": "demo_project",
            "collection": "demo_collection",
            "output_path": "./data/exports/demo_export.json",
        },
        name="Export demo collection",
        priority=1,
    )
    
    export_task_id = export_task["task_id"]
    print(f"✅ Created export task: {export_task_id}")
    
    # Wait for export
    print_section("5. Monitor Export Task")
    export_completed = wait_for_task(export_task_id, timeout=60)
    
    print(f"\n✅ Export completed!")
    if export_completed.get("result"):
        result = export_completed["result"]
        print(f"\nResult:")
        print(f"  Project: {result.get('project_id')}")
        print(f"  Collection: {result.get('collection')}")
        print(f"  Output: {result.get('output_path')}")
        print(f"  Vectors: {result.get('vector_count', 0)}")
    
    # List all tasks
    print_section("6. List All Tasks")
    tasks = list_tasks()
    print(f"Found {tasks['count']} tasks:\n")
    
    for task in tasks["tasks"][:10]:  # Show first 10
        print(f"  [{task['status']:10}] {task['name']:30} ({task['task_type']})")
        print(f"    Created: {task['created_at']}")
        if task['started_at']:
            print(f"    Started: {task['started_at']}")
        if task['completed_at']:
            print(f"    Completed: {task['completed_at']}")
        print()
    
    # Final stats
    print_section("7. Final Queue Statistics")
    final_stats = get_stats()
    print(f"Total tasks: {final_stats['total']}")
    print(f"Pending: {final_stats['pending']}")
    print(f"Running: {final_stats['running']}")
    print(f"Completed: {final_stats['completed']}")
    print(f"Failed: {final_stats['failed']}")
    
    print_section("✨ Demo Complete!")
    print("Task queue is working! You can:")
    print("  - Create tasks via POST /tasks/")
    print("  - Monitor tasks via GET /tasks/{task_id}")
    print("  - List tasks via GET /tasks/")
    print("  - View stats via GET /tasks/stats/queue")
    print("  - Cancel tasks via DELETE /tasks/{task_id}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
