# PreDoc-Chatbot

PreDoc-Chatbot is a small medical question-answering website. It reads the
Markdown files in `data/`, searches them for useful passages, and asks an AI
model to write an answer using those passages.

## The whole project in one picture

1. You open the website in a browser.
2. The browser sends your question to the FastAPI server in `backend/main.py`.
3. The server checks the login and API key.
4. LlamaIndex searches the medical notes and gives the best matching text to the model.
5. The model writes a Markdown answer, and the browser formats it on screen.

This is called **RAG**, or Retrieval-Augmented Generation: the AI retrieves
real notes first, then generates an answer from those notes. The AI is not a
replacement for a qualified medical professional.

## What each folder does

- `backend/main.py`: starts FastAPI, loads the search index, protects requests, and handles chat.
- `frontend/index.html`: the page a person sees and the JavaScript that calls `/chat`.
- `data/`: medical reference notes, grouped into Markdown files by category.
- `storage/`: saved search data. It is created after indexing so the app can start faster next time.
- `Dockerfile`: recipe for packaging the app into a container.
- `docker-compose.yml`: instructions for running the app and Cloudflare tunnel as services.
- `requirements.txt`: the Python packages the backend needs.

## Run locally

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
ADMIN_USER=admin
ADMIN_PASS=password
DEMO_API_KEY=demo123456
```

Install the packages and start the server:

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8010
```

Open `http://127.0.0.1:8010`. The browser will ask for `ADMIN_USER` and
`ADMIN_PASS`. On the page, enter `DEMO_API_KEY` before sending a question.

## Important idea

The first startup may take longer because the app creates embeddings for the
medical files. Those embeddings are saved in `storage/`; later startups load
them instead of doing all that work again.