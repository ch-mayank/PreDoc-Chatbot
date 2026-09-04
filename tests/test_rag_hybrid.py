"""Unit tests for BM25 + Vector Hybrid Retrieval and Resilient OpenRouter Client."""

import unittest
from llama_index.core.schema import TextNode

from backend.openrouter_client import OpenRouterResilientClient, FREE_MODELS
from backend.rag import ClinicalHybridRetriever, create_hybrid_retriever


class TestHybridRAGAndClient(unittest.TestCase):
    def setUp(self):
        # Sample clinical documents for offline testing
        self.node1 = TextNode(
            text="STEMI (ST-Elevation Myocardial Infarction): Hallmark symptom is acute crushing retrosternal chest pain.",
            id_="node-cvd-001"
        )
        self.node2 = TextNode(
            text="Atopic Dermatitis (Eczema): Characterized by pruritic erythematous flexural plaques.",
            id_="node-derm-001"
        )
        self.node3 = TextNode(
            text="Acute Appendicitis: Right lower quadrant pain at McBurney's point with fever and anorexia.",
            id_="node-gi-001"
        )
        self.nodes = [self.node1, self.node2, self.node3]

    def test_bm25_sparse_scoring_exact_match(self):
        retriever = ClinicalHybridRetriever(nodes=self.nodes, bm25_top_k=2)
        results = retriever.retrieve("crushing chest pain STEMI")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].node.node_id, "node-cvd-001")
        self.assertIn("STEMI", results[0].node.get_content())

    def test_bm25_sparse_scoring_dermatology(self):
        retriever = ClinicalHybridRetriever(nodes=self.nodes, bm25_top_k=2)
        results = retriever.retrieve("pruritic eczema plaques")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].node.node_id, "node-derm-001")

    def test_factory_function(self):
        retriever = create_hybrid_retriever(similarity_top_k=3, bm25_top_k=3)
        self.assertIsInstance(retriever, ClinicalHybridRetriever)
        self.assertEqual(retriever.similarity_top_k, 3)

    def test_openrouter_client_initialization(self):
        client = OpenRouterResilientClient(api_keys=["test-key-1", "test-key-2"])
        self.assertEqual(len(client.api_keys), 2)
        self.assertEqual(client.models, FREE_MODELS)
        self.assertEqual(client.models[0], "google/gemma-4-26b-a4b-it:free")

    def test_generic_openai_client_initialization(self):
        from backend.openai_client import GenericOpenAIClient
        client = GenericOpenAIClient(
            primary_base_url="https://integrate.api.nvidia.com/v1",
            primary_api_key="test-p-key",
            fallback_base_url="https://openrouter.ai/api/v1",
            fallback_api_key="test-f-key",
        )
        self.assertEqual(client.primary_base_url, "https://integrate.api.nvidia.com/v1")
        self.assertEqual(client.primary_provider, "nvidia")
        self.assertEqual(client.fallback_provider, "openrouter")
        self.assertEqual(client.primary_embedding_dim, 2048)

    def test_vector_dimension_adaptation(self):
        from backend.openai_client import adapt_vector_dimension
        import numpy as np

        # Test expansion (1024 -> 2048)
        v1024 = [0.1] * 1024
        adapted = adapt_vector_dimension(v1024, 2048)
        self.assertEqual(len(adapted), 2048)
        self.assertAlmostEqual(float(np.linalg.norm(adapted)), 1.0, places=4)

        # Test truncation (2048 -> 1024)
        v2048 = [0.05] * 2048
        truncated = adapt_vector_dimension(v2048, 1024)
        self.assertEqual(len(truncated), 1024)
        self.assertAlmostEqual(float(np.linalg.norm(truncated)), 1.0, places=4)



if __name__ == "__main__":
    unittest.main()
