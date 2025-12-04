from .adapters.infra.sentence_encoder import SentenceEncoder
from .adapters.infra.vdb_storage import (
    FileProjectStorage,
    LanceDBVectorStorage,
    HashSharding,
)
from .config import BATCH_SIZE, MODEL_ID, VDB_STORAGE_PATH
from .usecases.generate_embedding import GenerateEmbeddingUC
from .usecases.vdb_usecases import (
    CreateProjectUC,
    ListProjectsUC,
    CreateCollectionUC,
    ListCollectionsUC,
    AddVectorUC,
    SearchVectorsUC,
    DeleteVectorUC,
)


def build_usecase() -> GenerateEmbeddingUC:
    encoder = SentenceEncoder(MODEL_ID, device=None, batch_size=BATCH_SIZE)
    return GenerateEmbeddingUC(encoder)


def build_vdb_usecases():
    """Build all VDB use cases with dependencies."""
    # Infrastructure
    sharding = HashSharding()
    project_storage = FileProjectStorage(VDB_STORAGE_PATH)
    vector_storage = LanceDBVectorStorage(VDB_STORAGE_PATH, sharding)
    
    # Use cases
    return {
        "create_project": CreateProjectUC(project_storage),
        "list_projects": ListProjectsUC(project_storage),
        "create_collection": CreateCollectionUC(vector_storage, project_storage),
        "list_collections": ListCollectionsUC(vector_storage, project_storage),
        "add_vector": AddVectorUC(vector_storage, project_storage),
        "search_vectors": SearchVectorsUC(vector_storage, project_storage),
        "delete_vector": DeleteVectorUC(vector_storage, project_storage),
    }
