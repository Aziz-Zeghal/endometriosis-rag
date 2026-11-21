"""Local embedding models (optional `[local]` extra)."""

from langchain_core.embeddings import Embeddings

# model id -> (query prefix, document prefix)
PRESETS: dict[str, tuple[str, str]] = {
    # The API gateway sends input_type=query for both sides; the same prompt on both sides
    # keeps these local vectors in the API's vector space (offline fallback).
    "nvidia/Nemotron-3-Embed-1B-BF16": ("query: ", "query: "),
    "BAAI/bge-m3": ("", ""),
}


class SentenceTransformerEmbedder(Embeddings):
    """A LangChain `Embeddings` running a sentence-transformers model on the CPU.

    Queries and passages are separate because some models need different prefixes.
    """

    def __init__(self, model_id: str, query_prefix: str = "", document_prefix: str = "") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                f"Embedder {model_id!r} runs locally and needs sentence-transformers: "
                "install the optional extra with `uv pip install -e 'ingestion[local]'`."
            ) from exc
        self.name = model_id
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix
        self._model = SentenceTransformer(model_id, device="cpu", trust_remote_code=True)

    @classmethod
    def from_preset(cls, model_id: str) -> "SentenceTransformerEmbedder":
        query_prefix, document_prefix = PRESETS.get(model_id, ("", ""))
        return cls(model_id, query_prefix, document_prefix)

    @property
    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        inputs = [self.document_prefix + t for t in texts]
        return self._model.encode(inputs, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([self.query_prefix + text], normalize_embeddings=True)[0].tolist()
