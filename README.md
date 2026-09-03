# PreDoc-Chatbot 🩺🤖

A production-ready, secure Retrieval-Augmented Generation (RAG) clinical AI chatbot built with **FastAPI**, **LlamaIndex**, and an interactive web interface.

## 🚀 Key Features
* **Secure Access Control:** Browser-native HTTP Basic Authentication combined with header-based API key checks (`x-api-key`).
* **Clinical RAG Engine:** Powered by LlamaIndex, OpenRouter LLMs, and custom metadata-aware document vectorization.
* **Modern UI:** Responsive frontend with automatic Markdown rendering for clear medical summaries, bullet points, and emergency red flags.

## ⚙️ Environment Setup
Create a `.env` file in the root directory with the following configuration:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
ADMIN_USER=admin
ADMIN_PASS=password
DEMO_API_KEY=demo123456