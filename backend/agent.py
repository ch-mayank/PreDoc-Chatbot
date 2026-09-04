"""The LlamaIndex agent used by the PreDoc medical chatbot.

This file contains the agent's thinking instructions and its medical search
tool. The web server stays in main.py, while this file focuses on the AI worker.
"""

from typing import Any

from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.vector_stores import FilterCondition, MetadataFilter, MetadataFilters
from llama_index.retrievers.bm25 import BM25Retriever


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

        # Vector search understands meaning. BM25 search catches exact medical
        # words. Combining both is more reliable for names and symptoms.
        vector_retriever = index.as_retriever(
            similarity_top_k=5,
            **({"filters": metadata_filters} if metadata_filters else {}),
        )
        all_nodes = list(index.docstore.docs.values())
        filtered_nodes = [
            node
            for node in all_nodes
            if not selected_categories
            or node.metadata.get("category") in selected_categories
        ]
        keyword_retriever = BM25Retriever.from_defaults(
            nodes=filtered_nodes, similarity_top_k=5
        )
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
        query_engine = RetrieverQueryEngine.from_args(
            retriever=selected_retriever,
            text_qa_template=qa_template,
            use_async=True,
        )
        response = await query_engine.aquery(question)
        citation_lines = []
        seen_citations = set()
        for source_node in getattr(response, "source_nodes", []):
            metadata = source_node.node.metadata
            citation = (
                metadata.get("document", "Unknown document"),
                metadata.get("category", "Unknown category"),
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

        citations = "\n\n### References used\n" + "\n".join(citation_lines)
        return str(response) + (citations if citation_lines else "")

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
