"""Production-Grade Clinical Hybrid Retrieval Engine (BM25 + Dense Vector RAG).

Combines:
1. Dense Semantic Vector Search (via OpenRouter liquid/lfm-2.5-embedding-350m:free)
2. Sparse Keyword Matching (via BM25Okapi for exact ICD-10, eponyms, and acronyms)
3. Reciprocal Rank Fusion (RRF) for robust diagnostic scoring.
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from llama_index.core import (
    ChatPromptTemplate,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.schema import NodeWithScore, TextNode

try:
    from rank_bm25 import BM25Okapi
except (ImportError, ModuleNotFoundError):
    import math
    from collections import Counter

    class BM25Okapi:  # type: ignore[no-redef]
        """Pure-Python BM25Okapi implementation for zero-dependency hybrid retrieval."""

        def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
            self.corpus_size = len(corpus)
            self.avgdl = sum(len(doc) for doc in corpus) / max(1, self.corpus_size)
            self.k1 = k1
            self.b = b
            self.doc_len = [len(doc) for doc in corpus]
            self.doc_freqs: List[Counter] = [Counter(doc) for doc in corpus]
            self.nd = Counter()
            for doc in corpus:
                for word in set(doc):
                    self.nd[word] += 1
            self.idf: Dict[str, float] = {}
            for word, freq in self.nd.items():
                self.idf[word] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

        def get_scores(self, query: List[str]) -> List[float]:
            scores = [0.0] * self.corpus_size
            for q in query:
                if q not in self.idf:
                    continue
                q_idf = self.idf[q]
                for i, doc_freq in enumerate(self.doc_freqs):
                    freq = doc_freq.get(q, 0)
                    if freq > 0:
                        num = freq * (self.k1 + 1)
                        den = freq + self.k1 * (1 - self.b + self.b * (self.doc_len[i] / max(1.0, self.avgdl)))
                        scores[i] += q_idf * (num / max(1e-6, den))
            return scores

from backend.config import DATA_DIR, PERSIST_DIR, get_file_metadata

logger = logging.getLogger("predoc.rag")
logger.setLevel(logging.INFO)

SYSTEM_MESSAGE = ChatMessage(
    role=MessageRole.SYSTEM,
    content=(
        "You are an expert Clinical Decision Support AI Assistant.\n"
        "Base your answer strictly on the provided medical context.\n"
        "Use clean Markdown headings and bullet points.\n"
        "If the context does not contain the answer, say: 'I cannot find "
        "relevant clinical data for this condition in my reference database.'\n"
        "Never invent, extrapolate, diagnose, or prescribe. Always include "
        "the Category, Source, and Version when available."
    ),
)

USER_MESSAGE = ChatMessage(
    role=MessageRole.USER,
    content=(
        "---------------------\n"
        "Context Information:\n"
        "{context_str}\n"
        "---------------------\n"
        "Query: {query_str}"
    ),
)

CHAT_QA_TEMPLATE = ChatPromptTemplate(
    message_templates=[SYSTEM_MESSAGE, USER_MESSAGE]
)


class ClinicalHybridRetriever:
    """Hybrid Retriever combining BM25 keyword matching and Dense Vector search with RRF."""

    def __init__(
        self,
        vector_index: Optional[VectorStoreIndex] = None,
        nodes: Optional[List[TextNode]] = None,
        similarity_top_k: int = 5,
        bm25_top_k: int = 5,
        rrf_constant: int = 60,
    ):
        self.vector_index = vector_index
        self.similarity_top_k = similarity_top_k
        self.bm25_top_k = bm25_top_k
        self.rrf_constant = rrf_constant
        self.nodes = nodes or []
        self.bm25: Optional[BM25Okapi] = None
        self._build_bm25_index()

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into alphanumeric words for BM25 matching."""
        return re.findall(r"\w+", text.lower())

    def _build_bm25_index(self):
        """Construct BM25 corpus from text nodes."""
        if not self.nodes and self.vector_index is not None:
            # Extract nodes from vector index docstore if available
            try:
                docstore = self.vector_index.docstore
                self.nodes = list(docstore.docs.values())
            except Exception as e:
                logger.warning(f"Could not load nodes from docstore for BM25: {e}")

        if self.nodes:
            corpus = [self._tokenize(node.get_content()) for node in self.nodes]
            self.bm25 = BM25Okapi(corpus)
            logger.info(f"Initialized BM25 index with {len(self.nodes)} clinical documents.")

    def retrieve(self, query_str: str) -> List[NodeWithScore]:
        """Execute Reciprocal Rank Fusion hybrid retrieval."""
        dense_results: List[NodeWithScore] = []
        sparse_results: List[NodeWithScore] = []

        # 1. Dense Vector Retrieval
        if self.vector_index:
            try:
                retriever = self.vector_index.as_retriever(similarity_top_k=self.similarity_top_k)
                dense_results = retriever.retrieve(query_str)
            except Exception as e:
                logger.error(f"Dense vector retrieval error: {e}")

        # 2. BM25 Sparse Keyword Retrieval
        if self.bm25 and self.nodes:
            tokens = self._tokenize(query_str)
            if tokens:
                scores = self.bm25.get_scores(tokens)
                top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: self.bm25_top_k]
                for idx in top_indices:
                    if scores[idx] > 0:
                        sparse_results.append(NodeWithScore(node=self.nodes[idx], score=float(scores[idx])))

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}
        node_map: Dict[str, TextNode] = {}

        # Rank dense results
        for rank, item in enumerate(dense_results):
            nid = item.node.node_id
            node_map[nid] = item.node
            rrf_scores[nid] = rrf_scores.get(nid, 0.0) + (1.0 / (self.rrf_constant + rank + 1))

        # Rank sparse results
        for rank, item in enumerate(sparse_results):
            nid = item.node.node_id
            node_map[nid] = item.node
            rrf_scores[nid] = rrf_scores.get(nid, 0.0) + (1.0 / (self.rrf_constant + rank + 1))

        # Sort merged nodes by final RRF score
        sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        final_top_k = max(self.similarity_top_k, self.bm25_top_k)
        
        return [
            NodeWithScore(node=node_map[nid], score=score)
            for nid, score in sorted_items[:final_top_k]
        ]


