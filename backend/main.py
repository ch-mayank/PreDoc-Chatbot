import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

# LlamaIndex Imports
from llama_index.core import (
    ChatPromptTemplate,
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike

# ==========================================
# 1. ENVIRONMENT & API CONFIGURATION
# ==========================================
load_dotenv()


def get_secret(secret_name: str, env_name: str, default: Optional[str] = None) -> str:
    """Reads secret from Docker mount (/run/secrets/), falling back to .env or defaults."""
    secret_path = Path(f"/run/secrets/{secret_name}")
    if secret_path.exists():
        try:
            val = secret_path.read_text().strip()
            if val:
                return val
        except Exception:
            pass

    val = os.getenv(env_name, default)
    if not val:
        raise ValueError(f"Missing required configuration secret: {env_name}")
    return val.strip()


# Load sensitive credentials
OPENROUTER_API_KEY = get_secret("openrouter_key", "OPENROUTER_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENROUTER_API_KEY

ADMIN_USER = get_secret("admin_user", "ADMIN_USER", "admin")
ADMIN_PASS = get_secret("admin_pass", "ADMIN_PASS", "password")
DEMO_API_KEY = get_secret("demo_api_key", "DEMO_API_KEY", "demo123456")

BASE_DIR = Path(__file__).resolve().parent.parent
PERSIST_DIR = BASE_DIR / "storage"
DATA_DIR = BASE_DIR / "data"

# ==========================================
# 2. GLOBAL CHUNK & MODEL SETTINGS
# ==========================================
Settings.chunk_size = 256
Settings.chunk_overlap = 20

Settings.llm = OpenAILike(
    api_key=OPENROUTER_API_KEY,
    api_base="https://openrouter.ai/api/v1",
    model="openrouter/free",
    is_chat_model=True,
    default_headers={
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "PreDoc Chatbot",
    },
)

Settings.embed_model = OpenAILikeEmbedding(
    api_key=OPENROUTER_API_KEY,
    api_base="https://openrouter.ai/api/v1",
    model_name="liquid/lfm-2.5-embedding-350m:free",
)

# ==========================================
# 3. PROMPTS & METADATA
# ==========================================
def get_file_metadata(filename: str) -> dict:
    return {
        "category": Path(filename).stem,
        "source": "WHO / CDC Clinical Reference Data",
    }


system_msg = ChatMessage(
    role=MessageRole.SYSTEM,
    content=(
        "You are an expert Clinical Decision Support AI Assistant.\n"
        "Your goal is to provide precise, beautifully structured, and professional medical responses based *strictly* on the provided context.\n\n"
        "Formatting & Style Rules:\n"
        "1. Use clean Markdown formatting with professional headings (e.g., ### Clinical Summary, ### Key Symptoms, ### Urgent Red Flags).\n"
        "2. Structure symptoms using clean bullet points rather than cramped tables.\n"
        "3. Maintain an authoritative, objective, and clear clinical tone.\n\n"
        "Strict Guardrails:\n"
        "1. Base your answer EXCLUSIVELY on the provided context information below.\n"
        "2. If the answer cannot be found in the context, state: 'I cannot find relevant clinical data for this condition in my reference database.'\n"
        "3. Always conclude by clearly stating the Category and Source.\n"
        "4. Never invent, extrapolate, or hallucinate medical data."
    ),
)

user_msg_template = ChatMessage(
    role=MessageRole.USER,
    content=(
        "---------------------\n"
        "Context Information:\n"
        "{context_str}\n"
        "---------------------\n"
        "Query: {query_str}"
    ),
)

chat_qa_template = ChatPromptTemplate(message_templates=[system_msg, user_msg_template])

# ==========================================
# 4. LIFESPAN MANAGEMENT & INDEX BUILD
# ==========================================
app_state = {"query_engine": None, "startup_error": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages app startup/shutdown tasks safely without blocking global import state."""
    try:
        if PERSIST_DIR.exists() and any(PERSIST_DIR.iterdir()):
            print(f"Loading existing index from '{PERSIST_DIR}'...")
            storage_context = StorageContext.from_defaults(persist_dir=str(PERSIST_DIR))
            index = load_index_from_storage(storage_context)
        else:
            print(f"No existing index found. Processing documents from '{DATA_DIR}'...")
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            documents = SimpleDirectoryReader(
                str(DATA_DIR), file_metadata=get_file_metadata
            ).load_data()

            print("Indexing documents and generating embeddings...")
            index = VectorStoreIndex.from_documents(documents)
            PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            index.storage_context.persist(persist_dir=str(PERSIST_DIR))
            print(f"Index successfully created and saved to '{PERSIST_DIR}'!")

        app_state["query_engine"] = index.as_query_engine(
            text_qa_template=chat_qa_template, use_async=True
        )
    except Exception as e:
        app_state["startup_error"] = str(e)
        print(f"CRITICAL WARNING: Index engine initialization failed: {e}")

    yield
    app_state.clear()


# ==========================================
# 5. FASTAPI SETUP & SECURITY
# ==========================================
app = FastAPI(
    title="PreDoc-Chatbot API",
    description="Secure FastAPI backend for Healthcare RAG assistant.",
    version="1.0",
    lifespan=lifespan,
)

# FIXED: Replaced wildcard origin when allow_credentials=True to adhere to CORS spec
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

security_basic = HTTPBasic()
api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security_basic)) -> str:
    """Uses constant-time comparison to prevent timing attacks on basic auth."""
    correct_user = secrets.compare_digest(credentials.username, ADMIN_USER)
    correct_pass = secrets.compare_digest(credentials.password, ADMIN_PASS)

    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Uses constant-time comparison to prevent timing attacks on API key header."""
    if not secrets.compare_digest(api_key, DEMO_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate x-api-key credentials",
        )
    return api_key


# ==========================================
# 6. SCHEMAS & API ROUTES
# ==========================================
class QueryRequest(BaseModel):
    question: str = Field(
        ..., min_length=3, max_length=1000, example="What are the clinical signs of Dengue fever?"
    )


class QueryResponse(BaseModel):
    status: str
    authenticated_user: str
    answer: str


@app.get("/health", tags=["System"])
async def health_check():
    """Monitors engine operational status."""
    if app_state["query_engine"] is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Engine Unhealthy: {app_state['startup_error']}",
        )
    return {"status": "healthy"}


@app.get("/", tags=["Frontend"])
async def serve_frontend(user: str = Depends(verify_credentials)):
    html_path = BASE_DIR / "frontend" / "index.html"
    if not html_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Frontend file not found."
        )
    return FileResponse(html_path)


@app.post("/chat", response_model=QueryResponse, tags=["RAG Services"])
async def chat_endpoint(
    payload: QueryRequest,
    user: str = Depends(verify_credentials),
    _: str = Depends(verify_api_key),
):
    query_engine = app_state["query_engine"]
    if query_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chat engine failed to initialize: {app_state['startup_error']}",
        )

    try:
        # NON-BLOCKING: Asynchronous query engine execution
        response = await query_engine.aquery(payload.question)
        return QueryResponse(status="success", authenticated_user=user, answer=str(response))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution error: {str(e)}",
        )