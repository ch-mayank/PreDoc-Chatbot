"""The LlamaIndex agent used by the PreDoc medical chatbot.

This file contains the agent's thinking instructions and its medical search
tool. The web server stays in main.py, while this file focuses on the AI worker.
"""

from typing import Any

from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import BaseRetriever, QueryFusionRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.vector_stores import FilterCondition, MetadataFilter, MetadataFilters

try:
    from llama_index.retrievers.bm25 import BM25Retriever
except (ImportError, ModuleNotFoundError):
    BM25Retriever = None


class SimpleKeywordRetriever(BaseRetriever):
    """Fast, dependency-free in-memory keyword retriever for clinical knowledge nodes."""

    def __init__(self, nodes: list, similarity_top_k: int = 5):
        super().__init__()
        self._nodes = nodes
        self._similarity_top_k = similarity_top_k
        self._node_tokens = []
        import re
        for n in nodes:
            text = (n.get_content() + " " + " ".join(str(v) for v in n.metadata.values())).lower()
            tokens = set(re.findall(r"\w+", text))
            self._node_tokens.append((n, tokens))

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        import re
        q_tokens = set(re.findall(r"\w+", query_bundle.query_str.lower()))
        if not q_tokens:
            return [NodeWithScore(node=n, score=1.0) for n, _ in self._node_tokens[:self._similarity_top_k]]
        
        scored = []
        for node, tokens in self._node_tokens:
            overlap = len(q_tokens & tokens)
            if overlap > 0:
                scored.append(NodeWithScore(node=node, score=float(overlap)))
        
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:self._similarity_top_k]


ALLOWED_CATEGORIES = {
    "Cardiovascular",
    "Dermatological",
    "Endocrine & Metabolic",
    "Gastrointestinal",
    "Hematology & Immunology",
    "Infectious & Parasitic",
    "Mental & Behavioral",
    "Musculoskeletal",
    "Neurological",
    "Obstetrics & Gynecology",
    "Oncological (Cancers)",
    "Ophthalmology & ENT",
    "Pediatrics & Neonatology",
    "Renal & Urological",
    "Respiratory",
    "Toxicology & Environmental",
    "Geriatrics & Age-Related",
    "Critical Care & Anesthesia",
    "Clinical Genetics & Rare Diseases",
    "Pain & Palliative Care",
}


def create_clinical_agent(
    index: Any, qa_template: Any, llm: Any, retrieval_mode: str = "hybrid"
) -> ReActAgent:
    """Create an agent that categorizes a question before searching."""
    if retrieval_mode not in {"hybrid", "dense", "keyword"}:
        raise ValueError("retrieval_mode must be hybrid, dense, or keyword")

    def _build_keyword_retriever(nodes: list, top_k: int = 5):
        if BM25Retriever is not None:
            try:
                return BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=top_k)
            except Exception:
                pass
        return SimpleKeywordRetriever(nodes=nodes, similarity_top_k=top_k)

    async def search_medical_reference(question: str, categories: list[str]) -> str:
        """Search all or selected WHO, CDC, and ICD-10 reference categories."""
        selected_categories = [
            category for category in categories if category in ALLOWED_CATEGORIES
        ]

        metadata_filters = (
            MetadataFilters(
                filters=[
                    MetadataFilter(key="category", value=category)
                    for category in selected_categories
                ],
                condition=FilterCondition.OR,
            )
            if selected_categories
            else None
        )

        # Vector search understands meaning. Keyword search catches exact medical words.
        vector_retriever = index.as_retriever(
            similarity_top_k=5,
            **({"filters": metadata_filters} if metadata_filters else {}),
        )
        # Cache global keyword retriever on index to prevent rebuilding index on every call
        if not hasattr(index, "_cached_bm25"):
            all_nodes = list(index.docstore.docs.values())
            index._cached_bm25 = _build_keyword_retriever(nodes=all_nodes, top_k=5)

        if selected_categories:
            all_nodes = list(index.docstore.docs.values())
            filtered_nodes = [
                node
                for node in all_nodes
                if node.metadata.get("category") in selected_categories
            ]
            keyword_retriever = _build_keyword_retriever(
                nodes=filtered_nodes, top_k=5
            )
        else:
            keyword_retriever = index._cached_bm25

        hybrid_retriever = QueryFusionRetriever(
            retrievers=[vector_retriever, keyword_retriever],
            llm=None,
            mode="simple",
            similarity_top_k=5,
            num_queries=1,
            use_async=True,
            retriever_weights=[0.6, 0.4],
        )
        if retrieval_mode == "dense":
            selected_retriever = vector_retriever
        elif retrieval_mode == "keyword":
            selected_retriever = keyword_retriever
        else:
            selected_retriever = hybrid_retriever

        # Retrieve matching clinical knowledge nodes directly (< 200ms)
        nodes = await selected_retriever.aretrieve(question)
        if not nodes and selected_categories:
            nodes = await vector_retriever.aretrieve(question)

        citation_lines = []
        seen_citations = set()
        text_snippets = []
        for source_node in nodes:
            metadata = source_node.node.metadata
            category = metadata.get("category", "Clinical Guideline")
            content = source_node.node.get_content()
            text_snippets.append(f"[{category}]\n{content}")
            citation = (
                metadata.get("document", "Unknown document"),
                category,
                metadata.get("version", "unknown version"),
                metadata.get("effective_date", "unknown date"),
                metadata.get("reviewed_by", "unknown reviewer"),
                metadata.get("source", "Unknown source"),
            )
            if citation not in seen_citations:
                seen_citations.add(citation)
                citation_lines.append(
                    f"- {citation[0]} | Category: {citation[1]} | "
                    f"Version: {citation[2]} | Effective date: {citation[3]} | "
                    f"Reviewed by: {citation[4]} | Source: {citation[5]}"
                )

        citations = "\n\n### References used\n" + "\n".join(citation_lines) if citation_lines else ""
        return "\n\n---\n\n".join(text_snippets) + citations

    medical_search_tool = FunctionTool.from_defaults(
        async_fn=search_medical_reference,
        name="search_medical_reference",
        description=(
            "Search the approved WHO, CDC, and ICD-10 medical reference notes. "
            "First identify one or more matching categories and pass their "
            "exact names. Use an empty list only when no category is clear."
        ),
    )

    # ReAct means the agent reasons about what to do, uses a tool, and then
    # produces the final answer. It is more capable than calling RAG once.
    return ReActAgent(
        name="PreDocClinicalAgent",
        llm=llm,
        tools=[medical_search_tool],
        system_prompt=(
            "You are PreDoc AI, an expert clinical triage reference assistant. Always use the "
            "search_medical_reference tool before answering. First identify "
            "one or more likely medical categories from the user's symptoms and patient context, then "
            "pass those exact category names to the tool. If symptoms could "
            "belong to several categories, pass all relevant categories. "
            "If the user provided Age or Biological Sex, use them to filter out clinically incompatible "
            "differentials and highlight demographic-specific risk vectors. "
            "Base your answer strictly on returned reference text. "
            "When symptoms are underspecified or vague, select 2-3 high-yield patient probing questions "
            "from Column 10 ('Clarifying Probing Questions') of the matching conditions to ask the patient. "
            "Always include Triage Priority Badges (Level 1 Red for emergencies, Level 2 Yellow for urgent, Level 3 Green for routine) "
            "when listing potential differential matches. "
            "Explain possible matches only as educational information. "
            "Never diagnose, prescribe, or invent facts. Clearly tell the "
            "user that only a qualified clinician can diagnose them."
        ),
    )