def load_or_build_index(force_rebuild: bool = False) -> Optional[VectorStoreIndex]:
    """Load existing index from storage, or build it if documents exist or dimensions mismatch."""
    from backend.config import PRIMARY_EMBEDDING_DIM

    vector_file = PERSIST_DIR / "default__vector_store.json"
    dim_match = True

    if not force_rebuild and PERSIST_DIR.exists() and vector_file.exists():
        try:
            with open(vector_file, "r", encoding="utf-8") as f:
                vdata = json.load(f)
            nodes = vdata.get("embedding_dict", {})
            if nodes:
                first_emb = next(iter(nodes.values()))
                if len(first_emb) != PRIMARY_EMBEDDING_DIM:
                    logger.warning(
                        f"Stored index vector dimension ({len(first_emb)}) does not match current model "
                        f"dimension ({PRIMARY_EMBEDDING_DIM}). Re-indexing knowledge base into 2,048 dimensions..."
                    )
                    dim_match = False
        except Exception as err:
            logger.warning(f"Could not verify stored vector dimension: {err}")

    if not force_rebuild and dim_match and PERSIST_DIR.exists() and any(PERSIST_DIR.iterdir()):
        logger.info(f"Loading existing index from '{PERSIST_DIR}'...")
        storage_context = StorageContext.from_defaults(persist_dir=str(PERSIST_DIR))
        return load_index_from_storage(storage_context)

    kb_dir = DATA_DIR / "knowledge_base"
    kb_files = list(kb_dir.glob("*.md")) if kb_dir.exists() else []

    if not kb_files:
        logger.info("Knowledge base is currently awaiting autonomous agent population. Returning None.")
        return None

    logger.info(f"Processing documents from '{kb_dir}' into {PRIMARY_EMBEDDING_DIM}-dimension vector index...")
    documents = SimpleDirectoryReader(str(kb_dir), file_metadata=get_file_metadata).load_data()
    logger.info("Building VectorStoreIndex with cloud-native embeddings and persisting...")
    index = VectorStoreIndex.from_documents(documents)
    PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(PERSIST_DIR))
    logger.info(f"VectorStoreIndex successfully persisted to '{PERSIST_DIR}'.")
    return index


def create_hybrid_retriever(
    index: Optional[VectorStoreIndex] = None,
    similarity_top_k: int = 5,
    bm25_top_k: int = 5,
) -> ClinicalHybridRetriever:
    """Factory function to build a production hybrid retriever."""
    return ClinicalHybridRetriever(
        vector_index=index,
        similarity_top_k=similarity_top_k,
        bm25_top_k=bm25_top_k,
    )
