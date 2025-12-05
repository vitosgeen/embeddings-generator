#!/usr/bin/env python3
"""Quick test of task queue with simple task."""

import time
import requests
import json

BASE_URL = "http://localhost:8000"
API_KEY = "sk-admin-m1YHp13elEvafGYLT27H0gmD"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Create a simple cleanup task
data = {
    "task_type": "cleanup_old_data",
    "params": {
        "project_id": "test_project",
        "days_old": 30,
    },
    "name": "Test cleanup task",
    "priority": 1,
}

print("Creating task...")
response = requests.post(f"{BASE_URL}/tasks/", json=data, headers=headers)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Task ID: {result['task_id']}")

task_id = result['task_id']

# Monitor task
print("\nMonitoring task...")
for i in range(10):
    time.sleep(2)
    response = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)
    task = response.json()
    print(f"  Status: {task['status']}, Progress: {task['progress']}%, Message: {task.get('progress_message', 'N/A')}")
    
    if task['status'] in ['completed', 'failed', 'cancelled']:
        print(f"\n✅ Task {task['status']}!")
        if task.get('result'):
            print(f"Result: {json.dumps(task['result'], indent=2)}")
        if task.get('error_message'):
            print(f"Error: {task['error_message']}")
        break
