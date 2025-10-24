from .adapters.infra.sentence_encoder import SentenceEncoder
from .config import BATCH_SIZE, MODEL_ID
from .usecases.generate_embedding import GenerateEmbeddingUC


def build_usecase() -> GenerateEmbeddingUC:
    encoder = SentenceEncoder(MODEL_ID, device=None, batch_size=BATCH_SIZE)
    return GenerateEmbeddingUC(encoder)
