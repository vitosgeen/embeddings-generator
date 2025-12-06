"""Example task handlers for the task queue."""

import time
import logging
from typing import Dict, Any

from app.adapters.infra.task_queue import get_task_queue

logger = logging.getLogger(__name__)


def batch_embedding_handler(task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for batch embedding generation.
    
    Args:
        task_id: Task identifier
        params: Task parameters with:
            - project_id: Project ID
            - collection: Collection name
            - documents: List of documents to embed
            - metadata: Optional metadata list
            
    Returns:
        Result dictionary with count of embeddings generated
    """
    from app.bootstrap import build_usecase
    from app.adapters.infra.vdb_storage import LanceDBVectorStorage
    
    queue = get_task_queue()
    storage = LanceDBVectorStorage()
    
    project_id = params.get("project_id")
    collection = params.get("collection")
    documents = params.get("documents", [])
    metadata_list = params.get("metadata", [])
    
    if not project_id or not collection or not documents:
        raise ValueError("Missing required parameters: project_id, collection, documents")
    
    logger.info(f"Batch embedding task {task_id}: {len(documents)} documents")
    
    # Generate embeddings
    embedding_uc = build_usecase()
    total = len(documents)
    results = []
    
    for i, doc in enumerate(documents):
        try:
            # Update progress
            progress = int((i / total) * 100)
            queue.update_progress(task_id, progress, f"Processing document {i+1}/{total}")
            
            # Generate embedding
            result = embedding_uc.embed(doc, task_type="document")
            embedding = result["embedding"]
            
            # Store vector
            metadata = metadata_list[i] if i < len(metadata_list) else {}
            vector_id = f"{task_id}_{i}"
            
            storage.add_vector(
                project=project_id,
                collection=collection,
                vector_id=vector_id,
                vector=embedding,
                metadata=metadata,
                document=doc,
            )
            
            results.append({"id": vector_id, "status": "success"})
            
        except Exception as e:
            logger.error(f"Failed to process document {i}: {e}")
            results.append({"id": f"{task_id}_{i}", "status": "failed", "error": str(e)})
    
    queue.update_progress(task_id, 100, "Completed")
    
    return {
        "total": total,
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }


def cleanup_old_data_handler(task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for cleaning up old data.
    
    Args:
        task_id: Task identifier
        params: Task parameters with:
            - project_id: Project ID
            - days_old: Delete data older than this many days
            
    Returns:
        Result dictionary with count of deleted items
    """
    from datetime import datetime, timedelta
    
    queue = get_task_queue()
    
    project_id = params.get("project_id")
    days_old = params.get("days_old", 30)
    
    if not project_id:
        raise ValueError("Missing required parameter: project_id")
    
    logger.info(f"Cleanup task {task_id}: project={project_id}, days_old={days_old}")
    
    queue.update_progress(task_id, 10, "Identifying old data...")
    
    # Simulate cleanup (replace with actual implementation)
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    deleted_count = 0
    
    # TODO: Implement actual cleanup logic based on your storage structure
    # This is a placeholder
    time.sleep(2)
    
    queue.update_progress(task_id, 100, "Cleanup completed")
    
    return {
        "project_id": project_id,
        "cutoff_date": cutoff_date.isoformat(),
        "deleted_count": deleted_count,
    }


def export_collection_handler(task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for exporting collection data.
    
    Args:
        task_id: Task identifier
        params: Task parameters with:
            - project_id: Project ID
            - collection: Collection name
            - output_path: Output file path
            
    Returns:
        Result dictionary with export details
    """
    import json
    import os
    from app.adapters.infra.vdb_storage import LanceDBVectorStorage
    
    queue = get_task_queue()
    storage = LanceDBVectorStorage()
    
    project_id = params.get("project_id")
    collection = params.get("collection")
    output_path = params.get("output_path", f"./data/exports/{task_id}.json")
    
    if not project_id or not collection:
        raise ValueError("Missing required parameters: project_id, collection")
    
    logger.info(f"Export task {task_id}: {project_id}/{collection}")
    
    queue.update_progress(task_id, 10, "Fetching collection data...")
    
    # Get collection info
    coll_info = storage.get_collection(project_id, collection)
    if not coll_info:
        raise ValueError(f"Collection not found: {project_id}/{collection}")
    
    queue.update_progress(task_id, 30, "Exporting vectors...")
    
    # Get all vectors (this is simplified - you may need pagination)
    vectors = storage.list_vectors(project_id, collection, limit=10000)
    
    queue.update_progress(task_id, 80, "Writing to file...")
    
    # Export to JSON
    export_data = {
        "project_id": project_id,
        "collection": collection,
        "exported_at": time.time(),
        "count": len(vectors),
        "vectors": vectors,
    }
    
    # Create directory if needed
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=2)
    
    queue.update_progress(task_id, 100, "Export completed")
    
    return {
        "project_id": project_id,
        "collection": collection,
        "output_path": output_path,
        "vector_count": len(vectors),
    }


def register_default_handlers():
    """Register all default task handlers."""
    queue = get_task_queue()
    
    queue.register_handler("batch_embedding", batch_embedding_handler)
    queue.register_handler("cleanup_old_data", cleanup_old_data_handler)
    queue.register_handler("export_collection", export_collection_handler)
    
    logger.info("Registered default task handlers")
