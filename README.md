🤖 BGE-M3 Agentic RAG
A local Retrieval-Augmented Generation pipeline. Ingest PDFs into a vector store and chat with them using local AI models via Ollama.

🛠 Tech Stack
API: FastAPI

Vector DB: Qdrant (with FastEmbed)

Embeddings: BGE-Small/Large

LLM: Ollama (Llama 3.2 3B)

PDF Logic: PyMuPDF (fitz)

🚀 Initial Setup

1. Prerequisites
   Python 3.10+

Ollama installed and running.

Pull the Model:

Bash
ollama pull llama3.2 2. Install Dependencies
Bash

# Setup virtual environment

python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate

# Install requirements

pip install fastapi uvicorn qdrant-client pymupdf ollama python-dotenv 3. Environment Config (.env)
Create a .env file in the root directory:

Ini, TOML
QDRANT_HOST=./qdrant_db
QDRANT_PORT=6333
COLLECTION_NAME=agent_knowledge

EMBED_MODEL=BAAI/bge-small-en-v1.5
EMBED_MODEL_NAME=fast-bge-small-en-v1.5
CHAT_MODEL=llama3.2:3b
CONTEXT_WINDOW=4096

API_HOST=0.0.0.0
API_PORT=8000
🏃 How to Run
Run from the root folder:

Bash
python -m app.main
API: http://localhost:8000

Docs (Swagger): http://localhost:8000/docs

📡 API Endpoints
🟢 Ingest PDF (POST /v1/ingest/pdf)
JSON
{
"file_path": "C:/path/to/your/document.pdf",
"metadata": { "category": "manual" }
}
🔵 Agent Chat (POST /v1/agent/chat)
JSON
{
"question": "What does the document say about X?",
"history": []
}
📂 Project Structure
Plaintext
rag-agent/
├── app/
│ ├── main.py # FastAPI routes & Lifespan
│ ├── engine.py # RAG & LLM Logic
│ ├── database.py # Qdrant client & Init
│ ├── schemas.py # Pydantic models
│ └── **init**.py # Package marker
├── qdrant_db/ # Local vector storage
└── .env # App configuration
